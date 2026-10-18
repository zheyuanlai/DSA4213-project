"""2-of-3 majority voting and Fleiss' kappa for the third-judge sensitivity analysis."""
from __future__ import annotations

import pytest

from evaluation.majority_vote import _majority, _verdict_class, fleiss_kappa


def test_majority_needs_two_of_three():
    assert _majority(["SUPPORTED", "SUPPORTED", "OVERSTATED"]) == "SUPPORTED"
    assert _majority(["SUPPORTED", "OVERSTATED", "UNSUPPORTED"]) is None
    assert _majority(["ERROR", "ERROR"]) == "ERROR"  # two usable numeric verdicts that agree
    assert _majority(["CORRECT", "ERROR"]) is None


def test_verdict_classes():
    assert _verdict_class("CORRECT") == "CORRECT"
    assert _verdict_class("MISATTRIBUTED") == "ERROR"
    assert _verdict_class("INVALID_MAPPING") == "INVALID"


def test_fleiss_kappa_matches_hand_computation():
    # 4 items, 3 raters: two unanimous items, two 2-vs-1 splits
    rows = [("a", "a", "a"), ("b", "b", "b"), ("a", "a", "b"), ("a", "b", "b")]
    # P_i = 1, 1, 1/3, 1/3 -> P_bar = 2/3; p_a = p_b = 0.5 -> P_e = 0.5; kappa = (2/3 - 1/2) / (1/2) = 1/3
    assert fleiss_kappa(rows) == pytest.approx(1 / 3)
    assert fleiss_kappa([("a", "a", "a"), ("a", "a", "a")]) is None  # no variation: undefined, not 1
    assert fleiss_kappa([]) is None


def test_no_majority_label_is_unresolved_and_left_out_of_rates():
    from evaluation import atomic_claims as ac
    rec = {"claim_id": "x", "unit_id": "U", "alias": "K", "claim_type": "comparison", "result_claim": True,
           "final_label": "UNRESOLVED", "factual_error": None, "numbers": []}
    counts = ac.claim_counts([rec])
    assert counts["n_assessable"] == 0 and counts["n_unresolved"] == 1
