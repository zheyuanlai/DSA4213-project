"""Deterministic numeric checks: lookups, derived values, unit conversions, tolerance, entity association."""
from __future__ import annotations

import pytest

from evaluation.numeric_fidelity import (
    Assertion, EvidenceValues, ExpressionError, Mapping, RequiredFact, check_assertion, evaluate, fact_reported,
    gold_fact,
)
from src.package_schema import ResearchPackage


@pytest.fixture()
def ev() -> EvidenceValues:
    pkg = ResearchPackage.model_validate({
        "question": "Is A better than B?", "methods_summary": "A and B.", "experimental_setup": "Two datasets, 5 seeds.",
        "experiments": [{"experiment_id": "exp1", "description": "main",
                         "comparisons": [{"comparison_id": "cmp1", "description": "A vs B"}]}],
        "results_tables": [{
            "table_id": "T1", "caption": "Accuracy (fraction) and latency.",
            "columns": [{"column_id": "d1", "header": "Data-1", "higher_is_better": True},
                        {"column_id": "d2", "header": "Data-2", "higher_is_better": True},
                        {"column_id": "lat", "header": "Latency", "unit": "ms", "higher_is_better": False}],
            "rows": [
                {"row_id": "r1", "label": "A", "cells": {"d1": {"text": "0.837 ± 0.004", "value": 0.837, "spread": 0.004},
                                                         "d2": {"text": "0.679", "value": 0.679},
                                                         "lat": {"text": "112", "value": 112.0}}},
                {"row_id": "r2", "label": "B", "cells": {"d1": {"text": "0.814", "value": 0.814},
                                                         "d2": {"text": "0.683", "value": 0.683},
                                                         "lat": {"text": "241", "value": 241.0}}}]}],
        "statistical_tests": [{"test_id": "S1", "experiment_id": "exp1", "comparison_id": "cmp1",
                               "test_name": "paired t-test", "n": 5, "statistic_name": "t", "statistic": 3.1,
                               "df": 4, "p_value": 0.036, "p_value_text": "p = 0.036", "alpha": 0.05}],
        "source_passages": [{"passage_id": "P1", "citation_key": "Lee (2020)", "source_title": "Prior",
                             "text": "The prior method reduced latency by 31% on news."}],
        "task_instruction": "Write a short passage."})
    return EvidenceValues.from_package(pkg)


def chk(ev, written, value, mapping, **kw):
    return check_assertion(Assertion(written, value, **kw), mapping, ev).status


def test_exact_lookup_and_rounding(ev):
    assert chk(ev, "0.837", 0.837, Mapping("cell", "T1.r1.d1")) == "CORRECT"
    assert chk(ev, "0.84", 0.84, Mapping("cell", "T1.r1.d1")) == "CORRECT"  # rounded to two decimals
    assert chk(ev, "0.85", 0.85, Mapping("cell", "T1.r1.d1")) != "CORRECT"


def test_unit_conversion_accepted(ev):
    assert chk(ev, "83.7%", 83.7, Mapping("cell", "T1.r1.d1", scale=100)) == "CORRECT"
    assert chk(ev, "0.112 s", 0.112, Mapping("cell", "T1.r1.lat", scale=0.001)) == "CORRECT"
    assert chk(ev, "2.3 percentage points", 2.3, Mapping("cell", "T1.r1.d1 - T1.r2.d1", scale=100)) == "CORRECT"


def test_disallowed_scale_is_invalid(ev):
    assert chk(ev, "8.37", 8.37, Mapping("cell", "T1.r1.d1", scale=10)) == "INVALID_MAPPING"


def test_scale_error_detected(ev):
    assert chk(ev, "83.7", 83.7, Mapping("cell", "T1.r1.d1")) == "UNIT_OR_SCALE"


def test_derived_difference_ratio_and_percent_change(ev):
    assert chk(ev, "0.023", 0.023, Mapping("cell", "T1.r1.d1 - T1.r2.d1"), role="derived") == "CORRECT"
    assert chk(ev, "2.15×", 2.15, Mapping("cell", "T1.r2.lat / T1.r1.lat"), role="derived") == "CORRECT"
    assert chk(ev, "53.5%", 53.5, Mapping("cell", "(T1.r2.lat − T1.r1.lat) / T1.r2.lat × 100"), role="derived") == "CORRECT"
    assert chk(ev, "2.5×", 2.5, Mapping("cell", "T1.r2.lat / T1.r1.lat"), role="derived") == "ARITHMETIC"


