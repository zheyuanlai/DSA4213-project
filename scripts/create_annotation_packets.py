"""Build blinded annotation packets + private condition mapping, then verify integrity.

  python scripts/create_annotation_packets.py --kind synthetic \
      --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 --cases data/synthetic/test.jsonl
  python scripts/create_annotation_packets.py --kind real \
      --runs outputs/real_papers/deepseek__deepseek-v4-flash-0731 --cases data/real_papers/packages

Writes annotator-facing files to annotation/ and the mapping to private/ (gitignored). Refuses to
finish if the integrity checks fail or the mapping would not be gitignored.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.blinding import build_real_packet, build_synthetic_packet, verify_packet  # noqa: E402
from src.conditions import ALL_CONDITIONS, REAL_PAPER_CONDITIONS  # noqa: E402
from src.runner import load_cases  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["synthetic", "real"], required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--rubrics", default="data/synthetic/rubrics/test_rubric.jsonl")
    ap.add_argument("--annotation-dir", default="annotation")
    ap.add_argument("--private-dir", default="private")
    a = ap.parse_args()
    runs, ann, priv = ROOT / a.runs, ROOT / a.annotation_dir, ROOT / a.private_dir
    cases = load_cases(ROOT / a.cases)
    if a.kind == "synthetic":
        rub = {json.loads(l)["case_id"]: json.loads(l) for l in (ROOT / a.rubrics).read_text().splitlines() if l.strip()}
        meta = build_synthetic_packet(runs, cases, rub, list(ALL_CONDITIONS), ann, priv)
    else:
        meta = build_real_packet(runs, cases, list(REAL_PAPER_CONDITIONS), ann, priv)
    errs = verify_packet(ann, priv, runs, kind=a.kind, repo_root=ROOT)
    print(json.dumps(meta, indent=1))
    if errs:
        print("INTEGRITY CHECK FAILED:")
        for e in errs:
            print("  -", e)
        return 1
    print("integrity checks passed; private mapping kept in", priv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
