"""OpenRouter-based JSON calls for Phase 4 authoring, validation and revision judging.

V1's judges ran through the Codex and Claude CLIs (`evaluation/judges.py`), which are not installed on this machine. The
same model families are reached through OpenRouter with V1's own `OpenRouterClient` and `CostGuard`. Spend goes on a
**separate V2 judge ledger** (`v2/outputs/judge_ledger.jsonl`), never on V1's ledger or the V2 experiment ledger.

* Every call is cached by sha256 of (model, settings, system, prompt), so a re-run never repeats a paid call. The raw
  record (response text, usage, cost, provider, timestamps; no key and no headers) is stored under
  `v2/outputs/judge_raw/<stage>/`.
* `parse_json` extracts the first JSON object from the reply. Callers validate it and may ask for one repair turn.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from src.cost_guard import CostGuard, Pricing, now_iso
from src.openrouter_client import BaseClient, OpenRouterClient

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "v2" / "outputs" / "judge_ledger.jsonl"
RAW_DIR = ROOT / "v2" / "outputs" / "judge_raw"
HARD_CAP_USD = 6.0
STAGE_CAPS = {"p4_author": 3.5, "p4_validate": 1.0, "p4_judge": 1.5}

AUTHOR_MODEL = "openai/gpt-5.6-sol"
VALIDATOR_MODEL = "anthropic/claude-sonnet-5.5"
JUDGE_A_MODEL = "openai/gpt-5.6-sol"
JUDGE_B_MODEL = "anthropic/claude-haiku-5.5"
# list prices per token (OpenRouter /models, 2026-10-25); used only for CostGuard reservations
PRICES = {AUTHOR_MODEL: (4e-6, 20e-6), VALIDATOR_MODEL: (2e-6, 10e-6), JUDGE_B_MODEL: (1e-7, 5e-7)}
DECODING = {AUTHOR_MODEL: {"reasoning": {"effort": "medium"}}, VALIDATOR_MODEL: {}, JUDGE_B_MODEL: {}}


@dataclass
class JsonCall:
    model: str
    stage: str
    item_key: str
    content: str
    cost_usd: float
    cached: bool
    raw_path: str


_clients: dict[str, BaseClient] = {}
_guard: Optional[CostGuard] = None


def guard() -> CostGuard:
    global _guard
    if _guard is None:
        _guard = CostGuard(ledger_path=LEDGER, hard_cap_usd=HARD_CAP_USD, stage_caps=dict(STAGE_CAPS),
                           pricing=Pricing(4e-6, 20e-6), max_inflight=2)
    return _guard


def client_for(model: str) -> BaseClient:
    if model not in _clients:
        c = OpenRouterClient(model, {"require_parameters": True}, DECODING.get(model, {}), guard(), timeout_s=600.0,
                             max_retries=2, app_title="DSA4213-project-v2-phase4")
        _clients[model] = c
    return _clients[model]


def set_client(model: str, client: BaseClient) -> None:
    """Inject a client (tests use MockClient)."""
    _clients[model] = client


def cache_key(model: str, system: str, prompt: str, extra: str = "") -> str:
    blob = json.dumps({"model": model, "decoding": DECODING.get(model, {}), "system": system, "prompt": prompt,
                       "extra": extra}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def call_json(model: str, stage: str, item_key: str, system: str, prompt: str, *, max_tokens: int,
              history: Optional[list[dict[str, Any]]] = None) -> JsonCall:
    """One chat call returning text (expected to contain one JSON object). Cached by input hash."""
    messages = [{"role": "system", "content": system}] + list(history or []) + [{"role": "user", "content": prompt}]
    key = cache_key(model, system, json.dumps(messages[1:], ensure_ascii=False))
    raw = RAW_DIR / stage / f"{key}.json"
    if raw.exists():
        rec = json.loads(raw.read_text(encoding="utf-8"))
        return JsonCall(model, stage, item_key, rec["content"], rec.get("cost_usd") or 0.0, True, str(raw))
    client = client_for(model)
    if isinstance(client, OpenRouterClient) and model in PRICES:
        client.guard.pricing = Pricing(*PRICES[model])
    res = client.chat(messages, role=f"v2_{stage}", ctx={"stage": stage, "case_id": item_key, "condition": None,
                                                         "run_tag": "phase4"},
                      max_tokens=max_tokens, response_format={"type": "json_object"})
    rec = {"model": model, "stage": stage, "item_key": item_key, "ts": now_iso(), "content": res.content,
           "finish_reason": res.finish_reason, "usage": res.usage, "cost_usd": res.cost_usd,
           "cost_source": res.cost_source, "provider": res.provider, "generation_id": res.generation_id,
           "latency_s": res.latency_s, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
           "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(), "is_mock": client.is_mock}
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    return JsonCall(model, stage, item_key, res.content, res.cost_usd or 0.0, False, str(raw))


def parse_json(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("no JSON object in reply")
    obj = json.loads(t[i:j + 1])
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON is not an object")
    return obj


def spent(stage: Optional[str] = None) -> float:
    return guard().spent(stage)


Repair = Callable[[str], str]
