"""V2 oracle-evidence verifier for experiments E1/E2 (design: v2/docs/E1_E2_DESIGN.md).

The verifier gets the complete research package in context and makes one forced `submit_decision` call (plus at most one
repair turn, as in V1). There are no evidence tools, so retrieval cannot cause a failure. The variants differ ONLY in the
decision instructions and the decision schema:

* D0: the V1 adaptive-verifier prompt with the tool procedure removed; the V1 `submit_decision` schema.
* D1: D0 + an explicit structured strength judgement (fields generated before the decision).
* D2: D1 + a generic list of ways a sentence can understate its evidence.
* D1c: D1 + one general paragraph on the comparability of compared results (experiment E2b).

The system-prompt prefix, the evidence block, the user message and the token limit are identical across variants.
V1 modules are imported read-only; nothing in `src/` is modified.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.evidence_store import EvidenceStore
from src.openrouter_client import BaseClient
from src.package_schema import ResearchPackage
from src.prompts import decision_block, load as load_v1_prompt
from src.render import render_package
from src.schemas import CallRecord, Draft, VerificationDecision
from src.tools import submit_decision_schema
from src.verifier import ALL_DECISIONS, claim_user_message, validate_decision
from src.writer import call_record

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
VARIANTS = ("D0", "D1", "D2", "D1c")
RELATIONS = ["STRONGER_SUPPORTED", "MATCHES", "WEAKER_SUPPORTED", "NOT_SUPPORTED", "UNDETERMINED"]
# Mapping used to measure action consistency (and, only if rule R3 fires, by a later D3).
RELATION_TO_DECISION = {
    "STRONGER_SUPPORTED": {"STRENGTHEN"},
    "MATCHES": {"ACCEPT"},
    "WEAKER_SUPPORTED": {"WEAKEN"},
    "NOT_SUPPORTED": {"REMOVE", "WEAKEN"},
    "UNDETERMINED": {"FLAG"},
}
MAX_TOKENS = 800
MAX_DECISION_REPAIRS = 1
TASK_MARKER = "\n\n## Task\n"


def _load(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def prompt_files(variant: str) -> list[str]:
    files = ["verifier_oracle_d0.md"]
    if variant in ("D1", "D2", "D1c"):
        files.append("verifier_oracle_d1_addendum.md")
    if variant == "D2":
        files.append("verifier_oracle_d2_addendum.md")
    if variant == "D1c":
        files.append("verifier_oracle_d1c_comparability.md")
    return files


def v2_prompt_hashes() -> dict[str, str]:
    names = ["verifier_oracle_d0.md", "verifier_oracle_d1_addendum.md", "verifier_oracle_d2_addendum.md",
             "verifier_oracle_d1c_comparability.md"]
    return {n: hashlib.sha256(_load(n).encode("utf-8")).hexdigest()[:16] for n in names}


def system_prompt(variant: str, allowed: list[str]) -> str:
    """V1 shared reporting policy + D0 body (+ addenda). The D0 part is a strict prefix of D1, and D1 of D2."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}")
    body = _load("verifier_oracle_d0.md").replace("{{decision_definitions}}", decision_block(allowed))
    parts = [load_v1_prompt("common_reporting.md").strip(), body]
    parts += [_load(f) for f in prompt_files(variant)[1:]]
    out = "\n\n".join(parts)
    if "{{" in out:
        raise ValueError("unfilled placeholder in V2 oracle prompt")
    return out


def oracle_evidence(pkg: ResearchPackage) -> str:
    """The V1 writer view of the package (all values, tests and passages), without the writer's task instruction."""
    full = render_package(pkg)
    i = full.rfind(TASK_MARKER)
    return full[:i] if i >= 0 else full


def user_message(pkg: ResearchPackage, draft: Draft, idx: int) -> str:
    """V1 verifier message format with the full evidence block in place of the V1 evidence index."""
    return claim_user_message(oracle_evidence(pkg), draft, idx)


