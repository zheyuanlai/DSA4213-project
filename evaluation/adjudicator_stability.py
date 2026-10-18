"""Test–retest stability of the AI adjudicator (exploratory; protocol §11, amendment 11).

A replicate re-asks every adjudication prompt verbatim (only the cache key carries a salt) and writes under
``annotation/ai_extended/replicates/<name>/``. This module compares the replicate with the primary adjudication:
per-field agreement and Cohen's kappa, changes in final consensus labels, and the sensitivity of every planned
contrast when the whole evaluation is re-scored from the replicate consensus. AI–AI agreement only.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation.extended_data import ROOT
from evaluation.extended_pipeline import EXT, load_jsonl
from evaluation.merge_annotations import cohen_kappa

OUT = ROOT / "results" / "ai_extended"
FAMS = ("synthetic", "real", "diagnostic")


def _load(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path) if path.exists() else []


def _block(pairs: list[tuple[Any, Any]], labels: Optional[list[Any]] = None) -> dict[str, Any]:
    n = len(pairs)
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    return {"n": n, "agree": sum(x == y for x, y in pairs), "pct_agree": (sum(x == y for x, y in pairs) / n) if n else None,
            "cohen_kappa": cohen_kappa(xs, ys, labels) if n else None,
            "changes": dict(Counter(f"{x}->{y}" for x, y in pairs if x != y))}


def _choice(d: dict[str, Any], n: dict[str, Any]) -> str:
    return "own" if n["choice"] == "own" else d["_reading_map"][n["choice"]]


def test_retest(fam: str, replicate: str, ext: Path = EXT) -> dict[str, Any]:
    """Agreement between the primary and the replicate adjudication of the same disputed items."""
    prim, rep = ext / "adjudication", ext / "replicates" / replicate / "adjudication"
    out: dict[str, Any] = {}
    a = {d["item_id"]: d for d in _load(prim / f"{fam}_claims.jsonl")}
    b = {d["item_id"]: d for d in _load(rep / f"{fam}_claims.jsonl")}
    common = sorted(set(a) & set(b))
    out["claims_items"] = {"primary": len(a), "replicate": len(b), "common": len(common)}
    for f in ("label", "entailment"):
        out[f] = _block([(a[k][f], b[k][f]) for k in common if f in a[k]["disputed_fields"]])
    out["extraction_valid"] = _block([(a[k]["extraction_valid"], b[k]["extraction_valid"]) for k in common
                                      if "extraction" in a[k]["disputed_fields"]])
    pairs = []
    for k in common:
        bn = {n["number_id"]: n for n in b[k]["numbers"]}
        for n in a[k]["numbers"]:
            if n["number_id"] in bn:
                pairs.append((_choice(a[k], n), _choice(b[k], bn[n["number_id"]])))
    out["number_mapping_choice"] = _block(pairs)
    ca = {(d["text_id"], d["item_id"]): d["status"] for d in _load(prim / f"{fam}_coverage.jsonl")}
    cb = {(d["text_id"], d["item_id"]): d["status"] for d in _load(rep / f"{fam}_coverage.jsonl")}
    out["coverage_status"] = _block([(ca[k], cb[k]) for k in sorted(set(ca) & set(cb))])
    aa = {(d["pair_id"], d["claim_id"]): d for d in _load(prim / f"{fam}_align.jsonl")}
    ab = {(d["pair_id"], d["claim_id"]): d for d in _load(rep / f"{fam}_align.jsonl")}
    ks = sorted(set(aa) & set(ab))
    out["alignment_relation"] = _block([(aa[k]["relation"], ab[k]["relation"]) for k in ks])
    out["alignment_full"] = _block([((aa[k]["relation"], aa[k]["direction"], tuple(sorted(aa[k]["matched_y"]))),
                                     (ab[k]["relation"], ab[k]["direction"], tuple(sorted(ab[k]["matched_y"])))) for k in ks])
    out["alignment_full"].pop("changes")  # tuples are not informative as strings
    return out


def consensus_changes(fam: str, replicate: str, ext: Path = EXT) -> dict[str, Any]:
    """How many final consensus decisions differ when the replicate adjudication is used instead."""
    pc, rc = ext / "consensus", ext / "replicates" / replicate / "consensus"
    a = {r["claim_id"]: r for r in _load(pc / f"{fam}_claims.jsonl")}
    b = {r["claim_id"]: r for r in _load(rc / f"{fam}_claims.jsonl")}
    ks = sorted(set(a) & set(b))
    lab = Counter(f"{a[k]['final_label']}->{b[k]['final_label']}" for k in ks if a[k]["final_label"] != b[k]["final_label"])
    num = Counter(f"{x['verdict']}->{y['verdict']}" for k in ks for x, y in zip(a[k]["numbers"], b[k]["numbers"])
                  if x["verdict"] != y["verdict"])
    res: dict[str, Any] = {"claims": len(ks), "final_label_changed": sum(lab.values()), "final_label_changes": dict(lab),
                           "number_verdicts_changed": sum(num.values()), "number_verdict_changes": dict(num),
                           "factual_error_changed": sum(1 for k in ks if a[k]["factual_error"] != b[k]["factual_error"])}
    ca = {(r["text_id"], r["item_id"]): r["status"] for r in _load(pc / f"{fam}_coverage.jsonl")}
    cb = {(r["text_id"], r["item_id"]): r["status"] for r in _load(rc / f"{fam}_coverage.jsonl")}
    if ca:
        res["coverage_items"] = len(ca)
        res["coverage_changed"] = sum(1 for k in ca if k in cb and ca[k] != cb[k])
    return res


CLAIM_KEYS = ("support_rate", "factual_error_rate", "fully_supported", "numeric_precision", "numeric_recall")
COMPLETENESS_KEYS = ("finding_recall", "negative_finding_recall", "core_finding_recall")


def _ci(d: dict[str, Any]) -> dict[str, Any]:
    keys = ("diff", "ci_low", "ci_high", "n", "degenerate")
    return {k: d.get(k) for k in keys}


def _excludes_zero(d: dict[str, Any]) -> Optional[bool]:
    if d.get("diff") is None:
        return None
    return bool(d["ci_low"] > 0 or d["ci_high"] < 0)


def contrast_sensitivity(primary: dict[str, Any], replicate: dict[str, Any]) -> list[dict[str, Any]]:
    """Every planned contrast, scored from the primary and from the replicate consensus."""
    rows = []

    def add(metric: str, name: str, p: dict[str, Any], r: dict[str, Any]) -> None:
        if p.get("diff") is None and r.get("diff") is None:
            return
        same_sign = None
        if p.get("diff") is not None and r.get("diff") is not None:
            same_sign = (p["diff"] > 1e-12) == (r["diff"] > 1e-12) and (p["diff"] < -1e-12) == (r["diff"] < -1e-12)
        rows.append({"contrast": name, "metric": metric, "primary": _ci(p), "replicate": _ci(r),
                     "shift": None if p.get("diff") is None or r.get("diff") is None else r["diff"] - p["diff"],
                     "same_sign": same_sign, "primary_excludes_zero": _excludes_zero(p),
                     "replicate_excludes_zero": _excludes_zero(r)})

    for name, comp in primary["claims"]["comparisons"].items():
        for k in CLAIM_KEYS:
            add(k, name, comp[k], replicate["claims"]["comparisons"][name][k])
    if "metric_a" in primary:
        for name, comp in primary["metric_a"]["comparisons"].items():
            add("complete_correct_atomic", name, comp["complete_correct_atomic"],
                replicate["metric_a"]["comparisons"][name]["complete_correct_atomic"])
    if "completeness" in primary:
        for name, comp in primary["completeness"]["comparisons"].items():
            for k in COMPLETENESS_KEYS:
                add(k, name, comp[k], replicate["completeness"]["comparisons"][name][k])
    return rows


def edit_sensitivity(primary: dict[str, Any], replicate: dict[str, Any]) -> dict[str, Any]:
    keys = ("repair_recall", "edit_precision", "harmful_edit_rate", "initial_errors", "new_errors")
    return {c: {k: {"primary": primary["edits"]["summary"][c].get(k), "replicate": replicate["edits"]["summary"][c].get(k)}
                for k in keys} for c in primary["edits"]["summary"]}


def run(replicate: str) -> dict[str, Any]:
    from evaluation.extended_metrics import score_family
    report: dict[str, Any] = {
        "replicate": replicate,
        "provenance": "Primary vs replicate adjudication by the same AI adjudicator (GPT-5.6 via Codex CLI) on verbatim "
                      "identical prompts; AI-AI test-retest, not human reliability. Exploratory.",
        "families": {}}
    for fam in FAMS:
        prim = score_family(fam, write=False)
        rep = score_family(fam, consensus_dir=EXT / "replicates" / replicate / "consensus", write=False)
        rows = contrast_sensitivity(prim, rep)
        report["families"][fam] = {
            "test_retest": test_retest(fam, replicate), "consensus_changes": consensus_changes(fam, replicate),
            "contrasts": rows, "edits": edit_sensitivity(prim, rep),
            "contrast_summary": {"n": len(rows), "sign_changes": sum(1 for r in rows if r["same_sign"] is False),
                                 "zero_exclusion_changes": sum(1 for r in rows if r["primary_excludes_zero"] != r["replicate_excludes_zero"]),
                                 "max_abs_shift": max((abs(r["shift"]) for r in rows if r["shift"] is not None), default=None)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "adjudicator_stability.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    (OUT / "tables" / "adjudicator_stability.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def _f(x: Optional[float], nd: int = 3) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _ci_s(d: dict[str, Any]) -> str:
    if d.get("diff") is None:
        return "undefined"
    return f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"


def render_markdown(report: dict[str, Any]) -> str:
    L = [f"# Adjudicator test–retest (replicate {report['replicate']})", "",
         report["provenance"], "", "## Agreement between the two adjudications of the same disputed items", "",
         "| Set | Field | Items | Same decision | Raw agreement | Cohen's κ | Changed decisions |", "|---|---|---|---|---|---|---|"]
    names = {"label": "claim label", "entailment": "entailment", "extraction_valid": "extraction validity",
             "number_mapping_choice": "number mapping (judge A / B / own)", "coverage_status": "finding coverage",
             "alignment_relation": "alignment relation"}
    for fam, r in report["families"].items():
        for k, nm in names.items():
            b = r["test_retest"][k]
            if not b["n"]:
                continue
            ch = ", ".join(f"{a} ×{n}" for a, n in sorted(b["changes"].items(), key=lambda x: -x[1])) or "—"
            L.append(f"| {fam} | {nm} | {b['n']} | {b['agree']} | {_f(b['pct_agree'])} | {_f(b['cohen_kappa'])} | {ch} |")
    L += ["", "## Effect on the final consensus", "",
          "| Set | Claims | Final labels changed | Factual-error flags changed | Numeric verdicts changed | Coverage items changed |",
          "|---|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        c = r["consensus_changes"]
        cov = f"{c['coverage_changed']} of {c['coverage_items']}" if "coverage_items" in c else "—"
        L.append(f"| {fam} | {c['claims']} | {c['final_label_changed']} | {c['factual_error_changed']} | "
                 f"{c['number_verdicts_changed']} | {cov} |")
    L += ["", "## Planned contrasts re-scored from the replicate consensus", "",
          "| Set | Contrast | Metric | Primary | Replicate | Sign kept | Zero-exclusion kept |", "|---|---|---|---|---|---|---|"]
    for fam, r in report["families"].items():
        for row in r["contrasts"]:
            if row["primary"].get("degenerate") and row["replicate"].get("degenerate"):
                continue
            L.append(f"| {fam} | {row['contrast'].replace('_vs_', ' − ')} | {row['metric']} | {_ci_s(row['primary'])} | "
                     f"{_ci_s(row['replicate'])} | {'yes' if row['same_sign'] else 'no'} | "
                     f"{'yes' if row['primary_excludes_zero'] == row['replicate_excludes_zero'] else 'no'} |")
        s = r["contrast_summary"]
        L.append(f"| {fam} | **all {s['n']} contrasts** | | | | sign changes: {s['sign_changes']} | "
                 f"zero-exclusion changes: {s['zero_exclusion_changes']}; max shift {_f(s['max_abs_shift'])} |")
    L += ["", "Rows where both versions are degenerate (identical labels in every paired unit) are omitted.", ""]
    return "\n".join(L)
