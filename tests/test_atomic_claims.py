"""Atomic-claim parsing, disagreement detection, final labels and claim-level metrics."""
from __future__ import annotations

import pytest

from evaluation import atomic_claims as ac
from evaluation.extended_pipeline import expand_readings, localize, representatives
from tests.test_numeric_fidelity import ev  # noqa: F401  (fixture)

SENT = "A reached 0.837 on Data-1 versus 0.814 for B, and A is significantly better."


def extraction():
    return {"units": [{"unit_id": "U-1", "claims": [
        {"span": "A reached 0.837 on Data-1 versus 0.814 for B", "proposition": "A (0.837) beats B (0.814) on Data-1.",
         "claim_type": "comparison", "entities": ["A", "B"], "metrics": [], "datasets": ["Data-1"], "qualifiers": [],
         "numbers": [{"as_written": "0.837", "value": 0.837, "comparator": "=", "approximate": False, "role": "result", "unit": None},
                     {"as_written": "0.814", "value": 0.814, "comparator": "=", "approximate": False, "role": "result", "unit": None}]},
        {"span": "A is significantly better", "proposition": "A is significantly better than B on Data-1.",
         "claim_type": "statistical_significance", "entities": ["A", "B"], "metrics": [], "datasets": [],
         "qualifiers": ["significantly"], "numbers": []}]}]}


def reading(label="SUPPORTED", ent="ENTAILED", maps=None, flag="OK"):
    return {"label": label, "entailment": ent, "error_subtype": None, "evidence_ids": ["T1.r1.d1"], "justification": "x",
            "confidence": "high", "extraction_flag": flag, "consistent": ac.consistent(label, ent),
            "numbers": maps or {}}


def test_multiple_claims_in_one_sentence_get_stable_ids():
    claims = ac.parse_extraction(extraction(), {"U-1": SENT}, "synthetic", "K01")
    assert [c["claim_id"] for c in claims] == ["U-1.c1", "U-1.c2"]
    assert [n["number_id"] for n in claims[0]["numbers"]] == ["U-1.c1.n1", "U-1.c1.n2"]
    assert all(c["span_verbatim"] for c in claims)
    assert ac.extraction_problems(extraction(), {"U-1": SENT, "U-2": "other"})  # a missing unit is a problem


def test_label_entailment_consistency():
    assert ac.consistent("SUPPORTED", "ENTAILED")
    assert not ac.consistent("SUPPORTED", "CONTRADICTED")
    assert ac.consistent("UNDERSTATED", "CONTRADICTED")
    assert not ac.consistent("NOT_VERIFIABLE", "ENTAILED")


def _claims():
    return ac.parse_extraction(extraction(), {"U-1": SENT}, "synthetic", "K01")


def test_numeric_error_comes_from_the_checker_not_the_label(ev):  # noqa: F811
    c = _claims()[0]
    good = {"U-1.c1.n1": {"source_type": "cell", "expression": "T1.r1.d1", "quote": None, "scale": 1},
            "U-1.c1.n2": {"source_type": "cell", "expression": "T1.r2.d1", "quote": None, "scale": 1}}
    rec = ac.finalize_claim(c, reading(maps=good), reading(maps=good), ev)
    assert rec["final_label"] == "SUPPORTED" and rec["factual_error"] is False
    c_bad = dict(c, numbers=[dict(c["numbers"][0], as_written="0.85", value=0.85), c["numbers"][1]])
    rec = ac.finalize_claim(c_bad, reading(maps=good), reading(maps=good), ev)
    assert rec["final_label"] == "NUMERIC_ERROR" and rec["factual_error"] is True


def test_disagreements_are_detected_and_require_adjudication(ev):  # noqa: F811
    c = _claims()[1]
    a, b = reading("OVERSTATED", "NOT_ENTAILED"), reading("SUPPORTED", "ENTAILED")
    d = ac.claim_disputes(c, a, b, ev)
    assert set(d.fields) == {"label", "entailment"}
    with pytest.raises(ValueError):
        ac.finalize_claim(c, a, b, ev, None)
    adj = {"label": "OVERSTATED", "entailment": "NOT_ENTAILED", "extraction_valid": True, "numbers": [],
           "evidence_ids": ["S1"], "_reading_map": {"1": "B", "2": "A"}}
    rec = ac.finalize_claim(c, a, b, ev, adj)
    assert rec["final_label"] == "OVERSTATED" and rec["factual_error"] is True


