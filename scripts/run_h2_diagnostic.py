"""EXPLORATORY H2 failure diagnostic: C4 (STRENGTHEN allowed) vs C5 (not allowed) on 12 injected DEV drafts.

  python scripts/run_h2_diagnostic.py            # runs once; refuses to run again under the same tag

Uses the frozen backbone/decoding/routing (configs/frozen_primary.yaml), the original evidence tools and the
original verifier budget (4 evidence-tool calls per claim). Only the starting draft is injected, from
data/diagnostic/h2_counterfactual_drafts.json. DEV cases only; nothing from the TEST split is read.
Design: docs/H2_DIAGNOSTIC.md. The OpenRouter key is read from the environment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import atomic_write_json  # noqa: E402
from src.conditions import CONDITIONS  # noqa: E402
from src.cost_guard import now_iso  # noqa: E402
from src.prompts import prompt_hashes  # noqa: E402
from src.runner import code_hash, git_commit, load_cases, load_config, make_client, make_guard, model_slug  # noqa: E402
from src.schemas import ClaimDraft, Draft  # noqa: E402
from src.verifier import verify_draft  # noqa: E402

RUN_TAG = "h2diag_v1"
CONFIG = ROOT / "configs" / "frozen_primary.yaml"


def main() -> int:
    cfg = load_config(CONFIG)
    drafts = json.loads((ROOT / "data" / "diagnostic" / "h2_counterfactual_drafts.json").read_text())
    cases = {c.case_id: c for c in load_cases(ROOT / "data" / "synthetic" / "dev.jsonl")}
    assert all(cases[d["case_id"]].split == "dev" for d in drafts), "DEV cases only"
    guard = make_guard(cfg)
    client = make_client(cfg, guard)
    out_root = ROOT / "outputs" / "h2_diagnostic" / model_slug(client.model_id)
    meta_path = out_root / f"run_meta_{RUN_TAG}.json"
    if meta_path.exists():
        print(f"{meta_path} exists: this diagnostic is run ONCE; refusing to run again.")
        return 2
    vcfg = cfg["verifier"]
    atomic_write_json(meta_path, {"run_tag": RUN_TAG, "started_at": now_iso(), "config": cfg, "config_file": str(CONFIG.name),
                                  "prompt_hashes": prompt_hashes(), "code_hash": code_hash(), "git_commit": git_commit(),
                                  "conditions": ["C4", "C5"], "draft_ids": [d["draft_id"] for d in drafts],
                                  "exploratory": True})
    for d in drafts:
        rec = cases[d["case_id"]]
        draft = Draft(sentences=[ClaimDraft(claim_id="s1", text=d["draft_text"], evidence_ids=d["writer_evidence_hints"])])
        for cond in ("C4", "C5"):
            cc = CONDITIONS[cond]
            v = cc.verifier_config(max_tool_calls=int(vcfg["max_tool_calls"]), max_claims=int(vcfg["max_claims"]))
            calls: list = []
            ctx = {"case_id": d["draft_id"], "condition": cond, "stage": "buffer", "run_tag": RUN_TAG}
            started = now_iso()
            final, traces = verify_draft(client, rec.package, draft, v, ctx, calls)
            atomic_write_json(out_root / cond / f"{d['draft_id']}.json", {
                "run_id": f"{RUN_TAG}:{cond}:{d['draft_id']}", "draft_id": d["draft_id"], "case_id": d["case_id"],
                "condition": cond, "can_strengthen": cc.can_strengthen, "verify_mode": cc.verify_mode,
                "started_at": started, "finished_at": now_iso(), "injected_draft": draft.model_dump(),
                "final_passage": final.passage, "final_sentences": [s.model_dump() for s in final.sentences],
                "claim_traces": [t.model_dump() for t in traces], "calls": [c.model_dump() for c in calls],
                "cost_usd": round(sum(c.cost_usd or 0 for c in calls), 8), "model_id": client.model_id,
                "code_hash": code_hash(), "is_mock": False})
            t = traces[0]
            print(f"{d['draft_id']:10s} {cond}: {t.decision.decision:10s} tools={[a.tool for a in t.actions]}")
    print("ledger:", json.dumps(guard.summary()["by_stage"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