def test_sign_or_direction_error(ev):
    assert chk(ev, "-0.023", -0.023, Mapping("cell", "T1.r1.d1 - T1.r2.d1"), role="derived") == "SIGN_OR_DIRECTION"


def test_number_in_table_but_wrong_entity_is_misattributed(ev):
    # "A scored 0.814 on Data-1" — 0.814 is in the table, but it is B's score
    assert chk(ev, "0.814", 0.814, Mapping("cell", "T1.r1.d1")) == "MISATTRIBUTED"
    # right method, wrong dataset
    assert chk(ev, "0.679", 0.679, Mapping("cell", "T1.r1.d1")) == "MISATTRIBUTED"


def test_statistic_attached_to_wrong_test_quantity(ev):
    assert chk(ev, "p = 0.036", 0.036, Mapping("test", "S1.p_value"), role="statistical") == "CORRECT"
    assert chk(ev, "p = 0.36", 0.36, Mapping("test", "S1.p_value"), role="statistical") != "CORRECT"
    # read as an exact value, 0.05 is the test's alpha, not its p-value
    assert chk(ev, "p < 0.05", 0.05, Mapping("test", "S1"), role="statistical") == "STAT_MISASSOCIATION"
    a = Assertion("p < 0.05", 0.05, role="statistical")
    assert check_assertion(a, Mapping("test", "S1", comparator="<"), ev).status == "CORRECT"


def test_count_min_max(ev):
    assert chk(ev, "1", 1, Mapping("cell", "count(T1.r1.d1 > T1.r2.d1, T1.r1.d2 > T1.r2.d2)"), role="count_outcome") == "CORRECT"
    assert chk(ev, "2", 2, Mapping("cell", "count(T1.r1.d1 > T1.r2.d1, T1.r1.d2 > T1.r2.d2)"), role="count_outcome") != "CORRECT"
    assert chk(ev, "0.023", 0.023, Mapping("cell", "max(T1.r1.d1 - T1.r2.d1, T1.r1.d2 - T1.r2.d2)"), role="derived") == "CORRECT"


def test_text_quote_and_fabrication(ev):
    assert chk(ev, "31%", 31, Mapping("text", quote="reduced latency by 31%"), role="cited") == "CORRECT"
    assert chk(ev, "30%", 30, Mapping("text", quote="reduced latency by 31%"), role="cited") == "VALUE_MISMATCH"
    assert chk(ev, "about 30%", 30, Mapping("text", quote="reduced latency by 31%"), role="cited", approximate=True) == "CORRECT"
    assert chk(ev, "31%", 31, Mapping("text", quote="not in the package 31%"), role="cited") == "INVALID_MAPPING"
    assert chk(ev, "7.7", 7.7, Mapping("none"), role="result") == "FABRICATED"
    assert chk(ev, "0.683", 0.683, Mapping("none"), role="result") == "MISATTRIBUTED"


def test_unknown_ids_and_unsafe_expressions_rejected(ev):
    assert chk(ev, "1", 1, Mapping("cell", "T9.r1.d1")) == "INVALID_MAPPING"
    with pytest.raises(ExpressionError):
        evaluate("__import__('os').system('true')", ev)
    with pytest.raises(ExpressionError):
        evaluate("T1.r1.d1 ** 2", ev)


def test_required_fact_matching_needs_same_operands(ev):
    fact = gold_fact({"fact_id": "n3", "evidence_id": "derived", "derivation": "T1.r1.d1 - T1.r2.d1",
                      "value": 0.023, "tolerance": 0.0005}, ev)
    assert fact.operands == frozenset({"T1.r1.d1", "T1.r2.d1"})
    right = (Assertion("2.3", 2.3), Mapping("cell", "T1.r1.d1 - T1.r2.d1", scale=100))
    v = check_assertion(*right, ev)
    assert fact_reported(fact, [(*right, v)])
    # same value from different operands does not count
    other = RequiredFact("x", 0.023, 0.0005, frozenset({"T1.r1.d2", "T1.r2.d2"}))
    assert not fact_reported(other, [(*right, v)])
    # an incorrect assertion never reports a fact
    wrong = (Assertion("2.9", 2.9), Mapping("cell", "T1.r1.d1 - T1.r2.d1", scale=100))
    assert not fact_reported(fact, [(*wrong, check_assertion(*wrong, ev))])


def test_gold_fact_written_with_numbers_resolves_operands(ev):
    f = gold_fact({"fact_id": "n9", "evidence_id": "derived", "derivation": "(241 − 112) / 241 × 100",
                   "value": 53.5, "tolerance": 0.6}, ev)
    assert f.operands == frozenset({"T1.r1.lat", "T1.r2.lat"})
