"""Run V2 experiments E1/E2 on the DEV decision probes (design: v2/docs/E1_E2_DESIGN.md).

  # offline dry run with the deterministic mock (free; written to v2/outputs/_mock/)
  python v2/scripts/run_e1_e2.py --run-tag mock_demo --mock
  # paid run (needs OPENROUTER_API_KEY in the environment and the explicit --real flag)
  python v2/scripts/run_e1_e2.py --run-tag e1e2_v1 --real

Conditions: D0-tools (V1 adaptive verifier, unchanged code, C4 settings), D0-oracle, D1-oracle, D2-oracle, and
D1c-oracle (E2b); for E5, D0-tools-800 (V1 code at 800 tokens/turn) and D1-tools (V1 loop ported with the D1 prompt
addendum and schema, 800 tokens/turn). Select non-default conditions with --conditions.
Backbone, decoding and routing come from configs/frozen_primary.yaml. Spend is guarded by V1's CostGuard on a separate
V2 ledger (v2/outputs/cost_ledger.jsonl) with a hard cap. Re-running the same command resumes: finished jobs are skipped,
and a run directory created under different code or prompts is refused.
On Windows, put v2/compat_win on PYTHONPATH (see v2/README.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agent import atomic_write_json  # noqa: E402
from src.conditions import CONDITIONS  # noqa: E402
from src.cost_guard import BudgetExceeded, CostGuard, Pricing, now_iso  # noqa: E402
from src.openrouter_client import FatalAPIError, MockClient, TransientAPIError  # noqa: E402
from src.prompts import prompt_hashes as v1_prompt_hashes  # noqa: E402
from src.runner import code_hash as v1_code_hash, git_commit, git_dirty, load_cases, load_config, make_client  # noqa: E402
from src.schemas import ClaimDraft, Draft  # noqa: E402
from src.verifier import VerifierConfig, verify_draft  # noqa: E402
from v2.mock_responder import oracle_mock_responder  # noqa: E402
from v2.verifier_oracle import v2_prompt_hashes, verify_claim_oracle  # noqa: E402
from v2.verifier_tools import verify_draft_tools  # noqa: E402

CONFIG = ROOT / "configs" / "frozen_primary.yaml"
DEFAULT_PROBES = ROOT / "v2" / "data" / "dev_probes_batch1.json"
ALL_CONDITIONS = ("D0-tools", "D0-oracle", "D1-oracle", "D2-oracle", "D1c-oracle", "D0-tools-800", "D1-tools")
E1E2_CONDITIONS = ALL_CONDITIONS[:4]  # default = the original E1/E2 design
# E5: both tool-loop conditions use 800 tokens per turn (V1 used 450), so the decision frameworks are compared fairly.
E5_TOOL_CFG = VerifierConfig(mode="adaptive", can_strengthen=True, max_tool_calls=4, max_claims=6, max_tokens_per_turn=800)
STAGE = "v2_e1e2"
HARD_CAP_USD = 1.00
V2_LEDGER = ROOT / "v2" / "outputs" / "cost_ledger.jsonl"


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def v2_code_hash() -> str:
    h = hashlib.sha256()
    files = sorted((ROOT / "v2").glob("*.py")) + sorted((ROOT / "v2" / "scripts").glob("*.py")) + \
        sorted((ROOT / "v2" / "prompts").glob("*.md"))
    for f in files:
        h.update(f.relative_to(ROOT).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def make_v2_guard(cfg: dict[str, Any]) -> CostGuard:
    pr = cfg["model"]["pricing"]
    return CostGuard(ledger_path=V2_LEDGER, hard_cap_usd=HARD_CAP_USD, stage_caps={STAGE: HARD_CAP_USD},
                     pricing=Pricing(pr["prompt_per_mtok"] / 1e6, pr["completion_per_mtok"] / 1e6),
                     max_inflight=int(cfg["budget"].get("max_inflight", 2)))


def probe_draft(p: dict[str, Any]) -> Draft:
    return Draft(sentences=[ClaimDraft(claim_id="s1", text=p["draft_text"], evidence_ids=p["writer_evidence_hints"])])


def run_job(client, cases, p: dict[str, Any], cond: str, rep: int, run_tag: str) -> dict[str, Any]:
    rec = cases[p["case_id"]]
    draft = probe_draft(p)
    ctx = {"case_id": p["probe_id"], "condition": cond, "stage": STAGE, "run_tag": run_tag}
    started = now_iso()
    out: dict[str, Any] = {"run_id": f"{run_tag}:{cond}:{p['probe_id']}:r{rep}", "probe_id": p["probe_id"],
                           "case_id": p["case_id"], "condition": cond, "repeat": rep, "draft_text": p["draft_text"],
                           "model_id": client.model_id, "is_mock": client.is_mock, "started_at": started}
    if cond == "D0-tools":
        c4 = CONDITIONS["C4"]
        vcfg = c4.verifier_config(max_tool_calls=4, max_claims=6)
        calls: list = []
        _, traces = verify_draft(client, rec.package, draft, vcfg, ctx, calls)
        t = traces[0]
        d = t.decision
        out.update(decision=d.decision, revised_text=d.revised_text, rationale=d.rationale, evidence_ids=d.evidence_ids,
                   valid=d.valid, validation_notes=d.validation_notes, judgement={},
                   tools=[{"tool": a.tool, "args": a.args} for a in t.actions],
                   returned_ids=sorted({i for o in t.observations for i in o.returned_ids}),
                   trace=t.model_dump(), calls=[c.model_dump() for c in calls])
    elif cond in ("D0-tools-800", "D1-tools"):
        calls = []
        if cond == "D0-tools-800":  # V1's own code, unchanged, at 800 tokens per turn
            _, traces = verify_draft(client, rec.package, draft, E5_TOOL_CFG, ctx, calls)
            judgements = [{}]
        else:  # V2 port of the V1 loop with the D1 prompt addendum and schema
            _, traces, judgements = verify_draft_tools(client, rec.package, draft, E5_TOOL_CFG, "D1", ctx, calls)
        t = traces[0]
        d = t.decision
        out.update(decision=d.decision, revised_text=d.revised_text, rationale=d.rationale, evidence_ids=d.evidence_ids,
                   valid=d.valid, validation_notes=d.validation_notes, judgement=judgements[0],
                   tools=[{"tool": a.tool, "args": a.args} for a in t.actions],
                   returned_ids=sorted({i for o in t.observations for i in o.returned_ids}),
                   max_tokens_per_turn=E5_TOOL_CFG.max_tokens_per_turn,
                   trace=t.model_dump(), calls=[c.model_dump() for c in calls])
    else:
        variant = cond.split("-")[0]
        r = verify_claim_oracle(client, rec.package, draft, 0, variant, ctx, can_strengthen=True)
        d = r.decision
        out.update(decision=d.decision, revised_text=d.revised_text, rationale=d.rationale, evidence_ids=d.evidence_ids,
                   valid=d.valid, validation_notes=d.validation_notes, judgement=r.judgement,
                   raw_arguments=r.raw_arguments, protocol_errors=r.protocol_errors, model_calls=r.model_calls,
                   calls=[c.model_dump() for c in r.calls])
    out["cost_usd"] = round(sum((c.get("cost_usd") or 0) for c in out["calls"]), 8)
    out["prompt_tokens"] = sum((c.get("prompt_tokens") or 0) for c in out["calls"])
    out["completion_tokens"] = sum((c.get("completion_tokens") or 0) for c in out["calls"])
    out["finished_at"] = now_iso()
    out["status"] = "completed"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-tag", required=True)
    ap.add_argument("--probes", default=str(DEFAULT_PROBES))
    ap.add_argument("--conditions", default=",".join(E1E2_CONDITIONS))
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--probe-ids", default="", help="comma-separated subset (default: all)")
    ap.add_argument("--workers", type=int, default=2)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="offline deterministic mock (free)")
    mode.add_argument("--real", action="store_true", help="paid OpenRouter calls")
    ap.add_argument("--out-root", default="", help="override output root (tests)")
    a = ap.parse_args(argv)

    conds = [c.strip() for c in a.conditions.split(",") if c.strip()]
    bad = [c for c in conds if c not in ALL_CONDITIONS]
    if bad:
        ap.error(f"unknown conditions {bad}")
    probes_path = Path(a.probes)
    probes = json.loads(probes_path.read_text(encoding="utf-8"))["probes"]
    if a.probe_ids:
        keep = set(a.probe_ids.split(","))
        probes = [p for p in probes if p["probe_id"] in keep]
    cases = {c.case_id: c for c in load_cases(ROOT / "data" / "synthetic" / "dev.jsonl")}
    if any(cases[p["case_id"]].split != "dev" for p in probes):
        raise SystemExit("DEV cases only")

    cfg = load_config(CONFIG)
    if a.mock:
        client = MockClient(oracle_mock_responder, model_id="mock/" + cfg["model"]["id"])
        default_root = ROOT / "v2" / "outputs" / "_mock" / a.run_tag
    else:
        client = make_client(cfg, make_v2_guard(cfg))
        default_root = ROOT / "v2" / "outputs" / "e1e2" / a.run_tag
    out_root = Path(a.out_root) if a.out_root else default_root

    meta = {"run_tag": a.run_tag, "design": "v2/docs/E1_E2_DESIGN.md", "exploratory": True, "dev_only": True,
            "config_file": CONFIG.name, "model": cfg["model"], "is_mock": client.is_mock,
            "v1_prompt_hashes": v1_prompt_hashes(), "v2_prompt_hashes": v2_prompt_hashes(),
            "v1_code_hash": v1_code_hash(), "v2_code_hash": v2_code_hash(),
            "probes_file": probes_path.name, "probes_sha256": sha_file(probes_path),
            "hard_cap_usd": HARD_CAP_USD, "stage": STAGE}
    meta_path = out_root / "run_meta.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        keys = ("v1_prompt_hashes", "v2_prompt_hashes", "v1_code_hash", "v2_code_hash", "probes_sha256", "is_mock")
        diff = [k for k in keys if old.get(k) != meta[k]]
        if diff:
            raise SystemExit(f"{out_root} was created under different {diff}; use a new --run-tag")
    else:
        atomic_write_json(meta_path, {**meta, "started_at": now_iso(), "git_commit": git_commit(),
                                      "git_dirty": git_dirty(), "conditions": conds, "repeats": a.repeats})

    jobs = [(p, c, r) for r in range(1, a.repeats + 1) for p in probes for c in conds
            if not (out_root / c / f"{p['probe_id']}__r{r}.json").exists()]
    print(f"{len(jobs)} jobs to run -> {out_root}")
    lock = threading.Lock()
    done = {"n": 0}
    stop = threading.Event()

    def work(job):
        p, c, r = job
        if stop.is_set():
            return
        try:
            res = run_job(client, cases, p, c, r, a.run_tag)
        except (BudgetExceeded, FatalAPIError) as e:
            stop.set()
            raise SystemExit(f"stopping: {type(e).__name__}: {e}")
        except TransientAPIError as e:
            res = {"run_id": f"{a.run_tag}:{c}:{p['probe_id']}:r{r}", "probe_id": p["probe_id"], "condition": c,
                   "repeat": r, "status": "failed", "failure": str(e)}
            atomic_write_json(out_root / "_failed" / c / f"{p['probe_id']}__r{r}.json", res)
            return
        atomic_write_json(out_root / c / f"{p['probe_id']}__r{r}.json", res)
        with lock:
            done["n"] += 1
            print(f"[{done['n']}/{len(jobs)}] {c:10s} {p['probe_id']:22s} r{r}: {res['decision']}")

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for f in as_completed(futs):
            f.result()
    if not client.is_mock:
        print("V2 ledger by stage:", json.dumps(client.guard.summary().get("by_stage", {})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
