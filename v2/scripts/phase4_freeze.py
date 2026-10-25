"""Build and freeze the Phase 4 TEST set (design: v2/docs/PHASE4_DESIGN.md section 4).

  python v2/scripts/phase4_freeze.py --authored v2/private/phase4/authored/r1,v2/private/phase4/authored/r2 \
      --validation v2/private/phase4/validation/r2.json

The latest authored version of each pair is used. Items whose validation disagrees are dropped. Writes:
* public: v2/benchmarks/test_v2/cases.jsonl (V1 CaseRecord format, split "test") and items.json (draft sentences only,
  no expected decisions);
* private (gitignored): v2/private/phase4/gold.json (items + gold, in the probe format the analysis scripts read);
* v2/benchmarks/freeze_manifest.json: SHA-256 of the items, the gold and every file the TEST run and its scoring depend on.
Refuses to overwrite an existing manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.cost_guard import now_iso  # noqa: E402
from src.package_schema import CaseRecord  # noqa: E402
from src.runner import git_commit, git_dirty  # noqa: E402
from v2.benchmarks.phase4_checks import PAIR_SPEC  # noqa: E402

PUB = ROOT / "v2" / "benchmarks" / "test_v2"
PRIVATE = ROOT / "v2" / "private" / "phase4"
MANIFEST = ROOT / "v2" / "benchmarks" / "freeze_manifest.json"
FROZEN_FILES = [
    "v2/docs/PHASE4_DESIGN.md", "v2/benchmarks/phase4_pairs_spec.json", "v2/benchmarks/phase4_checks.py",
    "v2/prompts/phase4_author.md", "v2/prompts/phase4_validate.md",
    "v2/verifier_tools.py", "v2/verifier_oracle.py", "v2/prompts/verifier_oracle_d1_addendum.md",
    "v2/prompts/verifier_tools_d1_c5_addendum.md", "v2/scripts/run_e1_e2.py", "v2/scripts/analyze_e1_e2.py",
    "v2/scripts/phase4_judge.py", "v2/scripts/phase4_score.py", "v2/or_judge.py",
    "prompts/common_reporting.md", "prompts/verifier_adaptive.md", "src/verifier.py", "src/tools.py", "src/prompts.py",
    "annotation/ai_extended/prompts/verify.md", "annotation/ai_extended/prompts/adjudicate_claims.md",
    "annotation/ai_extended/prompts/system.md", "configs/frozen_primary.yaml",
]
ACCEPTABLE = {"STRENGTHEN": ["STRENGTHEN"], "ACCEPT": ["ACCEPT"], "WEAKEN": ["WEAKEN"],
              "REMOVE_OR_WEAKEN": ["REMOVE", "WEAKEN"]}
RELATION = {"STRENGTHEN": ["STRONGER_SUPPORTED"], "ACCEPT": ["MATCHES"], "WEAKEN": ["WEAKER_SUPPORTED"],
            "REMOVE_OR_WEAKEN": ["NOT_SUPPORTED", "WEAKER_SUPPORTED"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authored", required=True, help="comma-separated authored dirs, oldest first")
    ap.add_argument("--validation", required=True)
    a = ap.parse_args(argv)
    if MANIFEST.exists():
        raise SystemExit(f"{MANIFEST} exists: the Phase 4 TEST set is already frozen")
    pairs: dict[str, dict] = {}
    for d in a.authored.split(","):
        for f in sorted(Path(d).glob("P*.json")):
            rec = json.loads(f.read_text(encoding="utf-8"))
            if not rec["errors"] and rec["pair"] is not None:
                pairs[rec["pair_id"]] = rec["pair"]
    val = json.loads(Path(a.validation).read_text(encoding="utf-8"))
    kept = [x for x in val["items"] if x["agree"] and x["pair_id"] in pairs]
    dropped = [x for x in val["items"] if not x["agree"]]
    PUB.mkdir(parents=True, exist_ok=True)
    cases = []
    for pid, pair in sorted(pairs.items()):
        for member in ("strong", "partner"):
            cases.append(CaseRecord(case_id=f"T4-{pid}-{member}", category=None, split="test", pair_id=f"T4-{pid}",
                                    package=pair[f"{member}_package"],
                                    source_manifest={"origin": "synthetic_original",
                                                     "notes": "V2 Phase 4 held-out item; authored by GPT-5.6, validated "
                                                              "by Claude Sonnet 5.5 (see v2/docs/PHASE4_DESIGN.md)"}))
    with open(PUB / "cases.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for c in cases:
            f.write(c.model_dump_json() + "\n")
    public, gold = [], []
    # A U/U2 draft uses a pattern "new relative to DEV" if it contains none of the hedge/weakening markers used in the
    # DEV probes' U/U2 drafts (v2/data/dev_probes_batch1.json). Decided from the final text, because validation-driven
    # revisions changed some wording.
    dev_markers = ("appears", "slightly", "most of", "generally", " may ", "suggest", "somewhat", "higher mean")
    for x in kept:
        pair = pairs[x["pair_id"]]
        d = next(d for d in pair["drafts"] if d["key"] == x["key"])
        probe = {"probe_id": f"T4-{x['item_id']}", "case_id": f"T4-{x['pair_id']}-{x['member']}",
                 "draft_text": d["text"], "writer_evidence_hints": d.get("writer_evidence_hints", [])}
        public.append(probe)
        exp = x["expected"]
        gold.append({**probe, "pair": x["pair_id"], "draft_key": x["key"], "member": x["member"],
                     "case_gold_level": x["member_level"], "draft_expressed_level": x["draft_level"],
                     "expected_decision": "REMOVE" if exp == "REMOVE_OR_WEAKEN" else exp,
                     "acceptable_decisions": ACCEPTABLE[exp], "expected_support_relation": RELATION[exp],
                     "target_level_after_edit": x["member_level"] if exp != "ACCEPT" else None,
                     "decisive_evidence_ids": pair["decisive_evidence_ids"] if exp == "STRENGTHEN" else [],
                     "decisive_fact": pair["pair_contrast"] if exp == "STRENGTHEN" else None,
                     "subgroup": "claim_strength", "borderline": None, "pattern": d.get("pattern"),
                     "pattern_new_vs_dev": x["key"] in ("U", "U2") and not any(
                         m in f" {d['text'].lower()} " for m in dev_markers),
                     "needs_test": PAIR_SPEC[x["pair_id"]]["needs_test"],
                     "validator_label": x["validator_label"]})
    (PUB / "items.json").write_text(json.dumps({"description": "Phase 4 TEST items (draft sentences only; gold is "
                                                "private until scoring).", "probes": public}, ensure_ascii=False,
                                               indent=1), encoding="utf-8", newline="\n")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "gold.json").write_text(json.dumps({"probes": gold}, ensure_ascii=False, indent=1), encoding="utf-8",
                                       newline="\n")
    comp = {"pairs": len(pairs), "items": len(gold), "dropped": len(dropped),
            "expected": dict(Counter(g["expected_decision"] for g in gold)),
            "pattern_new_U_U2": sum(1 for g in gold if g["draft_key"] in ("U", "U2") and g["pattern_new_vs_dev"]
                                    and g["member"] == "strong"),
            "no_test_needed_STRENGTHEN": sum(1 for g in gold if g["expected_decision"] == "STRENGTHEN"
                                             and not g["needs_test"])}
    manifest = {"frozen_at": now_iso(), "git_commit": git_commit(), "git_dirty": git_dirty(), "composition": comp,
                "dropped_items": [x["item_id"] for x in dropped],
                "public": {"v2/benchmarks/test_v2/cases.jsonl": sha(PUB / "cases.jsonl"),
                           "v2/benchmarks/test_v2/items.json": sha(PUB / "items.json")},
                "gold_sha256": sha(PRIVATE / "gold.json"),
                "validation": {"file": Path(a.validation).name, "sha256": sha(Path(a.validation)),
                               "n_items": val["n_items"], "n_agree": val["n_agree"]},
                "files": {f: sha(ROOT / f) for f in FROZEN_FILES}}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(comp, indent=1))
    print(f"frozen -> {MANIFEST}")
    return 0


def check(argv: list[str] | None = None) -> int:
    """Verify that nothing frozen has changed (run before TEST inference and before scoring)."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = [f for f, h in {**m["public"], **m["files"]}.items() if sha(ROOT / f) != h]
    g = PRIVATE / "gold.json"
    if g.exists() and sha(g) != m["gold_sha256"]:
        bad.append("v2/private/phase4/gold.json")
    print("freeze check:", "OK" if not bad else f"CHANGED {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else main())
