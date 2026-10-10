"""CostGuard: hard cap, stage caps, ledger safety, concurrency."""
import json
import threading

import pytest

from src.cost_guard import BudgetExceeded, CostGuard, Pricing


def guard(tmp_path, cap=1.0, stage_caps=None, inflight=2):
    return CostGuard(tmp_path / "ledger.jsonl", cap, stage_caps or {"dev": 0.5, "main": 1.0},
                     Pricing(1e-6, 2e-6), max_inflight=inflight)


def test_reserve_and_hard_cap(tmp_path):
    g = guard(tmp_path)
    with g.reserve(0.1, "dev"):
        g.append({"stage": "dev", "cost_usd": 0.1})
    assert abs(g.spent() - 0.1) < 1e-12
    with pytest.raises(BudgetExceeded):
        with g.reserve(0.45, "dev"):  # stage cap 0.5
            pass
    g.append({"stage": "main", "cost_usd": 0.85})
    with pytest.raises(BudgetExceeded):
        with g.reserve(0.1, "main"):  # hard cap 1.0: 0.95 + 0.1
            pass
    with pytest.raises(BudgetExceeded):
        with g.reserve(0.0001, "unknown_stage"):
            pass


def test_ledger_refuses_sensitive_fields(tmp_path):
    g = guard(tmp_path)
    for k in ("Authorization", "headers", "api_key", "messages", "prompt"):
        with pytest.raises(ValueError):
            g.append({"stage": "dev", "cost_usd": 0, k: "x"})
    assert g.spent() == 0


def test_estimates(tmp_path):
    g = guard(tmp_path)
    assert g.estimate_from_tokens(1000, 100) == pytest.approx(1000e-6 + 200e-6)
    assert g.estimate_upper_bound(3000, 100) == pytest.approx(1.5 * (1000e-6 + 200e-6))


def test_concurrent_reservations_never_exceed_cap(tmp_path):
    g = guard(tmp_path, cap=1.0, stage_caps={"main": 1.0}, inflight=8)
    errors, done = [], []

    def worker():
        try:
            with g.reserve(0.1, "main"):
                g.append({"stage": "main", "cost_usd": 0.1})
                done.append(1)
        except BudgetExceeded as e:
            errors.append(e)

    ts = [threading.Thread(target=worker) for _ in range(30)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert g.spent() <= 1.0 + 1e-9
    assert len(done) + len(errors) == 30 and len(done) <= 10


def test_ledger_is_append_only_jsonl(tmp_path):
    g = guard(tmp_path)
    g.append({"stage": "dev", "cost_usd": 0.01, "call_id": "a"})
    g.append({"stage": "dev", "cost_usd": 0.02, "call_id": "b"})
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    assert [json.loads(x)["call_id"] for x in lines] == ["a", "b"]
    assert g.summary()["total_usd"] == pytest.approx(0.03)
