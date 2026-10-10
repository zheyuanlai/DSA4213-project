"""Summarize the cost ledger and reconcile it with OpenRouter's key usage counter (free endpoint).

  python scripts/summarize_ledger.py              # ledger only
  python scripts/summarize_ledger.py --reconcile  # also GET /api/v1/key (needs OPENROUTER_API_KEY in env)
Writes outputs/ledger_summary.json (secret-free).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cost_guard import now_iso  # noqa: E402

START_USAGE_USD = 0.0  # GET /api/v1/key at execution start (2026-10-10 10:13 UTC): usage 0, limit 15, limit_remaining 15


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reconcile", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "outputs" / "cost_ledger.jsonl").read_text().splitlines() if l.strip()]
    by_stage, by_tag, by_source = defaultdict(float), defaultdict(float), defaultdict(float)
    providers, statuses, calls_by_tag = Counter(), Counter(), Counter()
    tokens = defaultdict(int)
    for r in rows:
        c = float(r.get("cost_usd") or 0)
        by_stage[r.get("stage")] += c
        by_tag[r.get("run_tag") or "(none)"] += c
        by_source[r.get("cost_source")] += c
        statuses[r.get("status")] += 1
        calls_by_tag[r.get("run_tag") or "(none)"] += 1
        if r.get("status") == "ok":
            providers[r.get("provider")] += 1
            for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                tokens[k] += int(r.get(k) or 0)
    out = {
        "generated_at": now_iso(), "n_ledger_entries": len(rows), "status_counts": dict(statuses),
        "total_usd": round(sum(by_stage.values()), 6),
        "by_stage_usd": {k: round(v, 6) for k, v in sorted(by_stage.items(), key=lambda x: str(x[0]))},
        "by_run_tag_usd": {k: round(v, 6) for k, v in sorted(by_tag.items())},
        "calls_by_run_tag": dict(sorted(calls_by_tag.items())),
        "by_cost_source_usd": {k: round(v, 6) for k, v in by_source.items()},
        "provider_counts_ok_calls": dict(providers), "tokens_ok_calls": dict(tokens),
        "hard_cap_usd": 12.0, "start_key_usage_usd": START_USAGE_USD,
    }
    if a.reconcile:
        import httpx

        r = httpx.get("https://openrouter.ai/api/v1/key",
                      headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=20)
        d = r.json().get("data", {}) if r.status_code == 200 else {}
        out["key_check"] = {"checked_at": now_iso(), "http_status": r.status_code, "limit": d.get("limit"),
                            "limit_remaining": d.get("limit_remaining"), "usage": d.get("usage"),
                            "usage_daily": d.get("usage_daily")}
        if d.get("usage") is not None:
            out["key_usage_delta_since_start_usd"] = round(float(d["usage"]) - START_USAGE_USD, 6)
            out["ledger_minus_key_delta_usd"] = round(out["total_usd"] - out["key_usage_delta_since_start_usd"], 6)
    (ROOT / "outputs" / "ledger_summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
