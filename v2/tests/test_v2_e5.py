"""Offline tests for E5 (mock client only).  Run: python -m pytest v2/tests"""
import json
from pathlib import Path

import pytest

import src.mock_responder as v1_mock
from src.conditions import CONDITIONS
from src.openrouter_client import MockClient
from src.prompts import system_prompt as v1_system_prompt, decision_block
from src.runner import load_cases
from src.schemas import ClaimDraft, Draft
from src.verifier import VerifierConfig, verify_draft
from v2.mock_responder import oracle_mock_responder
from v2.verifier_oracle import _load
from v2.verifier_tools import tools_system_prompt, verify_draft_tools

ROOT = Path(__file__).resolve().parents[2]
CASES = {c.case_id: c for c in load_cases(ROOT / "data" / "synthetic" / "dev.jsonl")}
CFG_450 = CONDITIONS["C4"].verifier_config(max_tool_calls=4, max_claims=6)
CFG_800 = VerifierConfig(mode="adaptive", can_strengthen=True, max_tool_calls=4, max_claims=6, max_tokens_per_turn=800)


def _draft(*texts):
    return Draft(sentences=[ClaimDraft(claim_id=f"s{i}", text=t, evidence_ids=["T1.r1"]) for i, t in enumerate(texts, 1)])


@pytest.mark.parametrize("cfg", [CFG_450, CFG_800])
@pytest.mark.parametrize("case_id,texts", [
    ("SIG-p1a", ["Tessaline significantly outperforms Varrow-NMT.", "Its advantage is consistent across settings.",
                 "BLEU was measured on the test set."]),
    ("CON-p1b", ["Ferrule is better on most datasets."]),
])
def test_port_equals_v1_with_v1_prompt_and_schema(cfg, case_id, texts):
    pkg = CASES[case_id].package
    runs = []
    for fn in ("v1", "port"):
        v1_mock._counter["n"] = 0  # same tool-call ids in both runs
        client = MockClient(v1_mock.mock_responder)
        calls: list = []
        if fn == "v1":
            final, traces = verify_draft(client, pkg, _draft(*texts), cfg, {"stage": "t"}, calls)
        else:
            final, traces, _ = verify_draft_tools(client, pkg, _draft(*texts), cfg, "D0", {"stage": "t"}, calls)
        runs.append((client.calls, [t.model_dump() for t in traces], final.model_dump(), len(calls)))
    assert runs[0] == runs[1]


def test_d1_tools_prompt_and_schema():
    allowed = CFG_800.allowed_decisions()
    v1 = v1_system_prompt("verifier_adaptive.md", decision_definitions=decision_block(allowed), max_tool_calls="4")
    assert tools_system_prompt("D0", CFG_800) == v1
    assert tools_system_prompt("D1", CFG_800) == v1 + "\n\n" + _load("verifier_oracle_d1_addendum.md")
    client = MockClient(oracle_mock_responder)
    _, traces, judg = verify_draft_tools(client, CASES["CON-p1a"].package, _draft("Ferrule's advantage is consistent."),
                                         CFG_800, "D1", {"stage": "t"}, [])
    names = client.calls[0]["tools"]
    assert names[:4] == ["lookup_table", "get_test_metadata", "retrieve_passage", "compare_numbers"]
    assert names[-1] == "submit_decision"
    assert traces[0].decision.decision == "STRENGTHEN" and judg[0]["support_relation"] == "STRONGER_SUPPORTED"


def test_e5_runner_and_attribution_mock(tmp_path):
    from v2.scripts import analyze_e1_e2, run_e1_e2

    out = tmp_path / "run"
    ids = "P-CON-U-strong,P-SIG-S-partner,P-GEN-U-partner"
    assert run_e1_e2.main(["--run-tag", "t", "--mock", "--repeats", "2", "--probe-ids", ids, "--out-root", str(out),
                           "--conditions", "D0-tools-800,D1-tools,D1-oracle", "--workers", "1"]) == 0
    rec = json.loads((out / "D1-tools" / "P-CON-U-strong__r1.json").read_text(encoding="utf-8"))
    assert rec["max_tokens_per_turn"] == 800 and rec["tools"] and rec["judgement"].get("support_relation")
    rec0 = json.loads((out / "D0-tools-800" / "P-CON-U-strong__r1.json").read_text(encoding="utf-8"))
    assert rec0["judgement"] == {} and rec0["max_tokens_per_turn"] == 800
    res = tmp_path / "res"
    assert analyze_e1_e2.main(["--run-dir", str(out), "--out", str(res)]) == 0
    s = json.loads((res / "summary.json").read_text(encoding="utf-8"))
    assert "D1-tools" in s["conditions"] and isinstance(s["e5_attribution"], list)
