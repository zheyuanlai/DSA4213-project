"""Verifier repair effectiveness (protocol §5.D) and decisive-evidence retrieval (§5.F).

Every final text is compared with its own starting draft (shared-draft lineage; never across lineages).
Claims in sentences shared by draft and final are unchanged by construction (same sentence unit, same claims);
claims in changed sentences are aligned by the consensus alignment (``x_claims`` of the draft, ``added_y`` of
the final). Outcome classes are deterministic functions of the aligned final labels.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

ERRORS = ("OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR")
OK_LABELS = ("SUPPORTED", "NOT_VERIFIABLE")
UNKNOWN = ("UNRESOLVED", "EXCLUDED")


def is_error(label: str) -> bool:
    return label in ERRORS


@dataclass
class RunEdits:
    n_draft_claims: int = 0
    initial_errors: int = 0
    corrected: int = 0
    removed: int = 0
    retained_unedited: int = 0  # error in a sentence the system did not change
    retained_edited: int = 0  # error still present after the sentence was changed
    unknown: int = 0
    substantive_edits: int = 0
    beneficial: int = 0
    harmful: int = 0
    neutral: int = 0
    weakened: int = 0
    weakened_correct: int = 0  # WEAKENED edits of claims that were SUPPORTED: unnecessary weakening
    new_errors: int = 0
    new_unsupported: int = 0
    numeric_fixed: int = 0
    numeric_introduced: int = 0
    initial_numeric_errors: int = 0
    deleted_correct: int = 0
    findings_lost: int = 0
    findings_gained: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if k != "events"}
        return d


def ratio(num: float, den: float) -> Optional[float]:
    return None if den == 0 else num / den


def analyze_run(draft_units: list[str], final_units: list[str], claims_by_unit: dict[str, list[dict[str, Any]]],
                labels: dict[str, str], alignment: Optional[dict[str, Any]],
                covered_draft: Optional[set[str]] = None, covered_final: Optional[set[str]] = None) -> RunEdits:
    """Outcome of one draft -> final transformation.

    ``labels`` maps claim_id -> final consensus label. ``alignment`` is the consensus alignment of the pair
    (None when the final text equals the draft)."""
    r = RunEdits()
    fset, dset = set(final_units), set(draft_units)
    draft_claims = [c for u in draft_units for c in claims_by_unit.get(u, [])]
    r.n_draft_claims = len(draft_claims)
    xrel = {x["claim_id"]: x for x in (alignment or {}).get("x_claims", [])}
    if covered_draft is not None and covered_final is not None:
        r.findings_lost = len(covered_draft - covered_final)
        r.findings_gained = len(covered_final - covered_draft)

    def lab(cid: str) -> str:
        return labels.get(cid, "UNRESOLVED")

    for c in draft_claims:
        cid, before = c["claim_id"], lab(c["claim_id"])
        changed = c["unit_id"] not in fset
        if before in ERRORS:
            r.initial_errors += 1
            r.initial_numeric_errors += before == "NUMERIC_ERROR"
        if not changed:
            if before in ERRORS:
                r.retained_unedited += 1
            continue
        x = xrel.get(cid)
        if x is None:
            raise ValueError(f"claim {cid} is in a changed sentence but has no alignment")
        rel, ys = x["relation"], x["matched_y"]
        after = [lab(y) for y in ys]
        if before in ERRORS:
            if rel == "DELETED" or (ys and all(a == "NOT_VERIFIABLE" for a in after)):
                r.removed += 1
                r.numeric_fixed += before == "NUMERIC_ERROR"
                outcome = "removed"
            elif rel == "UNRESOLVED" or any(a in UNKNOWN for a in after):
                r.unknown += 1
                outcome = "unknown"
            elif all(a in OK_LABELS for a in after):
                r.corrected += 1
                r.numeric_fixed += before == "NUMERIC_ERROR"
                outcome = "corrected"
            else:
                r.retained_edited += 1
                outcome = "retained"
        else:
            outcome = "was_correct"
        if rel in ("MODIFIED", "DELETED"):
            r.substantive_edits += 1
            if rel == "DELETED":
                if before in ERRORS:
                    cls = "beneficial"
                else:
                    r.deleted_correct += 1
                    cls = "harmful" if (c.get("result_claim", True) and r.findings_lost > 0) else "neutral"
            else:
                if x.get("direction") == "WEAKENED":
                    r.weakened += 1
                    r.weakened_correct += before == "SUPPORTED"
                new_err = [a for a in after if a in ERRORS]
                if before in ERRORS and not new_err and not any(a in UNKNOWN for a in after):
                    cls = "beneficial"
                elif before not in ERRORS and before not in UNKNOWN and new_err:
                    cls = "harmful"
                    r.new_errors += 1
                    r.new_unsupported += any(a == "UNSUPPORTED" for a in new_err)
                    r.numeric_introduced += any(a == "NUMERIC_ERROR" for a in new_err)
                else:
                    cls = "neutral"
            setattr(r, cls, getattr(r, cls) + 1)
            r.events.append({"claim_id": cid, "relation": rel, "direction": x.get("direction"), "before": before,
                             "after": after, "matched_y": ys, "class": cls, "outcome": outcome})
    for y in (alignment or {}).get("added_y", []):
        a = lab(y)
        r.substantive_edits += 1
        if a in ERRORS:
            r.harmful += 1
            r.new_errors += 1
            r.new_unsupported += a == "UNSUPPORTED"
            r.numeric_introduced += a == "NUMERIC_ERROR"
            cls = "harmful"
        else:
            r.neutral += 1
            cls = "neutral"
        r.events.append({"claim_id": y, "relation": "ADDED", "direction": None, "before": None, "after": [a],
                         "matched_y": [y], "class": cls, "outcome": "added"})
    return r


def summarize(runs: list[RunEdits]) -> dict[str, Any]:
    tot = Counter()
    for r in runs:
        tot.update({k: v for k, v in r.as_dict().items() if isinstance(v, int)})
    t = dict(tot)
    return {**t,
            "repair_recall": ratio(t.get("corrected", 0) + t.get("removed", 0), t.get("initial_errors", 0)),
            "repair_recall_corrected_only": ratio(t.get("corrected", 0), t.get("initial_errors", 0)),
            "edit_precision": ratio(t.get("beneficial", 0), t.get("substantive_edits", 0)),
            "harmful_edit_rate": ratio(t.get("harmful", 0), t.get("substantive_edits", 0)),
            "unnecessary_weakening_rate": ratio(t.get("weakened_correct", 0), t.get("weakened", 0))}


# ----------------------------------------------------------------------------- decisive evidence (§5.F)
def covered(decisive: str, returned: set[str]) -> bool:
    if decisive in returned:
        return True
    if "/" in decisive:  # a comparison: checked if its test metadata was requested and found absent
        return f"absent:test:{decisive}" in returned  # (a found test is mapped to its comparison by the caller)
    parts = decisive.split(".")
    if len(parts) == 3:  # cell: returned directly or its row
        return ".".join(parts[:2]) in returned
    if len(parts) == 2:  # row: any of its cells
        return any(x.startswith(decisive + ".") for x in returned)
    if len(parts) == 1 and decisive.startswith("T"):
        return any(x.startswith(decisive + ".") for x in returned)
    return False


def decisive_retrieval(trace: dict[str, Any], decisive_ids: list[str], test_comparisons: dict[str, str]) -> dict[str, Any]:
    """Did the verifier's tool calls for this sentence return every evidence item the consensus judgement cited?"""
    returned: set[str] = set()
    for o in trace.get("observations", []):
        returned |= set(o.get("returned_ids") or [])
    # a test found by get_test_metadata also covers its comparison
    for t, cmp_id in test_comparisons.items():
        if t in returned:
            returned.add(cmp_id)
    ids = [d for d in decisive_ids if d]
    hits = [d for d in ids if covered(d, returned)]
    return {"n_decisive": len(ids), "n_retrieved": len(hits), "all": bool(ids) and len(hits) == len(ids),
            "any": bool(hits), "n_tool_calls": len(trace.get("observations", []))}
