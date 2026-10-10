"""Build the EXPLORATORY long-package diagnostic set (separate from the 48-case benchmark).

  python -m benchmarks.build_diagnostic

Reads private/diagnostic_source/long_cases.json ({"record": CaseRecord, "gold": GoldRecord} objects),
validates them, writes public packages to data/diagnostic/long.jsonl and gold to
private/gold/diagnostic_gold.jsonl, and records hashes in benchmarks/diagnostic_hashes.json.
This set never replaces or mixes with the 32-case primary TEST split.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from benchmarks.schema import GoldRecord
from benchmarks.validate import LEAK_PATTERNS, check_stat_test
from src.evidence_store import EvidenceStore
from src.package_schema import CaseRecord

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "private" / "diagnostic_source" / "long_cases.json"


def main() -> int:
    objs = json.loads(SRC.read_text())
    errs, pubs, golds = [], [], []
    for o in objs:
        rec = CaseRecord.model_validate(o["record"])
        g = GoldRecord.model_validate(o["gold"])
        if rec.split != "diagnostic" or not rec.case_id.startswith("LONG-") or g.case_id != rec.case_id:
            errs.append(f"{rec.case_id}: bad split/id")
        st = EvidenceStore.from_package(rec.package)
        ids = list(g.evidence_ids) + [i for f in g.required_findings for i in f.evidence_ids]
        errs += [f"{rec.case_id}: unknown evidence id {i}" for i in ids if not st.has(i)]
        for s in rec.package.statistical_tests:
            errs += check_stat_test(rec.case_id, s)
        vis = json.dumps(rec.package.model_dump(), ensure_ascii=False).lower()
        errs += [f"{rec.case_id}: rubric word {p}" for p in LEAK_PATTERNS if re.search(p, vis)]
        pubs.append(rec.model_dump())
        golds.append(g.model_dump())
    if len(objs) != 8:
        errs.append(f"expected 8 diagnostic cases, got {len(objs)}")
    if errs:
        print("\n".join(errs))
        return 1
    pub = ROOT / "data" / "diagnostic" / "long.jsonl"
    pub.parent.mkdir(parents=True, exist_ok=True)
    pub.write_text("".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n" for p in pubs))
    gp = ROOT / "private" / "gold" / "diagnostic_gold.jsonl"
    gp.write_text("".join(json.dumps(g, ensure_ascii=False, sort_keys=True) + "\n" for g in golds))
    h = {"public": hashlib.sha256(pub.read_bytes()).hexdigest(), "gold_PRIVATE": hashlib.sha256(gp.read_bytes()).hexdigest(),
         "source_PRIVATE": hashlib.sha256(SRC.read_bytes()).hexdigest()}
    (ROOT / "benchmarks" / "diagnostic_hashes.json").write_text(json.dumps(h, indent=1) + "\n")
    print(json.dumps(h, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
