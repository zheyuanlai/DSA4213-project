"""Atomic claims: parsing judge output, consensus, final labels and claim-level metrics (protocol §5.B).

Pure logic, no model calls. A *reading* is one judge's verification of one claim. Consensus takes agreed
fields as final and sends every disagreement to adjudication. Numeric correctness is never taken from a
model: each number's mapping is checked by ``evaluation.numeric_fidelity``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from evaluation.numeric_fidelity import (
    PRIMARY_ROLES, Assertion, EvidenceValues, Mapping, Verdict, check_assertion,
)

LABELS = ("SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NOT_VERIFIABLE")
FINAL_LABELS = LABELS + ("NUMERIC_ERROR",)
ERROR_LABELS = ("OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR")
NON_RESULT_TYPES = ("scope_or_caveat", "method_or_setup")
ALLOWED_ENTAILMENT = {
    "SUPPORTED": {"ENTAILED"},
    "OVERSTATED": {"NOT_ENTAILED", "CONTRADICTED"},
    "UNSUPPORTED": {"NOT_ENTAILED", "CONTRADICTED"},
    "UNDERSTATED": {"ENTAILED", "CONTRADICTED"},
    "NOT_VERIFIABLE": {"NA"},
}


def norm_span(s: str) -> str:
    s = (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def consistent(label: str, entailment: str) -> bool:
    return entailment in ALLOWED_ENTAILMENT.get(label, set())


# ----------------------------------------------------------------------------- extraction
def parse_extraction(parsed: dict[str, Any], units: dict[str, str], family: str, alias: str) -> list[dict[str, Any]]:
    """Turn a Judge-A extraction into claim records with stable IDs ``<unit>.c<k>`` / ``<claim>.n<j>``."""
    claims: list[dict[str, Any]] = []
    for u in parsed["units"]:
        uid = u["unit_id"]
        sent = units[uid]
        for k, c in enumerate(u["claims"], start=1):
            cid = f"{uid}.c{k}"
            nums = []
            for j, n in enumerate(c["numbers"], start=1):
                nums.append({"number_id": f"{cid}.n{j}", "as_written": n["as_written"], "value": float(n["value"]),
                             "comparator": n["comparator"], "approximate": bool(n["approximate"]),
                             "role": n["role"], "unit": n["unit"]})
            claims.append({"family": family, "alias": alias, "unit_id": uid, "claim_id": cid, "span": c["span"],
                           "span_verbatim": norm_span(c["span"]) in norm_span(sent),
                           "proposition": c["proposition"], "claim_type": c["claim_type"],
                           "entities": c["entities"], "metrics": c["metrics"], "datasets": c["datasets"],
                           "qualifiers": c["qualifiers"], "numbers": nums})
    return claims


def extraction_problems(parsed: dict[str, Any], units: dict[str, str]) -> list[str]:
    got = [u["unit_id"] for u in parsed.get("units", [])]
    probs = []
    if sorted(got) != sorted(units):
        missing, extra = set(units) - set(got), set(got) - set(units)
        probs.append(f"unit ids mismatch: missing {sorted(missing)[:5]}, extra {sorted(extra)[:5]}")
    if len(set(got)) != len(got):
        probs.append("duplicate unit ids")
    return probs


# ----------------------------------------------------------------------------- verification readings
def verification_problems(parsed: dict[str, Any], claims: list[dict[str, Any]]) -> list[str]:
    want = {c["claim_id"]: {n["number_id"] for n in c["numbers"]} for c in claims}
    got = [c["claim_id"] for c in parsed.get("claims", [])]
    probs = []
    if sorted(got) != sorted(want):
        probs.append(f"claim ids mismatch: missing {sorted(set(want) - set(got))[:5]}, extra {sorted(set(got) - set(want))[:5]}")
    for c in parsed.get("claims", []):
        if c["claim_id"] not in want:
            continue
        nids = [n["number_id"] for n in c["numbers"]]
        if sorted(nids) != sorted(want[c["claim_id"]]):
            probs.append(f"{c['claim_id']}: number ids mismatch")
    return probs


def parse_readings(parsed: dict[str, Any], judge: str) -> dict[str, dict[str, Any]]:
    out = {}
    for c in parsed["claims"]:
        out[c["claim_id"]] = {
            "judge": judge, "label": c["label"], "entailment": c["entailment"], "error_subtype": c["error_subtype"],
            "evidence_ids": c["evidence_ids"], "justification": c["justification"], "confidence": c["confidence"],
            "extraction_flag": c["extraction_flag"], "consistent": consistent(c["label"], c["entailment"]),
            "numbers": {n["number_id"]: {k: n[k] for k in ("source_type", "expression", "quote", "scale")}
                        for n in c["numbers"]}}
    return out


def to_assertion(n: dict[str, Any]) -> Assertion:
    return Assertion(n["as_written"], float(n["value"]), bool(n["approximate"]), n["role"], n.get("unit"))


def to_mapping(m: dict[str, Any], comparator: str = "=") -> Mapping:
    return Mapping(m["source_type"], m.get("expression"), m.get("quote"), float(m.get("scale") or 1.0), comparator)


def check_number(n: dict[str, Any], m: Optional[dict[str, Any]], ev: EvidenceValues) -> Verdict:
    if m is None:
        return Verdict("INVALID_MAPPING", note="no mapping")
    return check_assertion(to_assertion(n), to_mapping(m, n.get("comparator") or "="), ev)


# ----------------------------------------------------------------------------- disagreements
@dataclass
class ClaimDispute:
    claim_id: str
    fields: list[str] = field(default_factory=list)  # label, entailment, extraction
    numbers: list[str] = field(default_factory=list)  # number ids with disputed verdicts


def claim_disputes(claim: dict[str, Any], ra: dict[str, Any], rb: dict[str, Any], ev: EvidenceValues) -> ClaimDispute:
    d = ClaimDispute(claim["claim_id"])
    if ra["label"] != rb["label"]:
        d.fields.append("label")
    if ra["entailment"] != rb["entailment"] or not ra["consistent"] or not rb["consistent"]:
        d.fields.append("entailment")
        if "label" not in d.fields and (not ra["consistent"] or not rb["consistent"]):
            d.fields.append("label")
    if {ra["extraction_flag"], rb["extraction_flag"]} & {"NOT_IN_TEXT", "DISTORTED"}:
        d.fields.append("extraction")
    for n in claim["numbers"]:
        va = check_number(n, ra["numbers"].get(n["number_id"]), ev)
        vb = check_number(n, rb["numbers"].get(n["number_id"]), ev)
        if va.status == "INVALID_MAPPING" or vb.status == "INVALID_MAPPING" or va.correct != vb.correct:
            d.numbers.append(n["number_id"])
    return d


# ----------------------------------------------------------------------------- consensus
def finalize_claim(claim: dict[str, Any], ra: dict[str, Any], rb: dict[str, Any], ev: EvidenceValues,
                   adj: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Final record for one claim. ``adj`` is the adjudicator's decision (only disputed fields are used)."""
    disp = claim_disputes(claim, ra, rb, ev)
    log: list[str] = []

    def pick(fieldname: str) -> str:
        if fieldname not in disp.fields:
            return ra[fieldname]
        if adj is None:
            raise ValueError(f"{claim['claim_id']}: disputed {fieldname} has no adjudication")
        return adj[fieldname]

    label = pick("label")
    entailment = pick("entailment")
    extraction_valid = True
    if "extraction" in disp.fields:
        if adj is None:
            raise ValueError(f"{claim['claim_id']}: disputed extraction has no adjudication")
        extraction_valid = bool(adj["extraction_valid"])
    numbers = []
    for n in claim["numbers"]:
        nid = n["number_id"]
        if nid in disp.numbers:
            if adj is None:
                raise ValueError(f"{nid}: disputed number has no adjudication")
            choice = next((x for x in adj["numbers"] if x["number_id"] == nid), None)
            if choice is None:
                raise ValueError(f"{nid}: adjudication lacks this number")
            m = {"1": adj["_reading_map"]["1"], "2": adj["_reading_map"]["2"]}.get(choice["choice"])
            mapping = (ra if m == "A" else rb)["numbers"].get(nid) if m else \
                {k: choice[k] for k in ("source_type", "expression", "quote", "scale")}
            source = f"adjudicated:{m or 'own'}"
        else:
            mapping, source = ra["numbers"].get(nid), "agreed"
        v = check_number(n, mapping, ev)
        alt = []
        if source == "agreed":
            vb = check_number(n, rb["numbers"].get(nid), ev)
            if vb.correct:
                alt.append({"mapping": rb["numbers"].get(nid), "operands": list(vb.operands)})
        numbers.append({**n, "mapping": mapping, "mapping_source": source, "verdict": v.status,
                        "expected": v.expected, "tolerance": v.tolerance, "operands": list(v.operands),
                        "verdict_note": v.note, "alt_correct_mappings": alt})
        if v.status == "INVALID_MAPPING":
            log.append(f"{nid}: final mapping invalid ({v.note})")
    numeric_error = any(x["verdict"] not in ("CORRECT", "INVALID_MAPPING") for x in numbers)
    final = "EXCLUDED" if not extraction_valid else (
        "NUMERIC_ERROR" if numeric_error else label)
    if final == "UNRESOLVED" or (entailment == "UNRESOLVED" and final not in ("EXCLUDED", "NUMERIC_ERROR")):
        final = "UNRESOLVED"
    factual_error = None
    if final not in ("EXCLUDED", "UNRESOLVED", "NOT_VERIFIABLE"):
        factual_error = bool(numeric_error or entailment in ("NOT_ENTAILED", "CONTRADICTED"))
    elif final == "NOT_VERIFIABLE":
        factual_error = bool(numeric_error)
    return {"claim_id": claim["claim_id"], "unit_id": claim["unit_id"], "alias": claim["alias"],
            "claim_type": claim["claim_type"], "result_claim": claim["claim_type"] not in NON_RESULT_TYPES,
            "label_consensus": label, "entailment": entailment, "final_label": final,
            "factual_error": factual_error, "extraction_valid": extraction_valid,
            "disputed_fields": disp.fields, "disputed_numbers": disp.numbers,
            "evidence_ids": sorted(set(ra["evidence_ids"]) | set(rb["evidence_ids"]) |
                                   set((adj or {}).get("evidence_ids", []))),
            "numbers": numbers, "notes": log}


