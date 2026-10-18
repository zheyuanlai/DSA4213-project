"""Strict whole-passage success, missing outputs, and paired/clustered bootstrap behaviour."""
from __future__ import annotations

import pytest

from evaluation.extended_metrics import strict_passage_checks
from evaluation.extended_stats import mean_diff, rate_ci, ratio_diff

GOLD_ORD = {"category": "robustness", "gold_level": 0,
            "required_findings": [{"finding_id": "f1", "polarity": "neutral"}]}
RUB_ORD = {"required_findings": [{"finding_id": "f1"}], "numeric_facts": []}
GOLD_NEG = {"category": "negative_results", "gold_level": None,
            "required_findings": [{"finding_id": "f1", "polarity": "negative"}, {"finding_id": "f2", "polarity": "positive"}]}
RUB_NEG = {"required_findings": [{"finding_id": "f1"}, {"finding_id": "f2"}], "numeric_facts": [{"fact_id": "n1"}]}


def row(**kw):
    base = {"expressed_level": "", "focal_addressed": "no", "findings_covered": "f1", "unsupported_claims": "0",
            "numeric_errors": "0", "num_facts_correct": "", "neg_findings_reported": "", "neg_reframed_positive": ""}
    base.update(kw)
    return base


def ok(checks):
    return all(v for v in checks.values() if v is not None)


def test_legitimate_omission_of_level_zero_focal_claim_is_not_penalised():
    assert ok(strict_passage_checks(row(), GOLD_ORD, RUB_ORD))
    # ...but the required findings must still be reported
    assert not ok(strict_passage_checks(row(findings_covered=""), GOLD_ORD, RUB_ORD))
    # an affirmative level-2 claim on a level-0 case fails
    assert not ok(strict_passage_checks(row(expressed_level="2", focal_addressed="yes"), GOLD_ORD, RUB_ORD))


def test_any_unsupported_claim_or_numeric_error_fails_the_passage():
    assert not ok(strict_passage_checks(row(unsupported_claims="1"), GOLD_ORD, RUB_ORD))
    assert not ok(strict_passage_checks(row(numeric_errors="2"), GOLD_ORD, RUB_ORD))


def test_negative_result_checks_apply_only_to_neg_cases():
    good = row(findings_covered="f1;f2", neg_findings_reported="f1", neg_reframed_positive="no")
    c = strict_passage_checks(good, GOLD_NEG, RUB_NEG)
    assert c["focal_correct"] is None and c["num_facts_all_correct"] is None
    assert ok(c)
    assert not ok(strict_passage_checks(dict(good, neg_reframed_positive="yes"), GOLD_NEG, RUB_NEG))
    assert not ok(strict_passage_checks(dict(good, neg_findings_reported=""), GOLD_NEG, RUB_NEG))
    assert strict_passage_checks(good, GOLD_ORD, RUB_ORD)["neg_findings_all_reported"] is None


def test_missing_or_failed_output_fails_every_applicable_check():
    c = strict_passage_checks(None, GOLD_ORD, RUB_ORD)
    assert c["valid_output"] is False and not ok(c)
    assert c["focal_correct"] is False  # even though omission would be correct for level 0


def test_ratio_bootstrap_is_reproducible_and_resamples_cases():
    num_a, den_a = {"k1": 3, "k2": 1, "k3": 5}, {"k1": 4, "k2": 4, "k3": 5}
    num_b, den_b = {"k1": 2, "k2": 1, "k3": 3}, {"k1": 4, "k2": 2, "k3": 5}
    r1, r2 = ratio_diff(num_a, den_a, num_b, den_b), ratio_diff(num_a, den_a, num_b, den_b)
    assert r1 == r2
    assert r1["diff"] == pytest.approx(9 / 13 - 6 / 11)
    assert r1["ci_low"] <= r1["diff"] <= r1["ci_high"] and r1["n"] == 3
    rc = ratio_diff(num_a, den_a, num_b, den_b, clusters={"k1": "p1", "k2": "p1", "k3": "p2"})
    assert rc["matched_pair"]["n_clusters"] == 2


def test_identical_labels_give_a_flagged_degenerate_interval():
    a = {"k1": 1.0, "k2": 0.0, "k3": 1.0}
    r = mean_diff(a, dict(a))
    assert r["diff"] == 0 and r["ci_low"] == 0 and r["ci_high"] == 0 and r["degenerate"]
    rr = ratio_diff({"k": 2}, {"k": 4}, {"k": 2}, {"k": 4})
    assert rr["degenerate"]


def test_zero_denominators_are_undefined_not_zero():
    r = ratio_diff({"k": 0}, {"k": 0}, {"k": 1}, {"k": 2})
    assert r["diff"] is None
    assert rate_ci({"k": 0}, {"k": 0}) == (None, None, None)
