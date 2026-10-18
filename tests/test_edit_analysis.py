"""Verifier edit analysis: repairs, deletions, harmful and beneficial revisions, undefined denominators."""
from __future__ import annotations

from evaluation.edit_analysis import analyze_run, covered, decisive_retrieval, summarize


def cl(cid, unit, result=True):
    return {"claim_id": cid, "unit_id": unit, "result_claim": result}


BY_UNIT = {
    "U-d1": [cl("d1a", "U-d1"), cl("d1b", "U-d1")],
    "U-d2": [cl("d2a", "U-d2")],
    "U-same": [cl("s1", "U-same")],
    "U-f1": [cl("f1a", "U-f1")],
    "U-f2": [cl("f2a", "U-f2"), cl("f2b", "U-f2")],
}


def test_unchanged_text_has_no_edits_and_keeps_errors():
    labels = {"s1": "OVERSTATED"}
    r = analyze_run(["U-same"], ["U-same"], BY_UNIT, labels, None)
    assert r.initial_errors == 1 and r.retained_unedited == 1 and r.substantive_edits == 0
    s = summarize([r])
    assert s["repair_recall"] == 0.0
    assert s["edit_precision"] is None  # zero substantive edits: undefined, not 0 or 1
    assert s["unnecessary_weakening_rate"] is None


def test_beneficial_repair_and_harmful_weakening():
    labels = {"d1a": "OVERSTATED", "d1b": "SUPPORTED", "f1a": "SUPPORTED", "f2a": "UNDERSTATED", "s1": "SUPPORTED"}
    align = {"x_claims": [
        {"claim_id": "d1a", "relation": "MODIFIED", "direction": "WEAKENED", "matched_y": ["f1a"]},   # overstatement fixed
        {"claim_id": "d1b", "relation": "MODIFIED", "direction": "WEAKENED", "matched_y": ["f2a"]},   # correct -> understated
    ], "added_y": []}
    r = analyze_run(["U-d1", "U-same"], ["U-f1", "U-f2", "U-same"], BY_UNIT, labels, align)
    assert r.initial_errors == 1 and r.corrected == 1
    assert r.beneficial == 1 and r.harmful == 1 and r.substantive_edits == 2
    assert r.weakened == 2 and r.weakened_correct == 1 and r.new_errors == 1
    s = summarize([r])
    assert s["repair_recall"] == 1.0 and s["edit_precision"] == 0.5 and s["harmful_edit_rate"] == 0.5
    assert s["unnecessary_weakening_rate"] == 0.5


def test_deletion_of_error_is_a_removal_and_added_error_is_harmful():
    labels = {"d2a": "NUMERIC_ERROR", "f2a": "SUPPORTED", "f2b": "UNSUPPORTED"}
    align = {"x_claims": [{"claim_id": "d2a", "relation": "DELETED", "direction": None, "matched_y": []}],
             "added_y": ["f2a", "f2b"]}
    r = analyze_run(["U-d2"], ["U-f2"], BY_UNIT, labels, align)
    assert r.removed == 1 and r.numeric_fixed == 1 and r.corrected == 0
    assert r.harmful == 1 and r.new_unsupported == 1 and r.neutral == 1 and r.beneficial == 1
    s = summarize([r])
    assert s["repair_recall"] == 1.0 and s["repair_recall_corrected_only"] == 0.0


def test_deleting_correct_content_is_harmful_only_when_a_required_finding_is_lost():
    labels = {"d2a": "SUPPORTED"}
    align = {"x_claims": [{"claim_id": "d2a", "relation": "DELETED", "direction": None, "matched_y": []}], "added_y": []}
    lost = analyze_run(["U-d2"], [], BY_UNIT, labels, align, covered_draft={"f1", "f2"}, covered_final={"f1"})
    kept = analyze_run(["U-d2"], [], BY_UNIT, labels, align, covered_draft={"f1"}, covered_final={"f1"})
    assert lost.harmful == 1 and lost.findings_lost == 1 and lost.deleted_correct == 1
    assert kept.harmful == 0 and kept.neutral == 1


def test_retained_error_after_edit():
    labels = {"d2a": "UNSUPPORTED", "f1a": "OVERSTATED"}
    align = {"x_claims": [{"claim_id": "d2a", "relation": "MODIFIED", "direction": "WEAKENED", "matched_y": ["f1a"]}],
             "added_y": []}
    r = analyze_run(["U-d2"], ["U-f1"], BY_UNIT, labels, align)
    assert r.retained_edited == 1 and r.neutral == 1 and r.beneficial == 0


def test_decisive_evidence_retrieval_rules():
    trace = {"observations": [{"returned_ids": ["T1", "T1.r1.acc", "T1.r2.acc"]},
                              {"returned_ids": ["absent:test:exp1/cmp1"]}]}
    assert covered("T1.r1.acc", {"T1.r1.acc"}) and covered("T1.r1.acc", {"T1.r1"})
    assert not covered("T1.r3.acc", {"T1", "T1.r1.acc"})
    r = decisive_retrieval(trace, ["T1.r1.acc", "exp1/cmp1"], {})
    assert r["all"] and r["n_tool_calls"] == 2
    r2 = decisive_retrieval(trace, ["T1.r1.acc", "S1"], {"S1": "exp1/cmp1"})
    assert r2["any"] and not r2["all"]


def test_lost_findings_are_attributed_to_at_most_one_deletion_each():
    by_unit = {"U-a": [cl("a1", "U-a"), cl("a2", "U-a"), cl("a3", "U-a")]}
    labels = {"a1": "SUPPORTED", "a2": "SUPPORTED", "a3": "SUPPORTED"}
    align = {"x_claims": [{"claim_id": c, "relation": "DELETED", "direction": None, "matched_y": []} for c in ("a1", "a2", "a3")],
             "added_y": []}
    r = analyze_run(["U-a"], [], by_unit, labels, align, covered_draft={"f1", "f2"}, covered_final={"f2"})
    assert r.deleted_correct == 3 and r.harmful == 1 and r.neutral == 2


def test_unresolved_outcomes_leave_the_repair_denominator():
    labels = {"d2a": "OVERSTATED", "f1a": "UNRESOLVED"}
    align = {"x_claims": [{"claim_id": "d2a", "relation": "MODIFIED", "direction": "WEAKENED", "matched_y": ["f1a"]}],
             "added_y": []}
    r = analyze_run(["U-d2"], ["U-f1"], BY_UNIT, labels, align)
    assert r.unknown == 1 and summarize([r])["repair_recall"] is None
