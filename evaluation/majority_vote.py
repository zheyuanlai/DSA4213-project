"""Third judge family and 2-of-3 majority sensitivity (protocol §11, amendment 12; exploratory).

Judge C (Qwen 3.7 Plus via OpenRouter) re-verified every claim with the same prompt as Judges A (GPT-5.6) and
B (Claude). This module measures C's agreement with A and B, checks the GPT-family adjudicator's decisions against
the independent third family, builds a consensus by 2-of-3 majority without any adjudicator, and re-scores every
planned contrast from that majority consensus and from Judge C alone. Numbers are always checked by code.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Optional

from evaluation import atomic_claims as ac
from evaluation.adjudicator_stability import _f, _ci_s, contrast_sensitivity
from evaluation.extended_data import ROOT, FamilyData, load_family
from evaluation.extended_pipeline import EXT, load_jsonl
from evaluation.merge_annotations import cohen_kappa
from evaluation.numeric_fidelity import EvidenceValues

OUT = ROOT / "results" / "ai_extended"
FAMS = ("synthetic", "real", "diagnostic")
JUDGES = ("A", "B", "C")
ERRORISH = ("NOT_ENTAILED", "CONTRADICTED")


def fleiss_kappa(rows: list[tuple[str, ...]]) -> Optional[float]:
    """Fleiss' kappa for items each rated by the same number of raters."""
    if not rows:
        return None
    n = len(rows[0])
    cats = sorted({c for r in rows for c in r})
    N = len(rows)
    p_j = {c: sum(r.count(c) for r in rows) / (N * n) for c in cats}
    P_i = [(sum(r.count(c) ** 2 for c in cats) - n) / (n * (n - 1)) for r in rows]
    P_bar, P_e = sum(P_i) / N, sum(v * v for v in p_j.values())
    return None if P_e == 1 else (P_bar - P_e) / (1 - P_e)


def _majority(values: list[Any]) -> Optional[Any]:
    c = Counter(values).most_common()
    return c[0][0] if c and c[0][1] >= 2 else None


def _verdict_class(status: str) -> str:
    return "INVALID" if status == "INVALID_MAPPING" else ("CORRECT" if status == "CORRECT" else "ERROR")


def load_readings(fam: str) -> dict[str, dict[str, dict[str, Any]]]:
    return {j: {r["claim_id"]: r for r in load_jsonl(EXT / "readings" / f"{fam}_verify_{j}.jsonl")} for j in JUDGES}


