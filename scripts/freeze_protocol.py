"""Freeze the primary protocol BEFORE any TEST-split call, and audit that TEST was never touched.

  python scripts/freeze_protocol.py --config configs/frozen_primary.yaml          # write freeze manifest
  python scripts/freeze_protocol.py --config configs/frozen_primary.yaml --check  # verify nothing changed

The manifest records sha256 of: frozen config, every prompt file, src/*.py, the public benchmark
files, the DEV gold, and the (private) TEST gold/source hashes from benchmarks/build_hashes.json,
plus the git commit. It also records an audit showing that no ledger entry or output file
references a TEST case_id before the freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cost_guard import now_iso  # noqa: E402
from src.prompts import PROMPT_FILES  # noqa: E402
from src.runner import code_hash, git_commit, git_dirty, load_cases  # noqa: E402

MANIFEST = ROOT / "benchmarks" / "freeze_manifest.json"


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tracked_hashes(config: Path) -> dict[str, str]:
    files = [config, ROOT / "data/synthetic/dev.jsonl", ROOT / "data/synthetic/test.jsonl",
             ROOT / "data/synthetic/gold/dev_gold.jsonl", ROOT / "data/synthetic/rubrics/dev_rubric.jsonl",
             ROOT / "data/synthetic/rubrics/test_rubric.jsonl", ROOT / "docs/BENCHMARK_SPEC.md",
             ROOT / "annotation/ANNOTATION_GUIDE.md", ROOT / "evaluation/auto_metrics.py",
             ROOT / "evaluation/score_human.py", ROOT / "evaluation/paired_bootstrap.py"]
    files += [ROOT / "prompts" / f for f in PROMPT_FILES]
    files += sorted((ROOT / "src").glob("*.py"))
    return {str(f.relative_to(ROOT)): sha_file(f) for f in files}


def test_leakage_audit() -> dict:
    test_ids = {c.case_id for c in load_cases(ROOT / "data/synthetic/test.jsonl")}
    ledger = ROOT / "outputs" / "cost_ledger.jsonl"
    hits = []
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                if e.get("case_id") in test_ids:
                    hits.append({"call_id": e.get("call_id"), "stage": e.get("stage"), "ts": e.get("ts")})
    out_hits = []
    for p in (ROOT / "outputs").rglob("*.json"):
        if "_mock" in p.parts:
            continue
        if p.stem in test_ids or (p.parent.name in test_ids):
            out_hits.append(str(p.relative_to(ROOT)))
    return {"checked_at": now_iso(), "n_test_case_ids": len(test_ids), "ledger_entries_with_test_case_ids": hits,
            "output_files_for_test_case_ids": sorted(out_hits),
            "clean": not hits and not out_hits}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/frozen_primary.yaml"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cfg = Path(a.config) if Path(a.config).is_absolute() else (ROOT / a.config).resolve()
    if a.check:
        m = json.loads(MANIFEST.read_text())
        now = tracked_hashes(cfg)
        changed = sorted(k for k in m["file_sha256"] if m["file_sha256"][k] != now.get(k))
        print(json.dumps({"frozen_at": m["frozen_at"], "frozen_commit": m["git_commit"], "changed_since_freeze": changed}, indent=1))
        return 1 if changed else 0
    audit = test_leakage_audit()
    if not audit["clean"]:
        print(json.dumps(audit, indent=1))
        print("REFUSING TO FREEZE: TEST case ids already appear in ledger/outputs")
        return 2
    build = json.loads((ROOT / "benchmarks" / "build_hashes.json").read_text())
    manifest = {
        "frozen_at": now_iso(), "git_commit": git_commit(), "git_dirty_src_prompts_configs": git_dirty(),
        "code_hash": code_hash(), "config": str(cfg.relative_to(ROOT)), "file_sha256": tracked_hashes(cfg),
        "benchmark_build_hashes": build, "test_leakage_audit_before_freeze": audit,
        "note": "TEST gold sha256 is recorded (gold_test_PRIVATE); the file itself stays coordinator-private until annotation ends.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"freeze manifest written: {MANIFEST} (commit {manifest['git_commit']}, dirty={manifest['git_dirty_src_prompts_configs']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
