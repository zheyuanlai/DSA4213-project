"""Judge plumbing without paid inference: leakage control, caching, invalid outputs, budget guard."""
from __future__ import annotations

import json

import pytest

from evaluation import judges
from evaluation.judges import JudgeError, JudgeSpec, LeakageError, call_judge, check_leakage

MOCK = JudgeSpec("M", "mock", "mock-model")
PACKAGE = "## Results\nA baseline and a reviewer condition appear in the data. Table T1 ..."


def test_leakage_blocks_condition_labels_case_ids_and_gold():
    with pytest.raises(LeakageError):
        check_leakage("Judge passage from C4.", [PACKAGE])
    with pytest.raises(LeakageError):
        check_leakage("Case SIG-p2a: judge this.", [PACKAGE])
    with pytest.raises(LeakageError):
        check_leakage("gold_level: 2", [PACKAGE])
    with pytest.raises(LeakageError):
        check_leakage("Run primary_v1 output.", [PACKAGE])
    with pytest.raises(LeakageError):
        check_leakage("This is the verifier's revision of the draft.", [PACKAGE])
    gold_decision = "State that the difference is significant only for the tested comparison S1 at alpha 0.05."
    with pytest.raises(LeakageError):
        check_leakage(f"Instructions.\n{gold_decision}", [PACKAGE], [gold_decision])


def test_leakage_allows_words_inside_package_and_passages():
    passage = "Our method beats the baseline after revision."
    check_leakage(f"Instructions.\n{PACKAGE}\nPassage A: {passage}", [PACKAGE, passage])


def test_call_judge_caches_and_validates(tmp_path, monkeypatch):
    calls = {"n": 0}

    def responder(prompt, schema):
        calls["n"] += 1
        return {"judgments": [{"passage": "A", "item_id": "F1", "status": "CORRECT", "justification": "ok"}]}

    monkeypatch.setitem(judges.MOCK_RESPONDERS, "coverage", responder)
    r1 = call_judge(MOCK, "coverage", "x_K01", "coverage", "Prompt text", data_segments=[], raw_dir=tmp_path)
    r2 = call_judge(MOCK, "coverage", "x_K01", "coverage", "Prompt text", data_segments=[], raw_dir=tmp_path)
    assert calls["n"] == 1 and r2.cached and r1.parsed == r2.parsed
    rec = json.loads(r1.path.read_text())
    for k in ("model_requested", "prompt_template_sha256", "system_prompt_sha256", "cache_key", "started_at", "parsed"):
        assert k in rec
    # a different prompt is a different cache key
    call_judge(MOCK, "coverage", "x_K01", "coverage", "Another prompt", data_segments=[], raw_dir=tmp_path)
    assert calls["n"] == 2


def test_invalid_judge_output_is_retried_then_recorded_as_failure(tmp_path, monkeypatch):
    outputs = iter([{"judgments": [{"passage": "A", "item_id": "F1", "status": "MAYBE", "justification": ""}]},
                    {"wrong": 1}])
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "coverage", lambda p, s: next(outputs))
    with pytest.raises(JudgeError):
        call_judge(MOCK, "coverage", "x_K02", "coverage", "P", data_segments=[], raw_dir=tmp_path, max_attempts=2)
    failed = list(tmp_path.rglob("*.failed.json"))
    assert len(failed) == 1 and len(json.loads(failed[0].read_text())["failed_attempts"]) == 2


def test_validator_rejection_triggers_retry(tmp_path, monkeypatch):
    outs = iter([{"judgments": []},
                 {"judgments": [{"passage": "A", "item_id": "F1", "status": "ABSENT", "justification": "-"}]}])
    monkeypatch.setitem(judges.MOCK_RESPONDERS, "coverage", lambda p, s: next(outs))
    r = call_judge(MOCK, "coverage", "x_K03", "coverage", "P", data_segments=[], raw_dir=tmp_path,
                   validator=lambda p: [] if p["judgments"] else ["empty"])
    assert r.record["attempt"] == 2 and r.record["failed_attempts"][0]["error"] == "empty"


def test_metered_budget_guard_refuses_calls(tmp_path, monkeypatch):
    (tmp_path / "verify" / "B").mkdir(parents=True)
    (tmp_path / "verify" / "B" / "old.json").write_text(json.dumps({"backend": "claude", "cost_usd": 6.4, "status": "ok"}))
    assert judges.claude_spent(tmp_path) == pytest.approx(6.4)
    spec = JudgeSpec("B", "claude", "claude-sonnet-5-5")
    monkeypatch.setattr(judges, "_claude_call", lambda *a, **k: pytest.fail("must not call a paid model over budget"))
    with pytest.raises(JudgeError, match="budget"):
        call_judge(spec, "verify", "x_K04", "verify", "P", data_segments=[], raw_dir=tmp_path)


def test_judge_b_model_rule():
    assert judges.judge_b_for("synthetic", "verify").model == "claude-haiku-5-5"
    assert judges.judge_b_for("real", "verify").model == "claude-sonnet-5-5"
    assert judges.judge_b_for("diagnostic", "coverage").model == "claude-sonnet-5-5"
    assert judges.judge_b_for("real", "align").model == "claude-haiku-5-5"


def test_prompt_templates_contain_no_lineage_words():
    for p in judges.PROMPT_DIR.glob("*.md"):
        assert not judges.TEMPLATE_WORDS.search(p.read_text()), p.name
