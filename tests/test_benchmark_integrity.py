"""Benchmark invariants on the BUILT public data (+ private gold/source when present locally)."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from src.evidence_store import EvidenceStore
from src.package_schema import CATEGORIES, ORDINAL_CATEGORIES, CaseRecord

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "data" / "synthetic" / "dev.jsonl"
TEST = ROOT / "data" / "synthetic" / "test.jsonl"
PRIVATE_SRC = ROOT / "private" / "benchmark_source"
PRIVATE_GOLD = ROOT / "private" / "gold" / "test_gold.jsonl"


def load(p):
    return [CaseRecord.model_validate_json(x) for x in p.read_text().splitlines() if x.strip()]


@pytest.fixture(scope="module")
def cases():
    if not DEV.exists():
        pytest.skip("benchmark not built")
    return load(DEV) + load(TEST)


def test_counts_and_splits(cases):
    assert len(cases) == 48
    assert Counter(c.split for c in cases) == {"dev": 16, "test": 32}
    per = Counter(c.category for c in cases)
    assert all(per[cat] == 6 for cat in CATEGORIES)
    for cat in CATEGORIES:
        assert Counter(c.split for c in cases if c.category == cat) == {"dev": 2, "test": 4}


def test_pairs_within_split_and_unique(cases):
    ids = [c.case_id for c in cases]
    assert len(set(ids)) == 48
    pairs = {}
    for c in cases:
        pairs.setdefault(c.pair_id, set()).add(c.split)
    assert len(pairs) == 24 and all(len(v) == 1 for v in pairs.values())
    pk = [json.dumps(c.package.model_dump(), sort_keys=True) for c in cases]
    assert len(set(pk)) == 48


def test_evidence_stores_build_and_ids_resolve(cases):
    for c in cases:
        st = EvidenceStore.from_package(c.package)
        for s in c.package.statistical_tests:
            assert st.has(s.test_id) and st.has(f"{s.experiment_id}/{s.comparison_id}")


def test_build_hashes_match_public_files():
    hp = ROOT / "benchmarks" / "build_hashes.json"
    if not hp.exists():
        pytest.skip("not built")
    h = json.loads(hp.read_text())
    files = {"public_dev": DEV, "public_test": TEST,
             "rubric_dev": ROOT / "data/synthetic/rubrics/dev_rubric.jsonl",
             "rubric_test": ROOT / "data/synthetic/rubrics/test_rubric.jsonl",
             "gold_dev": ROOT / "data/synthetic/gold/dev_gold.jsonl"}
    for k, p in files.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == h[k], k
    if PRIVATE_GOLD.exists():
        assert hashlib.sha256(PRIVATE_GOLD.read_bytes()).hexdigest() == h["gold_test_PRIVATE"]


def test_dev_gold_public_and_complete():
    p = ROOT / "data/synthetic/gold/dev_gold.jsonl"
    if not p.exists():
        pytest.skip("not built")
    g = [json.loads(x) for x in p.read_text().splitlines()]
    assert len(g) == 16 and all(x["case_id"].split("-")[1].startswith("p1") for x in g)


def test_private_test_gold_distribution():
    if not PRIVATE_GOLD.exists():
        pytest.skip("private TEST gold not available on this machine (expected for non-coordinators)")
    g = [json.loads(x) for x in PRIVATE_GOLD.read_text().splitlines()]
    assert len(g) == 32
    for cat in ORDINAL_CATEGORIES:
        lv = Counter(x["gold_level"] for x in g if x["category"] == cat)
        assert lv[2] == 2 and lv[0] + lv[1] == 2, (cat, lv)
    non_strong = Counter(x["gold_level"] for x in g if x["category"] in ORDINAL_CATEGORIES and x["gold_level"] != 2)
    assert non_strong == {0: 6, 1: 6}
    assert all(x["gold_level"] is None for x in g if x["category"] not in ORDINAL_CATEGORIES)


def test_full_validator_on_private_source():
    if not PRIVATE_SRC.exists():
        pytest.skip("private authored source not available")
    from benchmarks.validate import check_collection, load_authored

    assert check_collection(load_authored(PRIVATE_SRC), full=True) == []


def test_validator_catches_planted_errors(example_authored):
    from benchmarks.validate import check_case, check_stat_test

    bad = example_authored.model_copy(deep=True)
    bad.package.statistical_tests[0].p_value = 0.4  # contradicts t=3.63, df=9 and the CI
    errs = check_stat_test("X", bad.package.statistical_tests[0])
    assert any("implies p" in e for e in errs) and any("excludes 0" in e for e in errs)
    bad2 = example_authored.model_copy(deep=True)
    bad2.gold.evidence_ids.append("T1.r9.em")
    assert any("unknown evidence id" in e for e in check_case(bad2))
    bad3 = example_authored.model_copy(deep=True)
    bad3.package.methods_summary += " This case has gold level 2."
    assert any("rubric word" in e for e in check_case(bad3))
