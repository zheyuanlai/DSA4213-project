"""Per-case pipeline: builds shared upstream artifacts once, then each condition's RunRecord.

Pipeline (full agent, C4):
  ResearchPackage -> evidence index (EvidenceStore, no gold) -> claim outline -> writer
  -> sentence-level claim segmentation (writer's sentence list) -> adaptive verifier
  -> ACCEPT/WEAKEN/STRENGTHEN/REMOVE/FLAG -> final passage + per-claim provenance + trace + costs
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from src.conditions import CONDITIONS, ConditionConfig
from src.cost_guard import BudgetExceeded, now_iso
from src.openrouter_client import BaseClient, FatalAPIError, TransientAPIError
from src.package_schema import CaseRecord
from src.schemas import CallRecord, ClaimTrace, Draft, Outline, RunRecord
from src.verifier import verify_draft
from src.writer import OutputFormatError, direct_draft, generic_review, generic_revise, make_outline, outline_draft

RECOVERABLE = (OutputFormatError, TransientAPIError)
FATAL = (FatalAPIError, BudgetExceeded)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, path)


def _draft_entry(stage: str, d: Draft) -> dict[str, Any]:
    return {"stage": stage, "passage": d.passage, "sentences": [s.model_dump() for s in d.sentences]}


class SharedArtifacts:
    """Loads or computes the direct draft and the outline+draft for one case (cached on disk)."""

    def __init__(self, client: BaseClient, record: CaseRecord, shared_dir: Path, base_ctx: dict[str, Any]):
        self.client, self.record, self.dir, self.base_ctx = client, record, shared_dir, base_ctx
        self._direct: Optional[dict[str, Any]] = None
        self._outline: Optional[dict[str, Any]] = None

    def _load(self, name: str) -> Optional[dict[str, Any]]:
        p = self.dir / f"{name}.json"
        if p.exists():
            d = json.loads(p.read_text())
            if d.get("model_id") == self.client.model_id and d.get("is_mock") == self.client.is_mock:
                return d
        return None

    def direct(self) -> dict[str, Any]:
        if self._direct is None:
            self._direct = self._load("direct")
        if self._direct is None:
            calls: list[CallRecord] = []
            ctx = {**self.base_ctx, "condition": "shared_direct"}
            art: dict[str, Any] = {"model_id": self.client.model_id, "is_mock": self.client.is_mock, "created_at": now_iso()}
            try:
                d = direct_draft(self.client, self.record.package, ctx, calls)
                art.update(status="ok", draft=d.model_dump(), sha256=sha256_obj(d.model_dump()))
            except RECOVERABLE as e:
                art.update(status="failed", error=f"{type(e).__name__}: {e}")
            art["calls"] = [c.model_dump() for c in calls]
            atomic_write_json(self.dir / "direct.json", art)
            self._direct = art
        return self._direct

    def outline(self) -> dict[str, Any]:
        if self._outline is None:
            self._outline = self._load("outline")
        if self._outline is None:
            calls: list[CallRecord] = []
            ctx = {**self.base_ctx, "condition": "shared_outline"}
            art: dict[str, Any] = {"model_id": self.client.model_id, "is_mock": self.client.is_mock, "created_at": now_iso()}
            try:
                o = make_outline(self.client, self.record.package, ctx, calls)
                art["outline"] = o.model_dump()
                d = outline_draft(self.client, self.record.package, o, ctx, calls)
                art.update(status="ok", draft=d.model_dump(), sha256=sha256_obj({"o": o.model_dump(), "d": d.model_dump()}))
            except RECOVERABLE as e:
                art.update(status="failed", error=f"{type(e).__name__}: {e}")
            art["calls"] = [c.model_dump() for c in calls]
            atomic_write_json(self.dir / "outline.json", art)
            self._outline = art
        return self._outline


def _totals(calls: list[CallRecord], own_calls: list[CallRecord], traces: list[ClaimTrace]) -> dict[str, Any]:
    def s(attr, cs):
        return sum((getattr(c, attr) or 0) for c in cs)

    dec_counts: dict[str, int] = {}
    for t in traces:
        if t.decision:
            dec_counts[t.decision.decision] = dec_counts.get(t.decision.decision, 0) + 1
    tool_counts: dict[str, int] = {}
    for t in traces:
        for a in t.actions:
            tool_counts[a.tool] = tool_counts.get(a.tool, 0) + 1
    return {
        "n_model_calls": len(calls),
        "n_model_calls_condition_only": len(own_calls),
        "n_tool_calls": sum(len(t.actions) for t in traces),
        "tool_counts": tool_counts,
        "prompt_tokens": s("prompt_tokens", calls),
        "completion_tokens": s("completion_tokens", calls),
        "reasoning_tokens": s("reasoning_tokens", calls),
        "cost_usd": round(s("cost_usd", calls), 8),
        "cost_usd_condition_only": round(s("cost_usd", own_calls), 8),
        "any_cost_estimated": any(c.cost_is_estimate for c in calls),
        "latency_s": round(s("latency_s", calls), 3),
        "n_claims": len(traces),
        "decision_counts": dec_counts,
        "n_invalid_decisions": sum(1 for t in traces if t.decision and not t.decision.valid),
        "n_protocol_errors": sum(len(t.protocol_errors) for t in traces),
        "n_ignored_parallel_calls": sum(t.ignored_parallel_calls for t in traces),
        "n_format_errors": sum(1 for c in calls if c.status == "format_error"),
    }


def run_condition(cond: ConditionConfig, shared: SharedArtifacts, client: BaseClient, record: CaseRecord,
                  run_meta: dict[str, Any], max_tool_calls: int = 4, max_claims: int = 6) -> RunRecord:
    ctx = {**shared.base_ctx, "condition": cond.code}
    rr = RunRecord(
        run_id=f"{run_meta['run_tag']}:{cond.code}:{record.case_id}", case_id=record.case_id, condition=cond.code,
        split=record.split, model_id=client.model_id, provider_routing=client.provider_routing,
        decoding=client.decoding, prompt_hashes=run_meta["prompt_hashes"], code_hash=run_meta["code_hash"],
        config_hash=run_meta["config_hash"], started_at=now_iso(), is_mock=client.is_mock,
    )
    upstream = shared.direct() if cond.upstream == "direct" else shared.outline()
    up_calls = [CallRecord(**c) for c in upstream.get("calls", [])]
    rr.shared_artifacts = {cond.upstream: upstream.get("sha256", "")}
    own_calls: list[CallRecord] = []
    traces: list[ClaimTrace] = []
    try:
        if upstream.get("status") != "ok":
            raise OutputFormatError(f"upstream {cond.upstream} artifact failed: {upstream.get('error')}")
        if cond.uses_outline:
            rr.outline = Outline(**upstream["outline"])
        draft = Draft(**upstream["draft"])
        rr.drafts.append(_draft_entry("direct_draft" if cond.upstream == "direct" else "outline_draft", draft))
        final = draft
        if cond.generic_review:
            rr.critique = generic_review(client, record.package, draft, ctx, own_calls)
            final = generic_revise(client, record.package, draft, rr.critique, ctx, own_calls)
            rr.drafts.append(_draft_entry("generic_revision", final))
        elif cond.verify_mode:
            vcfg = cond.verifier_config(max_tool_calls=max_tool_calls, max_claims=max_claims)
            final, traces = verify_draft(client, record.package, draft, vcfg, ctx, own_calls)
            rr.claim_traces = traces
            rr.drafts.append(_draft_entry(f"verified_{cond.verify_mode}", final))
        rr.final_passage = final.passage
        rr.final_sentences = [s.model_dump() for s in final.sentences]
        rr.status = "completed"
        if not final.sentences:
            rr.status = "completed"
            rr.failure = "empty_final_passage (all claims removed)"
    except RECOVERABLE as e:
        rr.status = "failed"
        rr.failure = f"{type(e).__name__}: {e}"
        rr.claim_traces = traces
    rr.calls = up_calls + own_calls
    rr.totals = _totals(rr.calls, own_calls, traces)
    rr.finished_at = now_iso()
    return rr


def run_case(client: BaseClient, record: CaseRecord, conditions: list[str], out_root: Path, run_meta: dict[str, Any],
             *, skip: Callable[[str, str], bool] = lambda c, k: False,
             on_done: Callable[[RunRecord], None] = lambda r: None, max_tool_calls: int = 4,
             max_claims: int = 6) -> list[RunRecord]:
    base_ctx = {"case_id": record.case_id, "stage": run_meta["stage"], "run_tag": run_meta["run_tag"]}
    shared = SharedArtifacts(client, record, out_root / "_shared" / record.case_id, base_ctx)
    out = []
    for code in conditions:
        if skip(code, record.case_id):
            continue
        rr = run_condition(CONDITIONS[code], shared, client, record, run_meta, max_tool_calls, max_claims)
        atomic_write_json(out_root / code / f"{record.case_id}.json", rr.model_dump())
        on_done(rr)
        out.append(rr)
    return out
