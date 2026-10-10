"""Validate and merge two INDEPENDENT annotation files; inter-annotator agreement; adjudication.

Run ONLY after both annotators have submitted real files:

  python -m evaluation.merge_annotations \
      --a annotation/completed/annotator_A_pass1.csv,annotation/completed/annotator_A_pass2.csv \
      --b annotation/completed/annotator_B_pass1.csv,annotation/completed/annotator_B_pass2.csv \
      --packet annotation/blinded_synthetic.csv --alias-map private/case_alias_map.csv \
      --rubric data/synthetic/rubrics/test_rubric.jsonl --out annotation/agreement
  # after filling annotation/agreement/adjudication_synthetic.csv:
  python -m evaluation.merge_annotations ... --adjudicated annotation/agreement/adjudication_synthetic.csv

Outputs: validation report, agreement.json (Cohen's kappa: unweighted + linear/quadratic weighted
for the ordinal level; item-level kappa for checklists), adjudication sheet of disagreements, and,
once adjudicated, consensus_synthetic.csv. No condition identities are needed or used here.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation.blinding import SYN_FIELDS, read_csv  # noqa: F401
from src.package_schema import ORDINAL_CATEGORIES

LIST_FIELDS = ("findings_covered", "num_facts_correct", "neg_findings_reported")
INT_FIELDS = ("unsupported_claims", "numeric_errors")


# ----------------------------------------------------------------------------- kappa
def cohen_kappa(a: list[Any], b: list[Any], labels: Optional[list[Any]] = None, weights: Optional[str] = None) -> Optional[float]:
    """Cohen's kappa; weights None | 'linear' | 'quadratic' (labels must then be ordered)."""
    if len(a) != len(b) or not a:
        return None
    labels = labels or sorted(set(a) | set(b))
    k = len(labels)
    idx = {l: i for i, l in enumerate(labels)}
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1
    ra = [sum(obs[i]) / n for i in range(k)]
    cb = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]

    def w(i, j):
        if weights is None:
            return 0.0 if i == j else 1.0
        d = abs(i - j) / (k - 1) if k > 1 else 0.0
        return d if weights == "linear" else d * d

    po = sum(w(i, j) * obs[i][j] / n for i in range(k) for j in range(k))
    pe = sum(w(i, j) * ra[i] * cb[j] for i in range(k) for j in range(k))
    if pe == 0:
        return 1.0 if po == 0 else None
    return 1.0 - po / pe


def _ids(s: str) -> set[str]:
    return {x.strip() for x in (s or "").replace(",", ";").split(";") if x.strip()}


