"""Blind packet construction and integrity checks on FAKE run outputs (test fixtures only)."""
import csv
import json

import pytest

from evaluation.blinding import SYN_FIELDS, build_synthetic_packet, read_csv, verify_packet
from src.package_schema import CaseRecord

CONDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]


def _write_fake_runs(root, case_ids, failed=("UNIT-2", "C3"), mock=False):
    for cid in case_ids:
        for c in CONDS:
            # identical texts across conditions, as happens when a verifier accepts everything
            text = {"C1": "A is better.", "C2": "A is higher.", "C6": "A is better.",
                    "C7": "A is better on D.", "C3": "A is better on D.", "C4": "A is better on D.",
                    "C5": "A is better on D."}[c] + f" ({cid})"
            st = "failed" if (cid, c) == failed else "completed"
            rr = {"run_id": f"tag:{c}:{cid}", "case_id": cid, "condition": c, "status": st,
                  "final_passage": text if st == "completed" else "", "is_mock": mock}
            p = root / c / f"{cid}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rr))


@pytest.fixture
def setup(tmp_path, record):
    cases = []
    for i in range(3):
        d = record.model_dump()
        d["case_id"] = f"UNIT-{i}"
        cases.append(CaseRecord.model_validate(d))
    rub = {c.case_id: {"case_id": c.case_id, "focal_proposition": "A outperforms B.",
                       "level_descriptors": {"0": "no", "1": "desc", "2": "sig"},
                       "required_findings": [{"finding_id": "f1", "description": "means"}], "numeric_facts": []}
           for c in cases}
    runs = tmp_path / "runs"
    _write_fake_runs(runs, [c.case_id for c in cases])
    ann, priv = tmp_path / "annotation", tmp_path / "private"
    meta = build_synthetic_packet(runs, cases, rub, CONDS, ann, priv)
    return tmp_path, runs, ann, priv, meta


def test_packet_counts_dedupe_and_mapping(setup):
    tmp, runs, ann, priv, meta = setup
    assert meta["n_condition_case_runs"] == 21 and meta["n_completed"] == 20 and meta["n_failed_or_missing"] == 1
    assert meta["n_packet_rows"] == 9  # 3 distinct texts per case
    mapping = read_csv(priv / "condition_mapping.csv")
    assert len(mapping) == 21
    failed = [m for m in mapping if m["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["output_id"] == ""
    # C3/C4/C5/C7 share one row per case (identical text) -> same output_id
    for cid in ("UNIT-0", "UNIT-1"):
        ids = {m["output_id"] for m in mapping if m["case_id"] == cid and m["condition"] in ("C3", "C4", "C5", "C7")}
        assert len(ids) == 1


def test_integrity_passes_and_blinding(setup):
    tmp, runs, ann, priv, meta = setup
    assert verify_packet(ann, priv, runs) == []
    A = read_csv(ann / "annotator_A_template.csv")
    header = (ann / "annotator_A_template.csv").read_text().splitlines()[0]
    assert "condition" not in header.lower() and "run_id" not in header
    for r in A:
        assert all(r[f] == "" for f in SYN_FIELDS)
        assert r["output_id"][0] == "S" and len(r["output_id"]) == 9
    viewer = (ann / "viewer_annotator_A.html").read_text()
    for leak in ("C1", "C4", "Full agent", "verifier", "deepseek", "run_id"):
        assert leak not in viewer
    pkg = (ann / "packages_synthetic" / "UNIT-0.md").read_text()
    assert "Focal proposition" in pkg and "gold" not in pkg.lower()


def test_integrity_detects_tampering(setup):
    tmp, runs, ann, priv, meta = setup
    rows = read_csv(ann / "blinded_synthetic.csv")
    rows[0]["output_text"] = rows[0]["output_text"] + " Extra."
    with open(ann / "blinded_synthetic.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    errs = verify_packet(ann, priv, runs)
    assert any("differs from stored output" in e for e in errs)


def test_missing_private_mapping_fails_loudly(setup):
    tmp, runs, ann, priv, meta = setup
    (priv / "condition_mapping.csv").unlink()
    assert "refusing to release" in verify_packet(ann, priv, runs)[0]


def test_prefilled_fields_detected(setup):
    tmp, runs, ann, priv, meta = setup
    rows = read_csv(ann / "annotator_B_template.csv")
    rows[0]["expressed_level"] = "2"
    with open(ann / "annotator_B_template.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert any("pre-filled" in e for e in verify_packet(ann, priv, runs))


def test_mock_outputs_refused(tmp_path, record):
    runs = tmp_path / "runs"
    _write_fake_runs(runs, ["UNIT-1"], mock=True)
    with pytest.raises(ValueError):
        build_synthetic_packet(runs, [record], {}, CONDS, tmp_path / "a", tmp_path / "p")
