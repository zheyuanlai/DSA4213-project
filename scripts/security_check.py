"""Pre-push secret/privacy scan of working tree, index and full git history.

  python scripts/security_check.py            # exit 1 on any finding (prints locations only, never secrets)
If OPENROUTER_API_KEY is set in the environment, the live key and its fragments are also searched for.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.security_scan import run_scan  # noqa: E402


def main() -> int:
    findings = run_scan(ROOT, include_history=True)
    live = "yes" if os.environ.get("OPENROUTER_API_KEY") else "no (generic patterns only)"
    print(f"security scan: live-key check = {live}; findings = {len(findings)}")
    for f in sorted(findings, key=str):
        print("  FINDING", f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
