"""Resumable runner: interruption, idempotent resume, failures stay in the denominator."""
import json

from src.cost_guard import BudgetExceeded
from src.mock_responder import mock_responder
from src.openrouter_client import MockClient
from src.package_schema import CaseRecord
from src.runner import run_experiment
from src.schemas import RunRecord

CFG = {"model": {"id": "mock/model"}, "verifier": {"max_tool_calls": 4, "max_claims": 6}}


def _records(record, n=3):
    out = []
    for i in range(n):
        d = record.model_dump()
        d["case_id"] = f"UNIT-{i}"
        out.append(CaseRecord.model_validate(d))
    return out


def test_interrupt_and_resume(record, tmp_path):
    recs = _records(record)
    state = {"calls": 0}

    def flaky(messages, tools, tool_choice, role):
        state["calls"] += 1
        if state["calls"] == 25:
            raise BudgetExceeded("simulated budget stop")
        return mock_responder(messages, tools, tool_choice, role)

    s1 = run_experiment(CFG, recs, ["C1", "C4", "C7"], family="synthetic", run_tag="r1", stage="dev",
                        client=MockClient(flaky), out_base=tmp_path)
    assert s1["stop_reason"] and "simulated budget stop" in s1["stop_reason"]
    assert s1["statuses"].get("pending", 0) > 0 and s1["statuses"].get("running", 0) == 0
    done_before = {p.name + p.parent.name: p.stat().st_mtime for p in (tmp_path / "synthetic").rglob("C*/*.json")}
    s2 = run_experiment(CFG, recs, ["C1", "C4", "C7"], family="synthetic", run_tag="r1", stage="dev",
                        client=MockClient(mock_responder), out_base=tmp_path)
    assert s2["statuses"] == {"completed": 9} and s2["stop_reason"] is None
    for p in (tmp_path / "synthetic").rglob("C*/*.json"):
        k = p.name + p.parent.name
        if k in done_before:
            assert p.stat().st_mtime == done_before[k], "completed job was re-run"
    events = [json.loads(x) for x in (tmp_path / "run_manifest.jsonl").read_text().splitlines()]
    assert any(e["status"] == "pending" for e in events)


def test_failed_jobs_not_silently_rerun(record, tmp_path):
    recs = _records(record, 1)

    def bad_writer(messages, tools, tool_choice, role):
        if role == "writer_direct":
            return {"content": "no json here"}
        return mock_responder(messages, tools, tool_choice, role)

    s1 = run_experiment(CFG, recs, ["C1"], family="synthetic", run_tag="r", stage="dev",
                        client=MockClient(bad_writer), out_base=tmp_path)
    assert s1["statuses"] == {"failed": 1}
    s2 = run_experiment(CFG, recs, ["C1"], family="synthetic", run_tag="r", stage="dev",
                        client=MockClient(mock_responder), out_base=tmp_path)
    assert s2["statuses"] == {"failed": 1}  # stays failed; no silent re-run until success


def test_runrecord_roundtrip(record, tmp_path):
    run_experiment(CFG, [record], ["C4"], family="synthetic", run_tag="r", stage="dev",
                   client=MockClient(mock_responder), out_base=tmp_path)
    p = next((tmp_path / "synthetic").rglob("C4/UNIT-1.json"))
    rr = RunRecord.model_validate_json(p.read_text())
    assert rr.is_mock and rr.condition == "C4" and rr.claim_traces
    assert RunRecord.model_validate_json(rr.model_dump_json()) == rr
    meta = json.loads(next((tmp_path / "synthetic").rglob("run_meta_r.json")).read_text())
    assert meta["is_mock"] is True and "prompt_hashes" in meta
