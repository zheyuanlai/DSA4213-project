"""Per-probe comparison of two conditions (possibly from different runs), using majority decisions over repeats.

  python v2/scripts/compare_conditions.py \
      --a v2/outputs/e1e2/e2b_v1:D1-oracle --b v2/outputs/e1e2/e2b_v1:D1c-oracle [--out file.md]

Lists every probe whose correctness changes (improvement / regression) and every probe whose majority decision changes
while correctness does not. Correctness follows the probe file's `acceptable_decisions`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v2.scripts.analyze_e1_e2 import SCOPE_ANCHORING, majority  # noqa: E402


def load(spec: str) -> dict[str, list[str]]:
    run_dir, cond = spec.rsplit(":", 1)
    out: dict[str, list[tuple[int, str]]] = {}
    for f in sorted((Path(run_dir) / cond).glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("status") == "completed":
            out.setdefault(r["probe_id"], []).append((r["repeat"], r["decision"]))
    return {k: [d for _, d in sorted(v)] for k, v in out.items()}


def compare(a: dict[str, list[str]], b: dict[str, list[str]], probes: list[dict]) -> dict[str, list[dict]]:
    res = {"improved": [], "regressed": [], "changed_same_correctness": [], "unchanged": []}
    for p in probes:
        pid = p["probe_id"]
        da, db = a.get(pid, []), b.get(pid, [])
        ma, mb = majority(da), majority(db)
        ca, cb = ma in p["acceptable_decisions"], mb in p["acceptable_decisions"]
        row = {"probe_id": pid, "expected": "/".join(p["acceptable_decisions"]), "a": f"{ma} {da}", "b": f"{mb} {db}",
               "scope_subgroup": pid in SCOPE_ANCHORING}
        key = ("improved" if cb and not ca else "regressed" if ca and not cb else
               "changed_same_correctness" if ma != mb else "unchanged")
        res[key].append(row)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="run_dir:condition")
    ap.add_argument("--b", required=True, help="run_dir:condition")
    ap.add_argument("--probes", default=str(ROOT / "v2" / "data" / "dev_probes_batch1.json"))
    ap.add_argument("--out", default="")
    x = ap.parse_args(argv)
    probes = json.loads(Path(x.probes).read_text(encoding="utf-8"))["probes"]
    res = compare(load(x.a), load(x.b), probes)
    lines = [f"# {x.a}  vs  {x.b}", ""]
    for k in ("improved", "regressed", "changed_same_correctness"):
        lines += [f"## {k} ({len(res[k])})", ""]
        if res[k]:
            lines += ["| Probe | Expected | A | B |", "|---|---|---|---|"]
            lines += [f"| {r['probe_id']}{' (scope subgroup)' if r['scope_subgroup'] else ''} | {r['expected']} | "
                      f"{r['a']} | {r['b']} |" for r in res[k]]
        lines.append("")
    lines.append(f"unchanged: {len(res['unchanged'])}")
    text = "\n".join(lines) + "\n"
    if x.out:
        Path(x.out).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
