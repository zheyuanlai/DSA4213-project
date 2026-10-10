"""Writer, planner and generic reviewer stages (model calls with JSON outputs)."""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from src.openrouter_client import BaseClient, ChatResult
from src.package_schema import ResearchPackage
from src.prompts import system_prompt
from src.render import render_package
from src.schemas import CallRecord, ClaimDraft, Draft, Outline, OutlineFinding

MAX_TOKENS = {"writer": 700, "outline": 700, "reviewer": 450, "reviser": 700}
MAX_SENTENCES_ACCEPTED = 8

PASSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "evidence_ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["sentences"],
    "additionalProperties": False,
}
OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "scope": {"type": "string"},
                    "caveats": {"type": "string"},
                },
                "required": ["finding_id", "summary", "evidence_ids", "scope", "caveats"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


class OutputFormatError(RuntimeError):
    pass


def response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}


def call_record(res: ChatResult, role: str) -> CallRecord:
    return CallRecord(
        call_id=res.call_id, role=role, model_id=getattr(res, "model_id", "") or "",
        provider=res.provider, generation_id=res.generation_id, finish_reason=res.finish_reason,
        prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
        reasoning_tokens=res.reasoning_tokens, cost_usd=res.cost_usd,
        cost_is_estimate=res.cost_source not in ("provider_reported", "mock"), latency_s=res.latency_s,
        attempts=res.attempts,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise OutputFormatError("no JSON object found in output")
        try:
            obj = json.loads(t[i : j + 1])
        except json.JSONDecodeError as e:
            raise OutputFormatError(f"malformed JSON: {e}") from e
    if not isinstance(obj, dict):
        raise OutputFormatError("top-level JSON is not an object")
    return obj


def to_draft(obj: dict[str, Any]) -> Draft:
    sents = obj.get("sentences")
    if not isinstance(sents, list) or not sents:
        raise OutputFormatError("'sentences' must be a non-empty list")
    if len(sents) > MAX_SENTENCES_ACCEPTED:
        raise OutputFormatError(f"too many sentences ({len(sents)}); write at most 5")
    out = []
    for i, s in enumerate(sents, 1):
        if not isinstance(s, dict) or not isinstance(s.get("text"), str) or not s["text"].strip():
            raise OutputFormatError(f"sentence {i} lacks non-empty 'text'")
        ids = s.get("evidence_ids") or []
        if not isinstance(ids, list):
            ids = []
        out.append(ClaimDraft(claim_id=f"s{i}", text=s["text"].strip(), evidence_ids=[str(x) for x in ids]))
    return Draft(sentences=out)


def to_outline(obj: dict[str, Any]) -> Outline:
    fs = obj.get("findings")
    if not isinstance(fs, list) or not fs:
        raise OutputFormatError("'findings' must be a non-empty list")
    out = []
    for i, f in enumerate(fs, 1):
        if not isinstance(f, dict) or not str(f.get("summary", "")).strip():
            raise OutputFormatError(f"finding {i} lacks 'summary'")
        out.append(OutlineFinding(
            finding_id=str(f.get("finding_id") or f"F{i}"), summary=str(f["summary"]).strip(),
            evidence_ids=[str(x) for x in (f.get("evidence_ids") or []) if isinstance(x, (str, int))],
            scope=str(f.get("scope") or ""), caveats=str(f.get("caveats") or ""),
        ))
    return Outline(findings=out)


def _json_call(client: BaseClient, system: str, user: str, *, role: str, ctx: dict[str, Any], max_tokens: int,
               schema_name: str, schema: dict[str, Any], convert: Callable[[dict[str, Any]], Any],
               calls: list[CallRecord], max_attempts: int = 2):
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last_err = ""
    for attempt in range(max_attempts):
        res = client.chat(messages, role=role, ctx=ctx, max_tokens=max_tokens,
                          response_format=response_format(schema_name, schema))
        rec = call_record(res, role)
        rec.model_id = client.model_id
        calls.append(rec)
        try:
            if res.finish_reason == "length":
                raise OutputFormatError("output was truncated (max_tokens reached); be more concise")
            return convert(parse_json_object(res.content))
        except OutputFormatError as e:
            last_err = str(e)
            rec.status = "format_error"
            rec.error = last_err
            messages = messages + [
                {"role": "assistant", "content": res.content or ""},
                {"role": "user", "content": f"Your previous output was invalid ({last_err}). Output ONLY the JSON object in the required format."},
            ]
    raise OutputFormatError(f"{role}: no valid output after {max_attempts} attempts: {last_err}")


# ----------------------------------------------------------------------------- stages
def direct_draft(client: BaseClient, pkg: ResearchPackage, ctx: dict[str, Any], calls: list[CallRecord]) -> Draft:
    return _json_call(client, system_prompt("writer_direct.md"), render_package(pkg), role="writer_direct", ctx=ctx,
                      max_tokens=MAX_TOKENS["writer"], schema_name="passage", schema=PASSAGE_SCHEMA,
                      convert=to_draft, calls=calls)


def make_outline(client: BaseClient, pkg: ResearchPackage, ctx: dict[str, Any], calls: list[CallRecord]) -> Outline:
    return _json_call(client, system_prompt("claim_outline.md"), render_package(pkg), role="outline", ctx=ctx,
                      max_tokens=MAX_TOKENS["outline"], schema_name="claim_plan", schema=OUTLINE_SCHEMA,
                      convert=to_outline, calls=calls)


def outline_draft(client: BaseClient, pkg: ResearchPackage, outline: Outline, ctx: dict[str, Any],
                  calls: list[CallRecord]) -> Draft:
    user = render_package(pkg) + "\n\n## Claim plan\n" + json.dumps(outline.model_dump(), ensure_ascii=False, indent=1)
    return _json_call(client, system_prompt("draft_writer.md"), user, role="writer_from_outline", ctx=ctx,
                      max_tokens=MAX_TOKENS["writer"], schema_name="passage", schema=PASSAGE_SCHEMA,
                      convert=to_draft, calls=calls)


def generic_review(client: BaseClient, pkg: ResearchPackage, draft: Draft, ctx: dict[str, Any],
                   calls: list[CallRecord]) -> str:
    user = render_package(pkg) + "\n\n## Draft passage to review\n" + draft.passage
    messages = [{"role": "system", "content": system_prompt("reviewer_generic.md")}, {"role": "user", "content": user}]
    res = client.chat(messages, role="reviewer_generic", ctx=ctx, max_tokens=MAX_TOKENS["reviewer"])
    rec = call_record(res, "reviewer_generic")
    rec.model_id = client.model_id
    calls.append(rec)
    text = (res.content or "").strip()
    if not text:
        rec.status = "empty_output"
        raise OutputFormatError("reviewer returned empty critique")
    return text


def generic_revise(client: BaseClient, pkg: ResearchPackage, draft: Draft, critique: str, ctx: dict[str, Any],
                   calls: list[CallRecord]) -> Draft:
    user = (render_package(pkg) + "\n\n## Draft passage\n" + draft.passage + "\n\n## Reviewer critique\n" + critique)
    return _json_call(client, system_prompt("reviser_generic.md"), user, role="reviser_generic", ctx=ctx,
                      max_tokens=MAX_TOKENS["reviser"], schema_name="passage", schema=PASSAGE_SCHEMA,
                      convert=to_draft, calls=calls)