# ----------------------------------------------------------------------------- validation
def validate(rows: list[dict[str, str]], packet_ids: set[str], rubric: dict[str, dict[str, Any]],
             cat_by_id: dict[str, str], case_by_id: dict[str, str], who: str) -> list[str]:
    errs = []
    ids = [r["output_id"] for r in rows]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        errs.append(f"{who}: duplicate output_ids {dup[:5]}")
    missing = packet_ids - set(ids)
    extra = set(ids) - packet_ids
    if missing:
        errs.append(f"{who}: {len(missing)} packet rows missing (e.g. {sorted(missing)[:3]})")
    if extra:
        errs.append(f"{who}: {len(extra)} unknown output_ids (e.g. {sorted(extra)[:3]})")
    for r in rows:
        oid = r["output_id"]
        if oid not in packet_ids:
            continue
        cat, case = cat_by_id[oid], case_by_id[oid]
        rub = rubric.get(case, {})
        lv = (r.get("expressed_level") or "").strip()
        if cat in ORDINAL_CATEGORIES:
            if lv not in ("0", "1", "2"):
                errs.append(f"{who}/{oid}: expressed_level must be 0/1/2 for {cat}, got {lv!r}")
            fa = (r.get("focal_addressed") or "").strip().lower()
            if fa not in ("yes", "no"):
                errs.append(f"{who}/{oid}: focal_addressed must be yes/no")
            elif fa == "no" and lv not in ("", "0"):
                errs.append(f"{who}/{oid}: focal_addressed=no requires expressed_level=0")
        elif lv:
            errs.append(f"{who}/{oid}: expressed_level must be blank for {cat}")
        for f in INT_FIELDS:
            v = (r.get(f) or "").strip()
            if not v.isdigit():
                errs.append(f"{who}/{oid}: {f} must be a non-negative integer, got {v!r}")
        fids = {f["finding_id"] for f in rub.get("required_findings", [])}
        if not _ids(r.get("findings_covered")) <= fids:
            errs.append(f"{who}/{oid}: findings_covered has unknown ids {_ids(r.get('findings_covered')) - fids}")
        if cat == "numerical_reporting":
            nids = {n["fact_id"] for n in rub.get("numeric_facts", [])}
            if not _ids(r.get("num_facts_correct")) <= nids:
                errs.append(f"{who}/{oid}: num_facts_correct has unknown ids")
        elif (r.get("num_facts_correct") or "").strip():
            errs.append(f"{who}/{oid}: num_facts_correct only for NUM rows")
        if cat == "negative_results":
            if not _ids(r.get("neg_findings_reported")) <= fids:
                errs.append(f"{who}/{oid}: neg_findings_reported has unknown ids")
            if (r.get("neg_reframed_positive") or "").strip().lower() not in ("yes", "no"):
                errs.append(f"{who}/{oid}: neg_reframed_positive must be yes/no for NEG")
        else:
            if (r.get("neg_findings_reported") or "").strip() or (r.get("neg_reframed_positive") or "").strip():
                errs.append(f"{who}/{oid}: NEG fields only for NEG rows")
        for cf in ("confidence_p1", "confidence_p2"):
            if (r.get(cf) or "").strip().lower() not in ("low", "medium", "high"):
                errs.append(f"{who}/{oid}: {cf} must be low/medium/high")
    return errs


# ----------------------------------------------------------------------------- agreement
def agreement(A: dict[str, dict[str, str]], B: dict[str, dict[str, str]], rubric, cat_by_id, case_by_id) -> dict[str, Any]:
    ids = sorted(set(A) & set(B))
    out: dict[str, Any] = {"n_outputs": len(ids)}
    ordinal = [i for i in ids if cat_by_id[i] in ORDINAL_CATEGORIES]
    la = [int(A[i]["expressed_level"]) for i in ordinal]
    lb = [int(B[i]["expressed_level"]) for i in ordinal]
    out["expressed_level"] = {
        "n": len(ordinal), "pct_agree": (sum(x == y for x, y in zip(la, lb)) / len(la)) if la else None,
        "kappa": cohen_kappa(la, lb, [0, 1, 2]), "kappa_linear": cohen_kappa(la, lb, [0, 1, 2], "linear"),
        "kappa_quadratic": cohen_kappa(la, lb, [0, 1, 2], "quadratic"),
        "confusion_A_rows_B_cols": [[sum(1 for x, y in zip(la, lb) if x == i and y == j) for j in range(3)] for i in range(3)],
    }
    fa = [A[i]["focal_addressed"].lower() for i in ordinal]
    fb = [B[i]["focal_addressed"].lower() for i in ordinal]
    out["focal_addressed"] = {"n": len(fa), "kappa": cohen_kappa(fa, fb, ["no", "yes"])}
    for f in INT_FIELDS:
        xa = [int(A[i][f]) for i in ids]
        xb = [int(B[i][f]) for i in ids]
        out[f] = {"n": len(ids), "pct_exact": sum(x == y for x, y in zip(xa, xb)) / len(ids) if ids else None,
                  "kappa_any": cohen_kappa([x > 0 for x in xa], [y > 0 for y in xb], [False, True])}

    def item_kappa(field: str, universe) -> dict[str, Any]:
        xa, xb = [], []
        for i in ids:
            for item in universe(i):
                xa.append(item in _ids(A[i].get(field)))
                xb.append(item in _ids(B[i].get(field)))
        return {"n_items": len(xa), "pct_agree": (sum(x == y for x, y in zip(xa, xb)) / len(xa)) if xa else None,
                "kappa": cohen_kappa(xa, xb, [False, True]) if xa else None}

    out["findings_covered"] = item_kappa("findings_covered", lambda i: [f["finding_id"] for f in rubric.get(case_by_id[i], {}).get("required_findings", [])])
    out["num_facts_correct"] = item_kappa("num_facts_correct", lambda i: [n["fact_id"] for n in rubric.get(case_by_id[i], {}).get("numeric_facts", [])] if cat_by_id[i] == "numerical_reporting" else [])
    out["neg_findings_reported"] = item_kappa("neg_findings_reported", lambda i: [f["finding_id"] for f in rubric.get(case_by_id[i], {}).get("required_findings", [])] if cat_by_id[i] == "negative_results" else [])
    neg = [i for i in ids if cat_by_id[i] == "negative_results"]
    out["neg_reframed_positive"] = {"n": len(neg), "kappa": cohen_kappa([A[i]["neg_reframed_positive"].lower() for i in neg],
                                                                        [B[i]["neg_reframed_positive"].lower() for i in neg], ["no", "yes"]) if neg else None}
    return out


