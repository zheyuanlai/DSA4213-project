"""OpenRouter chat-completions adapter (non-streaming) + offline mock.

Security: the API key is read from the environment at call time and only ever placed
in the Authorization header of the outgoing request. Headers, prompts and environment
variables are never logged. Error strings are scrubbed of anything key-like.
"""
from __future__ import annotations

import json
import os
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import httpx

from src.cost_guard import BudgetExceeded, CostGuard, now_iso

API_URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_RE = re.compile(r"sk-or-[A-Za-z0-9\-_]{8,}")


class FatalAPIError(RuntimeError):
    """Non-retryable: invalid key (401), forbidden (403), out of credit (402), bad request (400)."""


class TransientAPIError(RuntimeError):
    pass


def scrub(s: str) -> str:
    s = KEY_RE.sub("[REDACTED]", s or "")
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        s = s.replace(k, "[REDACTED]")
    return s[:500]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments_raw: str
    arguments: Optional[dict[str, Any]]  # None if JSON was malformed
    parse_error: Optional[str] = None


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall]
    finish_reason: Optional[str]
    assistant_message: dict[str, Any]  # to append to the conversation verbatim
    usage: dict[str, Any]
    provider: Optional[str]
    generation_id: Optional[str]
    latency_s: float
    cost_usd: float
    cost_source: str
    attempts: int
    call_id: str
    is_mock: bool = False

    @property
    def prompt_tokens(self) -> Optional[int]:
        return self.usage.get("prompt_tokens")

    @property
    def completion_tokens(self) -> Optional[int]:
        return self.usage.get("completion_tokens")

    @property
    def reasoning_tokens(self) -> Optional[int]:
        d = self.usage.get("completion_tokens_details") or {}
        return d.get("reasoning_tokens")


def _parse_tool_calls(msg: dict[str, Any]) -> list[ToolCall]:
    out = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw = fn.get("arguments") or ""
        args, err = None, None
        if isinstance(raw, dict):
            args, raw = raw, json.dumps(raw)
        else:
            try:
                parsed = json.loads(raw) if raw.strip() else {}
                if isinstance(parsed, dict):
                    args = parsed
                else:
                    err = "arguments JSON is not an object"
            except json.JSONDecodeError as e:
                err = f"malformed JSON arguments: {e}"
        out.append(ToolCall(id=tc.get("id") or f"call_{uuid.uuid4().hex[:8]}", name=fn.get("name") or "",
                            arguments_raw=raw, arguments=args, parse_error=err))
    return out


class BaseClient:
    model_id: str
    provider_routing: dict[str, Any]
    decoding: dict[str, Any]
    is_mock: bool = False

    def chat(self, messages: list[dict[str, Any]], *, role: str, ctx: dict[str, Any], max_tokens: int,
             tools: Optional[list[dict[str, Any]]] = None, tool_choice: Any = None,
             response_format: Optional[dict[str, Any]] = None) -> ChatResult:  # pragma: no cover
        raise NotImplementedError


