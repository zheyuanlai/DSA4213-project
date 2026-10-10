"""Benchmark integrity checks (used by authors, build.py and the test-suite).

Usage:
  python -m benchmarks.validate --source private/benchmark_source      # authored (with gold)
  python -m benchmarks.validate --source private/benchmark_source --category robustness
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from scipy import stats

from benchmarks.schema import AuthoredCase
from src.evidence_store import EvidenceStore
from src.package_schema import CATEGORIES, ORDINAL_CATEGORIES

CAT_ABBR = {
    "statistical_significance": "SIG",
    "robustness": "ROB",
    "generalization": "GEN",
    "consistency": "CON",
    "efficiency": "EFF",
    "citation_support": "CIT",
    "numerical_reporting": "NUM",
    "negative_results": "NEG",
}
NUM_RE = re.compile(r"[-−]?\d+(?:\.\d+)?")
# Words that must never appear in model-visible text (would leak the rubric/gold).
LEAK_PATTERNS = [
    r"\bgold\b",
    r"\bell\s*=",
    r"\blevel\s*[012]\b",
    r"\bforbidden\b",
    r"\boverstat",
    r"\bunderstat",
    r"\bcalibrat",
    r"\brequired finding",
]


def load_authored(source: Path, category: str | None = None) -> list[AuthoredCase]:
    files = sorted(source.glob("*.json"))
    cases: list[AuthoredCase] = []
    for f in files:
        data = json.loads(f.read_text())
        for d in data:
            c = AuthoredCase.model_validate(d)
            if category is None or c.category == category:
                cases.append(c)
    return cases


def _p_from_t(t: float, df: float, two_sided: bool = True) -> float:
    p = stats.t.sf(abs(t), df)
    return float(2 * p if two_sided else p)


def check_stat_test(case_id: str, s) -> list[str]:
    errs = []
    if s.p_value is not None and not (0 <= s.p_value <= 1):
        errs.append(f"{case_id}/{s.test_id}: p outside [0,1]")
    if s.n is not None and s.n < 2:
        errs.append(f"{case_id}/{s.test_id}: n < 2")
    name = s.test_name.lower()
    if s.statistic is not None and s.df is not None and s.p_value is not None and "t-test" in name:
        p = _p_from_t(s.statistic, s.df, two_sided=(s.sidedness != "one-sided"))
        if s.multiple_comparison_adjustment:
            # reported p is the ADJUSTED p: it can only be >= the raw p implied by (t, df)
            if s.p_value + max(0.0006, 0.05 * p) < p:
                errs.append(f"{case_id}/{s.test_id}: adjusted p {s.p_value} is smaller than raw p {p:.4g} implied by t, df")
        else:
            # allow rounding of reported p
            ok = abs(p - s.p_value) <= max(0.006, 0.15 * s.p_value)
            if not ok:
                errs.append(f"{case_id}/{s.test_id}: t={s.statistic}, df={s.df} implies p={p:.4g}, reported {s.p_value}")
        if s.paired and s.n is not None and abs(s.df - (s.n - 1)) > 1e-9:
            errs.append(f"{case_id}/{s.test_id}: paired t-test with n={s.n} should have df={s.n-1}, got {s.df}")
    if s.ci_low is not None and s.ci_high is not None:
        if s.ci_low > s.ci_high:
            errs.append(f"{case_id}/{s.test_id}: ci_low > ci_high")
        alpha = s.alpha if s.alpha is not None else 0.05
        lvl = s.ci_level if s.ci_level is not None else 0.95
        if s.p_value is not None and abs((1 - lvl) - alpha) < 1e-9 and not s.multiple_comparison_adjustment:
            excludes0 = s.ci_low > 0 or s.ci_high < 0
            sig = s.p_value < alpha
            if excludes0 != sig:
                errs.append(
                    f"{case_id}/{s.test_id}: CI [{s.ci_low},{s.ci_high}] excludes 0={excludes0} but p<alpha={sig}"
                )
    if s.p_value_text and s.p_value is not None:
        m = re.search(r"p\s*([<=≤>])\s*([0-9.eE\-]+)", s.p_value_text)
        if m:
            op, v = m.group(1), float(m.group(2))
            if op in "=" and abs(v - s.p_value) > max(0.0006, 0.05 * v):
                errs.append(f"{case_id}/{s.test_id}: p_value_text {s.p_value_text!r} != p_value {s.p_value}")
            if op in "<≤" and not s.p_value <= v:
                errs.append(f"{case_id}/{s.test_id}: p_value_text {s.p_value_text!r} inconsistent with {s.p_value}")
    return errs


def check_case(c: AuthoredCase) -> list[str]:
    errs: list[str] = []
    pkg = c.package
    try:
        store = EvidenceStore.from_package(pkg)
    except Exception as e:  # pragma: no cover - surfaced as error
        return [f"{c.case_id}: evidence store build failed: {e}"]
    # case id convention
    abbr = CAT_ABBR[c.category]
    if not re.match(rf"^{abbr}-p[123][ab]$", c.case_id):
        errs.append(f"{c.case_id}: case_id must look like {abbr}-p1a")
    if not c.pair_id == c.case_id[:-1]:
        errs.append(f"{c.case_id}: pair_id must be {c.case_id[:-1]}")
    expected_split = "dev" if c.case_id.endswith(("p1a", "p1b")) else "test"
    if c.split != expected_split:
        errs.append(f"{c.case_id}: split must be {expected_split}")
    # gold evidence ids resolve
    g = c.gold
    all_ids = list(g.evidence_ids)
    for f in g.required_findings:
        all_ids += f.evidence_ids
    for n in g.numeric_facts:
        if n.evidence_id != "derived":
            all_ids.append(n.evidence_id)
    for eid in all_ids:
        if not store.has(eid):
            errs.append(f"{c.case_id}: gold references unknown evidence id {eid!r}")
    # numeric facts consistent with cells
    for n in g.numeric_facts:
        item = store.get(n.evidence_id) if n.evidence_id != "derived" else None
        if item is not None and item.kind == "table_cell":
            if item.value is None or abs(item.value - n.value) > n.tolerance + 1e-9:
                errs.append(f"{c.case_id}: numeric fact {n.fact_id}={n.value} != cell {n.evidence_id}={item.value}")
        if n.evidence_id == "derived" and not n.derivation:
            errs.append(f"{c.case_id}: derived numeric fact {n.fact_id} needs a derivation")
    # table cells: value matches first number in text
    for t in pkg.results_tables:
        for r in t.rows:
            for cid, cell in r.cells.items():
                nums = NUM_RE.findall(cell.text.replace(",", ""))
                if cell.value is not None:
                    if not nums:
                        errs.append(f"{c.case_id}: {t.table_id}.{r.row_id}.{cid} value set but text has no number")
                    elif abs(float(nums[0].replace("−", "-")) - cell.value) > 1e-6:
                        errs.append(
                            f"{c.case_id}: {t.table_id}.{r.row_id}.{cid} value {cell.value} != text {cell.text!r}"
                        )
                if cell.spread is not None and "±" not in cell.text:
                    errs.append(f"{c.case_id}: {t.table_id}.{r.row_id}.{cid} spread set but no ± in text")
    for s in pkg.statistical_tests:
        errs += check_stat_test(c.case_id, s)
    # leakage of rubric vocabulary into model-visible text
    visible = json.dumps(pkg.model_dump(), ensure_ascii=False).lower()
    for pat in LEAK_PATTERNS:
        if re.search(pat, visible):
            errs.append(f"{c.case_id}: model-visible package contains rubric word matching {pat!r}")
    if len(visible) > 12000:
        errs.append(f"{c.case_id}: package too long ({len(visible)} chars JSON); keep packages short")
    return errs


def check_collection(cases: list[AuthoredCase], full: bool = True) -> list[str]:
    errs: list[str] = []
    ids = [c.case_id for c in cases]
    for k, v in Counter(ids).items():
        if v > 1:
            errs.append(f"duplicate case_id {k}")
    qs = Counter(c.package.question.strip().lower() for c in cases)
    by_pair: dict[str, list[AuthoredCase]] = defaultdict(list)
    for c in cases:
        by_pair[c.pair_id].append(c)
    for pid, members in by_pair.items():
        if len(members) != 2:
            errs.append(f"pair {pid} has {len(members)} members (need 2)")
            continue
        if len({m.split for m in members}) != 1:
            errs.append(f"pair {pid} spans splits")
        a, b = members
        if a.package.model_dump() == b.package.model_dump():
            errs.append(f"pair {pid} members have identical packages")
        if a.category in ORDINAL_CATEGORIES and a.gold.gold_level == b.gold.gold_level:
            errs.append(f"pair {pid}: members must differ in gold level")
    # cross-pair duplicate packages
    seen = {}
    for c in cases:
        key = json.dumps(c.package.model_dump(), sort_keys=True)
        if key in seen:
            errs.append(f"{c.case_id} duplicates package of {seen[key]}")
        seen[key] = c.case_id
    if full:
        if len(cases) != 48:
            errs.append(f"expected 48 cases, got {len(cases)}")
        per_cat = Counter(c.category for c in cases)
        for cat in CATEGORIES:
            if per_cat.get(cat, 0) != 6:
                errs.append(f"category {cat}: {per_cat.get(cat, 0)} cases (need 6)")
        splits = Counter(c.split for c in cases)
        if splits.get("dev", 0) != 16 or splits.get("test", 0) != 32:
            errs.append(f"split sizes {dict(splits)} (need dev=16, test=32)")
    # per ordinal category TEST distribution (works for partial collections too)
    for cat in ORDINAL_CATEGORIES:
        test = [c for c in cases if c.category == cat and c.split == "test"]
        if not test:
            continue
        lv = Counter(c.gold.gold_level for c in test)
        if len(test) == 4 and (lv.get(2, 0) != 2 or lv.get(0, 0) + lv.get(1, 0) != 2):
            errs.append(f"{cat}: TEST levels {dict(lv)} (need exactly two 2s and two non-strong)")
    if full:
        test_nonstrong = Counter(
            c.gold.gold_level for c in cases if c.category in ORDINAL_CATEGORIES and c.split == "test" and c.gold.gold_level != 2
        )
        if test_nonstrong.get(0, 0) == 0 or test_nonstrong.get(1, 0) == 0:
            errs.append(f"TEST non-strong must include both 0s and 1s, got {dict(test_nonstrong)}")
    for q, n in qs.items():
        if n > 2:
            errs.append(f"question text used {n} times: {q[:60]!r}")
    for c in cases:
        errs += check_case(c)
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="private/benchmark_source")
    ap.add_argument("--category", default=None)
    args = ap.parse_args(argv)
    cases = load_authored(Path(args.source), args.category)
    full = args.category is None
    errs = check_collection(cases, full=full)
    print(f"loaded {len(cases)} cases")
    for e in errs:
        print("ERROR:", e)
    print("OK" if not errs else f"{len(errs)} error(s)")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