def test_unresolved_and_excluded_claims_leave_denominators(ev):  # noqa: F811
    c = _claims()[1]
    a, b = reading("OVERSTATED", "NOT_ENTAILED", flag="NOT_IN_TEXT"), reading("SUPPORTED", "ENTAILED")
    adj = {"label": "UNRESOLVED", "entailment": "UNRESOLVED", "extraction_valid": True, "numbers": [],
           "evidence_ids": [], "_reading_map": {"1": "A", "2": "B"}}
    rec = ac.finalize_claim(c, a, b, ev, adj)
    assert rec["final_label"] == "UNRESOLVED"
    rec2 = ac.finalize_claim(c, a, b, ev, dict(adj, label="SUPPORTED", entailment="ENTAILED", extraction_valid=False))
    assert rec2["final_label"] == "EXCLUDED"
    counts = ac.claim_counts([rec, rec2])
    assert counts["n_assessable"] == 0 and counts["n_unresolved"] == 1 and counts["n_excluded"] == 1


def test_numeric_dispute_uses_adjudicated_mapping(ev):  # noqa: F811
    c = _claims()[0]
    good = {"U-1.c1.n1": {"source_type": "cell", "expression": "T1.r1.d1", "quote": None, "scale": 1},
            "U-1.c1.n2": {"source_type": "cell", "expression": "T1.r2.d1", "quote": None, "scale": 1}}
    wrong = dict(good, **{"U-1.c1.n2": {"source_type": "cell", "expression": "T1.r1.d1", "quote": None, "scale": 1}})
    a, b = reading(maps=good), reading(maps=wrong)
    assert ac.claim_disputes(c, a, b, ev).numbers == ["U-1.c1.n2"]
    adj = {"label": "SUPPORTED", "entailment": "ENTAILED", "extraction_valid": True, "evidence_ids": [],
           "numbers": [{"number_id": "U-1.c1.n2", "choice": "2", "source_type": "none", "expression": None,
                        "quote": None, "scale": 1}], "_reading_map": {"1": "B", "2": "A"}}
    rec = ac.finalize_claim(c, a, b, ev, adj)  # reading 2 is judge A's (correct) mapping
    assert rec["final_label"] == "SUPPORTED"
    assert rec["numbers"][1]["mapping_source"] == "adjudicated:A"


def test_text_with_no_assessable_claims_is_not_fully_supported():
    s = ac.text_claim_summary({}, ["U-9"])
    assert s["fully_supported"] == 0 and s["no_assessable_claims"] == 1 and s["all"]["n_assessable"] == 0


def test_text_summary_aggregates_shared_sentence_units():
    mk = lambda cid, u, lab: {"claim_id": cid, "unit_id": u, "final_label": lab, "factual_error": lab != "SUPPORTED",  # noqa: E731
                              "result_claim": True, "numbers": []}
    by_unit = {"U-1": [mk("a", "U-1", "SUPPORTED")], "U-2": [mk("b", "U-2", "OVERSTATED")]}
    s1, s2 = ac.text_claim_summary(by_unit, ["U-1"]), ac.text_claim_summary(by_unit, ["U-1", "U-2"])
    assert s1["fully_supported"] == 1 and s2["fully_supported"] == 0
    assert s2["all"]["n_overstated"] == 1 and s2["all"]["n_factual_error"] == 1


def test_dedup_copies_readings_to_identical_claims_and_local_ids_round_trip():
    base = _claims()[1]
    twin = dict(base, claim_id="U-2.c1", unit_id="U-2", numbers=[])
    reps, rep_of = representatives([base, twin])
    assert len(reps) == 1 and rep_of["U-2.c1"] == base["claim_id"]
    out = expand_readings({base["claim_id"]: reading("OVERSTATED", "NOT_ENTAILED")}, [base, twin], rep_of)
    assert out["U-2.c1"]["label"] == "OVERSTATED" and out["U-2.c1"]["copied_from"] == base["claim_id"]
    local, back = localize(_claims())
    assert [c["claim_id"] for c in local] == ["c1", "c2"] and back["c1.n2"] == "U-1.c1.n2"
