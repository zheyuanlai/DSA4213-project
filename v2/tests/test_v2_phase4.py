"""Offline tests for the Phase 4 pipeline (mock clients; nothing paid; all outputs in tmp_path)."""
import copy
import json
import re
from pathlib import Path

import pytest

from src.openrouter_client import MockClient
from v2 import or_judge
from v2.benchmarks import phase4_checks
from v2.scripts import phase4_author, phase4_freeze, phase4_judge, phase4_score, phase4_validate, run_e1_e2

ROOT = Path(__file__).resolve().parents[2]


def _pkg(partner: bool) -> dict:
    tasks = [("t1", "Quorline-Intent", 91.2, 89.8), ("t2", "Pelvane-Slots", 84.5, 83.1), ("t3", "Hesker-NER", 78.3, 77.9),
             ("t4", "Ombrel-QA", 88.6, 88.6 if partner else 87.4), ("t5", "Trevick-Sum", 72.4, 71.0)]
    return {
        "question": "Does Marlow-Tune outperform Ressil-FT across the five tasks of the Calden suite?",
        "methods_summary": "Marlow-Tune is a parameter-efficient fine-tuning method; Ressil-FT is full fine-tuning.",
        "experimental_setup": "Both methods use the same backbone and tuning budget; scores are means over 3 seeds.",
        "experiments": [{"experiment_id": "exp1", "description": "Calden suite", "comparisons": [
            {"comparison_id": "cmp1", "description": "Marlow-Tune vs Ressil-FT, score per task"}]}],
        "results_tables": [{"table_id": "T1", "caption": "Score per task (mean over 3 seeds).", "columns": [
            {"column_id": "mt", "header": "Marlow-Tune", "unit": None, "higher_is_better": True},
            {"column_id": "rf", "header": "Ressil-FT", "unit": None, "higher_is_better": True}],
            "rows": [{"row_id": r, "label": lab, "cells": {"mt": {"text": f"{a}", "value": a, "spread": None},
                                                         "rf": {"text": f"{b}", "value": b, "spread": None}}}
                     for r, lab, a, b in tasks], "notes": None}],
        "statistical_tests": [], "source_passages": [],
        "task_instruction": "Write a 2-4 sentence Results passage answering the question."}


def fixture_pair() -> dict:
    return {"pair_id": "P3", "focal_proposition": "Marlow-Tune outperforms Ressil-FT on every Calden task",
            "level_descriptors": {"0": "no overall advantage", "1": "better on several/most or comparable-or-better",
                                  "2": "strictly better on all five tasks"},
            "pair_contrast": "Ombrel-QA is a win (88.6 vs 87.4) in the strong member and a tie in the partner.",
            "decisive_evidence_ids": ["T1.t4.rf"],
            "strong_package": _pkg(False), "partner_package": _pkg(True),
            "drafts": [
                {"key": "U", "text": "Marlow-Tune scored higher than Ressil-FT in several of the Calden tasks.",
                 "expressed_level": 1, "pattern": "in several of", "writer_evidence_hints": ["T1"]},
                {"key": "U2", "text": "Marlow-Tune was comparable or better than Ressil-FT on every Calden task.",
                 "expressed_level": 1, "pattern": "comparable or better", "writer_evidence_hints": ["T1"]},
                {"key": "S", "text": "Marlow-Tune scored higher than Ressil-FT on all five Calden tasks.",
                 "expressed_level": 2, "pattern": "strong", "writer_evidence_hints": ["T1"]}]}


def test_checks_accept_fixture_and_catch_errors():
    errs, _ = phase4_checks.check_pair(fixture_pair(), avoid=set())
    assert errs == []
    bad = copy.deepcopy(fixture_pair())
    bad["drafts"][0]["text"] = "Marlow-Tune scored 95.5 on Quorline-Intent."
    bad["partner_package"]["question"] = "Something else?"
    bad["strong_package"]["methods_summary"] += " This is understated."
    errs, _ = phase4_checks.check_pair(bad, avoid={"Quorline-Intent"})
    joined = " ".join(errs)
    assert "95.5" in joined and "question differs" in joined and "rubric word" in joined and "reuses V1" in joined


def test_known_names_cover_dev_and_test():
    names = phase4_checks.known_names()
    assert "Varrow-NMT" in names and "Tessaline" in names and len(names) > 60


def test_label_definitions_are_v1_verbatim():
    d = phase4_validate.label_definitions()
    v1 = (ROOT / "annotation" / "ai_extended" / "prompts" / "verify.md").read_text(encoding="utf-8")
    assert d in v1 and "`UNDERSTATED`" in d and "`OVERSTATED`" in d


def test_expected_decision_rule():
    f = phase4_validate.expected_decision
    assert (f(1, 2), f(2, 2), f(2, 1), f(1, 1), f(1, 0), f(0, 0)) == \
        ("STRENGTHEN", "ACCEPT", "WEAKEN", "ACCEPT", "REMOVE_OR_WEAKEN", "ACCEPT")


