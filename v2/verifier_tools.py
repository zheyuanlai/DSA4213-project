"""V2 tool-loop verifier for E5 (plan: v2/docs/E5_PLAN.md).

A faithful port of V1's `src.verifier.verify_claim` / `verify_draft` with two injectable parts: the system prompt and
the `submit_decision` schema. V1 builds its schema inside `verify_claim`, so the D1 schema cannot be passed to V1
directly. Everything else (tools, tool execution, budgets, duplicate handling, forced submit, decision validation,
repair turn) is V1's own code, called read-only. `tests/test_v2_e5.py` checks that with V1's prompt and schema the port
sends the same messages and returns the same decisions as V1.

Variants: "D0" = V1 adaptive prompt and schema; "D1" = V1 adaptive prompt + the D1 addendum, D1 schema;
"D1-C5" = as D1 but for a config with STRENGTHEN disabled: the addendum's single mapping line reads
"STRONGER_SUPPORTED -> ACCEPT (strengthening is not available)" (v2/prompts/verifier_tools_d1_c5_addendum.md), and
V1's no-strengthen note is appended to the decision definitions automatically.
"""
from __future__ import annotations

import json
from typing import Any

from src.evidence_store import EvidenceStore
from src.openrouter_client import BaseClient
from src.package_schema import ResearchPackage
from src.prompts import decision_block, system_prompt as v1_system_prompt
from src.render import render_verifier_context
from src.schemas import CallRecord, ClaimDraft, ClaimTrace, Draft, ToolAction, ToolObservation, VerificationDecision
from src.tools import EVIDENCE_TOOLS, TOOL_SCHEMAS, execute_tool, observation_to_message
from src.verifier import VerifierConfig, _canon_args, _named, claim_user_message, validate_decision
from src.writer import call_record
from v2.verifier_oracle import _judgement, _load, decision_schema

TOOL_VARIANTS = ("D0", "D1", "D1-C5")
ADDENDUM = {"D1": "verifier_oracle_d1_addendum.md", "D1-C5": "verifier_tools_d1_c5_addendum.md"}


def tools_system_prompt(variant: str, cfg: VerifierConfig) -> str:
    """V1's adaptive system prompt exactly as V1 builds it, plus the D1 addendum for D1."""
    if variant not in TOOL_VARIANTS or cfg.mode != "adaptive":
        raise ValueError("the adaptive loop with variant D0, D1 or D1-C5 is required")
    if variant != "D0" and (variant == "D1-C5") == cfg.can_strengthen:
        raise ValueError("D1-C5 requires can_strengthen=False, and D1 requires can_strengthen=True")
    base = v1_system_prompt("verifier_adaptive.md", decision_definitions=decision_block(cfg.allowed_decisions()),
                            max_tool_calls=str(cfg.max_tool_calls))
    return base if variant == "D0" else base + "\n\n" + _load(ADDENDUM[variant])