def majority_claims(fam: str, data: FamilyData) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Claim records from a 2-of-3 majority of A, B and C, with no adjudicator.

    Where the three disagree completely, the primary (adjudicated) decision is kept and counted."""
    raw = load_jsonl(EXT / "claims" / f"{fam}.jsonl")
    rd = load_readings(fam)
    primary = {r["claim_id"]: r for r in load_jsonl(EXT / "consensus" / f"{fam}_claims.jsonl")}
    inv = {v: k for k, v in data.aliases.items()}
    evs: dict[str, EvidenceValues] = {}
    stats = Counter()
    out = []
    for c in raw:
        cid = c["claim_id"]
        ev = evs.setdefault(c["alias"], EvidenceValues.from_package(data.cases[inv[c["alias"]]].package))
        p = primary[cid]
        reads = [rd[j][cid] for j in JUDGES]
        label = _majority([r["label"] for r in reads])
        if label is None:
            label = p["label_consensus"]
            stats["label_no_majority"] += 1
        ent = _majority([r["entailment"] for r in reads])
        if ent is None:
            ent = p["entailment"]
            stats["entailment_no_majority"] += 1
        nums = []
        for idx, n in enumerate(c["numbers"]):
            vs = [(j, ac.check_number(n, rd[j][cid]["numbers"].get(n["number_id"]), ev)) for j in JUDGES]
            classes = [_verdict_class(v.status) for _, v in vs if v.status != "INVALID_MAPPING"]
            maj = _majority(classes)
            if maj is None:
                stats["number_no_majority"] += 1
                pv = p["numbers"][idx]
                status, operands, alt = pv["verdict"], pv.get("operands", []), pv.get("alt_correct_mappings", [])
                mapping = pv.get("mapping")
            else:
                agree = [(j, v) for j, v in vs if v.status != "INVALID_MAPPING" and _verdict_class(v.status) == maj]
                j0, v0 = agree[0]
                status, operands, mapping = v0.status, list(v0.operands), rd[j0][cid]["numbers"].get(n["number_id"])
                alt = [{"mapping": rd[j][cid]["numbers"].get(n["number_id"]), "operands": list(v.operands)}
                       for j, v in agree[1:] if v.correct]
            nums.append({**n, "mapping": mapping, "verdict": status, "operands": operands, "expected": None,
                         "tolerance": None, "alt_correct_mappings": alt})
        num_err = any(x["verdict"] not in ("CORRECT", "INVALID_MAPPING") for x in nums)
        if p["final_label"] == "EXCLUDED":
            final = "EXCLUDED"
        else:
            final = "NUMERIC_ERROR" if num_err else label
        fe = None
        if final not in ("EXCLUDED", "NOT_VERIFIABLE"):
            fe = bool(num_err or ent in ERRORISH)
        elif final == "NOT_VERIFIABLE":
            fe = bool(num_err)
        stats["final_label_changed_vs_primary"] += final != p["final_label"]
        out.append({"claim_id": cid, "unit_id": c["unit_id"], "alias": c["alias"], "claim_type": c["claim_type"],
                    "result_claim": c["claim_type"] not in ac.NON_RESULT_TYPES, "final_label": final,
                    "factual_error": fe, "entailment": ent, "numbers": nums})
    stats["claims"] = len(out)
    return out, dict(stats)


def agreement(fam: str, data: FamilyData) -> dict[str, Any]:
    raw = {c["claim_id"]: c for c in load_jsonl(EXT / "claims" / f"{fam}.jsonl")}
    rd = load_readings(fam)
    reps = [cid for cid in raw if not rd["A"][cid].get("copied_from")]
    inv = {v: k for k, v in data.aliases.items()}
    evs: dict[str, EvidenceValues] = {}

    def pair(x: str, y: str, field: str) -> dict[str, Any]:
        a = [rd[x][k][field] for k in reps]
        b = [rd[y][k][field] for k in reps]
        return {"n": len(reps), "pct_agree": sum(u == v for u, v in zip(a, b)) / len(reps), "cohen_kappa": cohen_kappa(a, b)}

    res: dict[str, Any] = {}
    for field in ("label", "entailment"):
        res[field] = {f"{x}-{y}": pair(x, y, field) for x, y in (("A", "B"), ("A", "C"), ("B", "C"))}
        res[field]["fleiss_kappa_ABC"] = fleiss_kappa([tuple(rd[j][k][field] for j in JUDGES) for k in reps])
        res[field]["all_three_agree"] = sum(len({rd[j][k][field] for j in JUDGES}) == 1 for k in reps) / len(reps)
    cls: dict[str, list[str]] = {j: [] for j in JUDGES}
    for k in reps:
        c = raw[k]
        ev = evs.setdefault(c["alias"], EvidenceValues.from_package(data.cases[inv[c["alias"]]].package))
        for n in c["numbers"]:
            for j in JUDGES:
                cls[j].append(_verdict_class(ac.check_number(n, rd[j][k]["numbers"].get(n["number_id"]), ev).status))
    res["numeric_verdict"] = {f"{x}-{y}": {"n": len(cls[x]), "pct_agree": sum(u == v for u, v in zip(cls[x], cls[y])) / max(1, len(cls[x])),
                                           "cohen_kappa": cohen_kappa(cls[x], cls[y])}
                              for x, y in (("A", "B"), ("A", "C"), ("B", "C"))}
    res["numeric_verdict"]["judge_C_unusable_mappings"] = cls["C"].count("INVALID")
    res["label_distribution"] = {j: dict(Counter(rd[j][k]["label"] for k in reps)) for j in JUDGES}
    return res


def adjudicator_check(fam: str) -> dict[str, Any]:
    """On items the A–B adjudication decided, does the independent third family agree with the adjudicator?"""
    rd = load_readings(fam)
    p = EXT / "adjudication" / f"{fam}_claims.jsonl"
    out: dict[str, Any] = {}
    for field in ("label", "entailment"):
        rows = Counter()
        for d in (load_jsonl(p) if p.exists() else []):
            if field not in d["disputed_fields"]:
                continue
            k = d["item_id"]
            a, b, c, adj = rd["A"][k][field], rd["B"][k][field], rd["C"][k][field], d[field]
            side = "sided_A" if adj == a else "sided_B" if adj == b else "neither"
            rows[(side, "C_agrees" if c == adj else "C_differs")] += 1
        tot = sum(rows.values())
        out[field] = {"n": tot, "C_agrees_with_adjudicator": sum(v for (s, a), v in rows.items() if a == "C_agrees"),
                      "by_side": {f"{s}/{a}": v for (s, a), v in sorted(rows.items())}}
    return out


KEYS = ("support_rate", "factual_error_rate", "overstated_rate", "understated_rate", "unsupported_rate",
        "numeric_precision", "numeric_recall", "fully_supported")


def _summ(recs_summary: dict[str, Any]) -> dict[str, Any]:
    return {c: {k: (v[k]["value"] if isinstance(v[k], dict) else v[k]) for k in KEYS} for c, v in recs_summary.items()}


def run() -> dict[str, Any]:
    from evaluation.extended_metrics import COMPARISONS, compare_texts, edits, single_judge_claims, summarize_texts, text_records
    report: dict[str, Any] = {
        "provenance": "Judge C = qwen/qwen3.7-plus via OpenRouter (Alibaba; temperature 0, seed 4213, reasoning off), "
                      "same verification prompt as Judges A (GPT-5.6) and B (Claude). Majority = 2 of 3 AI judges, no "
                      "adjudicator; numbers checked by code. AI-only, exploratory.",
        "families": {}}
    for fam in FAMS:
        data = load_family(fam)
        checklists = json.loads((EXT / "checklists" / f"{fam}.json").read_text()) if fam != "synthetic" else None
        clusters = {c: c[:-1] for c in data.cases} if fam == "synthetic" else None
        primary = json.loads((OUT / fam / "results.json").read_text())
        maj_claims, stats = majority_claims(fam, data)
        recs = text_records(fam, data, maj_claims, checklists)
        maj = {"claims": {"summary": summarize_texts(recs), "comparisons": compare_texts(recs, COMPARISONS[fam], clusters)}}
        crecs = text_records(fam, data, single_judge_claims(fam, data, "C"), checklists)
        conly = {"claims": {"summary": summarize_texts(crecs), "comparisons": compare_texts(crecs, COMPARISONS[fam], clusters)}}
        prim = {"claims": primary["claims"]}
        cov_sets: dict[str, set[str]] = {}  # coverage is not re-judged: required-finding loss is left out here
        maj_edits = edits(fam, data, maj_claims, recs, cov_sets)["summary"]
        rows_m, rows_c = contrast_sensitivity(prim, maj), contrast_sensitivity(prim, conly)
        report["families"][fam] = {
            "agreement": agreement(fam, data), "adjudicator_check": adjudicator_check(fam), "majority_stats": stats,
            "summary": {"primary": _summ(primary["claims"]["summary"]), "majority": _summ(maj["claims"]["summary"]),
                        "judge_C_only": _summ(conly["claims"]["summary"])},
            "contrasts_majority": rows_m, "contrasts_judge_C": rows_c,
            "edits_majority": {c: {k: v.get(k) for k in ("initial_errors", "corrected", "removed", "new_errors", "repair_recall")}
                               for c, v in maj_edits.items()},
            "edits_primary": {c: {k: v.get(k) for k in ("initial_errors", "corrected", "removed", "new_errors", "repair_recall")}
                              for c, v in primary["edits"]["summary"].items()},
            "contrast_summary": {
                lab: {"n": len(rows), "sign_changes": sum(1 for r in rows if r["same_sign"] is False),
                      "zero_exclusion_changes": sum(1 for r in rows if r["primary_excludes_zero"] != r["replicate_excludes_zero"]),
                      "max_abs_shift": max((abs(r["shift"]) for r in rows if r["shift"] is not None), default=None)}
                for lab, rows in (("majority", rows_m), ("judge_C_only", rows_c))}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "majority_vote.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    (OUT / "tables" / "majority_vote.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    L = ["# Third judge (Qwen 3.7 Plus) and 2-of-3 majority", "", report["provenance"], "",
         "## Agreement before adjudication (representative claims)", "",
         "| Set | Field | A–B | A–C | B–C | Fleiss κ (A,B,C) | all three agree |", "|---|---|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        for field in ("label", "entailment"):
            a = r["agreement"][field]
            cell = lambda k: f"{_f(a[k]['pct_agree'])} (κ {_f(a[k]['cohen_kappa'])})"  # noqa: E731
            L.append(f"| {fam} | {field} | {cell('A-B')} | {cell('A-C')} | {cell('B-C')} | {_f(a['fleiss_kappa_ABC'])} | {_f(a['all_three_agree'])} |")
        nv = r["agreement"]["numeric_verdict"]
        L.append(f"| {fam} | numeric verdict | {_f(nv['A-B']['pct_agree'])} | {_f(nv['A-C']['pct_agree'])} | "
                 f"{_f(nv['B-C']['pct_agree'])} | — | C unusable mappings: {nv['judge_C_unusable_mappings']} |")
    L += ["", "## Does the independent third judge agree with the adjudicator?", "",
          "| Set | Field | Adjudicated items | Judge C agrees | By adjudicator side (sided_A / sided_B / neither) |", "|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        for field, x in r["adjudicator_check"].items():
            if x["n"]:
                L.append(f"| {fam} | {field} | {x['n']} | {x['C_agrees_with_adjudicator']} | "
                         + ", ".join(f"{k} {v}" for k, v in x["by_side"].items()) + " |")
    L += ["", "## Headline rates: primary (adjudicated) vs 2-of-3 majority vs Judge C alone", "",
          "| Set | Condition | Support (prim / maj / C) | Factual error (prim / maj / C) | Fully supported (prim / maj / C) |",
          "|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        s = r["summary"]
        for c in s["primary"]:
            g = lambda k: " / ".join(_f(s[v][c][k]) for v in ("primary", "majority", "judge_C_only"))  # noqa: E731
            L.append(f"| {fam} | {c} | {g('support_rate')} | {g('factual_error_rate')} | {g('fully_supported')} |")
    L += ["", "## Planned contrasts: primary vs majority vs Judge C alone (non-degenerate rows)", "",
          "| Set | Contrast | Metric | Primary | 2-of-3 majority | Judge C alone |", "|---|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        cmap = {(x["contrast"], x["metric"]): x for x in r["contrasts_judge_C"]}
        for x in r["contrasts_majority"]:
            if x["primary"].get("degenerate") and x["replicate"].get("degenerate"):
                continue
            y = cmap.get((x["contrast"], x["metric"]), {}).get("replicate", {})
            L.append(f"| {fam} | {x['contrast'].replace('_vs_', ' − ')} | {x['metric']} | {_ci_s(x['primary'])} | "
                     f"{_ci_s(x['replicate'])} | {_ci_s(y) if y else '—'} |")
        for lab, v in r["contrast_summary"].items():
            L.append(f"| {fam} | **all {v['n']} contrasts, {lab}** | | sign changes {v['sign_changes']} | "
                     f"zero-exclusion changes {v['zero_exclusion_changes']} | max shift {_f(v['max_abs_shift'])} |")
    L += ["", "Majority fallbacks to the adjudicated decision (no 2-of-3 agreement): " +
          "; ".join(f"{fam}: {r['majority_stats'].get('label_no_majority', 0)} labels, "
                    f"{r['majority_stats'].get('number_no_majority', 0)} numbers"
                    for fam, r in report["families"].items()), ""]
    return "\n".join(L)
