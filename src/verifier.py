"""Claim-by-claim verifier: an explicit finite-state action/observation loop.

States per claim:  SELECT_ACTION -> (EXECUTE_TOOL -> OBSERVE)* -> DECIDE -> VALIDATE -> DONE
* adaptive: the model chooses the next tool (or to stop) from its observations
  (tool_choice="required"); <= max_tool_calls evidence calls; duplicates detected.
* scripted: identical tools, but each step's tool is FORCED in a fixed order
  (tool_choice = named function); the model only fills arguments.
Decisions are validated: allowed set (STRENGTHEN rejected when disabled), cited IDs
must have been returned by this claim's observations, edits need revised text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from src.evidence_store import EvidenceStore
from src.openrouter_client import BaseClient
from src.package_schema import ResearchPackage
from src.prompts import decision_block, system_prompt
from src.render import render_verifier_context
from src.schemas import CallRecord, ClaimDraft, ClaimTrace, Draft, ToolAction, ToolObservation, VerificationDecision
from src.tools import EVIDENCE_TOOLS, TOOL_SCHEMAS, execute_tool, observation_to_message, submit_decision_schema
from src.writer import call_record

ALL_DECISIONS = ["ACCEPT", "WEAKEN", "STRENGTHEN", "REMOVE", "FLAG"]
SCRIPTED_SEQUENCE = ("lookup_table", "compare_numbers", "get_test_metadata", "retrieve_passage")


@dataclass(frozen=True)
class VerifierConfig:
    mode: Literal["adaptive", "scripted"]
    can_strengthen: bool
    max_tool_calls: int = 4
    max_claims: int = 6
    max_tokens_per_turn: int = 450
    max_duplicate_calls: int = 2
    max_protocol_retries: int = 1
    max_decision_repairs: int = 1
    scripted_sequence: tuple[str, ...] = SCRIPTED_SEQUENCE

    def allowed_decisions(self) -> list[str]:
        return [d for d in ALL_DECISIONS if self.can_strengthen or d != "STRENGTHEN"]

    def __post_init__(self):
        if self.mode == "scripted" and len(self.scripted_sequence) > self.max_tool_calls:
            raise ValueError("scripted sequence longer than tool budget")
        if any(t not in EVIDENCE_TOOLS for t in self.scripted_sequence):
            raise ValueError("scripted sequence contains a non-evidence tool")


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _canon_args(args: dict[str, Any] | None) -> str:
    if not args:
        return "{}"
    return json.dumps({k: (_norm(v) if isinstance(v, str) else v) for k, v in sorted(args.items())}, sort_keys=True)


def _named(name: str) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name}}


def claim_user_message(context: str, draft: Draft, idx: int) -> str:
    marked = []
    for j, s in enumerate(draft.sentences):
        marked.append(f">>> {s.text} <<<" if j == idx else s.text)
    c = draft.sentences[idx]
    return (
        f"{context}\n\n## Draft passage under review (the claim being verified is marked >>> <<<)\n"
        + " ".join(marked)
        + f"\n\n## Claim to verify now (claim_id {c.claim_id})\n\"{c.text}\"\n"
        + f"Writer's self-reported evidence IDs (unverified hints): {json.dumps(c.evidence_ids)}"
    )


def _parse_ids(raw: Any) -> list[str]:
    """evidence_ids should be a list; tolerate a JSON-encoded list or a comma-separated string."""
    if isinstance(raw, str):
        txt = raw.strip()
        try:
            parsed = json.loads(txt)
            raw = parsed if isinstance(parsed, list) else [txt]
        except json.JSONDecodeError:
            raw = [x.strip().strip('"\'') for x in txt.strip("[]").split(",") if x.strip()]
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if isinstance(x, (str, int)) and str(x).strip()]


def validate_decision(args: dict[str, Any] | None, claim: ClaimDraft, observed: set[str], allowed: list[str]) -> VerificationDecision:
    notes: list[str] = []
    if args is None:
        return VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                    revised_text=claim.text, valid=False, validation_notes=["unparseable decision arguments"])
    dec = str(args.get("decision", "")).strip().upper()
    rationale = str(args.get("rationale", ""))[:1200]
    revised = str(args.get("revised_text") or "").strip()
    ids = _parse_ids(args.get("evidence_ids"))
    valid = True
    if dec not in allowed:
        return VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                    revised_text=claim.text, rationale=rationale, valid=False,
                                    validation_notes=[f"decision {dec!r} not allowed (allowed: {allowed})"])
    bad_ids = [i for i in ids if i not in observed]
    good_ids = [i for i in ids if i in observed]
    if bad_ids:
        notes.append(f"cited ids not returned by this claim's tool calls: {bad_ids}")
    if dec in ("WEAKEN", "STRENGTHEN"):
        if not revised:
            return VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                        revised_text=claim.text, rationale=rationale, evidence_ids=good_ids, valid=False,
                                        validation_notes=notes + [f"{dec} without revised_text"])
        if _norm(revised) == _norm(claim.text):
            notes.append(f"{dec} with unchanged text -> treated as ACCEPT")
            dec = "ACCEPT"
    if dec in ("WEAKEN", "STRENGTHEN", "REMOVE") and not good_ids:
        return VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                    revised_text=claim.text, rationale=rationale, valid=False,
                                    validation_notes=notes + [f"{dec} must cite evidence returned by tools"])
    if dec in ("ACCEPT", "FLAG"):
        revised = claim.text
    elif dec == "REMOVE":
        revised = ""
    return VerificationDecision(claim_id=claim.claim_id, decision=dec, original_text=claim.text, revised_text=revised,
                                evidence_ids=good_ids, rationale=rationale, valid=valid, validation_notes=notes)


def verify_claim(client: BaseClient, store: EvidenceStore, system: str, context: str, draft: Draft, idx: int,
                 cfg: VerifierConfig, ctx: dict[str, Any], calls: list[CallRecord]) -> ClaimTrace:
    claim = draft.sentences[idx]
    allowed = cfg.allowed_decisions()
    tools = [TOOL_SCHEMAS[t] for t in EVIDENCE_TOOLS] + [submit_decision_schema(allowed)]
    trace = ClaimTrace(claim_id=claim.claim_id, original_text=claim.text)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": claim_user_message(context, draft, idx)},
    ]
    observed: set[str] = set()
    seen: dict[str, ToolObservation] = {}
    n_evidence = dup = protocol_retries = repairs = 0
    hard_cap_calls = cfg.max_tool_calls + cfg.max_protocol_retries + cfg.max_decision_repairs + 2
    role = f"verify_{cfg.mode}"
    while True:
        if trace.model_calls >= hard_cap_calls:
            trace.decision = VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                                  revised_text=claim.text, valid=False,
                                                  validation_notes=["model-call cap reached without a decision"])
            trace.stop_reason = "call_cap"
            break
        # ---- SELECT_ACTION: what the model is allowed/forced to do next
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
            dec = validate_decision(submit.arguments, claim, observed, allowed)
            if not dec.valid and repairs < cfg.max_decision_repairs:
                repairs += 1
                trace.protocol_errors.append("invalid decision: " + "; ".join(dec.validation_notes))
                for tc in res.tool_calls:  # every tool_call id must receive a tool message before the next turn
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
        # ---- EXECUTE_TOOL / OBSERVE (one call per turn: the policy chooses the NEXT check
        # after seeing each observation; extra parallel calls are answered NOT EXECUTED)
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
    return trace


def verify_draft(client: BaseClient, pkg: ResearchPackage, draft: Draft, cfg: VerifierConfig, ctx: dict[str, Any],
                 calls: list[CallRecord]) -> tuple[Draft, list[ClaimTrace]]:
    store = EvidenceStore.from_package(pkg)
    role_file = "verifier_scripted.md" if cfg.mode == "scripted" else "verifier_adaptive.md"
    subs = {"decision_definitions": decision_block(cfg.allowed_decisions())}
    if cfg.mode == "scripted":
        subs["scripted_sequence"] = " → ".join(cfg.scripted_sequence)
    else:
        subs["max_tool_calls"] = str(cfg.max_tool_calls)
    system = system_prompt(role_file, **subs)
    context = render_verifier_context(pkg)
    traces: list[ClaimTrace] = []
    final: list[ClaimDraft] = []
    for idx, claim in enumerate(draft.sentences):
        if idx >= cfg.max_claims:
            t = ClaimTrace(claim_id=claim.claim_id, original_text=claim.text, stop_reason="over_claim_cap",
                           decision=VerificationDecision(claim_id=claim.claim_id, decision="FLAG", original_text=claim.text,
                                                         revised_text=claim.text, valid=False,
                                                         validation_notes=["not verified: claim cap"]))
        else:
            t = verify_claim(client, store, system, context, draft, idx, cfg, ctx, calls)
        traces.append(t)
        d = t.decision
        assert d is not None
        if d.decision == "REMOVE":
            continue
        text = d.revised_text if d.decision in ("WEAKEN", "STRENGTHEN") else claim.text
        ids = d.evidence_ids if d.decision in ("WEAKEN", "STRENGTHEN") else claim.evidence_ids
        final.append(ClaimDraft(claim_id=claim.claim_id, text=text, evidence_ids=ids))
    return Draft(sentences=final), traces
