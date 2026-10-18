"""Final HUMAN-scored analysis (run only after real consensus annotations exist).

  python -m evaluation.score_human --consensus annotation/agreement/consensus_synthetic.csv \
      --mapping private/condition_mapping.csv --gold private/gold/test_gold.jsonl \
      --rubric data/synthetic/rubrics/test_rubric.jsonl \
      --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 --out results/human_scored

Pre-registered definitions (see docs/PROTOCOL_FREEZE.md):
  eligible ordinal cases: 6 categories x 4 TEST cases = 24 (strong stratum N=12, non-strong N=12)
  calibration_accuracy = mean(l_hat == l); overstatement = mean(l_hat > l); understatement = mean(l_hat < l)
  omission: focal_addressed == no  ->  l_hat = 0 (also reported as a separate omission rate)
  coverage = correctly reported required findings / total required findings (all 32 TEST cases)
  ITT: a failed/missing run counts as an output with no claims (l_hat = 0, nothing covered); a
       completed-only sensitivity analysis is also reported.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation.blinding import read_csv
from evaluation.merge_annotations import _ids
from evaluation.paired_bootstrap import cluster_bootstrap, paired_bootstrap
from src.package_schema import ORDINAL_CATEGORIES

CONDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
TRANSITIONS = [("C4", "C7"), ("C5", "C7"), ("C3", "C7"), ("C2", "C1"), ("C6", "C1")]
COMPARISONS = {
    "H1_C4_vs_C2": ("C4", "C2"), "H1_C4_vs_C1": ("C4", "C1"), "H1_C6_vs_C2_same_draft": ("C6", "C2"),
    "H2_C4_vs_C5": ("C4", "C5"), "H3_C4_vs_C3": ("C4", "C3"), "verification_C4_vs_C7": ("C4", "C7"),
    "outline_C4_vs_C6": ("C4", "C6"),
}


def load_jsonl(p: Path) -> dict[str, dict[str, Any]]:
    return {json.loads(l)["case_id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}


def transition(before: int, after: int, gold: int) -> str:
    def st(x):
        return "correct" if x == gold else ("over" if x > gold else "under")

    b, a = st(before), st(after)
    if b == a == "correct":
        return "correct->correct"
    if b != "correct" and a == "correct":
        return f"{b}->correct (fix)"
    if b == "correct":
        return f"correct->{a} (harmful)"
    return f"{b}->{a} ({'unchanged' if before == after else 'changed'})"


def score(consensus: list[dict[str, str]], mapping: list[dict[str, str]], gold: dict[str, dict[str, Any]],
          rubric: dict[str, dict[str, Any]], runs_dir: Optional[Path] = None, itt: bool = True) -> dict[str, Any]:
    lab = {r["output_id"]: r for r in consensus}
    completed_ids = {m["output_id"] for m in mapping if m["status"] == "completed" and m["output_id"]}
    missing = sorted(completed_ids - set(lab))
    if missing:
        raise ValueError(f"{len(missing)} completed outputs have no consensus label (e.g. {missing[:3]}); refusing to "
                         f"score (a stale mapping or an incomplete consensus would silently bias results)")
    for oid in completed_ids:
        lv = (lab[oid].get("expressed_level") or "").strip()
        if lv not in ("", "0", "1", "2"):
            raise ValueError(f"invalid consensus expressed_level {lv!r} for {oid}")
    cell: dict[tuple[str, str], Optional[dict[str, str]]] = {}
    for m in mapping:
        key = (m["case_id"], m["condition"])
        cell[key] = lab.get(m["output_id"]) if m["status"] == "completed" and m["output_id"] else None
    cases = sorted(gold)
    conds = sorted({c for _, c in cell}, key=CONDS.index)
    per_case: dict[str, dict[str, dict[str, Any]]] = {c: {} for c in conds}
    for case in cases:
        g = gold[case]
        rub = rubric.get(case, {})
        req = [f["finding_id"] for f in rub.get("required_findings", [])]
        negs = [f["finding_id"] for f in g.get("required_findings", []) if f.get("polarity") in ("negative", "null", "mixed")]
        facts = [n["fact_id"] for n in rub.get("numeric_facts", [])]
        for c in conds:
            row = cell.get((case, c))
            if row is None and not itt:
                continue
            missing = row is None
            row = row or {}
            d: dict[str, Any] = {"missing_output": missing}
            if g["category"] in ORDINAL_CATEGORIES:
                if not missing and (row.get("expressed_level") or "") == "" and (row.get("focal_addressed") or "no") == "yes":
                    raise ValueError(f"ordinal case {case}/{c}: expressed_level blank although focal_addressed=yes")
                hat = int(row.get("expressed_level") or 0)
                if (row.get("focal_addressed") or "no") == "no":
                    hat = 0
                abs_error = abs(hat - g["gold_level"])
                d.update(gold=g["gold_level"], hat=hat, correct=int(hat == g["gold_level"]), over=int(hat > g["gold_level"]),
                         under=int(hat < g["gold_level"]), omitted=int((row.get("focal_addressed") or "no") == "no"),
                         abs_error=abs_error, severe_error=int(abs_error == 2))
            cov = _ids(row.get("findings_covered"))
            d["coverage"] = (len(cov & set(req)) / len(req)) if req else None
            d["n_req"], d["n_covered"] = len(req), len(cov & set(req))
            d["unsupported"] = int(row.get("unsupported_claims") or 0)
            d["numeric_errors"] = int(row.get("numeric_errors") or 0)
            if g["category"] == "numerical_reporting":
                d["num_fact_acc"] = len(_ids(row.get("num_facts_correct")) & set(facts)) / len(facts) if facts else None
            if g["category"] == "negative_results":
                d["neg_recall"] = len(_ids(row.get("neg_findings_reported")) & set(negs)) / len(negs) if negs else None
                d["neg_reframed"] = int((row.get("neg_reframed_positive") or "no") == "yes")
            d["category"], d["pair_id"] = g["category"], case[:-1]
            per_case[c][case] = d

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return (sum(vals) / len(vals)) if vals else None

    summary: dict[str, Any] = {}
    for c in conds:
        pc = per_case[c]
        ordv = [d for d in pc.values() if "hat" in d]
        strong = [d for d in ordv if d["gold"] == 2]
        weak = [d for d in ordv if d["gold"] != 2]
        per_level = {}
        for level in range(3):
            tp = sum(d["gold"] == level and d["hat"] == level for d in ordv)
            fp = sum(d["gold"] != level and d["hat"] == level for d in ordv)
            fn = sum(d["gold"] == level and d["hat"] != level for d in ordv)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            per_level[str(level)] = {"support": sum(d["gold"] == level for d in ordv), "precision": precision,
                                     "recall": recall, "f1": f1}
        summary[c] = {
            "n_ordinal": len(ordv),
            "calibration_accuracy": mean([d["correct"] for d in ordv]),
            "macro_f1": mean([v["f1"] for v in per_level.values()]),
            "ordinal_mae": mean([d["abs_error"] for d in ordv]),
            "severe_error_rate": mean([d["severe_error"] for d in ordv]),
            "per_level": per_level,
            "overstatement_rate": mean([d["over"] for d in ordv]),
            "understatement_rate": mean([d["under"] for d in ordv]),
            "omission_rate": mean([d["omitted"] for d in ordv]),
            "strong_n": len(strong), "strong_understatement": mean([d["under"] for d in strong]),
            "strong_accuracy": mean([d["correct"] for d in strong]),
            "nonstrong_n": len(weak), "nonstrong_overstatement": mean([d["over"] for d in weak]),
            "nonstrong_accuracy": mean([d["correct"] for d in weak]),
            "coverage_case_mean": mean([d["coverage"] for d in pc.values()]),
            "coverage_pooled": (sum(d["n_covered"] for d in pc.values()) / max(1, sum(d["n_req"] for d in pc.values()))),
            "unsupported_mean": mean([d["unsupported"] for d in pc.values()]),
            "pct_outputs_with_unsupported": mean([int(d["unsupported"] > 0) for d in pc.values()]),
            "numeric_errors_mean": mean([d["numeric_errors"] for d in pc.values()]),
            "num_fact_accuracy": mean([d.get("num_fact_acc") for d in pc.values()]),
            "neg_recall": mean([d.get("neg_recall") for d in pc.values()]),
            "neg_reframed_rate": mean([d.get("neg_reframed") for d in pc.values() if "neg_reframed" in d]),
            "n_missing_outputs": sum(1 for d in pc.values() if d["missing_output"]),
            "confusion_gold_rows_hat_cols": [[sum(1 for d in ordv if d["gold"] == i and d["hat"] == j) for j in range(3)] for i in range(3)],
        }
    trans: dict[str, dict[str, int]] = {}
    for after, before in TRANSITIONS:
        if after in per_case and before in per_case:
            cnt = Counter()
            for case, d in per_case[after].items():
                b = per_case[before].get(case)
                if "hat" in d and b and "hat" in b:
                    cnt[transition(b["hat"], d["hat"], d["gold"])] += 1
            trans[f"{before}->{after}"] = dict(cnt)
    comps: dict[str, Any] = {}
    clusters = {case: case[:-1] for case in cases}
    for name, (x, y) in COMPARISONS.items():
        if x not in per_case or y not in per_case:
            continue
        res = {}
        for metric, subset in (("correct", None), ("abs_error", None), ("severe_error", None),
                               ("over", None), ("under", None), ("coverage", None),
                               ("under", "strong"), ("over", "nonstrong"), ("unsupported", None),
                               ("numeric_errors", None), ("num_fact_acc", None),
                               ("neg_recall", None), ("neg_reframed", None)):
            def vals(cond):
                out = {}
                for case, d in per_case[cond].items():
                    if metric not in d:
                        continue
                    if subset == "strong" and d.get("gold") != 2:
                        continue
                    if subset == "nonstrong" and d.get("gold") == 2:
                        continue
                    out[case] = d[metric]
                return out
            key = metric + (f"_{subset}" if subset else "")
            res[key] = {"case_bootstrap": paired_bootstrap(vals(x), vals(y)),
                        "matched_pair_bootstrap": cluster_bootstrap(vals(x), vals(y), clusters)}
        comps[name] = res
    costs = {}
    if runs_dir is not None:
        for c in conds:
            tot = []
            for p in sorted((runs_dir / c).glob("*.json")):
                rr = json.loads(p.read_text())
                if rr["case_id"] in gold:
                    tot.append(rr.get("totals", {}))
            if tot:
                costs[c] = {k: mean([t.get(k) for t in tot]) for k in ("cost_usd", "n_model_calls", "n_tool_calls", "latency_s",
                                                                       "prompt_tokens", "completion_tokens")}
    return {"policy": "ITT" if itt else "completed_only", "summary": summary, "transitions": trans,
            "comparisons": comps, "costs_mean_per_case": costs, "per_case": per_case}


def plots(res: dict[str, Any], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = res["summary"]
    conds = list(s)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    bottoms = [0.0] * len(conds)
    for key, lab, col in (("calibration_accuracy", "correct", "#4c72b0"), ("overstatement_rate", "over", "#dd8452"),
                          ("understatement_rate", "under", "#55a868")):
        vals = [s[c][key] or 0 for c in conds]
        ax.bar(conds, vals, bottom=bottoms, label=lab, color=col)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_ylabel("share of ordinal TEST cases (N=24)")
    ax.set_title("HUMAN-scored focal-claim outcomes by condition")
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(out / "human_outcomes_by_condition.png", dpi=200)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", required=True)
    ap.add_argument("--mapping", default="private/condition_mapping.csv")
    ap.add_argument("--gold", default="private/gold/test_gold.jsonl")
    ap.add_argument("--rubric", default="data/synthetic/rubrics/test_rubric.jsonl")
    ap.add_argument("--runs", default=None)
    ap.add_argument("--out", default="results/human_scored")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cons, mapping = read_csv(Path(a.consensus)), read_csv(Path(a.mapping))
    gold, rubric = load_jsonl(Path(a.gold)), load_jsonl(Path(a.rubric))
    if not cons:
        print("consensus file is empty")
        return 1
    for itt in (True, False):
        res = score(cons, mapping, gold, rubric, Path(a.runs) if a.runs else None, itt=itt)
        (out / f"human_results_{res['policy']}.json").write_text(json.dumps(res, indent=1))
        if itt:
            plots(res, out)
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
