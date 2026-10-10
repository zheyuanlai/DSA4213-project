"""Deterministic offline responder for MockClient (tests and `--mock` dry runs only).

It produces protocol-correct outputs (JSON passages, tool calls honouring forced
tool_choice, submit_decision citing returned ids). Outputs are flagged is_mock and must
never be mixed into real analyses.
"""
from __future__ import annotations

import json
import re
from typing import Any

_counter = {"n": 0}


def _tc(name: str, args: dict[str, Any]) -> dict[str, Any]:
    _counter["n"] += 1
    return {"id": f"call_mock_{_counter['n']}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def _ids_in(text: str) -> list[str]:
    return re.findall(r"`(T\d+)`", text)


def _last_tool_payloads(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for m in messages:
        if m.get("role") == "tool":
            try:
                out.append(json.loads(m["content"]))
            except Exception:
                pass
    return out


def mock_responder(messages, tools, tool_choice, role):
    user = next((m["content"] for m in messages if m["role"] == "user"), "")
    if role in ("writer_direct", "writer_from_outline", "reviser_generic"):
        tables = re.findall(r"### Table (\w+):", user)
        t = tables[0] if tables else "T1"
        sents = [
            {"text": "The proposed method significantly outperforms the baseline on the evaluated benchmark.", "evidence_ids": [f"{t}.r1"]},
            {"text": "Its advantage is consistent across settings.", "evidence_ids": []},
        ]
        if role == "reviser_generic":
            sents[0]["text"] = "The proposed method achieves a higher score than the baseline on the evaluated benchmark."
        return {"content": json.dumps({"sentences": sents})}
    if role == "outline":
        return {"content": json.dumps({"findings": [{"finding_id": "F1", "summary": "Method beats baseline.",
                                                     "evidence_ids": ["T1.r1"], "scope": "main benchmark", "caveats": ""}]})}
    if role == "reviewer_generic":
        return {"content": "1. Avoid significance language unless a test is reported."}
    if role.startswith("verify"):
        forced = tool_choice.get("function", {}).get("name") if isinstance(tool_choice, dict) else None
        payloads = _last_tool_payloads(messages)
        observed = [i for p in payloads for i in p.get("citable_ids", [])]
        tables = re.findall(r"### Table (\w+):", user) or ["T1"]
        comps = re.findall(r"comparison `(\w+)/(\w+)`", user)
        args_for = {
            "lookup_table": {"table_id": tables[0]},
            "compare_numbers": {"claimed": 1.0, "evidence_id": f"{tables[0]}.r1.x"},
            "get_test_metadata": {"experiment_id": comps[0][0], "comparison_id": comps[0][1]} if comps else {"experiment_id": "exp1", "comparison_id": "cmp1"},
            "retrieve_passage": {"query_or_source_id": "P1"},
        }
        if forced and forced != "submit_decision":
            return {"content": "", "tool_calls": [_tc(forced, args_for[forced])]}
        if forced is None and len(payloads) < 2:
            name = "lookup_table" if not payloads else "get_test_metadata"
            return {"content": "", "tool_calls": [_tc(name, args_for[name])]}
        allowed = []
        for t in tools or []:
            if t["function"]["name"] == "submit_decision":
                allowed = t["function"]["parameters"]["properties"]["decision"]["enum"]
        claim = re.search(r'## Claim to verify now \(claim_id \w+\)\n"(.*)"', user)
        text = claim.group(1) if claim else ""
        if "significantly" in text and observed:
            return {"content": "", "tool_calls": [_tc("submit_decision", {
                "rationale": "No test supports significance.", "decision": "WEAKEN",
                "revised_text": text.replace("significantly outperforms", "achieves a higher score than"),
                "evidence_ids": observed[:2]})]}
        if "consistent" in text and "STRENGTHEN" in allowed and observed:
            return {"content": "", "tool_calls": [_tc("submit_decision", {
                "rationale": "mock strengthen", "decision": "STRENGTHEN",
                "revised_text": text.replace("is consistent", "holds on every evaluated setting"),
                "evidence_ids": observed[:1]})]}
        return {"content": "", "tool_calls": [_tc("submit_decision", {
            "rationale": "Supported.", "decision": "ACCEPT", "revised_text": "", "evidence_ids": observed[:1]})]}
    return {"content": "{}"}
