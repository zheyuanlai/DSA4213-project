"""Merge / kappa / adjudication / human scoring on SYNTHETIC DUMMY LABELS.

!!! These labels are TEST FIXTURES invented for unit tests. They are NOT human annotations and
!!! must never be reported as observations.
"""
import pytest

from evaluation.merge_annotations import agreement, cohen_kappa, consensus, disagreements, validate
from evaluation.score_human import score, transition

FIXTURE_NOTE = "DUMMY TEST FIXTURE — not real annotation"


def test_kappa_known_values():
    assert cohen_kappa([0, 1, 2, 2], [0, 1, 2, 2]) == pytest.approx(1.0)
    # classic 2x2 example: po=0.7, pe=0.5 -> kappa=0.4
    a = [1] * 25 + [1] * 25 + [0] * 10 + [0] * 40
    b = [1] * 25 + [0] * 25 + [1] * 5 + [0] * 45
    po = (25 + 45) / 100
    pa1, pb1 = 0.5, 0.3
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    assert cohen_kappa(a, b, [0, 1]) == pytest.approx((po - pe) / (1 - pe))
    # weighted kappa penalises 0<->2 more than 0<->1
    x = [0, 0, 1, 2, 2, 1]
    y1 = [1, 0, 1, 2, 2, 1]
    y2 = [2, 0, 1, 2, 2, 1]
    assert cohen_kappa(x, y1, [0, 1, 2], "quadratic") > cohen_kappa(x, y2, [0, 1, 2], "quadratic")


def _row(oid, case, cat, lv="", fa="", fc="", uns="0", ne="0", nf="", nr="", nrp="", conf="high"):
    return {"output_id": oid, "case_id": case, "category": cat, "expressed_level": lv, "focal_addressed": fa,
            "findings_covered": fc, "unsupported_claims": uns, "numeric_errors": ne, "num_facts_correct": nf,
            "neg_findings_reported": nr, "neg_reframed_positive": nrp, "confidence_p1": conf, "confidence_p2": conf,
            "notes_p1": FIXTURE_NOTE, "notes_p2": FIXTURE_NOTE}


RUBRIC = {"SIG-x": {"required_findings": [{"finding_id": "f1"}, {"finding_id": "f2"}], "numeric_facts": []},
          "NEG-x": {"required_findings": [{"finding_id": "f1"}, {"finding_id": "f2"}], "numeric_facts": []}}
CAT = {"S1": "statistical_significance", "S2": "statistical_significance", "S3": "negative_results"}
CASE = {"S1": "SIG-x", "S2": "SIG-x", "S3": "NEG-x"}


def test_validation_catches_errors():
    rows = [_row("S1", "SIG-x", CAT["S1"], lv="3", fa="yes"), _row("S2", "SIG-x", CAT["S2"], lv="2", fa="no"),
            _row("S3", "NEG-x", CAT["S3"], lv="1", nrp="maybe", fc="f9")]
    errs = validate(rows, {"S1", "S2", "S3", "S4"}, RUBRIC, CAT, CASE, "A")
    joined = "\n".join(errs)
    assert "missing" in joined and "0/1/2" in joined and "focal_addressed=no" in joined
    assert "blank for negative_results" in joined and "unknown ids" in joined and "yes/no" in joined


def test_agreement_disagreement_consensus():
    A = {"S1": _row("S1", "SIG-x", CAT["S1"], "2", "yes", "f1;f2"), "S2": _row("S2", "SIG-x", CAT["S2"], "1", "yes", "f1"),
         "S3": _row("S3", "NEG-x", CAT["S3"], fc="f1", nr="f2", nrp="no")}
    B = {"S1": _row("S1", "SIG-x", CAT["S1"], "2", "yes", "f2;f1"), "S2": _row("S2", "SIG-x", CAT["S2"], "0", "yes", "f1"),
         "S3": _row("S3", "NEG-x", CAT["S3"], fc="f1", nr="", nrp="no")}
    ag = agreement(A, B, RUBRIC, CAT, CASE)
    assert ag["expressed_level"]["n"] == 2 and ag["expressed_level"]["pct_agree"] == 0.5
    dis = disagreements(A, B)
    assert {(d["output_id"], d["field"]) for d in dis} == {("S2", "expressed_level"), ("S3", "neg_findings_reported")}
    rows, errs = consensus(A, B, [])
    assert len(errs) == 2
    adj = [dict(d, adjudicated_value="1") if d["field"] == "expressed_level" else dict(d, adjudicated_value="NONE") for d in dis]
    rows, errs = consensus(A, B, adj)
    assert not errs
    r = {x["output_id"]: x for x in rows}
    assert r["S2"]["expressed_level"] == "1" and r["S3"]["neg_findings_reported"] == "" and r["S1"]["findings_covered"] == "f1;f2"


