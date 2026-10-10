"""Generic experiment CLI (idempotent/resumable: re-running the same command resumes).

  python scripts/run_experiment.py --config configs/frozen_primary.yaml --cases data/synthetic/test.jsonl \
      --family synthetic --run-tag primary_v1 --stage main --conditions all
  add --mock for an offline dry run with the deterministic mock responder (outputs flagged is_mock,
  written under outputs/_mock/ and never mixed into real analyses).
The OpenRouter key is read from the OPENROUTER_API_KEY environment variable only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.conditions import ALL_CONDITIONS  # noqa: E402
from src.runner import load_cases, load_config, run_experiment  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True, help="jsonl file or directory of CaseRecord json files")
    ap.add_argument("--family", required=True, help="output family, e.g. synthetic, dev, real_papers")
    ap.add_argument("--run-tag", required=True)
    ap.add_argument("--stage", required=True, help="cost stage: preflight|dev|main|real|buffer")
    ap.add_argument("--conditions", default="all")
    ap.add_argument("--case-ids", default=None, help="comma-separated subset")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    cases = load_cases(ROOT / a.cases if not Path(a.cases).is_absolute() else a.cases)
    if a.case_ids:
        keep = set(a.case_ids.split(","))
        cases = [c for c in cases if c.case_id in keep]
    conds = list(ALL_CONDITIONS) if a.conditions == "all" else a.conditions.split(",")
    client, out_base = None, None
    if a.mock:
        from src.mock_responder import mock_responder
        from src.openrouter_client import MockClient

        client = MockClient(mock_responder)
        out_base = ROOT / "outputs" / "_mock"
    s = run_experiment(cfg, cases, conds, family=a.family, run_tag=a.run_tag, stage=a.stage, client=client,
                       out_base=out_base, workers=a.workers)
    print(json.dumps(s, indent=1))
    return 0 if not s.get("stop_reason") else 3


if __name__ == "__main__":
    sys.exit(main())