class OpenRouterClient(BaseClient):
    def __init__(self, model_id: str, provider_routing: dict[str, Any], decoding: dict[str, Any],
                 cost_guard: CostGuard, *, timeout_s: float = 120.0, max_retries: int = 3,
                 code_hash: str = "", app_title: str = "DSA4213-project"):
        if "OPENROUTER_API_KEY" not in os.environ or not os.environ["OPENROUTER_API_KEY"].strip():
            raise FatalAPIError("OPENROUTER_API_KEY is not set in the environment")
        self.model_id = model_id
        self.provider_routing = provider_routing
        self.decoding = decoding
        self.guard = cost_guard
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.code_hash = code_hash
        self.app_title = app_title
        self._http = httpx.Client(timeout=httpx.Timeout(timeout_s, connect=20.0))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
            "X-Title": self.app_title,
        }

    def build_body(self, messages, max_tokens, tools, tool_choice, response_format) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "usage": {"include": True},
        }
        for k, v in self.decoding.items():
            if v is not None:
                body[k] = v
        if self.provider_routing:
            body["provider"] = self.provider_routing
        if tools:
            body["tools"] = tools
            # parallel_tool_calls is NOT sent: several providers do not support it and
            # require_parameters would filter them out; multiple calls per turn are handled in code.
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
        if response_format is not None:
            body["response_format"] = response_format
        return body

    def chat(self, messages, *, role, ctx, max_tokens, tools=None, tool_choice=None, response_format=None) -> ChatResult:
        body = self.build_body(messages, max_tokens, tools, tool_choice, response_format)
        payload = json.dumps(body, ensure_ascii=False)
        stage = ctx.get("stage", "dev")
        estimate = self.guard.estimate_upper_bound(len(payload), max_tokens)
        call_id = f"{ctx.get('case_id','na')}:{ctx.get('condition','na')}:{role}:{uuid.uuid4().hex[:10]}"
        attempt = 0
        last_err: Optional[str] = None
        while True:
            attempt += 1
            with self.guard.reserve(estimate, stage):
                t0 = time.time()
                status_code = None
                try:
                    r = self._http.post(API_URL, content=payload.encode("utf-8"), headers=self._headers())
                    status_code = r.status_code
                    latency = time.time() - t0
                    data = None
                    try:
                        data = r.json()
                    except Exception:
                        data = None
                    err_obj = (data or {}).get("error") if isinstance(data, dict) else None
                    if r.status_code in (401, 403):
                        self._log_error(call_id, role, ctx, stage, attempt, status_code, "auth/forbidden", latency, 0.0)
                        raise FatalAPIError(f"HTTP {r.status_code}: {scrub(str(err_obj or r.text))}")
                    if r.status_code == 402:
                        self._log_error(call_id, role, ctx, stage, attempt, status_code, "insufficient credits", latency, 0.0)
                        raise FatalAPIError(f"HTTP 402 insufficient credits: {scrub(str(err_obj or r.text))}")
                    if r.status_code == 404:
                        self._log_error(call_id, role, ctx, stage, attempt, status_code, scrub(str(err_obj))[:300], latency, 0.0)
                        raise FatalAPIError(f"HTTP 404 (no endpoint / routing): {scrub(str(err_obj or r.text))}")
                    if r.status_code == 400:
                        self._log_error(call_id, role, ctx, stage, attempt, status_code, scrub(str(err_obj)), latency, 0.0)
                        raise FatalAPIError(f"HTTP 400 bad request: {scrub(str(err_obj or r.text))}")
                    if r.status_code in (408, 429) or r.status_code >= 500 or data is None:
                        raise TransientAPIError(f"HTTP {r.status_code}: {scrub(str(err_obj or r.text[:200]))}")
                    if err_obj:
                        code = err_obj.get("code") if isinstance(err_obj, dict) else None
                        if code in (401, 402, 403):
                            raise FatalAPIError(f"in-body error {code}: {scrub(str(err_obj))}")
                        raise TransientAPIError(f"in-body error: {scrub(str(err_obj))}")
                    choices = data.get("choices") or []
                    if not choices:
                        raise TransientAPIError("empty choices")
                    usage = data.get("usage") or {}
                    cost = usage.get("cost")
                    if cost is not None:
                        cost_source = "provider_reported"
                        cost = float(cost)
                    elif usage.get("prompt_tokens") is not None:
                        cost = self.guard.estimate_from_tokens(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                        cost_source = "estimated_from_tokens"
                    else:
                        cost, cost_source = estimate, "estimated_upper_bound"
                    msg = choices[0].get("message") or {}
                    tcs = _parse_tool_calls(msg)
                    assistant_message: dict[str, Any] = {"role": "assistant", "content": msg.get("content") or ""}
                    if msg.get("tool_calls"):
                        assistant_message["tool_calls"] = msg["tool_calls"]
                    res = ChatResult(
                        content=msg.get("content") or "", tool_calls=tcs,
                        finish_reason=choices[0].get("finish_reason"), assistant_message=assistant_message,
                        usage=usage, provider=data.get("provider"), generation_id=data.get("id"),
                        latency_s=round(latency, 3), cost_usd=cost, cost_source=cost_source,
                        attempts=attempt, call_id=call_id,
                    )
                    self.guard.append({
                        "ts": now_iso(), "call_id": call_id, "stage": stage, "case_id": ctx.get("case_id"),
                        "condition": ctx.get("condition"), "role": role, "model_id": self.model_id,
                        "provider": res.provider, "generation_id": res.generation_id,
                        "finish_reason": res.finish_reason, "prompt_tokens": res.prompt_tokens,
                        "completion_tokens": res.completion_tokens, "reasoning_tokens": res.reasoning_tokens,
                        "cost_usd": cost, "cost_source": cost_source, "latency_s": res.latency_s,
                        "status": "ok", "http_status": status_code, "attempt": attempt,
                        "n_tool_calls": len(tcs), "code_hash": self.code_hash, "run_tag": ctx.get("run_tag"),
                        "prompt_hash": ctx.get("prompt_hash"),
                    })
                    return res
                except (httpx.TimeoutException, httpx.TransportError, TransientAPIError) as e:
                    latency = time.time() - t0
                    # A timed-out request may still have been billed: log the upper bound to stay safe.
                    timed_out = isinstance(e, httpx.TimeoutException)
                    self._log_error(call_id, role, ctx, stage, attempt, status_code, scrub(f"{type(e).__name__}: {e}"),
                                    latency, estimate if timed_out else 0.0,
                                    cost_source="estimated_upper_bound_timeout" if timed_out else "error_no_charge_assumed")
                    last_err = scrub(str(e))
            if attempt > self.max_retries:
                raise TransientAPIError(f"giving up after {attempt} attempts: {last_err}")
            time.sleep(min(30.0, 2.0 ** attempt) + random.uniform(0, 1.0))

    def _log_error(self, call_id, role, ctx, stage, attempt, status_code, err, latency, cost, cost_source="error_no_charge_assumed"):
        self.guard.append({
            "ts": now_iso(), "call_id": call_id, "stage": stage, "case_id": ctx.get("case_id"),
            "condition": ctx.get("condition"), "role": role, "model_id": self.model_id, "provider": None,
            "generation_id": None, "cost_usd": cost, "cost_source": cost_source, "latency_s": round(latency, 3),
            "status": "error", "http_status": status_code, "error": err, "attempt": attempt,
            "code_hash": self.code_hash, "run_tag": ctx.get("run_tag"),
        })


# --------------------------------------------------------------------------- mock
Responder = Callable[[list[dict[str, Any]], Optional[list[dict[str, Any]]], Any, str], dict[str, Any]]


class MockClient(BaseClient):
    """Offline adapter. `responder(messages, tools, tool_choice, role)` returns an OpenAI-style
    message dict ({'content': ..., 'tool_calls': [...]}). Costs are zero; outputs are flagged mock
    and are never written to the real ledger."""

    is_mock = True

    def __init__(self, responder: Responder, model_id: str = "mock/model", provider_routing=None, decoding=None):
        self.responder = responder
        self.model_id = model_id
        self.provider_routing = provider_routing or {}
        self.decoding = decoding or {"temperature": 0}
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, role, ctx, max_tokens, tools=None, tool_choice=None, response_format=None) -> ChatResult:
        msg = self.responder(messages, tools, tool_choice, role)
        self.calls.append({"role": role, "ctx": dict(ctx), "tools": [t["function"]["name"] for t in tools or []],
                           "tool_choice": tool_choice, "n_messages": len(messages),
                           "messages": json.loads(json.dumps(messages))})
        tcs = _parse_tool_calls(msg)
        am: dict[str, Any] = {"role": "assistant", "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            am["tool_calls"] = msg["tool_calls"]
        return ChatResult(content=msg.get("content") or "", tool_calls=tcs,
                          finish_reason="tool_calls" if tcs else "stop", assistant_message=am,
                          usage={"prompt_tokens": 100, "completion_tokens": 20}, provider="mock",
                          generation_id=f"mock-{uuid.uuid4().hex[:8]}", latency_s=0.0, cost_usd=0.0,
                          cost_source="mock", attempts=1, call_id=f"mock:{role}:{uuid.uuid4().hex[:6]}", is_mock=True)
