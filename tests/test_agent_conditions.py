"""Condition switches, verifier FSM behaviour and fairness invariants (offline, mock client)."""
import json

import pytest

from src.agent import SharedArtifacts, run_case
from src.conditions import ALL_CONDITIONS, CONDITIONS, ConditionConfig
from src.mock_responder import mock_responder
from src.openrouter_client import MockClient
from src.prompts import load, system_prompt
from src.schemas import ClaimDraft, Draft
from src.verifier import SCRIPTED_SEQUENCE, VerifierConfig, validate_decision, verify_draft

META = {"run_tag": "t", "stage": "dev", "prompt_hashes": {}, "code_hash": "x", "config_hash": "y"}


def _tc(i, name, args):
    return {"id": f"c{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def run_all(record, tmp_path, conds=ALL_CONDITIONS):
    client = MockClient(mock_responder)
    rrs = run_case(client, record, list(conds), tmp_path, META)
    return client, {r.condition: r for r in rrs}


def test_condition_table():
    assert set(CONDITIONS) == {"C1", "C2", "C3", "C4", "C5", "C6", "C7"}
    c = CONDITIONS
    assert not c["C1"].uses_tools and not c["C1"].generic_review and not c["C1"].uses_outline
    assert c["C2"].generic_review and not c["C2"].uses_tools
    assert c["C3"].verify_mode == "scripted" and c["C3"].can_strengthen and c["C3"].uses_outline
    assert c["C4"].adaptive and c["C4"].can_strengthen and c["C4"].uses_outline
    assert c["C5"].adaptive and not c["C5"].can_strengthen and c["C5"].uses_outline
    assert c["C6"].adaptive and c["C6"].can_strengthen and not c["C6"].uses_outline
    assert c["C7"].uses_outline and not c["C7"].uses_tools and not c["C7"].can_strengthen
    with pytest.raises(ValueError):
        ConditionConfig("X", "bad", "direct", generic_review=True, verify_mode="adaptive")
    with pytest.raises(ValueError):
        ConditionConfig("X", "bad", "direct", can_strengthen=True)


def test_c5_cannot_strengthen():
    v = CONDITIONS["C5"].verifier_config()
    assert "STRENGTHEN" not in v.allowed_decisions()
    claim = ClaimDraft(claim_id="s1", text="A beats B.")
    d = validate_decision({"rationale": "r", "decision": "STRENGTHEN", "revised_text": "A significantly beats B.",
                           "evidence_ids": ["S1"]}, claim, {"S1"}, v.allowed_decisions())
    assert d.decision == "FLAG" and not d.valid and d.revised_text == "A beats B."


def test_tool_usage_by_condition(record, tmp_path):
    client, rr = run_all(record, tmp_path)
    by_cond = {}
    for call in client.calls:
        by_cond.setdefault(call["ctx"]["condition"], []).append(call)
    # C1/C2/C7: no tool definitions ever offered in their own calls
    for c in ("C2",):
        assert all(not call["tools"] for call in by_cond.get(c, []))
    assert "C1" not in by_cond and "C7" not in by_cond  # only shared upstream calls, no own calls
    assert all(not call["tools"] for call in by_cond["shared_direct"] + by_cond["shared_outline"])
    for c in ("C1", "C2", "C7"):
        assert rr[c].claim_traces == [] and rr[c].totals["n_tool_calls"] == 0
    for c in ("C3", "C4", "C5", "C6"):
        assert rr[c].totals["n_tool_calls"] > 0
    # outline leakage: C6 has no outline; C3/C4/C5/C7 do
    assert rr["C6"].outline is None and rr["C1"].outline is None and rr["C2"].outline is None
    for c in ("C3", "C4", "C5", "C7"):
        assert rr[c].outline is not None
    # C7 never invokes the verifier
    assert not any(call["role"].startswith("verify") for call in by_cond.get("C7", []))


def test_shared_starting_drafts(record, tmp_path):
    _, rr = run_all(record, tmp_path)
    start = {c: rr[c].drafts[0]["passage"] for c in rr}
    assert start["C3"] == start["C4"] == start["C5"] == start["C7"] == rr["C7"].final_passage
    assert start["C1"] == start["C2"] == start["C6"] == rr["C1"].final_passage
    assert rr["C4"].shared_artifacts == rr["C5"].shared_artifacts == rr["C3"].shared_artifacts
    # strengthening only where allowed
    assert rr["C4"].totals["decision_counts"].get("STRENGTHEN", 0) >= 1
    assert rr["C5"].totals["decision_counts"].get("STRENGTHEN", 0) == 0


def test_scripted_forces_fixed_sequence(record, tmp_path):
    client, rr = run_all(record, tmp_path, ["C3"])
    verify_calls = [c for c in client.calls if c["role"] == "verify_scripted"]
    per_claim = len(SCRIPTED_SEQUENCE) + 1
    first = [c["tool_choice"]["function"]["name"] for c in verify_calls[:per_claim]]
    assert first == list(SCRIPTED_SEQUENCE) + ["submit_decision"]
    for t in rr["C3"].claim_traces:
        assert [a.tool for a in t.actions] == list(SCRIPTED_SEQUENCE)
        assert all(a.policy == "scripted" for a in t.actions)


def test_adaptive_uses_required_choice(record, tmp_path):
    client, rr = run_all(record, tmp_path, ["C4"])
    vc = [c for c in client.calls if c["role"] == "verify_adaptive"]
    assert vc[0]["tool_choice"] == "required"
    assert all(a.policy == "adaptive" for t in rr["C4"].claim_traces for a in t.actions)


def test_common_policy_identical_everywhere():
    common = load("common_reporting.md").strip()
    for role in ("writer_direct.md", "claim_outline.md", "draft_writer.md", "reviewer_generic.md", "reviser_generic.md"):
        assert system_prompt(role).startswith(common)
    assert system_prompt("verifier_adaptive.md", max_tool_calls="4", decision_definitions="x").startswith(common)
    assert system_prompt("verifier_scripted.md", scripted_sequence="a", decision_definitions="x").startswith(common)
    with pytest.raises(ValueError):
        system_prompt("verifier_adaptive.md")  # unfilled placeholders rejected


# ---------------------------------------------------------------- verifier FSM edge cases
def _draft():
    return Draft(sentences=[ClaimDraft(claim_id="s1", text="Ours significantly beats Baseline (83.7 vs 82.9).")])


def test_budget_and_duplicate_stop(pkg):
    n = {"i": 0}

    def responder(messages, tools, tool_choice, role):
        n["i"] += 1
        if isinstance(tool_choice, dict) and tool_choice["function"]["name"] == "submit_decision":
            return {"tool_calls": [_tc(n["i"], "submit_decision", {"rationale": "r", "decision": "ACCEPT",
                                                                   "revised_text": "", "evidence_ids": ["T1"]})]}
        return {"tool_calls": [_tc(n["i"], "lookup_table", {"table_id": "T1"})]}  # always the same call

    cfg = VerifierConfig(mode="adaptive", can_strengthen=True, max_tool_calls=4)
    calls = []
    final, traces = verify_draft(MockClient(responder), pkg, _draft(), cfg, {"case_id": "u", "stage": "dev"}, calls)
    t = traces[0]
    assert len(t.actions) == 3  # 1 real + 2 duplicates, then forced submit
    assert "DUPLICATE" in t.observations[1].message
    assert t.decision.decision == "ACCEPT" and t.stop_reason == "decision"


def test_invalid_evidence_ids_repair_then_fallback(pkg):
    def responder(messages, tools, tool_choice, role):
        if not any(m["role"] == "tool" for m in messages):
            return {"tool_calls": [_tc(1, "lookup_table", {"table_id": "T1"})]}
        return {"tool_calls": [_tc(9, "submit_decision", {"rationale": "r", "decision": "WEAKEN",
                                                          "revised_text": "Ours scores higher.", "evidence_ids": ["S7"]})]}

    cfg = VerifierConfig(mode="adaptive", can_strengthen=True)
    final, traces = verify_draft(MockClient(responder), pkg, _draft(), cfg, {"case_id": "u", "stage": "dev"}, [])
    d = traces[0].decision
    assert d.decision == "FLAG" and not d.valid  # edit without valid cited evidence -> fallback FLAG
    assert final.sentences[0].text == _draft().sentences[0].text  # FLAG keeps text
    assert any("invalid decision" in e for e in traces[0].protocol_errors)


def test_no_tool_call_protocol_failure(pkg):
    def responder(messages, tools, tool_choice, role):
        return {"content": "I think it is fine."}

    cfg = VerifierConfig(mode="adaptive", can_strengthen=True)
    _, traces = verify_draft(MockClient(responder), pkg, _draft(), cfg, {"case_id": "u", "stage": "dev"}, [])
    assert traces[0].decision.decision == "FLAG" and traces[0].stop_reason == "protocol_failure"
    assert traces[0].model_calls == 2


def test_remove_and_weaken_assembly(pkg):
    d = Draft(sentences=[ClaimDraft(claim_id="s1", text="Ours significantly beats Baseline."),
                         ClaimDraft(claim_id="s2", text="Ours is robust to noise.")])

    def responder(messages, tools, tool_choice, role):
        user = messages[1]["content"]
        if not any(m["role"] == "tool" for m in messages):
            return {"tool_calls": [_tc(1, "get_test_metadata", {"experiment_id": "exp1", "comparison_id": "cmp2"})]}
        if ">>> Ours significantly" in user:
            return {"tool_calls": [_tc(2, "submit_decision", {"rationale": "no test", "decision": "WEAKEN",
                                                              "revised_text": "Ours has lower WER than Baseline.",
                                                              "evidence_ids": ["absent:test:exp1/cmp2"]})]}
        return {"tool_calls": [_tc(3, "submit_decision", {"rationale": "none", "decision": "REMOVE", "revised_text": "",
                                                          "evidence_ids": ["absent:test:exp1/cmp2"]})]}

    cfg = VerifierConfig(mode="adaptive", can_strengthen=False)
    final, traces = verify_draft(MockClient(responder), pkg, d, cfg, {"case_id": "u", "stage": "dev"}, [])
    assert final.passage == "Ours has lower WER than Baseline."
    assert [t.decision.decision for t in traces] == ["WEAKEN", "REMOVE"]


def test_malformed_tool_arguments_are_observed_as_errors(pkg):
    def responder(messages, tools, tool_choice, role):
        if not any(m["role"] == "tool" for m in messages):
            return {"tool_calls": [{"id": "bad", "type": "function", "function": {"name": "lookup_table", "arguments": "{oops"}}]}
        return {"tool_calls": [_tc(2, "submit_decision", {"rationale": "r", "decision": "FLAG", "revised_text": "", "evidence_ids": []})]}

    _, traces = verify_draft(MockClient(responder), pkg, _draft(), VerifierConfig(mode="adaptive", can_strengthen=True),
                             {"case_id": "u", "stage": "dev"}, [])
    assert traces[0].observations[0].status == "TOOL_ERROR"
    assert traces[0].decision.decision == "FLAG"


def test_writer_format_error_repaired(record, tmp_path):
    state = {"n": 0}

    def responder(messages, tools, tool_choice, role):
        if role == "writer_direct":
            state["n"] += 1
            if state["n"] == 1:
                return {"content": "Sure! Here is the passage: Ours is better."}
        return mock_responder(messages, tools, tool_choice, role)

    rrs = run_case(MockClient(responder), record, ["C1"], tmp_path, META)
    assert rrs[0].status == "completed" and rrs[0].totals["n_format_errors"] == 1 and state["n"] == 2


def test_writer_unrecoverable_failure_recorded(record, tmp_path):
    def responder(messages, tools, tool_choice, role):
        if role == "writer_direct":
            return {"content": "not json"}
        return mock_responder(messages, tools, tool_choice, role)

    rrs = run_case(MockClient(responder), record, ["C1", "C2", "C6"], tmp_path, META)
    assert [r.status for r in rrs] == ["failed", "failed", "failed"]
    assert all("upstream direct artifact failed" in r.failure for r in rrs)
    assert all(r.final_passage == "" for r in rrs)


def test_shared_artifact_cache_not_mixed_between_mock_and_real(record, tmp_path):
    c = MockClient(mock_responder)
    s = SharedArtifacts(c, record, tmp_path / "_shared" / record.case_id, {"case_id": record.case_id, "stage": "dev"})
    assert s.direct()["is_mock"] is True
    c2 = MockClient(mock_responder, model_id="other/model")
    s2 = SharedArtifacts(c2, record, tmp_path / "_shared" / record.case_id, {"case_id": record.case_id, "stage": "dev"})
    assert s2._load("direct") is None  # different model -> cache not reused


def test_parallel_calls_only_first_executed(pkg):
    def responder(messages, tools, tool_choice, role):
        if not any(m["role"] == "tool" for m in messages):
            return {"tool_calls": [_tc(1, "lookup_table", {"table_id": "T1"}),
                                   _tc(2, "compare_numbers", {"claimed": 83.7, "evidence_id": "T1.r1.acc"}),
                                   _tc(3, "get_test_metadata", {"experiment_id": "exp1", "comparison_id": "cmp1"})]}
        return {"tool_calls": [_tc(4, "submit_decision", {"rationale": "r", "decision": "ACCEPT", "revised_text": "",
                                                          "evidence_ids": ["T1"]})]}

    client = MockClient(responder)
    _, traces = verify_draft(client, pkg, _draft(), VerifierConfig(mode="adaptive", can_strengthen=True),
                             {"case_id": "u", "stage": "dev"}, [])
    t = traces[0]
    assert [a.tool for a in t.actions] == ["lookup_table"] and t.ignored_parallel_calls == 2
    # every tool_call id still received a tool message (valid protocol)
    last = client.calls[-1]["messages"]
    answered = {m["tool_call_id"] for m in last if m["role"] == "tool"}
    assert answered == {"c1", "c2", "c3"}


def test_evidence_ids_string_tolerated():
    claim = ClaimDraft(claim_id="s1", text="A beats B by 2 points.")
    for raw in ('["T1.r1.a", "T1.r2.a"]', "T1.r1.a, T1.r2.a", ["T1.r1.a", "T1.r2.a"]):
        d = validate_decision({"rationale": "r", "decision": "WEAKEN", "revised_text": "A beats B by 1 point.",
                               "evidence_ids": raw}, claim, {"T1.r1.a", "T1.r2.a"}, ["ACCEPT", "WEAKEN"])
        assert d.valid and d.evidence_ids == ["T1.r1.a", "T1.r2.a"], raw


def test_verifier_prompts_share_checklist():
    a, s = load("verifier_adaptive.md"), load("verifier_scripted.md")
    for block in ("What to check", "Your decision must agree with your rationale"):
        ia, is_ = a.index(block), s.index(block)
        assert a[ia:ia + 300] == s[is_:is_ + 300]