def test_transition_categories():
    assert transition(2, 1, 1) == "over->correct (fix)"
    assert transition(1, 2, 2) == "under->correct (fix)"
    assert transition(2, 1, 2) == "correct->under (harmful)"
    assert transition(1, 2, 1) == "correct->over (harmful)"
    assert transition(1, 1, 1) == "correct->correct"
    assert transition(2, 2, 0) == "over->over (unchanged)"


def test_score_end_to_end_dummy():
    gold = {"SIG-p2a": {"case_id": "SIG-p2a", "category": "statistical_significance", "gold_level": 1,
                        "required_findings": [{"finding_id": "f1", "polarity": "positive"}]},
            "SIG-p2b": {"case_id": "SIG-p2b", "category": "statistical_significance", "gold_level": 2,
                        "required_findings": [{"finding_id": "f1", "polarity": "positive"}]}}
    rubric = {k: {"required_findings": [{"finding_id": "f1"}], "numeric_facts": []} for k in gold}
    cons = [  # DUMMY consensus labels (fixtures)
        {"output_id": "Sa", "expressed_level": "2", "focal_addressed": "yes", "findings_covered": "f1", "unsupported_claims": "1", "numeric_errors": "0"},
        {"output_id": "Sb", "expressed_level": "1", "focal_addressed": "yes", "findings_covered": "f1", "unsupported_claims": "0", "numeric_errors": "0"},
        {"output_id": "Sc", "expressed_level": "2", "focal_addressed": "yes", "findings_covered": "", "unsupported_claims": "0", "numeric_errors": "0"},
    ]
    mapping = [
        {"output_id": "Sa", "case_id": "SIG-p2a", "condition": "C7", "status": "completed"},  # draft overstated
        {"output_id": "Sb", "case_id": "SIG-p2a", "condition": "C4", "status": "completed"},  # fixed
        {"output_id": "Sb", "case_id": "SIG-p2b", "condition": "C7", "status": "completed"},  # understated
        {"output_id": "Sc", "case_id": "SIG-p2b", "condition": "C4", "status": "completed"},  # strengthened -> correct
        {"output_id": "", "case_id": "SIG-p2a", "condition": "C5", "status": "failed"},
        {"output_id": "Sb", "case_id": "SIG-p2b", "condition": "C5", "status": "completed"},
    ]
    res = score(cons, mapping, gold, rubric, itt=True)
    s = res["summary"]
    assert s["C4"]["calibration_accuracy"] == 1.0 and s["C7"]["calibration_accuracy"] == 0.0
    assert s["C7"]["overstatement_rate"] == 0.5 and s["C7"]["understatement_rate"] == 0.5
    assert s["C5"]["n_missing_outputs"] == 1  # ITT keeps the failed run in the denominator
    assert res["transitions"]["C7->C4"] == {"over->correct (fix)": 1, "under->correct (fix)": 1}
    co = score(cons, mapping, gold, rubric, itt=False)
    assert co["summary"]["C5"]["n_ordinal"] == 1


