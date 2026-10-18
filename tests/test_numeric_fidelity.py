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


def test_number_words_in_quoted_prose(ev):
    assert chk(ev, "five", 5, Mapping("text", quote="Two datasets, 5 seeds."), role="setup") == "CORRECT"
    assert chk(ev, "two", 2, Mapping("text", quote="Two datasets, 5 seeds."), role="setup") == "CORRECT"
    assert chk(ev, "three", 3, Mapping("text", quote="Two datasets, 5 seeds."), role="setup") == "VALUE_MISMATCH"
    # prose without any number cannot verify an implicit count
    assert chk(ev, "single", 1, Mapping("text", quote="The prior method reduced latency"), role="setup") == "INVALID_MAPPING"


def test_implicit_word_counts_are_not_checkable_but_digit_values_are(ev):
    q = "The prior method reduced latency by 31% on news."
    assert chk(ev, "single", 1, Mapping("text", quote=q), role="setup") == "INVALID_MAPPING"
    assert chk(ev, "30%", 30, Mapping("text", quote=q), role="cited") == "VALUE_MISMATCH"


def test_quotes_ignore_markdown_and_text_spreads_resolve(ev):
    # the rendered column legend shows `d1` = Data-1 with backticks; a judge may copy it without them
    assert chk(ev, "112", 112, Mapping("cell", "T1.r1.lat")) == "CORRECT"
    assert chk(ev, "0.004", 0.004, Mapping("cell", "T1.r1.d1.spread"), role="statistical") == "CORRECT"
    q = "d1 = Data-1 (higher is better)"
    assert check_assertion(Assertion("1", 1, role="setup"), Mapping("text", quote=q), ev).status in ("CORRECT", "VALUE_MISMATCH")


def test_aggregate_fact_is_reported_by_its_attaining_cell(ev):
    f = RequiredFact("best", 0.837, 0.0005, frozenset({"T1.r1.d1", "T1.r2.d1"}))  # max over the Data-1 column
    a, m = Assertion("0.837", 0.837), Mapping("cell", "T1.r1.d1")
    assert fact_reported(f, [(a, m, check_assertion(a, m, ev))])
    a2, m2 = Assertion("0.837", 0.837), Mapping("text", quote="0.837 ± 0.004")  # no operands: not evidence-linked
    assert not fact_reported(f, [(a2, m2, check_assertion(a2, m2, ev))])


def _pkg_with(cells_r1, cells_r2, caption="Scores.", extra_cols=("a",)):
    cols = [{"column_id": c, "header": c.upper(), "higher_is_better": True} for c in extra_cols]
    return EvidenceValues.from_package(ResearchPackage.model_validate({
        "question": "Q?", "methods_summary": "M.", "experimental_setup": "Run in 2020 on two datasets.",
        "results_tables": [{"table_id": "T1", "caption": caption, "columns": cols,
                            "rows": [{"row_id": "r1", "label": "A", "cells": cells_r1},
                                     {"row_id": "r2", "label": "B", "cells": cells_r2}]}],
        "task_instruction": "Write."}))


def test_displayed_gain_in_cell_text_is_accepted_but_sd_parenthetical_is_not_a_gain():
    ev2 = _pkg_with({"a": {"text": "22.51 (2.33 ↑)", "value": 22.51}}, {"a": {"text": "20.17", "value": 20.17}},
                    caption="Mean ROUGE-L; gain over the base loss in parentheses.")
    a = Assertion("2.33", 2.33, role="derived")
    assert check_assertion(a, Mapping("cell", "T1.r1.a - T1.r2.a"), ev2).status == "CORRECT"
    ev3 = _pkg_with({"a": {"text": "66.2 (4.9)", "value": 66.2}}, {"a": {"text": "61.3", "value": 61.3}},
                    caption="Accuracy, mean over 5 splits, standard deviation in parentheses.")
    assert "T1.r1.a.spread" in ev3.values and ev3.values["T1.r1.a.spread"].value == 4.9
    b = Assertion("4.8", 4.8, role="derived")  # true gain is 4.9: the SD must not rescue a wrong gain
    assert check_assertion(Assertion("4.9", 4.9, role="derived"), Mapping("cell", "T1.r1.a - T1.r2.a"), ev3).correct
    assert not check_assertion(b, Mapping("cell", "T1.r1.a - T1.r2.a"), ev3).correct


def test_scientific_notation_and_exact_bounds(ev):
    ev2 = _pkg_with({"a": {"text": "1.2e-4", "value": 0.00012}}, {"a": {"text": "5.1e-3", "value": 0.0051}})
    assert check_assertion(Assertion("1.2e-4", 0.00012), Mapping("cell", "T1.r1.a"), ev2).correct
    assert not check_assertion(Assertion("2.8e-4", 0.00028), Mapping("cell", "T1.r1.a"), ev2).correct
    # p = 0.036 satisfies "p < 0.05"; a bound is compared exactly, without rounding slack
    assert check_assertion(Assertion("p < 0.05", 0.05, role="statistical"), Mapping("test", "S1", comparator="<"), ev).correct
    assert not check_assertion(Assertion("p < 0.03", 0.03, role="statistical"), Mapping("test", "S1", comparator="<"), ev).correct
    assert not check_assertion(Assertion("p < 0.035", 0.035, role="statistical"), Mapping("test", "S1", comparator="<"), ev).correct
    # a year in quoted prose is not a bound on a quantity
    assert check_assertion(Assertion("more than 40", 40, role="setup"),
                           Mapping("text", quote="Run in 2020 on two datasets.", comparator=">"), ev2).status != "CORRECT"


def test_no_source_branch_does_not_turn_word_counts_or_bounds_into_errors(ev):
    assert check_assertion(Assertion("single", 1, role="setup"), Mapping("none"), ev).status == "INVALID_MAPPING"
    assert check_assertion(Assertion("p < 0.001", 0.001, role="statistical"), Mapping("none", comparator="<"), ev).status == "INVALID_MAPPING"
    assert check_assertion(Assertion("7.7", 7.7), Mapping("none"), ev).status == "FABRICATED"
