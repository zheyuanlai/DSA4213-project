"""Source-grounded evidence tools (real Python implementations, no mocks, no web).

Every observation is computed deterministically from the `EvidenceStore`. Model-
supplied IDs are validated; unknown IDs yield NOT_FOUND, never fabricated data.
Absence observations return citable *absence IDs* (e.g. ``absent:test:exp1/cmp1``)
so that a decision like "no test reported -> weaken" can cite what was checked.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable

from src.evidence_store import EvidenceStore, format_test
from src.schemas import ToolObservation

EVIDENCE_TOOLS = ("lookup_table", "get_test_metadata", "retrieve_passage", "compare_numbers")
NO_TEST_MSG = (
    "No statistical test is reported for this comparison. This means statistical significance "
    "is NOT established; it is NOT evidence that the effect is absent or that the methods are equivalent."
)

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "lookup_table": {
        "type": "function",
        "function": {
            "name": "lookup_table",
            "description": (
                "Return literal values from a results table with exact evidence IDs and units. "
                "Give table_id; optionally narrow to one row_id and/or one column (column id or header). "
                "Omit row_id/column to get the whole table or a whole row/column."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "string", "description": "e.g. T1"},
                    "row_id": {"type": "string", "description": "e.g. r2 (optional)"},
                    "column": {"type": "string", "description": "column id or header, e.g. acc (optional)"},
                },
                "required": ["table_id"],
                "additionalProperties": False,
            },
        },
    },
    "get_test_metadata": {
        "type": "function",
        "function": {
            "name": "get_test_metadata",
            "description": (
                "Return the statistical test reported for a comparison (test name, pairing, n, statistic, "
                "p-value, confidence interval, multiple-comparison adjustment), or NOT_FOUND if none was reported."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_id": {"type": "string", "description": "e.g. exp1"},
                    "comparison_id": {"type": "string", "description": "e.g. cmp1"},
                },
                "required": ["experiment_id", "comparison_id"],
                "additionalProperties": False,
            },
        },
    },
    "retrieve_passage": {
        "type": "function",
        "function": {
            "name": "retrieve_passage",
            "description": (
                "Return supplied cited-source passages (verbatim) with stable passage IDs. Accepts a passage id "
                "(e.g. P1), a citation key/author name, or a free-text query. Only passages supplied in the package "
                "can be returned; there is no web access."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query_or_source_id": {"type": "string"}},
                "required": ["query_or_source_id"],
                "additionalProperties": False,
            },
        },
    },
    "compare_numbers": {
        "type": "function",
        "function": {
            "name": "compare_numbers",
            "description": (
                "Deterministically check a number stated in a claim against table evidence. mode='value' compares "
                "to the cell value; 'difference' uses evidence_id minus reference_evidence_id; 'ratio' uses "
                "evidence_id / reference_evidence_id; 'percent_change' uses (evidence-reference)/reference*100. "
                "Returns the true value, whether the claimed number matches within tolerance, and direction "
                "(which entry is better given the column's higher/lower-is-better)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "claimed": {"type": "number", "description": "the number as stated in the claim"},
                    "evidence_id": {"type": "string", "description": "a table cell id, e.g. T1.r1.acc"},
                    "reference_evidence_id": {"type": "string", "description": "second cell id for difference/ratio modes"},
                    "mode": {"type": "string", "enum": ["value", "difference", "ratio", "percent_change"]},
                    "tolerance": {"type": "number", "description": "absolute tolerance (optional)"},
                },
                "required": ["claimed", "evidence_id"],
                "additionalProperties": False,
            },
        },
    },
}


def submit_decision_schema(allowed: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "submit_decision",
            "description": (
                "Finish verifying the current claim. Cite only evidence/absence IDs returned by your tool calls "
                "for this claim. revised_text is required for WEAKEN and STRENGTHEN (the full replacement sentence) "
                "and must be empty for ACCEPT, REMOVE and FLAG."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rationale": {"type": "string", "description": "<= 60 words: what the evidence shows"},
                    "decision": {"type": "string", "enum": list(allowed)},
                    "revised_text": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["rationale", "decision", "revised_text", "evidence_ids"],
                "additionalProperties": False,
            },
        },
    }


# ---------------------------------------------------------------------------- impl
def _decimals(text: str) -> int:
    m = re.search(r"[-−]?\d+(?:\.(\d+))?", text or "")
    return len(m.group(1)) if m and m.group(1) else 0


def _cell_payload(store: EvidenceStore, eid: str) -> dict[str, Any]:
    it = store.get(eid)
    assert it is not None
    return {
        "evidence_id": eid,
        "row": it.label.split(" / ")[0],
        "column": it.label.split(" / ")[-1],
        "text": it.text,
        "value": it.value,
        "unit": it.unit,
        "higher_is_better": it.higher_is_better,
    }


def lookup_table(store: EvidenceStore, table_id: str, row_id: str | None = None, column: str | None = None) -> ToolObservation:
    t = store.table(str(table_id).strip())
    if t is None:
        avail = [x.table_id for x in store.package.results_tables]
        return ToolObservation(call_id="", tool="lookup_table", status="NOT_FOUND",
                               message=f"No table {table_id!r}. Available tables: {avail}")
    rows = t.rows
    if row_id not in (None, "", "*"):
        rows = [r for r in t.rows if r.row_id == str(row_id).strip()]
        if not rows:
            return ToolObservation(call_id="", tool="lookup_table", status="NOT_FOUND",
                                   message=f"No row {row_id!r} in {t.table_id}. Rows: " +
                                   "; ".join(f"{r.row_id}={r.label}" for r in t.rows))
    cols = t.columns
    if column not in (None, "", "*"):
        key = str(column).strip().lower()
        cols = [c for c in t.columns if c.column_id.lower() == key or c.header.lower() == key]
        if not cols:
            return ToolObservation(call_id="", tool="lookup_table", status="NOT_FOUND",
                                   message=f"No column {column!r} in {t.table_id}. Columns: " +
                                   "; ".join(f"{c.column_id}={c.header}" for c in t.columns))
    cells = []
    for r in rows:
        for c in cols:
            if c.column_id in r.cells:
                cells.append(_cell_payload(store, f"{t.table_id}.{r.row_id}.{c.column_id}"))
    return ToolObservation(
        call_id="", tool="lookup_table", status="FOUND",
        data={"table_id": t.table_id, "caption": t.caption, "notes": t.notes, "cells": cells},
        returned_ids=[t.table_id] + [c["evidence_id"] for c in cells],
        provenance=f"table {t.table_id}",
    )


def get_test_metadata(store: EvidenceStore, experiment_id: str, comparison_id: str) -> ToolObservation:
    e, c = str(experiment_id).strip(), str(comparison_id).strip()
    comps = {(x, y): d for x, y, d in store.comparisons()}
    if (e, c) not in comps:
        return ToolObservation(call_id="", tool="get_test_metadata", status="NOT_FOUND",
                               message=f"Unknown comparison {e}/{c}. Known comparisons: " +
                               "; ".join(f"{x}/{y} ({d})" for (x, y), d in comps.items()))
    tests = store.tests_by_comparison.get((e, c), [])
    if not tests:
        return ToolObservation(call_id="", tool="get_test_metadata", status="NOT_FOUND",
                               data={"comparison": f"{e}/{c}", "description": comps[(e, c)]},
                               returned_ids=[f"absent:test:{e}/{c}"], message=NO_TEST_MSG,
                               provenance=f"comparison {e}/{c}")
    out = []
    for s in tests:
        d = s.model_dump()
        d["summary"] = format_test(s)
        out.append(d)
    return ToolObservation(call_id="", tool="get_test_metadata", status="FOUND",
                           data={"comparison": f"{e}/{c}", "description": comps[(e, c)], "tests": out},
                           returned_ids=[s.test_id for s in tests], provenance=f"comparison {e}/{c}")


def retrieve_passage(store: EvidenceStore, query_or_source_id: str) -> ToolObservation:
    q = str(query_or_source_id).strip()
    ps = store.package.source_passages
    if not ps:
        return ToolObservation(call_id="", tool="retrieve_passage", status="NOT_FOUND",
                               returned_ids=["absent:passage"], message="No cited passages were supplied in this package.")
    hits = [p for p in ps if p.passage_id == q]
    if not hits:
        ql = q.lower()
        hits = [p for p in ps if ql and (ql in p.citation_key.lower() or p.citation_key.lower().split()[0].strip(",(") in ql)]
    if not hits:
        ranked = store.search_passages(q, k=2)
        hits = [p for p in ps if p.passage_id in {pid for _, pid in ranked}]
        hits.sort(key=lambda p: [pid for _, pid in ranked].index(p.passage_id))
    if not hits:
        return ToolObservation(call_id="", tool="retrieve_passage", status="NOT_FOUND",
                               returned_ids=["absent:passage"],
                               message="No supplied passage matches this query. Available: " +
                               "; ".join(f"{p.passage_id} ({p.citation_key})" for p in ps))
    return ToolObservation(
        call_id="", tool="retrieve_passage", status="FOUND",
        data={"passages": [{"passage_id": p.passage_id, "citation_key": p.citation_key,
                            "source_title": p.source_title, "text": p.text} for p in hits]},
        returned_ids=[p.passage_id for p in hits], provenance="supplied passages",
    )


def compare_numbers(store: EvidenceStore, claimed: Any, evidence_id: str, reference_evidence_id: str | None = None,
                    mode: str | None = None, tolerance: float | None = None) -> ToolObservation:
    try:
        claimed_f = float(str(claimed).replace("−", "-").replace("%", "").replace(",", ""))
        if math.isnan(claimed_f) or math.isinf(claimed_f):
            raise ValueError
    except (TypeError, ValueError):
        return ToolObservation(call_id="", tool="compare_numbers", status="TOOL_ERROR",
                               message=f"claimed must be a number, got {claimed!r}")
    mode = (mode or ("difference" if reference_evidence_id else "value")).strip()
    if mode not in ("value", "difference", "ratio", "percent_change"):
        return ToolObservation(call_id="", tool="compare_numbers", status="TOOL_ERROR", message=f"unknown mode {mode!r}")
    it = store.get(str(evidence_id).strip())
    if it is None:
        return ToolObservation(call_id="", tool="compare_numbers", status="NOT_FOUND",
                               message=f"Unknown evidence id {evidence_id!r}. Use lookup_table to find cell ids (format T1.r1.col).")
    if it.kind != "table_cell" or it.value is None:
        return ToolObservation(call_id="", tool="compare_numbers", status="NOT_APPLICABLE",
                               returned_ids=[it.evidence_id],
                               message=f"{it.evidence_id} is a {it.kind} without a numeric value; compare_numbers needs a numeric table cell.")
    dp = _decimals(it.text)
    ref = None
    if mode != "value":
        if not reference_evidence_id:
            return ToolObservation(call_id="", tool="compare_numbers", status="TOOL_ERROR",
                                   message=f"mode {mode} requires reference_evidence_id")
        ref = store.get(str(reference_evidence_id).strip())
        if ref is None:
            return ToolObservation(call_id="", tool="compare_numbers", status="NOT_FOUND",
                                   message=f"Unknown reference evidence id {reference_evidence_id!r}")
        if ref.kind != "table_cell" or ref.value is None:
            return ToolObservation(call_id="", tool="compare_numbers", status="NOT_APPLICABLE",
                                   returned_ids=[ref.evidence_id],
                                   message=f"{ref.evidence_id} has no numeric value")
        dp = max(dp, _decimals(ref.text))
    unit_note = None
    if mode == "value":
        actual = it.value
        default_tol = 0.5 * 10 ** (-dp)
    elif mode == "difference":
        actual = it.value - ref.value
        default_tol = 1.0 * 10 ** (-dp)
    elif mode == "ratio":
        if ref.value == 0:
            return ToolObservation(call_id="", tool="compare_numbers", status="TOOL_ERROR", message="reference value is 0")
        actual = it.value / ref.value
        default_tol = max(0.01 * abs(actual), 0.005)
    else:
        if ref.value == 0:
            return ToolObservation(call_id="", tool="compare_numbers", status="TOOL_ERROR", message="reference value is 0")
        actual = (it.value - ref.value) / abs(ref.value) * 100.0
        default_tol = max(0.5, 0.01 * abs(actual))
        unit_note = "percent change relative to the reference"
    if ref is not None and it.unit and ref.unit and it.unit != ref.unit:
        unit_note = f"UNIT MISMATCH: {it.unit} vs {ref.unit}"
    tol = float(tolerance) if tolerance is not None else default_tol
    tol = max(tol, 1e-9)
    match = abs(claimed_f - actual) <= tol + 1e-12
    data: dict[str, Any] = {
        "mode": mode,
        "claimed": claimed_f,
        "actual": round(actual, 6),
        "abs_error": round(abs(claimed_f - actual), 6),
        "tolerance": tol,
        "match": match,
        "evidence": _cell_payload(store, it.evidence_id),
    }
    if ref is not None:
        data["reference"] = _cell_payload(store, ref.evidence_id)
        hib = it.higher_is_better if it.higher_is_better is not None else ref.higher_is_better
        if it.value == ref.value:
            better = "tie"
        elif hib is None:
            better = "unknown (column direction not specified)"
        else:
            better = it.evidence_id if ((it.value > ref.value) == hib) else ref.evidence_id
        data["better_entry"] = better
        if claimed_f != 0 and actual != 0 and (claimed_f > 0) != (actual > 0):
            data["sign_mismatch"] = True
    if unit_note:
        data["unit_note"] = unit_note
    ids = [it.evidence_id] + ([ref.evidence_id] if ref is not None else [])
    return ToolObservation(call_id="", tool="compare_numbers", status="FOUND", data=data, returned_ids=ids,
                           provenance="deterministic arithmetic on table cells")


_IMPL: dict[str, Callable[..., ToolObservation]] = {
    "lookup_table": lookup_table,
    "get_test_metadata": get_test_metadata,
    "retrieve_passage": retrieve_passage,
    "compare_numbers": compare_numbers,
}
_ALLOWED_ARGS = {
    name: set(TOOL_SCHEMAS[name]["function"]["parameters"]["properties"]) for name in EVIDENCE_TOOLS
}
_REQUIRED_ARGS = {name: set(TOOL_SCHEMAS[name]["function"]["parameters"]["required"]) for name in EVIDENCE_TOOLS}


def execute_tool(store: EvidenceStore, name: str, args: dict[str, Any], call_id: str) -> ToolObservation:
    """Validate arguments and run a tool. Never raises on bad model input."""
    if name not in _IMPL:
        obs = ToolObservation(call_id=call_id, tool=name, status="TOOL_ERROR", message=f"unknown tool {name!r}")
        return obs
    if not isinstance(args, dict):
        return ToolObservation(call_id=call_id, tool=name, status="TOOL_ERROR", message="arguments must be a JSON object")
    missing = _REQUIRED_ARGS[name] - {k for k, v in args.items() if v not in (None, "")}
    unknown = set(args) - _ALLOWED_ARGS[name]
    if missing:
        return ToolObservation(call_id=call_id, tool=name, status="TOOL_ERROR", message=f"missing required args {sorted(missing)}")
    clean = {k: v for k, v in args.items() if k in _ALLOWED_ARGS[name]}
    try:
        obs = _IMPL[name](store, **clean)
    except Exception as e:  # defensive: tool bugs must not crash a run
        obs = ToolObservation(call_id=call_id, tool=name, status="TOOL_ERROR", message=f"{type(e).__name__}: {e}")
    obs.call_id = call_id
    if unknown:
        obs.message = (obs.message + " " if obs.message else "") + f"(ignored unknown args {sorted(unknown)})"
    return obs


def observation_to_message(obs: ToolObservation) -> str:
    """Compact JSON string returned to the model as the tool result."""
    import json

    payload = {"status": obs.status, "citable_ids": obs.returned_ids}
    if obs.message:
        payload["message"] = obs.message
    if obs.data:
        payload["data"] = obs.data
    return json.dumps(payload, ensure_ascii=False, default=str)