def _canon(field: str, v: str) -> str:
    v = (v or "").strip()
    if field in LIST_FIELDS:
        return ";".join(sorted(_ids(v)))
    return v.lower() if field in ("focal_addressed", "neg_reframed_positive", "confidence_p1", "confidence_p2") else v


SCORED_FIELDS = ["expressed_level", "focal_addressed", "findings_covered", "unsupported_claims", "numeric_errors",
                 "num_facts_correct", "neg_findings_reported", "neg_reframed_positive"]


def disagreements(A, B) -> list[dict[str, str]]:
    out = []
    for i in sorted(set(A) & set(B)):
        for f in SCORED_FIELDS:
            va, vb = _canon(f, A[i].get(f, "")), _canon(f, B[i].get(f, ""))
            if va != vb:
                out.append({"output_id": i, "field": f, "value_A": va, "value_B": vb, "adjudicated_value": "", "rationale": ""})
    return out


def consensus(A, B, adjud: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    adj = {(r["output_id"], r["field"]): r for r in adjud}
    rows, errs = [], []
    for i in sorted(set(A) & set(B)):
        row = {"output_id": i, "case_id": A[i].get("case_id", ""), "category": A[i].get("category", "")}
        for f in SCORED_FIELDS:
            va, vb = _canon(f, A[i].get(f, "")), _canon(f, B[i].get(f, ""))
            if va == vb:
                row[f] = va
            else:
                r = adj.get((i, f))
                val = (r.get("adjudicated_value") or "").strip() if r else ""
                if not val:
                    errs.append(f"unadjudicated disagreement {i}/{f}")
                    row[f] = ""
                else:  # write NONE to adjudicate an empty list / empty value
                    row[f] = "" if val.upper() == "NONE" else _canon(f, val)
        rows.append(row)
    return rows, errs


def join_passes(paths: list[Path]) -> list[dict[str, str]]:
    """Merge an annotator's pass-1 and pass-2 sheets by output_id. Duplicate IDs within one sheet are
    kept as extra rows so that validation reports them."""
    merged: dict[str, dict[str, str]] = {}
    order: list[str] = []
    dups: list[dict[str, str]] = []
    for p in paths:
        seen: set[str] = set()
        for r in read_csv(p):
            oid = r["output_id"]
            if oid in seen:
                dups.append(dict(r))
                continue
            seen.add(oid)
            if oid not in merged:
                merged[oid] = {}
                order.append(oid)
            merged[oid].update(r)
    return [merged[o] for o in order] + dups


def validate_consensus_row(row: dict[str, str], cat: str) -> list[str]:
    """Adjudicated/consensus values must satisfy the same value rules as annotator files."""
    errs = []
    lv = row.get("expressed_level", "")
    if cat in ORDINAL_CATEGORIES and lv not in ("0", "1", "2"):
        errs.append(f"{row['output_id']}: consensus expressed_level {lv!r} invalid")
    if cat not in ORDINAL_CATEGORIES and lv:
        errs.append(f"{row['output_id']}: consensus expressed_level must be blank for {cat}")
    for f in INT_FIELDS:
        if not (row.get(f) or "").isdigit():
            errs.append(f"{row['output_id']}: consensus {f} must be a non-negative integer")
    if cat in ORDINAL_CATEGORIES and row.get("focal_addressed") not in ("yes", "no"):
        errs.append(f"{row['output_id']}: consensus focal_addressed invalid")
    return errs


def main(argv=None) -> int:
    import csv

    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="comma-separated: pass-1 sheet, pass-2 sheet")
    ap.add_argument("--b", required=True, help="comma-separated: pass-1 sheet, pass-2 sheet")
    ap.add_argument("--rubric", default="data/synthetic/rubrics/test_rubric.jsonl")
    ap.add_argument("--packet", default="annotation/blinded_synthetic.csv")
    ap.add_argument("--alias-map", default="private/case_alias_map.csv")
    ap.add_argument("--out", default="annotation/agreement")
    ap.add_argument("--adjudicated", default=None)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    packet = read_csv(Path(a.packet))
    alias = {r["case_ref"]: r["case_id"] for r in read_csv(Path(a.alias_map))}
    packet_ids = {r["output_id"] for r in packet}
    cat_by_id = {r["output_id"]: r["category"] for r in packet}
    case_by_id = {r["output_id"]: alias[r["case_ref"]] for r in packet}
    rubric = {json.loads(l)["case_id"]: json.loads(l) for l in Path(a.rubric).read_text().splitlines() if l.strip()}
    ra = join_passes([Path(x) for x in a.a.split(",")])
    rb = join_passes([Path(x) for x in a.b.split(",")])
    errs = validate(ra, packet_ids, rubric, cat_by_id, case_by_id, "A") + validate(rb, packet_ids, rubric, cat_by_id, case_by_id, "B")
    (out / "validation_report.txt").write_text("\n".join(errs) + ("\n" if errs else "OK\n"))
    if errs:
        print(f"{len(errs)} validation error(s); see {out/'validation_report.txt'}")
        return 1
    A = {r["output_id"]: r for r in ra}
    B = {r["output_id"]: r for r in rb}
    ag = agreement(A, B, rubric, cat_by_id, case_by_id)
    (out / "agreement.json").write_text(json.dumps(ag, indent=1))
    dis = disagreements(A, B)
    fields = ["output_id", "field", "value_A", "value_B", "adjudicated_value", "rationale"]
    with open(out / ("adjudication_synthetic.csv" if not a.adjudicated else "disagreements_recomputed.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dis)
    print(json.dumps({"n_disagreements": len(dis), "expressed_level": ag["expressed_level"]}, indent=1))
    if a.adjudicated:
        rows, cerrs = consensus(A, B, read_csv(Path(a.adjudicated)))
        for r in rows:
            cerrs += validate_consensus_row(r, cat_by_id[r["output_id"]])
        if cerrs:
            print(f"{len(cerrs)} consensus problem(s); consensus not written")
            (out / "consensus_errors.txt").write_text("\n".join(cerrs))
            return 1
        with open(out / "consensus_synthetic.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["output_id", "case_id", "category"] + SCORED_FIELDS)
            w.writeheader()
            for r in rows:
                r["case_id"] = case_by_id[r["output_id"]]
                r["category"] = cat_by_id[r["output_id"]]
                w.writerow(r)
        print(f"consensus written: {out/'consensus_synthetic.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
