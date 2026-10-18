"""Offline end-to-end run of the extension pipeline on a one-case fixture with mock judges (no paid inference).

Draft (an unverified text): "A scored 0.837 on Data-1 versus 0.814 for B. A is significantly better than B."
Final (a verified text):    the same first sentence, then "A scored higher than B on Data-1."
Judge A and Judge B disagree on the significance claim and on one number's mapping; the adjudicator resolves
both. The run must end with a corrected overstatement and no condition identity in any judge prompt.
"""
from __future__ import annotations

import json
import re

import pytest

from evaluation import extended_consensus as C
from evaluation import extended_pipeline as P
from evaluation import judges
from evaluation.edit_analysis import analyze_run, summarize
from evaluation.extended_data import Family, FamilyData, RunView, TextEntry, unit_id
from src.package_schema import CaseRecord
from tests.test_numeric_fidelity import ev  # noqa: F401  (fixture)

S1 = "A scored 0.837 on Data-1 versus 0.814 for B."
S2 = "A is significantly better than B."
S3 = "A scored higher than B on Data-1."


@pytest.fixture()
def fixture_family(ev):  # noqa: F811
    case = CaseRecord.model_validate({"case_id": "FIX-1", "category": None, "split": "diagnostic",
                                      "package": ev.package.model_dump(),
                                      "source_manifest": {"origin": "synthetic_original"}})
    fam = Family("fixture", P.ROOT, P.ROOT, None, ("C7", "C4"), None, "F", {"C7": None, "C4": "C7"})
    draft = TextEntry("Dx1", "FIX-1", f"{S1} {S2}", [S1, S2], {"final:C7", "draft:C4"})
    final = TextEntry("Dx2", "FIX-1", f"{S1} {S3}", [S1, S3], {"final:C4"})
    runs = {("FIX-1", "C7"): RunView("FIX-1", "C7", "completed", "Dx1", None, [], {}, P.ROOT),
            ("FIX-1", "C4"): RunView("FIX-1", "C4", "completed", "Dx2", "Dx1", [], {}, P.ROOT)}
    return FamilyData(fam, {"FIX-1": case}, {"Dx1": draft, "Dx2": final}, runs, {"FIX-1": "F01"})