def verify_claim_tools(client: BaseClient, store: EvidenceStore, system: str, context: str, draft: Draft, idx: int,
                       cfg: VerifierConfig, ctx: dict[str, Any], calls: list[CallRecord], schema: dict[str, Any],
                       role: str) -> tuple[ClaimTrace, dict[str, Any] | None]:
    """Port of V1 `verify_claim` (adaptive branch kept; scripted branch kept for equivalence). Returns the trace and the
    raw arguments of the accepted submit_decision call (for the D1 judgement fields)."""
    claim = draft.sentences[idx]
    allowed = cfg.allowed_decisions()
    tools = [TOOL_SCHEMAS[t] for t in EVIDENCE_TOOLS] + [schema]
    trace = ClaimTrace(claim_id=claim.claim_id, original_text=claim.text)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": claim_user_message(context, draft, idx)},
    ]
    observed: set[str] = set()
    seen: dict[str, ToolObservation] = {}
    n_evidence = dup = protocol_retries = repairs = 0
    hard_cap_calls = cfg.max_tool_calls + cfg.max_protocol_retries + cfg.max_decision_repairs + 2
    last_args: dict[str, Any] | None = None
    while True:
        if trace.model_calls >= hard_cap_calls:
            trace.decision = VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                                  revised_text=claim.text, valid=False,
                                                  validation_notes=["model-call cap reached without a decision"])
            trace.stop_reason = "call_cap"
            break
        force_submit = (n_evidence >= cfg.max_tool_calls or dup >= cfg.max_duplicate_calls or repairs > 0)
        if cfg.mode == "scripted":
            expected = cfg.scripted_sequence[n_evidence] if n_evidence < len(cfg.scripted_sequence) and repairs == 0 else "submit_decision"
            tool_choice: Any = _named(expected)
        else:
            expected = "submit_decision" if force_submit else None
            tool_choice = _named("submit_decision") if force_submit else "required"
        res = client.chat(messages, role=role, ctx=ctx, max_tokens=cfg.max_tokens_per_turn, tools=tools,
                          tool_choice=tool_choice)
        rec = call_record(res, role)
        rec.model_id = client.model_id
        calls.append(rec)
        trace.model_calls += 1
        if not res.tool_calls:
            trace.protocol_errors.append(f"no tool call (finish_reason={res.finish_reason})")
            if protocol_retries < cfg.max_protocol_retries:
                protocol_retries += 1
                messages += [res.assistant_message,
                             {"role": "user", "content": "Respond by calling one tool: an evidence tool or submit_decision."}]
                continue
            trace.decision = VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                                  revised_text=claim.text, valid=False,
                                                  validation_notes=["model failed to call a tool"])
            trace.stop_reason = "protocol_failure"
            break
        messages.append(res.assistant_message)
        submit = next((tc for tc in res.tool_calls if tc.name == "submit_decision"), None)
        if submit is not None:
            for tc in res.tool_calls:
                if tc is not submit:
                    trace.protocol_errors.append(f"ignored {tc.name} issued in the same turn as submit_decision")
            if expected not in (None, "submit_decision"):
                trace.protocol_errors.append(f"scripted step expected {expected}, got submit_decision")
            last_args = submit.arguments
            dec = validate_decision(submit.arguments, claim, observed, allowed)
            if not dec.valid and repairs < cfg.max_decision_repairs:
                repairs += 1
                trace.protocol_errors.append("invalid decision: " + "; ".join(dec.validation_notes))
                for tc in res.tool_calls:
                    if tc is not submit:
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(
                            {"status": "NOT_EXECUTED", "message": "Ignored: issued in the same turn as submit_decision."})})
                messages.append({"role": "tool", "tool_call_id": submit.id,
                                 "content": json.dumps({"status": "INVALID_DECISION", "problems": dec.validation_notes,
                                                        "citable_ids_observed": sorted(observed),
                                                        "allowed_decisions": allowed})})
                continue
            trace.decision = dec
            trace.stop_reason = "decision" if dec.valid else "invalid_decision_fallback"
            break
        for k, tc in enumerate(res.tool_calls):
            if k > 0:
                trace.ignored_parallel_calls += 1
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(
                    {"status": "NOT_EXECUTED", "message": "Only one tool call per turn is processed. "
                     "Re-issue this call in a later turn if it is still needed."})})
                continue
            step = len(trace.actions) + 1
            policy = "scripted" if cfg.mode == "scripted" else "adaptive"
            action = ToolAction(call_id=tc.id, tool=tc.name, args=tc.arguments or {}, policy=policy, step=step)
            if tc.parse_error:
                obs = ToolObservation(call_id=tc.id, tool=tc.name, status="TOOL_ERROR", message=tc.parse_error)
            elif tc.name not in EVIDENCE_TOOLS:
                obs = ToolObservation(call_id=tc.id, tool=tc.name, status="TOOL_ERROR", message=f"unknown tool {tc.name!r}")
            elif n_evidence >= cfg.max_tool_calls:
                obs = ToolObservation(call_id=tc.id, tool=tc.name, status="TOOL_ERROR",
                                      message="evidence-tool budget exhausted; call submit_decision")
            else:
                if cfg.mode == "scripted" and tc.name != expected:
                    trace.protocol_errors.append(f"scripted step expected {expected}, got {tc.name}")
                key = tc.name + _canon_args(tc.arguments)
                if key in seen:
                    dup += 1
                    prev = seen[key]
                    obs = prev.model_copy(update={"call_id": tc.id,
                                                  "message": (prev.message + " " if prev.message else "") +
                                                  "DUPLICATE: identical call already made; same result repeated."})
                else:
                    obs = execute_tool(store, tc.name, tc.arguments or {}, tc.id)
                    seen[key] = obs
                n_evidence += 1
            observed.update(obs.returned_ids)
            trace.actions.append(action)
            trace.observations.append(obs)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": observation_to_message(obs)})
    return trace, last_args


def verify_draft_tools(client: BaseClient, pkg: ResearchPackage, draft: Draft, cfg: VerifierConfig, variant: str,
                       ctx: dict[str, Any], calls: list[CallRecord]) -> tuple[Draft, list[ClaimTrace], list[dict[str, Any]]]:
    """Port of V1 `verify_draft` for the adaptive loop. Returns (final draft, traces, D1 judgements per claim)."""
    store = EvidenceStore.from_package(pkg)
    system = tools_system_prompt(variant, cfg)
    schema = decision_schema("D0" if variant == "D0" else "D1", cfg.allowed_decisions())
    context = render_verifier_context(pkg)
    role = f"verify_{cfg.mode}" if variant == "D0" else f"verify_{cfg.mode}_{variant}"
    traces: list[ClaimTrace] = []
    judgements: list[dict[str, Any]] = []
    final: list[ClaimDraft] = []
    for idx, claim in enumerate(draft.sentences):
        if idx >= cfg.max_claims:
            t = ClaimTrace(claim_id=claim.claim_id, original_text=claim.text, stop_reason="over_claim_cap",
                           decision=VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                                         revised_text=claim.text, valid=False,
                                                         validation_notes=["not verified: claim cap"]))
            args = None
        else:
            t, args = verify_claim_tools(client, store, system, context, draft, idx, cfg, ctx, calls, schema, role)
        traces.append(t)
        judgements.append(_judgement(args) if variant != "D0" else {})
        d = t.decision
        assert d is not None
        if d.decision == "REMOVE":
            continue
        text = d.revised_text if d.decision in ("WEAKEN", "STRENGTHEN") else claim.text
        ids = d.evidence_ids if d.decision in ("WEAKEN", "STRENGTHEN") else claim.evidence_ids
        final.append(ClaimDraft(claim_id=claim.claim_id, text=text, evidence_ids=ids))
    return Draft(sentences=final), traces, judgements
