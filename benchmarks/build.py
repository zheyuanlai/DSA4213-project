"""Split the authored benchmark (private source with gold) into its stores via explicit allowlists.

  data/synthetic/dev.jsonl, data/synthetic/test.jsonl     public CaseRecords (model-visible package + metadata)
  data/synthetic/rubrics/{dev,test}_rubric.jsonl          annotator rubric (no gold level / justification)
  data/synthetic/gold/dev_gold.jsonl                      DEV gold (public: used for tuning + annotator training)
  private/gold/test_gold.jsonl                            TEST gold (coordinator-only until annotation ends)
  benchmarks/build_hashes.json                            sha256 of every output (incl. private gold)

Usage: python -m benchmarks.build [--source private/benchmark_source]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from benchmarks.validate import check_collection, load_authored

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def build(source: Path, root: Path = ROOT) -> dict[str, str]:
    cases = load_authored(source)
    errs = check_collection(cases, full=True)
    if errs:
        raise SystemExit("benchmark invalid:\n" + "\n".join(errs))
    cases.sort(key=lambda c: c.case_id)
    outs: dict[str, Path] = {}
    for split in ("dev", "test"):
        sel = [c for c in cases if c.split == split]
        p = root / "data" / "synthetic" / f"{split}.jsonl"
        write_jsonl(p, [c.public_record().model_dump() for c in sel])
        outs[f"public_{split}"] = p
        p = root / "data" / "synthetic" / "rubrics" / f"{split}_rubric.jsonl"
        write_jsonl(p, [c.annotator_rubric() for c in sel])
        outs[f"rubric_{split}"] = p
    p = root / "data" / "synthetic" / "gold" / "dev_gold.jsonl"
    write_jsonl(p, [c.gold.model_dump() for c in cases if c.split == "dev"])
    outs["gold_dev"] = p
    p = root / "private" / "gold" / "test_gold.jsonl"
    write_jsonl(p, [c.gold.model_dump() for c in cases if c.split == "test"])
    outs["gold_test_PRIVATE"] = p
    src_hash = hashlib.sha256()
    for f in sorted(source.glob("*.json")):
        src_hash.update(f.name.encode())
        src_hash.update(f.read_bytes())
    hashes = {k: sha256_file(v) for k, v in outs.items()}
    hashes["authored_source_PRIVATE"] = src_hash.hexdigest()
    (root / "benchmarks" / "build_hashes.json").write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n")
    return hashes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(ROOT / "private" / "benchmark_source"))
    a = ap.parse_args(argv)
    h = build(Path(a.source))
    print(json.dumps(h, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
