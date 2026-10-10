"""Blind packet construction and integrity checks on FAKE run outputs (test fixtures only)."""
import csv
import json

import pytest

from evaluation.blinding import (PASS1_FIELDS, PASS2_FIELDS, MappingExistsError, build_real_packet,
                                 build_synthetic_packet, read_csv, verify_packet)
from src.package_schema import CaseRecord

CONDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]


def _write_fake_runs(root, case_ids, failed=("UNIT-2", "C3"), mock=False, conds=CONDS):
    for cid in case_ids:
        for c in conds:
            # identical texts across conditions, as happens when a verifier accepts everything
            text = {"C1": "A is better.", "C2": "A is higher.", "C6": "A is better.",
                    "C7": "A is better on D.", "C3": "A is better on D.", "C4": "A is better on D.",
                    "C5": "A is better on D."}[c] + f" (variant {cid[-1]}) Second sentence here."
            st = "failed" if (cid, c) == failed else "completed"
            rr = {"run_id": f"tag:{c}:{cid}", "case_id": cid, "condition": c, "status": st,
                  "final_passage": text if st == "completed" else "", "is_mock": mock}
            p = root / c / f"{cid}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rr))


def _cases(record, n=3, category="statistical_significance"):
    out = []
    for i in range(n):
        d = record.model_dump()
        d["case_id"] = f"UNIT-{i}"
        d["category"] = category
        out.append(CaseRecord.model_validate(d))
    return out


RUB = {f"UNIT-{i}": {"case_id": f"UNIT-{i}", "focal_proposition": "A outperforms B.",
                     "level_descriptors": {"0": "no", "1": "desc", "2": "sig"},
                     "required_findings": [{"finding_id": "f1", "description": "difference is statistically significant"}],
                     "numeric_facts": []} for i in range(3)}


@pytest.fixture
def setup(tmp_path, record):
    cases = _cases(record)
    runs = tmp_path / "runs"
    _write_fake_runs(runs, [c.case_id for c in cases])
    ann, priv = tmp_path / "annotation", tmp_path / "private"
    meta = build_synthetic_packet(runs, cases, RUB, CONDS, ann, priv)
    return tmp_path, runs, ann, priv, meta


def test_packet_counts_dedupe_and_mapping(setup):
    tmp, runs, ann, priv, meta = setup
    assert meta["n_condition_case_runs"] == 21 and meta["n_completed"] == 20 and meta["n_failed_or_missing"] == 1
    assert meta["n_packet_rows"] == 9  # 3 distinct texts per case
    mapping = read_csv(priv / "condition_mapping.csv")
    assert len(mapping) == 21
    failed = [m for m in mapping if m["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["output_id"] == ""
    for cid in ("UNIT-0", "UNIT-1"):
        ids = {m["output_id"] for m in mapping if m["case_id"] == cid and m["condition"] in ("C3", "C4", "C5", "C7")}
        assert len(ids) == 1
    alias = read_csv(priv / "case_alias_map.csv")
    assert sorted(a["case_ref"] for a in alias) == ["K01", "K02", "K03"]


def test_integrity_passes_and_blinding(setup):
    tmp, runs, ann, priv, meta = setup
    assert verify_packet(ann, priv, runs) == []
    for part, fields in (("pass1", PASS1_FIELDS), ("pass2", PASS2_FIELDS)):
        rows = read_csv(ann / part / f"annotator_A_{part}.csv")
        header = (ann / part / f"annotator_A_{part}.csv").read_text().splitlines()[0]
        assert "condition" not in header.lower() and "run_id" not in header and "case_id" not in header
        for r in rows:
            assert all(r[f] == "" for f in fields)
            assert r["output_id"][0] == "S" and len(r["output_id"]) == 9 and r["case_ref"].startswith("K")
    viewer = (ann / "pass1" / "viewer_annotator_A_pass1.html").read_text()
    for leak in ("C1", "C4", "Full agent", "verifier", "deepseek", "run_id", "UNIT-", "difference is statistically"):
        assert leak not in viewer
    p1 = (ann / "pass1" / "packages" / "K01.md").read_text()
    assert "Focal proposition" in p1 and "checklist" not in p1.lower() and "gold" not in p1.lower()
    p2 = (ann / "pass2" / "packages" / "K01.md").read_text()
    assert "Required-findings checklist" in p2


def test_integrity_detects_tampering_and_checklist_leak(setup):
    tmp, runs, ann, priv, meta = setup
    rows = read_csv(ann / "blinded_synthetic.csv")
    rows[0]["output_text"] += " Extra."
    with open(ann / "blinded_synthetic.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (ann / "pass1" / "packages" / "K02.md").write_text("Required-findings checklist: f1 ...")
    errs = verify_packet(ann, priv, runs)
    assert any("differs from stored output" in e for e in errs)
    assert any("contains a pass-2 checklist" in e for e in errs)


def test_missing_private_mapping_fails_loudly(setup):
    tmp, runs, ann, priv, meta = setup
    (priv / "condition_mapping.csv").unlink()
    assert "refusing to release" in verify_packet(ann, priv, runs)[0]


def test_rebuild_refuses_to_overwrite_mapping(setup, record):
    tmp, runs, ann, priv, meta = setup
    with pytest.raises(MappingExistsError):
        build_synthetic_packet(runs, _cases(record), RUB, CONDS, ann, priv)
    build_synthetic_packet(runs, _cases(record), RUB, CONDS, ann, priv, force=True)
    assert list(priv.glob("condition_mapping.backup_*.csv"))


def test_prefilled_fields_detected(setup):
    tmp, runs, ann, priv, meta = setup
    f = ann / "pass2" / "annotator_B_pass2.csv"
    rows = read_csv(f)
    rows[0]["findings_covered"] = "f1"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert any("pre-filled" in e for e in verify_packet(ann, priv, runs))


def test_mock_outputs_refused(tmp_path, record):
    runs = tmp_path / "runs"
    _write_fake_runs(runs, ["UNIT-1"], mock=True)
    with pytest.raises(ValueError):
        build_synthetic_packet(runs, [record], {}, CONDS, tmp_path / "a", tmp_path / "p")


def test_real_packet_sentence_rows(tmp_path, record):
    runs = tmp_path / "runs"
    _write_fake_runs(runs, ["UNIT-0"], failed=None, conds=["C1", "C2", "C3", "C4"])
    cases = _cases(record, 1)
    meta = build_real_packet(runs, cases, ["C1", "C2", "C3", "C4"], tmp_path / "ann", tmp_path / "priv")
    assert meta["n_packet_rows"] == 3 and meta["n_sentence_rows"] == 6
    assert verify_packet(tmp_path / "ann", tmp_path / "priv", runs, kind="real") == []