def test_score_refuses_missing_or_invalid_labels():
    gold = {"SIG-p2a": {"case_id": "SIG-p2a", "category": "statistical_significance", "gold_level": 1,
                        "required_findings": [{"finding_id": "f1", "polarity": "positive"}]}}
    rubric = {"SIG-p2a": {"required_findings": [{"finding_id": "f1"}], "numeric_facts": []}}
    mapping = [{"output_id": "Sa", "case_id": "SIG-p2a", "condition": "C4", "status": "completed"},
               {"output_id": "Sb", "case_id": "SIG-p2a", "condition": "C7", "status": "completed"}]
    cons = [{"output_id": "Sa", "expressed_level": "1", "focal_addressed": "yes", "findings_covered": "f1",
             "unsupported_claims": "0", "numeric_errors": "0"}]  # Sb missing (DUMMY fixture)
    with pytest.raises(ValueError, match="no consensus label"):
        score(cons, mapping, gold, rubric)
    cons.append({"output_id": "Sb", "expressed_level": "3", "focal_addressed": "yes", "findings_covered": "",
                 "unsupported_claims": "0", "numeric_errors": "0"})
    with pytest.raises(ValueError, match="invalid consensus"):
        score(cons, mapping, gold, rubric)


def test_consensus_values_validated():
    from evaluation.merge_annotations import validate_consensus_row
    assert validate_consensus_row({"output_id": "S1", "expressed_level": "3", "focal_addressed": "yes",
                                   "unsupported_claims": "0", "numeric_errors": "0"}, "statistical_significance")
    assert not validate_consensus_row({"output_id": "S1", "expressed_level": "", "focal_addressed": "",
                                       "unsupported_claims": "1", "numeric_errors": "0"}, "negative_results")


def test_real_paper_merge_and_score_dummy(tmp_path, record):
    """DUMMY fixture labels only: exercises validate -> agreement -> adjudication -> consensus -> score."""
    import csv as _csv
    import json as _json
    from evaluation.blinding import build_real_packet, read_csv
    from evaluation.score_real_papers import merge, score
    from src.package_schema import CaseRecord
    runs = tmp_path / "runs"
    for c, text in (("C1", "A is better. It is fast."), ("C2", "A is higher. It is fast."),
                    ("C3", "A is better. It is fast."), ("C4", "A is better on D. It is fast.")):
        p = runs / c / "RP-01.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_json.dumps({"run_id": f"t:{c}:RP-01", "case_id": "RP-01", "condition": c, "status": "completed",
                                  "final_passage": text, "is_mock": False}))
    d = record.model_dump()
    d.update(case_id="RP-01", category=None, split="real")
    rec = CaseRecord.model_validate(d)
    ann, priv = tmp_path / "ann", tmp_path / "priv"
    build_real_packet(runs, [rec], ["C1", "C2", "C3", "C4"], ann, priv)

    def fill(src, dst, f):
        rows = read_csv(src)
        for r in rows:
            f(r)
        with open(dst, "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    for who in ("A", "B"):
        fill(ann / "real" / f"annotator_{who}_real.csv", tmp_path / f"{who}_o.csv",
             lambda r: r.update(readability="4" if who == "A" else "3", overall_calibration="well_calibrated", confidence="high"))
        fill(ann / "real" / f"annotator_{who}_real_sentences.csv", tmp_path / f"{who}_s.csv",
             lambda r: r.update(support_label="SUPPORTED"))
    out = tmp_path / "agree"
    assert merge([tmp_path / "A_o.csv", tmp_path / "A_s.csv"], [tmp_path / "B_o.csv", tmp_path / "B_s.csv"], out, None, ann / "real") == 0
    adj = read_csv(out / "adjudication_real.csv")
    assert adj and all(r["field"] == "readability" for r in adj)
    fill(out / "adjudication_real.csv", tmp_path / "adj.csv", lambda r: r.update(adjudicated_value="4"))
    assert merge([tmp_path / "A_o.csv", tmp_path / "A_s.csv"], [tmp_path / "B_o.csv", tmp_path / "B_s.csv"], out,
                 tmp_path / "adj.csv", ann / "real") == 0
    res = score(read_csv(out / "consensus_real_outputs.csv"), read_csv(out / "consensus_real_sentences.csv"),
                read_csv(priv / "condition_mapping_real.csv"))
    assert res["summary"]["C4"]["supported_rate"] == 1.0 and res["summary"]["C1"]["readability"] == 4