def run_fixture_pipeline(fixture_family, tmp_path, monkeypatch, sig_adjudication="OVERSTATED"):
    """Run the whole pipeline on the one-case fixture with mock judges; return (data, packets, out, prompts)."""
    for mod in (P, C):
        monkeypatch.setattr(mod, "EXT", tmp_path / "ext")
    monkeypatch.setattr(judges, "RAW_DIR", tmp_path / "raw")
    prompts: list[str] = []

    def extract(prompt, schema):
        prompts.append(prompt)
        units = re.findall(r'^- (U-[0-9a-f]+): "(.*)"$', prompt, re.M)
        out = []
        for uid, text in units:
            nums = [{"as_written": n, "value": float(n), "comparator": "=", "approximate": False, "role": "result",
                     "unit": None} for n in re.findall(r"\d+\.\d+", text)]
            ctype = "statistical_significance" if "significantly" in text else "comparison"
            out.append({"unit_id": uid, "claims": [{"span": text.rstrip("."), "proposition": text, "claim_type": ctype,
                                                    "entities": ["A", "B"], "metrics": [], "datasets": [],
                                                    "qualifiers": [], "numbers": nums}]})
        return {"units": out}

    def verifier(sig_label, wrong_mapping):
        def respond(prompt, schema):
            prompts.append(prompt)
            claims = re.findall(r"- claim (c\d+) \((\w+)\)", prompt)
            numbers = re.findall(r'number (c\d+\.n\d+): "([\d.]+)"', prompt)
            out = []
            for cid, ctype in claims:
                sig = ctype == "statistical_significance"
                lab = sig_label if sig else "SUPPORTED"
                ent = "NOT_ENTAILED" if lab == "OVERSTATED" else "ENTAILED"
                nums = []
                for nid, val in numbers:
                    if nid.startswith(cid + "."):
                        cell = "T1.r1.d1" if val == "0.837" or wrong_mapping else "T1.r2.d1"
                        nums.append({"number_id": nid, "source_type": "cell", "expression": cell, "quote": None, "scale": 1})
                out.append({"claim_id": cid, "label": lab, "entailment": ent, "error_subtype": None,
                            "evidence_ids": ["S1"], "justification": "j", "confidence": "high",
                            "extraction_flag": "OK", "numbers": nums})
            return {"claims": out}
        return respond

    def align(prompt, schema):
        prompts.append(prompt)
        pid = re.search(r"### Pair (P-[0-9a-f]+)", prompt).group(1)
        x = re.search(r"Version X claims:\n\s+- (\S+):", prompt).group(1)
        y = re.search(r"Version Y claims:\n\s+- (\S+):", prompt).group(1)
        return {"pairs": [{"pair_id": pid, "x_claims": [{"claim_id": x, "relation": "MODIFIED", "direction": "WEAKENED",
                                                         "matched_y": [y]}], "added_y": []}]}

    def adjudicate(prompt, schema):
        prompts.append(prompt)
        items = re.findall(r"### Item (\S+)", prompt)
        out = []
        for it in items:
            block = prompt.split(f"### Item {it}")[1].split("### Item")[0]
            nums = [{"number_id": n, "choice": "own", "source_type": "cell", "expression": "T1.r2.d1", "quote": None,
                     "scale": 1} for n in re.findall(r"number (\S+\.n\d+) ", block)]
            nums = list({n["number_id"]: n for n in nums}.values())
            ent = "ENTAILED" if sig_adjudication == "SUPPORTED" else "NOT_ENTAILED"
            out.append({"item_id": it, "label": sig_adjudication, "entailment": ent, "extraction_valid": True,
                        "numbers": nums, "rationale": "Decided from S1.", "evidence_ids": ["S1"]})
        return {"decisions": out}

    mock_a, mock_b = judges.JudgeSpec("A", "mock", "mock-a"), judges.JudgeSpec("B", "mock", "mock-b")
    monkeypatch.setattr(P, "JUDGE_A", mock_a)
    monkeypatch.setattr(C, "ADJUDICATOR", judges.JudgeSpec("ADJ", "mock", "mock-adj"))
    data = fixture_family
    packets = P.build_packets(data, out_root=tmp_path / "packets")
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "extract", extract)
    claims = P.run_extraction(data, packets, judge=mock_a, workers=1)
    assert len(claims) == 3  # three distinct sentences, one claim each
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "verify", verifier("OVERSTATED", False))
    P.run_verification(data, packets, claims, mock_a, workers=1)
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "verify", verifier("SUPPORTED", True))
    P.run_verification(data, packets, claims, mock_b, workers=1)
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "align", align)
    P.run_alignment(data, packets, claims, mock_a, workers=1)
    P.run_alignment(data, packets, claims, mock_b, workers=1)
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "adjudicate_claims", adjudicate)
    C.run_claim_adjudication(data, packets, workers=1)
    C.run_alignment_adjudication(data, packets, workers=1)
    out = C.build_consensus(data, packets)
    return data, packets, out, prompts


def test_pipeline_end_to_end_with_mock_judges(fixture_family, tmp_path, monkeypatch):
    data, packets, out, prompts = run_fixture_pipeline(fixture_family, tmp_path, monkeypatch)
    final = {r["claim_id"]: r for r in P.load_jsonl(out["claims"])}

    sig = next(r for r in final.values() if r["unit_id"] == unit_id("FIX-1", S2))
    assert sig["final_label"] == "OVERSTATED" and sig["disputed_fields"] and "adjudication" in sig
    cmp_claim = next(r for r in final.values() if r["unit_id"] == unit_id("FIX-1", S1))
    assert cmp_claim["final_label"] == "SUPPORTED"
    assert [n["verdict"] for n in cmp_claim["numbers"]] == ["CORRECT", "CORRECT"]
    assert cmp_claim["numbers"][1]["mapping_source"].startswith("adjudicated")

    by_unit: dict = {}
    for r in final.values():
        by_unit.setdefault(r["unit_id"], []).append(r)
    labels = {k: v["final_label"] for k, v in final.items()}
    al = P.load_jsonl(out["alignment"])[0]
    r = analyze_run(data.texts["Dx1"].units, data.texts["Dx2"].units, by_unit, labels, al)
    s = summarize([r])
    assert r.initial_errors == 1 and r.corrected == 1 and s["repair_recall"] == 1.0 and s["edit_precision"] == 1.0

    # judges never saw a condition label, a run tag or which version came from which system
    assert prompts and not any(re.search(r"\bC[1-7]\b|primary_v1", p) or re.search(r"verifier|draft", p, re.I)
                               for p in prompts)
    manifest = json.loads((tmp_path / "ext" / "consensus" / "MANIFEST_fixture.json").read_text())
    assert set(manifest) == {"claims", "alignment"}
