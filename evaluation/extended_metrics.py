"""Scoring of the evaluation extension (protocol §5, §8, §9). Unblinds; run only after consensus is frozen.

Writes ``results/ai_extended/<family>/results.json`` and Markdown tables. All numbers are computed from frozen
consensus files, the private condition mappings, gold (synthetic/diagnostic) and the run records.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation import atomic_claims as ac
from evaluation.edit_analysis import ERRORS, analyze_run, decisive_retrieval, summarize
from evaluation.extended_data import ROOT, FamilyData, load_family, unit_id
from evaluation.extended_stats import mean_diff, rate_ci, ratio_diff
from evaluation.numeric_fidelity import (
    PRIMARY_ROLES, Assertion, EvidenceValues, ExpressionError, Mapping, Verdict, fact_from_expression, fact_reported,
    gold_fact,
)
from src.package_schema import ORDINAL_CATEGORIES

EXT = ROOT / "annotation" / "ai_extended"
OUT = ROOT / "results" / "ai_extended"
DRAFT = "DRAFT"  # pseudo-condition: the real-paper outline draft that starts C3/C4
COMPARISONS = {
    "synthetic": [("C4", "C2"), ("C4", "C1"), ("C4", "C3"), ("C4", "C5"), ("C4", "C7"),
                  ("C3", "C7"), ("C5", "C7"), ("C2", "C1"), ("C6", "C1")],
    "real": [("C4", "C2"), ("C4", "C1"), ("C4", "C3"), ("C2", "C1"), ("C3", DRAFT), ("C4", DRAFT)],
    "diagnostic": [("C4", "C7"), ("C3", "C7"), ("C4", "C3")],
}
PRIMARY_PLANNED = {("C4", "C2"), ("C4", "C1"), ("C4", "C3"), ("C4", "C5"), ("C4", "C7")}


def read_csv(p: Path) -> list[dict[str, str]]:
    with p.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _ids(s: Optional[str]) -> set[str]:
    return {x.strip() for x in (s or "").replace(",", ";").split(";") if x.strip()}


def _mean(xs: list[Optional[float]]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ----------------------------------------------------------------------------- Metric A
def strict_passage_checks(row: Optional[dict[str, str]], gold: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Optional[bool]]:
    """Applicable checks of protocol §5.A for one synthetic output (None = not applicable)."""
    cat = gold["category"]
    if row is None:  # missing or failed run (ITT): every applicable check fails
        row = {}
        valid = False
    else:
        valid = True
    req = {f["finding_id"] for f in rubric.get("required_findings", [])}
    facts = {n["fact_id"] for n in rubric.get("numeric_facts", [])}
    negs = {f["finding_id"] for f in gold.get("required_findings", []) if f.get("polarity") in ("negative", "null", "mixed")}
    checks: dict[str, Optional[bool]] = {"valid_output": valid}
    if cat in ORDINAL_CATEGORIES:
        hat = 0 if (row.get("focal_addressed") or "no") == "no" else int(row.get("expressed_level") or 0)
        checks["focal_correct"] = valid and hat == gold["gold_level"]
    else:
        checks["focal_correct"] = None
    checks["all_findings_covered"] = valid and req <= _ids(row.get("findings_covered"))
    checks["no_unsupported"] = valid and int(row.get("unsupported_claims") or 0) == 0
    checks["no_numeric_error"] = valid and int(row.get("numeric_errors") or 0) == 0
    checks["num_facts_all_correct"] = (valid and facts <= _ids(row.get("num_facts_correct"))) if cat == "numerical_reporting" else None
    checks["neg_findings_all_reported"] = (valid and negs <= _ids(row.get("neg_findings_reported"))) if cat == "negative_results" else None
    checks["no_positive_reframing"] = (valid and (row.get("neg_reframed_positive") or "no") == "no") if cat == "negative_results" else None
    return checks


def metric_a(atomic_clean: Optional[dict[tuple[str, str], int]] = None) -> dict[str, Any]:
    cons = {r["output_id"]: r for r in read_csv(ROOT / "annotation" / "ai" / "consensus" / "consensus_synthetic.csv")}
    mapping = read_csv(ROOT / "private" / "condition_mapping.csv")
    gold = {r["case_id"]: r for r in load_jsonl(ROOT / "private" / "gold" / "test_gold.jsonl")}
    rubric = {r["case_id"]: r for r in load_jsonl(ROOT / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl")}
    per: dict[str, dict[str, dict[str, Any]]] = {}
    for m in mapping:
        row = cons.get(m["output_id"]) if m["status"] == "completed" else None
        if m["status"] == "completed" and row is None:
            raise ValueError(f"completed output {m['output_id']} has no AI consensus row")
        ch = strict_passage_checks(row, gold[m["case_id"]], rubric[m["case_id"]])
        rec = {k: (None if v is None else int(v)) for k, v in ch.items()}
        rec["complete_correct"] = int(all(v for v in ch.values() if v is not None))
        rec["completed"] = int(row is not None)
        if atomic_clean is not None:
            ch2 = dict(ch)
            ch2["no_unsupported"] = ch2["no_numeric_error"] = None
            ch2["no_atomic_error"] = bool(atomic_clean.get((m["case_id"], m["condition"]), 0))
            rec["no_atomic_error"] = int(ch2["no_atomic_error"])
            rec["complete_correct_atomic"] = int(all(v for v in ch2.values() if v is not None))
        per.setdefault(m["condition"], {})[m["case_id"]] = rec
    clusters = {c: c[:-1] for c in gold}
    keys = ["complete_correct", "focal_correct", "all_findings_covered", "no_unsupported", "no_numeric_error",
            "num_facts_all_correct", "neg_findings_all_reported", "no_positive_reframing"] + \
        (["no_atomic_error", "complete_correct_atomic"] if atomic_clean is not None else [])
    summary = {}
    for policy in ("ITT", "completed_only"):
        summary[policy] = {}
        for cond, d in sorted(per.items()):
            rows = [r for r in d.values() if policy == "ITT" or r["completed"]]
            summary[policy][cond] = {k: _mean([r.get(k) for r in rows]) for k in keys}
            summary[policy][cond]["n"] = {k: sum(r.get(k) is not None for r in rows) for k in keys}
    comps = {}
    for a, b in COMPARISONS["synthetic"]:
        comps[f"{a}_vs_{b}"] = {k: mean_diff({c: r[k] for c, r in per[a].items()}, {c: r[k] for c, r in per[b].items()}, clusters)
                                for k in keys}
    return {"definition": "protocol §5.A", "per_case": per, "summary": summary, "comparisons": comps,
            "missing_runs": sum(1 - r["completed"] for d in per.values() for r in d.values())}


# ----------------------------------------------------------------------------- per-text records
def _verdict_tuples(numbers: list[dict[str, Any]]) -> list[tuple[Assertion, Mapping, Verdict]]:
    out = []
    for n in numbers:
        a = ac.to_assertion(n)
        if n.get("mapping"):
            out.append((a, ac.to_mapping(n["mapping"], n.get("comparator") or "="),
                        Verdict(n["verdict"], n.get("expected"), n.get("tolerance"), tuple(n.get("operands") or ()))))
        for alt in n.get("alt_correct_mappings") or []:
            out.append((a, ac.to_mapping(alt["mapping"], n.get("comparator") or "="),
                        Verdict("CORRECT", None, None, tuple(alt.get("operands") or ()))))
    return out


def required_facts(fam: str, data: FamilyData, case_id: str, checklists: Optional[dict[str, Any]]) -> list:
    ev = EvidenceValues.from_package(data.cases[case_id].package)
    if fam == "synthetic":
        g = {r["case_id"]: r for r in load_jsonl(ROOT / "private" / "gold" / "test_gold.jsonl")}[case_id]
        return [gold_fact(f, ev) for f in g.get("numeric_facts") or []]
    facts = []
    for f in checklists["checklists"][data.aliases[case_id]]["numeric_facts"]:
        try:
            facts.append(fact_from_expression(f["fact_id"], f["expression"], ev, f["description"]))
        except ExpressionError:
            continue
    return facts


def text_records(fam: str, data: FamilyData, claims: list[dict[str, Any]], checklists: Optional[dict[str, Any]]):
    """Per (condition, case) record for every completed run (plus the real-paper DRAFT pseudo-condition)."""
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_unit.setdefault(c["unit_id"], []).append(c)
    facts_cache: dict[str, list] = {}
    texts: dict[str, dict[str, str]] = {}
    for (case_id, cond), rv in data.runs.items():
        if rv.status == "completed":
            texts.setdefault(cond, {})[case_id] = rv.final_text_id
            if fam == "real" and data.family.draft_of.get(cond) == "DRAFT_OUTLINE":
                texts.setdefault(DRAFT, {})[case_id] = rv.draft_text_id
    recs: dict[str, dict[str, dict[str, Any]]] = {}
    for cond, d in texts.items():
        for case_id, tid in d.items():
            t = data.texts[tid]
            s = ac.text_claim_summary(by_unit, t.units)
            if case_id not in facts_cache:
                facts_cache[case_id] = required_facts(fam, data, case_id, checklists)
            facts = facts_cache[case_id]
            vt = _verdict_tuples([n for u in t.units for c in by_unit.get(u, []) for n in c["numbers"]])
            s["n_required_facts"] = len(facts)
            s["n_required_facts_reported"] = sum(fact_reported(f, vt) for f in facts)
            s["text_id"] = tid
            recs.setdefault(cond, {})[case_id] = s
    return recs


CLAIM_RATES = {  # name: (numerator key, denominator key, scope)
    "support_rate": ("n_supported", "n_assessable", "all"),
    "factual_error_rate": ("n_factual_error", "n_assessable", "all"),
    "overstated_rate": ("n_overstated", "n_assessable", "all"),
    "understated_rate": ("n_understated", "n_assessable", "all"),
    "unsupported_rate": ("n_unsupported", "n_assessable", "all"),
    "numeric_error_claim_rate": ("n_numeric_error", "n_assessable", "all"),
    "support_rate_result_claims": ("n_supported", "n_assessable", "result"),
    "factual_error_rate_result_claims": ("n_factual_error", "n_assessable", "result"),
    "unsupported_rate_result_claims": ("n_unsupported", "n_assessable", "result"),
}
NUM_RATES = {"numeric_precision": ("n_numbers_primary_correct", "n_numbers_primary"),
             "numeric_recall": ("n_required_facts_reported", "n_required_facts")}
PASSAGE_RATES = ("fully_supported", "factually_clean", "numeric_error_free", "no_assessable_claims")


def _num_den(recs: dict[str, dict[str, Any]], num: str, den: str, scope: Optional[str] = None):
    pick = (lambda r: r[scope]) if scope else (lambda r: r)
    return {k: float(pick(r)[num]) for k, r in recs.items()}, {k: float(pick(r)[den]) for k, r in recs.items()}


def summarize_texts(recs: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    out = {}
    for cond, d in recs.items():
        s: dict[str, Any] = {"n_texts": len(d)}
        for name, (num, den, scope) in CLAIM_RATES.items():
            n, dd = _num_den(d, num, den, scope)
            v, lo, hi = rate_ci(n, dd)
            s[name] = {"value": v, "ci": [lo, hi], "numerator": sum(n.values()), "denominator": sum(dd.values())}
        for name, (num, den) in NUM_RATES.items():
            n, dd = _num_den(d, num, den)
            v, lo, hi = rate_ci(n, dd)
            s[name] = {"value": v, "ci": [lo, hi], "numerator": sum(n.values()), "denominator": sum(dd.values())}
        p, r = s["numeric_precision"]["value"], s["numeric_recall"]["value"]
        s["numeric_f1_secondary"] = (2 * p * r / (p + r)) if p and r else None
        for k in PASSAGE_RATES:
            s[k] = _mean([r[k] for r in d.values()])
        s["claims_per_text"] = _mean([r["all"]["n_claims"] for r in d.values()])
        s["assessable_per_text"] = _mean([r["all"]["n_assessable"] for r in d.values()])
        s["n_not_verifiable"] = sum(r["all"]["n_not_verifiable"] for r in d.values())
        s["n_unresolved"] = sum(r["all"]["n_unresolved"] for r in d.values())
        s["n_excluded"] = sum(r["all"]["n_excluded"] for r in d.values())
        s["numbers_per_text"] = _mean([r["n_numbers_primary"] for r in d.values()])
        s["numeric_error_types"] = dict(Counter(t for r in d.values() for t in r["numeric_error_types"]))
        s["setup_numbers"] = {"n": sum(r["n_numbers_setup"] for r in d.values()),
                              "correct": sum(r["n_numbers_setup_correct"] for r in d.values())}
        out[cond] = s
    return out


def compare_texts(recs: dict[str, dict[str, dict[str, Any]]], pairs: list[tuple[str, str]],
                  clusters: Optional[dict[str, str]] = None, itt_failed: Optional[dict[str, set[str]]] = None) -> dict[str, Any]:
    comps = {}
    for a, b in pairs:
        if a not in recs or b not in recs:
            continue
        ra, rb = recs[a], recs[b]
        res: dict[str, Any] = {"planned_primary": (a, b) in PRIMARY_PLANNED}
        for name, (num, den, scope) in CLAIM_RATES.items():
            na, da = _num_den(ra, num, den, scope)
            nb, db = _num_den(rb, num, den, scope)
            res[name] = ratio_diff(na, da, nb, db, clusters)
        for name, (num, den) in NUM_RATES.items():
            na, da = _num_den(ra, num, den)
            nb, db = _num_den(rb, num, den)
            res[name] = ratio_diff(na, da, nb, db, clusters)
        for k in ("fully_supported", "factually_clean", "numeric_error_free"):
            res[k] = mean_diff({c: r[k] for c, r in ra.items()}, {c: r[k] for c, r in rb.items()}, clusters)
            if itt_failed:  # failure-inclusive: a failed run counts as 0 on passage-level success
                fa = {c: 0 for c in itt_failed.get(a, set())}
                fb = {c: 0 for c in itt_failed.get(b, set())}
                res[k + "_ITT"] = mean_diff({**{c: r[k] for c, r in ra.items()}, **fa},
                                            {**{c: r[k] for c, r in rb.items()}, **fb}, clusters)
        comps[f"{a}_vs_{b}"] = res
    return comps


# ----------------------------------------------------------------------------- completeness (real, diagnostic)
def completeness(fam: str, data: FamilyData, checklists: dict[str, Any], recs: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    cov = {(r["text_id"], r["item_id"]): r["status"] for r in load_jsonl(EXT / "consensus" / f"{fam}_coverage.jsonl")}
    from evaluation.extended_pipeline import coverage_items
    per: dict[str, dict[str, dict[str, Any]]] = {}
    failed: dict[str, set[str]] = {}
    items_by_case = {c: coverage_items(data, data.aliases[c], checklists["checklists"][data.aliases[c]]) for c in data.cases}
    for cond, d in recs.items():
        for case_id, r in d.items():
            items = items_by_case[case_id]
            st = {i["item_id"]: cov.get((r["text_id"], i["item_id"])) for i in items}
            if any(v is None for v in st.values()):
                raise ValueError(f"{fam}/{case_id}/{cond}: missing coverage consensus")

            def rec(sel):
                xs = [i for i in items if sel(i)]
                return (sum(st[i["item_id"]] == "CORRECT" for i in xs), sum(st[i["item_id"]] == "INCORRECT" for i in xs),
                        len(xs))
            ck = lambda i: i["source"] == "checklist"  # noqa: E731
            c_ok, c_bad, c_n = rec(ck)
            n_ok, _, n_n = rec(lambda i: ck(i) and i["polarity"] in ("negative", "null", "mixed"))
            k_ok, _, k_n = rec(lambda i: ck(i) and i["importance"] == "core")
            g_ok, g_bad, g_n = rec(lambda i: i["source"] == "gold_required")
            per.setdefault(cond, {})[case_id] = {
                "n_items": c_n, "n_correct": c_ok, "n_incorrect": c_bad, "n_neg_items": n_n, "n_neg_correct": n_ok,
                "n_core_items": k_n, "n_core_correct": k_ok, "complete_core": int(k_n > 0 and k_ok == k_n),
                "n_gold_items": g_n, "n_gold_correct": g_ok, "complete_gold": int(g_n > 0 and g_ok == g_n) if g_n else None,
                "text_id": r["text_id"], "completed": 1}
    for (case_id, cond), rv in data.runs.items():
        if rv.status != "completed":
            failed.setdefault(cond, set()).add(case_id)
    rates = {"finding_recall": ("n_correct", "n_items"), "finding_incorrect_rate": ("n_incorrect", "n_items"),
             "negative_finding_recall": ("n_neg_correct", "n_neg_items"), "core_finding_recall": ("n_core_correct", "n_core_items")}
    if fam == "diagnostic":
        rates["gold_required_recall"] = ("n_gold_correct", "n_gold_items")
    summary = {}
    for cond, d in per.items():
        s = {"n_texts": len(d)}
        for name, (num, den) in rates.items():
            v, lo, hi = rate_ci({k: r[num] for k, r in d.items()}, {k: r[den] for k, r in d.items()})
            s[name] = {"value": v, "ci": [lo, hi], "numerator": sum(r[num] for r in d.values()),
                       "denominator": sum(r[den] for r in d.values())}
            # failure-inclusive: a failed run reports nothing
            if failed.get(cond):
                tot_items = {c: next(iter(per.values())).get(c, {}).get(den, 0) for c in failed[cond]}
                nn = {**{k: r[num] for k, r in d.items()}, **{c: 0 for c in failed[cond]}}
                dd = {**{k: r[den] for k, r in d.items()}, **{c: max(tot_items.get(c, 0), _items_den(items_by_case[c], den)) for c in failed[cond]}}
                v2, lo2, hi2 = rate_ci(nn, dd)
                s[name + "_ITT"] = {"value": v2, "ci": [lo2, hi2]}
        s["paragraph_completeness_core"] = _mean([r["complete_core"] for r in d.values()])
        if fam == "diagnostic":
            s["paragraph_completeness_gold"] = _mean([r["complete_gold"] for r in d.values()])
        if failed.get(cond):
            s["paragraph_completeness_core_ITT"] = sum(r["complete_core"] for r in d.values()) / (len(d) + len(failed[cond]))
        summary[cond] = s
    comps = {}
    for a, b in COMPARISONS[fam]:
        if a in per and b in per:
            res = {"planned_primary": (a, b) in PRIMARY_PLANNED}
            for name, (num, den) in rates.items():
                res[name] = ratio_diff({k: r[num] for k, r in per[a].items()}, {k: r[den] for k, r in per[a].items()},
                                       {k: r[num] for k, r in per[b].items()}, {k: r[den] for k, r in per[b].items()})
            res["paragraph_completeness_core"] = mean_diff({k: r["complete_core"] for k, r in per[a].items()},
                                                           {k: r["complete_core"] for k, r in per[b].items()})
            comps[f"{a}_vs_{b}"] = res
    return {"per_case": per, "summary": summary, "comparisons": comps,
            "failed_runs": {k: sorted(v) for k, v in failed.items()}}


def _items_den(items: list[dict[str, Any]], den: str) -> int:
    ck = [i for i in items if i["source"] == "checklist"]
    return {"n_items": len(ck), "n_neg_items": sum(i["polarity"] in ("negative", "null", "mixed") for i in ck),
            "n_core_items": sum(i["importance"] == "core" for i in ck),
            "n_gold_items": sum(i["source"] == "gold_required" for i in items)}[den]


# ----------------------------------------------------------------------------- edits, decisions, efficiency
def edits(fam: str, data: FamilyData, claims: list[dict[str, Any]], recs, coverage_sets) -> dict[str, Any]:
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_unit.setdefault(c["unit_id"], []).append(c)
    labels = {c["claim_id"]: c["final_label"] for c in claims}
    align = {(r["draft_text_id"], r["final_text_id"]): r for r in load_jsonl(EXT / "consensus" / f"{fam}_alignment.jsonl")}
    per: dict[str, dict[str, Any]] = {}
    examples = []
    for (case_id, cond), rv in sorted(data.runs.items()):
        if rv.status != "completed" or not rv.draft_text_id:
            continue
        d, f = data.texts[rv.draft_text_id], data.texts[rv.final_text_id]
        al = None if rv.draft_text_id == rv.final_text_id else align[(rv.draft_text_id, rv.final_text_id)]
        r = analyze_run(d.units, f.units, by_unit, labels, al, coverage_sets.get(rv.draft_text_id),
                        coverage_sets.get(rv.final_text_id))
        per.setdefault(cond, {})[case_id] = r
        for e in r.events:
            if e["class"] in ("beneficial", "harmful") and cond not in ("C2",):
                examples.append({"case_id": case_id, "alias": data.aliases[case_id], "condition": cond, **e})
    summary = {cond: summarize(list(d.values())) for cond, d in per.items()}
    # decisions and tool use from the traces
    decisions = {}
    for (case_id, cond), rv in data.runs.items():
        if rv.status == "completed" and rv.claim_traces:
            c = decisions.setdefault(cond, Counter())
            for t in rv.claim_traces:
                c[t["decision"]["decision"]] += 1
    comps = {}
    pairs = [(a, b) for a, b in (("C4", "C3"), ("C4", "C5"), ("C3", "C5"), ("C6", "C2")) if a in per and b in per]
    for a, b in pairs:
        res = {}
        for key in ("initial_errors", "corrected", "removed", "new_errors", "harmful", "beneficial", "substantive_edits"):
            res[key] = mean_diff({c: getattr(r, key) for c, r in per[a].items()}, {c: getattr(r, key) for c, r in per[b].items()})
        res["repairs"] = mean_diff({c: r.corrected + r.removed for c, r in per[a].items()},
                                   {c: r.corrected + r.removed for c, r in per[b].items()})
        comps[f"{a}_vs_{b}"] = res
    return {"per_case": {c: {k: v.as_dict() | {"events": v.events} for k, v in d.items()} for c, d in per.items()},
            "summary": summary, "decisions": {k: dict(v) for k, v in decisions.items()},
            "strengthen_observed": sum(v.get("STRENGTHEN", 0) for v in decisions.values()),
            "comparisons_same_draft": comps, "examples": examples}


def retrieval(fam: str, data: FamilyData, claims: list[dict[str, Any]]) -> dict[str, Any]:
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_unit.setdefault(c["unit_id"], []).append(c)
    out: dict[str, Counter] = {}
    for (case_id, cond), rv in data.runs.items():
        if rv.status != "completed" or not rv.claim_traces:
            continue
        pkg = data.cases[case_id].package
        tmap = {s.test_id: f"{s.experiment_id}/{s.comparison_id}" for s in pkg.statistical_tests}
        cnt = out.setdefault(cond, Counter())
        for t in rv.claim_traces:
            u = unit_id(case_id, t["original_text"])
            cnt["verified_sentences"] += 1
            cnt["tool_calls"] += len(t.get("observations", []))
            for c in by_unit.get(u, []):
                cnt["verified_claims"] += 1
                if c["final_label"] in ERRORS:
                    r = decisive_retrieval(t, c["evidence_ids"], tmap)
                    cnt["opportunities"] += 1
                    cnt["all_decisive_retrieved"] += r["all"]
                    cnt["any_decisive_retrieved"] += r["any"]
    return {cond: dict(c) | {"share_all_decisive": (c["all_decisive_retrieved"] / c["opportunities"]) if c["opportunities"] else None,
                             "share_any_decisive": (c["any_decisive_retrieved"] / c["opportunities"]) if c["opportunities"] else None,
                             "tool_calls_per_verified_claim": (c["tool_calls"] / c["verified_claims"]) if c["verified_claims"] else None}
            for cond, c in out.items()}


def efficiency(data: FamilyData, quality: dict[str, dict[str, Optional[float]]], repairs: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for cond in data.family.conditions:
        runs = [rv for (c, k), rv in data.runs.items() if k == cond and rv.status == "completed"]
        if not runs:
            continue
        tot = lambda key: [float(rv.totals.get(key) or 0.0) for rv in runs]  # noqa: E731
        cost, lat, tools = _mean(tot("cost_usd")), _mean(tot("latency_s")), _mean(tot("n_tool_calls"))
        s = {"n_runs": len(runs), "cost_usd_per_text": cost, "latency_s_per_text": lat, "tool_calls_per_text": tools,
             "model_calls_per_text": _mean(tot("n_model_calls")),
             "tool_calls_per_verified_claim": (sum(tot("n_tool_calls")) / sum(tot("n_claims"))) if sum(tot("n_claims")) else None}
        for qname, qv in quality.get(cond, {}).items():
            s[f"cost_per_{qname}"] = (cost / qv) if qv else None
        rep = repairs.get(cond)
        if rep and sum(tot("n_tool_calls")):
            s["repairs_per_100_tool_calls"] = 100 * (rep.get("corrected", 0) + rep.get("removed", 0)) / sum(tot("n_tool_calls"))
        out[cond] = s
    return out


# ----------------------------------------------------------------------------- family scoring
def score_family(fam: str) -> dict[str, Any]:
    data = load_family(fam)
    claims = load_jsonl(EXT / "consensus" / f"{fam}_claims.jsonl")
    checklists = json.loads((EXT / "checklists" / f"{fam}.json").read_text()) if fam != "synthetic" else None
    recs = text_records(fam, data, claims, checklists)
    clusters = {c: c[:-1] for c in data.cases} if fam == "synthetic" else None
    failed = {}
    for (case_id, cond), rv in data.runs.items():
        if rv.status != "completed":
            failed.setdefault(cond, set()).add(case_id)
    res: dict[str, Any] = {"family": fam, "provenance": "AI judges (GPT-5.6 via Codex CLI; Claude Sonnet 5.5 via Claude CLI) "
                           "with GPT-5.6 adjudication; numeric verdicts deterministic. Not human annotation.",
                           "n_cases": len(data.cases), "failed_runs": {k: sorted(v) for k, v in failed.items()},
                           "claims": {"summary": summarize_texts(recs),
                                      "comparisons": compare_texts(recs, COMPARISONS[fam], clusters, failed or None),
                                      "per_case": recs}}
    coverage_sets: dict[str, set[str]] = {}
    if fam == "synthetic":
        cons = {r["output_id"]: r for r in read_csv(ROOT / "annotation" / "ai" / "consensus" / "consensus_synthetic.csv")}
        rubric = {r["case_id"]: r for r in load_jsonl(ROOT / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl")}
        for tid, t in data.texts.items():
            req = {f["finding_id"] for f in rubric[t.case_id].get("required_findings", [])}
            coverage_sets[tid] = _ids(cons[tid]["findings_covered"]) & req
        atomic_clean = {(case_id, cond): int(not any(r["all"][f"n_{x.lower()}"] for x in ERRORS))
                        for cond, d in recs.items() for case_id, r in d.items()}
        res["metric_a"] = metric_a(atomic_clean)
    else:
        res["completeness"] = completeness(fam, data, checklists, {k: v for k, v in recs.items()})
        for r in load_jsonl(EXT / "consensus" / f"{fam}_coverage.jsonl"):
            if r["status"] == "CORRECT" and not r["item_id"].startswith("G"):
                coverage_sets.setdefault(r["text_id"], set()).add(r["item_id"])
        for t in data.texts:
            coverage_sets.setdefault(t, set())
        if fam == "real":
            read = {r["output_id"]: int(r["readability"]) for r in
                    read_csv(ROOT / "annotation" / "ai" / "consensus" / "consensus_real_outputs.csv")}
            pts = []
            for cond, d in res["completeness"]["per_case"].items():
                if cond == DRAFT:
                    continue
                for case_id, r in d.items():
                    if r["text_id"] in read and r["n_items"]:
                        pts.append({"condition": cond, "case_id": case_id, "recall": r["n_correct"] / r["n_items"],
                                    "readability": read[r["text_id"]],
                                    "support_rate": (recs[cond][case_id]["all"]["n_supported"] / recs[cond][case_id]["all"]["n_assessable"])
                                    if recs[cond][case_id]["all"]["n_assessable"] else None})
            res["completeness"]["readability_points"] = pts
            res["completeness"]["spearman_recall_readability"] = _spearman([p["recall"] for p in pts], [p["readability"] for p in pts])
            sp = [p for p in pts if p["support_rate"] is not None]
            res["completeness"]["spearman_recall_support"] = _spearman([p["recall"] for p in sp], [p["support_rate"] for p in sp])
    res["edits"] = edits(fam, data, claims, recs, coverage_sets)
    res["retrieval"] = retrieval(fam, data, claims)
    quality = {}
    for cond in data.family.conditions:
        q = {}
        if fam == "synthetic":
            q["complete_correct_passage"] = res["metric_a"]["summary"]["ITT"].get(cond, {}).get("complete_correct")
        if cond in recs:
            q["fully_supported_passage"] = res["claims"]["summary"][cond]["fully_supported"]
        quality[cond] = q
    res["efficiency"] = efficiency(data, quality, res["edits"]["summary"])
    OUT.joinpath(fam).mkdir(parents=True, exist_ok=True)
    (OUT / fam / "results.json").write_text(json.dumps(res, indent=1, default=_json_default), encoding="utf-8")
    print(f"  scored {fam} -> {(OUT / fam / 'results.json').relative_to(ROOT)}")
    return res


def _json_default(o):
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


def _spearman(x: list[float], y: list[float]) -> Optional[float]:
    if len(x) < 3:
        return None
    from scipy.stats import spearmanr
    r = spearmanr(x, y)
    return float(r.statistic) if r.statistic == r.statistic else None
