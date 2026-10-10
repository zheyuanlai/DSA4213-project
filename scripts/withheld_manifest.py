"""Write outputs/WITHHELD_UNTIL_ANNOTATION.json: sha256 of every raw output file that is withheld from git
until blind annotation ends (outputs/synthetic, outputs/real_papers). After release, re-run with --verify.

  python scripts/withheld_manifest.py            # write manifest
  python scripts/withheld_manifest.py --verify   # check released files match the manifest
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "WITHHELD_UNTIL_ANNOTATION.json"
DIRS = ["outputs/synthetic", "outputs/real_papers"]


def scan() -> dict:
    files, statuses = {}, Counter()
    for d in DIRS:
        for p in sorted((ROOT / d).rglob("*.json")):
            rel = str(p.relative_to(ROOT))
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            parts = p.relative_to(ROOT / d).parts
            if len(parts) == 3 and parts[1].startswith("C"):
                st = json.loads(p.read_text()).get("status")
                statuses[f"{d.split('/')[1]}:{parts[1]}:{st}"] += 1
    return {"files": files, "n_files": len(files), "run_record_status_counts": dict(sorted(statuses.items()))}


def main() -> int:
    if "--verify" in sys.argv:
        m = json.loads(OUT.read_text())
        now = scan()["files"]
        bad = [k for k, v in m["files"].items() if now.get(k) != v]
        print(f"{len(m['files'])} files in manifest; mismatched/missing: {len(bad)}")
        for b in bad[:20]:
            print("  ", b)
        return 1 if bad else 0
    s = scan()
    s["note"] = ("Raw run records for the held-out TEST split and the real-paper study are withheld from git until blind "
                 "human annotation is complete (they reveal which condition produced each annotated text). The "
                 "coordinator keeps them locally and must back them up with private/. Release procedure: "
                 "docs/HUMAN_REVIEW_HANDOFF.md.")
    OUT.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT} ({s['n_files']} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
