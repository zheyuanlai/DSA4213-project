"""Run-level typed schemas: drafts, tool actions/observations, decisions, run records."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DecisionType = Literal["ACCEPT", "WEAKEN", "STRENGTHEN", "REMOVE", "FLAG"]
ObsStatus = Literal["FOUND", "NOT_FOUND", "NOT_APPLICABLE", "TOOL_ERROR"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimDraft(_M):
    claim_id: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list, description="self-reported by writer; diagnostic only")
    scope: Optional[str] = None


class Draft(_M):
    """A passage as an ordered list of sentence-level claims."""

    sentences: list[ClaimDraft]

    @property
    def passage(self) -> str:
        return " ".join(s.text.strip() for s in self.sentences if s.text.strip())


class OutlineFinding(_M):
    finding_id: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    scope: str = ""
    caveats: str = ""


class Outline(_M):
    findings: list[OutlineFinding]


class ToolAction(_M):
    call_id: str
    tool: str
    args: dict[str, Any]
    policy: Literal["adaptive", "scripted"]
    step: int


class ToolObservation(_M):
    call_id: str
    tool: str
    status: ObsStatus
    data: dict[str, Any] = Field(default_factory=dict)
    returned_ids: list[str] = Field(default_factory=list, description="evidence/absence IDs citable in decisions")
    message: str = ""
    provenance: str = ""


class VerificationDecision(_M):
    claim_id: str
    decision: DecisionType
    original_text: str
    revised_text: str
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    valid: bool = True
    validation_notes: list[str] = Field(default_factory=list)


class ClaimTrace(_M):
    claim_id: str
    original_text: str
    actions: list[ToolAction] = Field(default_factory=list)
    observations: list[ToolObservation] = Field(default_factory=list)
    decision: Optional[VerificationDecision] = None
    model_calls: int = 0
    protocol_errors: list[str] = Field(default_factory=list)
    stop_reason: str = ""


class CallRecord(_M):
    """Secret-free record of one model API call (mirrors a cost-ledger line)."""

    call_id: str
    role: str
    model_id: str
    provider: Optional[str] = None
    generation_id: Optional[str] = None
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_is_estimate: bool = False
    latency_s: Optional[float] = None
    status: str = "ok"
    error: Optional[str] = None
    attempts: int = 1


class RunRecord(_M):
    run_id: str
    case_id: str
    condition: str
    split: str
    model_id: str
    provider_routing: dict[str, Any]
    decoding: dict[str, Any]
    prompt_hashes: dict[str, str]
    code_hash: str
    config_hash: str
    started_at: str
    finished_at: Optional[str] = None
    status: Literal["completed", "failed", "partial"] = "completed"
    failure: Optional[str] = None
    shared_artifacts: dict[str, str] = Field(default_factory=dict, description="name -> sha256 of shared upstream artifact")
    outline: Optional[Outline] = None
    drafts: list[dict[str, Any]] = Field(default_factory=list, description="every draft/revision, in order")
    critique: Optional[str] = None
    claim_traces: list[ClaimTrace] = Field(default_factory=list)
    final_passage: str = ""
    final_sentences: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallRecord] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    is_mock: bool = False
