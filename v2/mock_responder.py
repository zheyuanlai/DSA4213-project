"""Deterministic offline responder for V2 oracle verification (tests and --mock dry runs only).

It honours the forced `submit_decision` call and fills the judgement fields when the schema asks for them. The decisions
are keyword-based and meaningless as results; they only exercise every code path (ACCEPT, WEAKEN, STRENGTHEN, REMOVE and
the repair turn). For V1-condition calls (D0-tools) it delegates to V1's mock responder.
"""
from __future__ import annotations

import json
import re
from typing import Any

from src.mock_responder import mock_responder as v1_mock_responder

_n = {"i": 0}


def _tc(args: dict[str, Any]) -> dict[str, Any]:
    _n["i"] += 1
    return {"id": f"call_v2mock_{_n['i']}", "type": "function",
            "function": {"name": "submit_decision", "arguments": json.dumps(args)}}


def _wants_judgement(tools) -> bool:
    for t in tools or []:
        if t["function"]["name"] == "submit_decision":
            return "support_relation" in t["function"]["parameters"]["properties"]
    return False


def oracle_mock_responder(messages, tools, tool_choice, role):
    if not role.startswith("verify_oracle"):
        msg = v1_mock_responder(messages, tools, tool_choice, role)
        if _wants_judgement(tools):  # D1 in the tool loop: add the judgement fields to V1's mock decision
            for tc in msg.get("tool_calls", []):
                if tc["function"]["name"] == "submit_decision":
                    a = json.loads(tc["function"]["arguments"])
                    rel = {"STRENGTHEN": "STRONGER_SUPPORTED", "WEAKEN": "WEAKER_SUPPORTED"}.get(a["decision"], "MATCHES")
                    tc["function"]["arguments"] = json.dumps({"proposition": "mock", "expressed_strength": "mock",
                                                              "strongest_supported": "mock", "support_relation": rel, **a})
        return msg
    user = next(m["content"] for m in messages if m["role"] == "user")
    m = re.search(r'## Claim to verify now \(claim_id \w+\)\n"(.*)"', user)
    text = m.group(1) if m else ""
    ids = re.findall(r"\| (r\d+) \|", user)
    cite = [f"T1.{ids[0]}"] if ids else []
    props = tools[0]["function"]["parameters"]["properties"]
    repairing = any(x.get("role") == "tool" for x in messages)
    rel = "UNDETERMINED"
    if "MOCK_INVALID" in text and not repairing:
        args = {"rationale": "x", "decision": "WEAKEN", "revised_text": "", "evidence_ids": cite}
    elif "most" in text or "may" in text:
        args = {"rationale": "mock: evidence supports more", "decision": "STRENGTHEN",
                "revised_text": text.replace("most", "all").replace("may ", ""), "evidence_ids": cite}
        rel = "STRONGER_SUPPORTED"
    elif "significantly" in text:
        args = {"rationale": "mock: no test", "decision": "WEAKEN",
                "revised_text": text.replace("significantly ", ""), "evidence_ids": cite}
        rel = "WEAKER_SUPPORTED"
    elif "Insurance" in text and "Insurance" not in user.split("## Draft passage")[0]:
        args = {"rationale": "mock: not in package", "decision": "REMOVE", "revised_text": "", "evidence_ids": cite}
        rel = "NOT_SUPPORTED"
    else:
        args = {"rationale": "mock: supported", "decision": "ACCEPT", "revised_text": "", "evidence_ids": cite}
        rel = "MATCHES"
    if "support_relation" in props:
        args = {"proposition": "mock proposition", "expressed_strength": "mock", "strongest_supported": "mock sentence",
                "support_relation": rel, **args}
    return {"content": "", "tool_calls": [_tc(args)]}