# ----------------------------------------------------------------------------- metrics
def assessable(c: dict[str, Any]) -> bool:
    return c["final_label"] in ("SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR")


def claim_counts(claims: Iterable[dict[str, Any]], result_only: bool = False) -> dict[str, int]:
    cs = [c for c in claims if (c["result_claim"] or not result_only)]
    out = {"n_claims": len(cs), "n_assessable": sum(assessable(c) for c in cs),
           "n_not_verifiable": sum(c["final_label"] == "NOT_VERIFIABLE" for c in cs),
           "n_unresolved": sum(c["final_label"] == "UNRESOLVED" for c in cs),
           "n_excluded": sum(c["final_label"] == "EXCLUDED" for c in cs),
           "n_factual_error": sum(bool(c["factual_error"]) for c in cs if assessable(c))}
    for lab in ("SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR"):
        out[f"n_{lab.lower()}"] = sum(c["final_label"] == lab for c in cs)
    return out


def text_claim_summary(claims_by_unit: dict[str, list[dict[str, Any]]], units: list[str]) -> dict[str, Any]:
    """Claims of one text are the claims of its sentence units (identical sentences share claims)."""
    cs = [c for u in units for c in claims_by_unit.get(u, [])]
    allc, res = claim_counts(cs), claim_counts(cs, result_only=True)
    n = allc["n_assessable"]
    fully = int(n > 0 and allc["n_supported"] == n)
    clean = int(n > 0 and allc["n_factual_error"] == 0)
    nums = [x for c in cs for x in c["numbers"]]
    prim = [x for x in nums if x["role"] in PRIMARY_ROLES and x["verdict"] != "INVALID_MAPPING"]
    return {"all": allc, "result": res, "fully_supported": fully, "factually_clean": clean,
            "no_assessable_claims": int(n == 0),
            "n_numbers_primary": len(prim), "n_numbers_primary_correct": sum(x["verdict"] == "CORRECT" for x in prim),
            "n_numbers_setup": sum(1 for x in nums if x["role"] == "setup"),
            "n_numbers_setup_correct": sum(1 for x in nums if x["role"] == "setup" and x["verdict"] == "CORRECT"),
            "numeric_error_types": [x["verdict"] for x in nums if x["verdict"] not in ("CORRECT", "INVALID_MAPPING")],
            "numeric_error_free": int(not any(x["verdict"] not in ("CORRECT", "INVALID_MAPPING") for x in nums))}