def _mock_responder(messages, tools, tool_choice, role):
    user = messages[-1]["content"]
    if role == "v2_p4_author":
        return {"content": json.dumps(fixture_pair())}
    if role == "v2_p4_validate":
        js = []
        strong_member = "88.6 | 87.4" in user or '"text": "87.4"' in user or "| 87.4 |" in user
        for sid, text in re.findall(r"^\[(d\d+)\] (.*)$", user, flags=re.M):
            if "all five" in text:
                lab = "SUPPORTED" if strong_member else "OVERSTATED"
            else:
                lab = "UNDERSTATED" if strong_member else "SUPPORTED"
            js.append({"sentence_id": sid, "label": lab, "strongest_supported": "x", "same_proposition": True,
                       "justification": "mock", "confidence": "high"})
        return {"content": json.dumps({"judgements": js})}
    if role == "v2_p4_judge":
        if "Disputed items" in user:
            ids = re.findall(r"^\* item (c\d+):", user, flags=re.M)
            return {"content": json.dumps({"decisions": [
                {"item_id": i, "label": "SUPPORTED", "entailment": "ENTAILED", "extraction_valid": True, "numbers": [],
                 "rationale": "mock", "evidence_ids": []} for i in ids]})}
        cids = re.findall(r"- claim (c\d+) ", user)
        model_b = "haiku" in messages[0]["content"]  # never true; both judges agree in the mock
        return {"content": json.dumps({"claims": [
            {"claim_id": c, "label": "SUPPORTED", "entailment": "ENTAILED", "error_subtype": None, "evidence_ids": [],
             "justification": "mock", "confidence": "high", "extraction_flag": "OK", "numbers": []} for c in cids]})}
    raise AssertionError(role)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    monkeypatch.setattr(or_judge, "RAW_DIR", tmp_path / "raw")
    for m in (or_judge.AUTHOR_MODEL, or_judge.VALIDATOR_MODEL, or_judge.JUDGE_A_MODEL, or_judge.JUDGE_B_MODEL):
        or_judge.set_client(m, MockClient(_mock_responder, model_id=m))
    priv = tmp_path / "private"
    monkeypatch.setattr(phase4_author, "PRIVATE", priv)
    monkeypatch.setattr(phase4_validate, "PRIVATE", priv)
    monkeypatch.setattr(phase4_freeze, "PRIVATE", priv)
    monkeypatch.setattr(phase4_freeze, "PUB", tmp_path / "pub")
    monkeypatch.setattr(phase4_freeze, "MANIFEST", tmp_path / "freeze_manifest.json")
    monkeypatch.setattr(phase4_judge, "PRIVATE", priv)
    monkeypatch.setattr(phase4_checks, "known_names", lambda: set())
    monkeypatch.setattr(phase4_author, "known_names", lambda: set())
    yield tmp_path
    or_judge._clients.clear()


def test_pipeline_author_validate_freeze_run_judge_score(mock_env):
    tmp = mock_env
    assert phase4_author.main(["--round", "r1", "--pairs", "P3"]) == 0
    rec = json.loads((tmp / "private" / "authored" / "r1" / "P3.json").read_text(encoding="utf-8"))
    assert rec["errors"] == []
    assert phase4_validate.main(["--round", "r1", "--authored", str(tmp / "private" / "authored" / "r1")]) == 0
    val = json.loads((tmp / "private" / "validation" / "r1.json").read_text(encoding="utf-8"))
    assert val["n_items"] == 6 and val["n_agree"] == 6
    assert phase4_freeze.main(["--authored", str(tmp / "private" / "authored" / "r1"),
                               "--validation", str(tmp / "private" / "validation" / "r1.json")]) == 0
    with pytest.raises(SystemExit):  # refuses to re-freeze
        phase4_freeze.main(["--authored", str(tmp / "private" / "authored" / "r1"),
                            "--validation", str(tmp / "private" / "validation" / "r1.json")])
    gold = json.loads((tmp / "private" / "gold.json").read_text(encoding="utf-8"))["probes"]
    assert sorted(g["expected_decision"] for g in gold) == ["ACCEPT", "ACCEPT", "ACCEPT", "STRENGTHEN", "STRENGTHEN",
                                                            "WEAKEN"]
    items = json.loads((tmp / "pub" / "items.json").read_text(encoding="utf-8"))["probes"]
    assert all("expected_decision" not in p for p in items)  # public items carry no gold
    out = tmp / "run"
    assert run_e1_e2.main(["--run-tag", "p4mock", "--mock", "--repeats", "1", "--probes", str(tmp / "pub" / "items.json"),
                           "--cases", str(tmp / "pub" / "cases.jsonl"), "--split", "test",
                           "--conditions", "D0-tools-800,D1-tools,D1-tools-C5", "--out-root", str(out),
                           "--workers", "1"]) == 0
    res = tmp / "res"
    assert phase4_judge.main(["--run-dir", str(out), "--cases", str(tmp / "pub" / "cases.jsonl"),
                              "--out", str(res)]) == 0
    assert phase4_score.main(["--run-dir", str(out), "--gold", str(tmp / "private" / "gold.json"),
                              "--out", str(res)]) == 0
    s = json.loads((res / "summary.json").read_text(encoding="utf-8"))
    assert set(s["conditions"]) == {"V1 C4", "V2 C4", "V2 C5"}
    assert s["conditions"]["V2 C5"]["false_strengthen"]["runs"].startswith("0/")


def test_score_rules():
    g = {"expected_decision": "ACCEPT", "acceptable_decisions": ["ACCEPT"]}
    r = {"decision": "WEAKEN", "case_id": "c", "revised_text": "t"}
    j = {phase4_score.opaque("c", "t"): {"final_label": "OVERSTATED", "numeric": "ok"}}
    o = phase4_score.run_outcomes(r, g, j)
    assert o["harmful_edit"] == 1.0 and o["control_preserved"] == 0.0 and o["false_strengthen"] == 0.0
    g2 = {"expected_decision": "STRENGTHEN", "acceptable_decisions": ["STRENGTHEN"]}
    r2 = {"decision": "STRENGTHEN", "case_id": "c", "revised_text": "t"}
    j2 = {phase4_score.opaque("c", "t"): {"final_label": "SUPPORTED", "numeric": "error"}}
    assert phase4_score.run_outcomes(r2, g2, j2)["correct_strengthen"] == 0.0