def decision_schema(variant: str, allowed: list[str]) -> dict[str, Any]:
    base = submit_decision_schema(allowed)
    if variant == "D0":
        return base
    params = base["function"]["parameters"]
    judgement = {
        "proposition": {"type": "string", "description": "the main proposition the sentence asserts, in a few words"},
        "expressed_strength": {"type": "string",
                               "description": "how strongly the sentence asserts it, quoting the words that set its strength"},
        "strongest_supported": {"type": "string", "description": (
            "one sentence: the strongest version of the same proposition that the package supports within the "
            "evaluated scope")},
        "support_relation": {"type": "string", "enum": list(RELATIONS)},
    }
    # Judgement fields come first so they are generated before the decision.
    params["properties"] = {**judgement, **params["properties"]}
    params["required"] = list(judgement) + list(params["required"])
    base["function"]["description"] = (
        "Record the strength judgement, then the decision. " + base["function"]["description"])
    return base


@dataclass
class OracleResult:
    variant: str
    decision: VerificationDecision
    judgement: dict[str, Any] = field(default_factory=dict)
    raw_arguments: list[Any] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    protocol_errors: list[str] = field(default_factory=list)
    model_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"variant": self.variant, "decision": self.decision.model_dump(), "judgement": self.judgement,
                "raw_arguments": self.raw_arguments, "calls": [c.model_dump() for c in self.calls],
                "protocol_errors": self.protocol_errors, "model_calls": self.model_calls}


def _judgement(args: dict[str, Any] | None) -> dict[str, Any]:
    if not args:
        return {}
    return {k: args.get(k) for k in ("proposition", "expressed_strength", "strongest_supported", "support_relation")}


def verify_claim_oracle(client: BaseClient, pkg: ResearchPackage, draft: Draft, idx: int, variant: str,
                        ctx: dict[str, Any], *, can_strengthen: bool = True) -> OracleResult:
    """One oracle verification of draft sentence `idx`. Validation is V1's, with every package ID citable."""
    allowed = [d for d in ALL_DECISIONS if can_strengthen or d != "STRENGTHEN"]
    store = EvidenceStore.from_package(pkg)
    citable = set(store.items)
    claim = draft.sentences[idx]
    schema = decision_schema(variant, allowed)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(variant, allowed)},
        {"role": "user", "content": user_message(pkg, draft, idx)},
    ]
    role = f"verify_oracle_{variant}"
    out = OracleResult(variant=variant, decision=VerificationDecision(
        claim_id=claim.claim_id, decision="FLAG", original_text=claim.text, revised_text=claim.text, valid=False,
        validation_notes=["no decision"]))
    repairs = 0
    while True:
        res = client.chat(messages, role=role, ctx=ctx, max_tokens=MAX_TOKENS, tools=[schema],
                          tool_choice={"type": "function", "function": {"name": "submit_decision"}})
        rec = call_record(res, role)
        rec.model_id = client.model_id
        out.calls.append(rec)
        out.model_calls += 1
        submit = next((tc for tc in res.tool_calls if tc.name == "submit_decision"), None)
        if submit is None:
            out.protocol_errors.append(f"no submit_decision call (finish_reason={res.finish_reason})")
            out.decision.validation_notes = ["model failed to call submit_decision"]
            return out
        args = submit.arguments
        out.raw_arguments.append(args if args is not None else submit.arguments_raw)
        dec = validate_decision(args, claim, citable, allowed)
        if variant != "D0":
            rel = (args or {}).get("support_relation")
            if rel not in RELATIONS:
                dec.validation_notes.append(f"support_relation {rel!r} not in {RELATIONS}")
        out.judgement = _judgement(args)
        out.decision = dec
        if dec.valid or repairs >= MAX_DECISION_REPAIRS:
            return out
        repairs += 1
        out.protocol_errors.append("invalid decision: " + "; ".join(dec.validation_notes))
        messages += [res.assistant_message, {"role": "tool", "tool_call_id": submit.id, "content": json.dumps(
            {"status": "INVALID_DECISION", "problems": dec.validation_notes, "allowed_decisions": allowed})}]


def action_consistent(judgement: dict[str, Any], decision: str) -> bool | None:
    rel = judgement.get("support_relation")
    if rel not in RELATION_TO_DECISION:
        return None
    return decision in RELATION_TO_DECISION[rel]
