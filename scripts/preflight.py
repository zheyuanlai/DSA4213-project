"""Preflight: key limits (free endpoint), model metadata snapshot, and tiny paid compatibility probes.

Usage (key must be in the environment; never pass it on the command line):
  python scripts/preflight.py --key-only
  python scripts/preflight.py --probe deepseek/deepseek-v4-flash-0731 [--reasoning off|default]
Writes secret-free JSON to outputs/preflight/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cost_guard import CostGuard, Pricing, now_iso  # noqa: E402
from src.openrouter_client import OpenRouterClient  # noqa: E402
from src.tools import TOOL_SCHEMAS, submit_decision_schema  # noqa: E402
from src.writer import PASSAGE_SCHEMA, parse_json_object, response_format  # noqa: E402

OUT = ROOT / "outputs" / "preflight"
SAFE_KEY_FIELDS = ["limit", "limit_remaining", "limit_reset", "usage", "usage_daily", "usage_weekly",
                   "usage_monthly", "is_free_tier", "is_provisioning_key"]  # 'label' omitted: contains key fragments


def key_status() -> dict:
    r = httpx.get("https://openrouter.ai/api/v1/key",
                  headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=20)
    d = r.json().get("data", {}) if r.status_code == 200 else {}
    out = {"checked_at": now_iso(), "http_status": r.status_code, **{k: d.get(k) for k in SAFE_KEY_FIELDS}}
    c = httpx.get("https://openrouter.ai/api/v1/credits",
                  headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=20)
    out["credits_endpoint_http_status"] = c.status_code
    out["credits_endpoint_note"] = "requires a management key" if c.status_code == 403 else ""
    return out


def model_metadata(model_ids: list[str]) -> dict:
    out = {"fetched_at": now_iso(), "models": {}}
    for mid in model_ids:
        r = httpx.get(f"https://openrouter.ai/api/v1/models/{mid}/endpoints", timeout=30)
        if r.status_code != 200:
            out["models"][mid] = {"error": r.status_code}
            continue
        eps = []
        for e in r.json()["data"]["endpoints"]:
            eps.append({k: e.get(k) for k in ("provider_name", "tag", "quantization", "context_length",
                                               "max_completion_tokens", "status", "supported_parameters")}
                       | {"pricing": e.get("pricing")})
        out["models"][mid] = {"endpoints": eps}
    return out


def probe(model_id: str, reasoning: str, stage: str = "preflight") -> dict:
    mcfg = yaml.safe_load((ROOT / "configs" / "model.yaml").read_text())["candidates"][model_id]
    b = yaml.safe_load((ROOT / "configs" / "budget.yaml").read_text())
    pr = mcfg["pricing"]
    guard = CostGuard(ROOT / "outputs" / "cost_ledger.jsonl", b["hard_cap_usd"], b["stage_caps"],
                      Pricing(pr["prompt_per_mtok"] / 1e6, pr["completion_per_mtok"] / 1e6), max_inflight=1)
    decoding = {"temperature": 0}
    if reasoning == "off":
        decoding["reasoning"] = {"enabled": False}
    client = OpenRouterClient(model_id, mcfg["provider_routing"], decoding, guard, timeout_s=90, max_retries=3)
    ctx = {"case_id": "preflight", "condition": "probe", "stage": stage, "run_tag": f"preflight_{reasoning}"}
    res: dict = {"model_id": model_id, "reasoning": reasoning, "provider_routing": mcfg["provider_routing"], "probes": {}}

    def rec(name, r, ok, note=""):
        res["probes"][name] = {"ok": ok, "note": note, "provider": r.provider if r else None,
                               "finish_reason": r.finish_reason if r else None,
                               "prompt_tokens": r.prompt_tokens if r else None,
                               "completion_tokens": r.completion_tokens if r else None,
                               "reasoning_tokens": r.reasoning_tokens if r else None,
                               "cost_usd": r.cost_usd if r else None, "cost_source": r.cost_source if r else None,
                               "latency_s": r.latency_s if r else None}

    # 1. health
    try:
        r = client.chat([{"role": "user", "content": "Reply with the single word OK."}], role="probe_health",
                        ctx=ctx, max_tokens=200)
        rec("health", r, "ok" in r.content.lower(), r.content[:40])
    except Exception as e:
        res["probes"]["health"] = {"ok": False, "note": f"{type(e).__name__}: {e}"[:300]}
        return res
    # 2. JSON schema output
    try:
        r = client.chat([{"role": "system", "content": "Output only JSON."},
                         {"role": "user", "content": "Write two sentences about a method TALON scoring 83.2 vs a baseline 82.6 "
                          "exact match, as {\"sentences\":[{\"text\":...,\"evidence_ids\":[...]}]}; evidence ids T1.r1.em and T1.r2.em."}],
                        role="probe_json", ctx=ctx, max_tokens=400, response_format=response_format("passage", PASSAGE_SCHEMA))
        obj = parse_json_object(r.content)
        rec("json_schema", r, isinstance(obj.get("sentences"), list), r.content[:200])
    except Exception as e:
        res["probes"]["json_schema"] = {"ok": False, "note": f"{type(e).__name__}: {e}"[:300]}
    # 3. forced named tool + multi-turn tool protocol + required tool choice
    tools = [TOOL_SCHEMAS[t] for t in TOOL_SCHEMAS] + [submit_decision_schema(["ACCEPT", "WEAKEN", "REMOVE", "FLAG"])]
    msgs = [{"role": "system", "content": "You verify a claim using tools."},
            {"role": "user", "content": "Claim: 'TALON significantly outperforms GridLM (83.2 vs 82.6).' Tables: T1 rows r1=TALON, r2=GridLM, column em. Comparison exp1/cmp1 = TALON vs GridLM."}]
    try:
        r = client.chat(msgs, role="probe_tool_forced", ctx=ctx, max_tokens=300, tools=tools,
                        tool_choice={"type": "function", "function": {"name": "lookup_table"}})
        ok = bool(r.tool_calls) and r.tool_calls[0].name == "lookup_table" and r.tool_calls[0].arguments is not None
        rec("tool_forced_named", r, ok, json.dumps([(t.name, t.arguments_raw) for t in r.tool_calls])[:200])
        if ok:
            msgs.append(r.assistant_message)
            msgs.append({"role": "tool", "tool_call_id": r.tool_calls[0].id, "content": json.dumps(
                {"status": "FOUND", "citable_ids": ["T1", "T1.r1.em", "T1.r2.em"],
                 "data": {"cells": [{"evidence_id": "T1.r1.em", "text": "83.2"}, {"evidence_id": "T1.r2.em", "text": "82.6"}]}})})
            r2 = client.chat(msgs, role="probe_tool_required", ctx=ctx, max_tokens=300, tools=tools, tool_choice="required")
            ok2 = bool(r2.tool_calls) and all(t.arguments is not None for t in r2.tool_calls)
            rec("tool_required_multiturn", r2, ok2, json.dumps([(t.name, t.arguments_raw) for t in r2.tool_calls])[:300])
            if ok2:
                msgs.append(r2.assistant_message)
                for t in r2.tool_calls:
                    msgs.append({"role": "tool", "tool_call_id": t.id, "content": json.dumps(
                        {"status": "NOT_FOUND", "citable_ids": ["absent:test:exp1/cmp1"],
                         "message": "No statistical test is reported for this comparison."})})
                r3 = client.chat(msgs, role="probe_submit_forced", ctx=ctx, max_tokens=400, tools=tools,
                                 tool_choice={"type": "function", "function": {"name": "submit_decision"}})
                ok3 = bool(r3.tool_calls) and r3.tool_calls[0].name == "submit_decision" and r3.tool_calls[0].arguments is not None
                rec("submit_forced", r3, ok3, json.dumps([(t.name, t.arguments_raw) for t in r3.tool_calls])[:400])
    except Exception as e:
        res["probes"]["tools"] = {"ok": False, "note": f"{type(e).__name__}: {e}"[:300]}
    res["ledger_after"] = guard.summary()
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-only", action="store_true")
    ap.add_argument("--probe", default=None)
    ap.add_argument("--reasoning", default="off", choices=["off", "default"])
    a = ap.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    ks = key_status()
    (OUT / f"key_status_{int(time.time())}.json").write_text(json.dumps(ks, indent=1))
    print("key:", json.dumps(ks))
    if a.key_only:
        meta = model_metadata(list(yaml.safe_load((ROOT / "configs" / "model.yaml").read_text())["candidates"]))
        (OUT / "model_metadata_snapshot.json").write_text(json.dumps(meta, indent=1))
        print("metadata snapshot saved")
        return 0
    if a.probe:
        res = probe(a.probe, a.reasoning)
        name = a.probe.replace("/", "__") + f"_{a.reasoning}.json"
        (OUT / f"probe_{name}").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
