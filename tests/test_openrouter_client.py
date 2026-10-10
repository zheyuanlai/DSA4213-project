"""OpenRouter adapter: parsing, retries, fatal errors, cost logging, secret hygiene (no network)."""
import json

import httpx
import pytest

from src.cost_guard import CostGuard, Pricing
from src.openrouter_client import FatalAPIError, OpenRouterClient, TransientAPIError, _parse_tool_calls, scrub

FAKE_KEY = "sk-or-v1-" + "0" * 64  # obviously fake test value


def make_client(tmp_path, handler, monkeypatch, retries=2):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    monkeypatch.setattr("src.openrouter_client.time.sleep", lambda s: None)
    g = CostGuard(tmp_path / "ledger.jsonl", 1.0, {"dev": 1.0}, Pricing(1e-6, 2e-6))
    c = OpenRouterClient("test/model", {"order": ["x"]}, {"temperature": 0}, g, max_retries=retries)
    c._http = httpx.Client(transport=httpx.MockTransport(handler))
    return c, g


def ok_body(content="hi", tool_calls=None, cost=0.001):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"id": "gen-1", "provider": "P", "choices": [{"message": msg, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": cost,
                      "completion_tokens_details": {"reasoning_tokens": 0}}}


CTX = {"case_id": "c", "condition": "C1", "stage": "dev"}


def test_success_logs_provider_cost(tmp_path, monkeypatch):
    seen = {}

    def h(req):
        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(200, json=ok_body())

    c, g = make_client(tmp_path, h, monkeypatch)
    r = c.chat([{"role": "user", "content": "x"}], role="w", ctx=CTX, max_tokens=50,
               tools=[{"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}], tool_choice="required")
    assert r.content == "hi" and r.cost_source == "provider_reported" and r.provider == "P"
    assert "parallel_tool_calls" not in seen["body"] and seen["body"]["tool_choice"] == "required"
    assert seen["body"]["provider"] == {"order": ["x"]} and seen["body"]["temperature"] == 0
    ledger = (tmp_path / "ledger.jsonl").read_text()
    assert FAKE_KEY not in ledger and "Bearer" not in ledger and "authorization" not in ledger.lower()
    assert g.spent() == pytest.approx(0.001)


def test_retry_on_429_then_success(tmp_path, monkeypatch):
    n = {"i": 0}

    def h(req):
        n["i"] += 1
        if n["i"] < 3:
            return httpx.Response(429, json={"error": {"message": "rate limited", "code": 429}})
        return httpx.Response(200, json=ok_body())

    c, g = make_client(tmp_path, h, monkeypatch, retries=3)
    r = c.chat([{"role": "user", "content": "x"}], role="w", ctx=CTX, max_tokens=50)
    assert r.attempts == 3 and n["i"] == 3
    rows = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [x["status"] for x in rows] == ["error", "error", "ok"]


def test_retry_exhaustion(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, lambda req: httpx.Response(503, text="down"), monkeypatch, retries=2)
    with pytest.raises(TransientAPIError):
        c.chat([{"role": "user", "content": "x"}], role="w", ctx=CTX, max_tokens=50)


@pytest.mark.parametrize("code", [400, 401, 402, 403, 404])
def test_fatal_codes_not_retried(tmp_path, monkeypatch, code):
    n = {"i": 0}

    def h(req):
        n["i"] += 1
        return httpx.Response(code, json={"error": {"message": f"bad {FAKE_KEY}", "code": code}})

    c, _ = make_client(tmp_path, h, monkeypatch, retries=3)
    with pytest.raises(FatalAPIError) as ei:
        c.chat([{"role": "user", "content": "x"}], role="w", ctx=CTX, max_tokens=50)
    assert n["i"] == 1
    assert FAKE_KEY not in str(ei.value)


def test_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    g = CostGuard(tmp_path / "l.jsonl", 1.0, {"dev": 1.0}, Pricing(1e-6, 1e-6))
    with pytest.raises(FatalAPIError):
        OpenRouterClient("m", {}, {}, g)


def test_parse_tool_calls_malformed():
    tcs = _parse_tool_calls({"tool_calls": [
        {"id": "a", "function": {"name": "lookup_table", "arguments": "{\"table_id\": \"T1\"}"}},
        {"id": "b", "function": {"name": "lookup_table", "arguments": "{bad json"}},
        {"id": "c", "function": {"name": "lookup_table", "arguments": "[1,2]"}},
    ]})
    assert tcs[0].arguments == {"table_id": "T1"} and tcs[1].arguments is None and tcs[1].parse_error
    assert tcs[2].arguments is None


def test_scrub(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    assert FAKE_KEY not in scrub(f"error with {FAKE_KEY} inside")
    assert "[REDACTED]" in scrub("token sk-or-v1-abcdefabcdefabcdef")
