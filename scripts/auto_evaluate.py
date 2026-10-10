"""Automatic (non-human) evaluation of a completed run family.

  python scripts/auto_evaluate.py --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 \
      --cases data/synthetic/test.jsonl --gold private/gold/test_gold.jsonl --out results/automatic/synthetic_test

Writes (public, aggregate only): summary_by_condition.csv, comparisons.json, trajectories.json, figures/*.png.
Per-case rows that contain TEST gold levels are written ONLY to private/auto_eval/ (gitignored) so the
public repo does not reveal TEST gold before annotation. Every PROXY column is labelled UNVALIDATED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from evaluation.auto_metrics import load_gold, load_runs, run_row, trajectories  # noqa: E402
from evaluation.paired_bootstrap import cluster_bootstrap, paired_bootstrap  # noqa: E402
from src.conditions import ALL_CONDITIONS  # noqa: E402
from src.runner import load_cases  # noqa: E402

COMPARISONS = {"H1_C4_vs_C2": ("C4", "C2"), "H1_C4_vs_C1": ("C4", "C1"), "C6_vs_C2_same_draft": ("C6", "C2"),
               "H2_C4_vs_C5": ("C4", "C5"), "H3_C4_vs_C3": ("C4", "C3"), "verification_C4_vs_C7": ("C4", "C7"),
               "outline_C4_vs_C6": ("C4", "C6")}
AUTO_METRICS = ["cost_usd", "n_model_calls", "n_tool_calls", "latency_s", "n_ungrounded_numbers", "n_words",
                "changed_from_start"]
PROXY_METRICS = ["proxy_correct_UNVALIDATED", "proxy_over_UNVALIDATED", "proxy_under_UNVALIDATED"]


def figures(df: pd.DataFrame, traj: dict, out: Path, title_suffix: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.mkdir(parents=True, exist_ok=True)
    conds = [c for c in ALL_CONDITIONS if c in set(df.condition)]
    g = df.groupby("condition")
    # 1 cost vs calls
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    ax[0].bar(conds, [g.get_group(c).cost_usd.mean() * 1000 for c in conds], color="#4c72b0")
    ax[0].set_ylabel("mean cost per case (USD × 10⁻³)")
    ax[0].set_title("Actual billed cost (provider-reported)")
    ax[1].bar(conds, [g.get_group(c).n_model_calls.mean() for c in conds], color="#8172b2", label="model calls")
    ax[1].bar(conds, [g.get_group(c).n_tool_calls.mean() for c in conds], color="#ccb974", alpha=.8, label="tool calls")
    ax[1].set_title("Mean calls per case")
    ax[1].legend(frameon=False)
    fig.suptitle(title_suffix, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "cost_and_calls_by_condition.png", dpi=200)
    plt.close(fig)
    # 2 verifier decisions
    vc = [c for c in conds if c in traj]
    if vc:
        fig, ax = plt.subplots(figsize=(6, 3.2))
        bottom = [0] * len(vc)
        for d, col in (("ACCEPT", "#8c8c8c"), ("WEAKEN", "#dd8452"), ("STRENGTHEN", "#55a868"), ("REMOVE", "#c44e52"), ("FLAG", "#937860")):
            vals = [traj[c]["decisions"].get(d, 0) / max(1, traj[c]["n_claims"]) for c in vc]
            ax.bar(vc, vals, bottom=bottom, label=d, color=col)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_ylabel("share of verified claims")
        ax.set_title("Verifier decisions per claim " + title_suffix, fontsize=9)
        ax.legend(frameon=False, fontsize=7, ncol=5, loc="lower center", bbox_to_anchor=(.5, -.35))
        fig.tight_layout()
        fig.savefig(out / "verifier_decisions.png", dpi=200)
        plt.close(fig)
        # 3 tool usage
        tools = ["lookup_table", "compare_numbers", "get_test_metadata", "retrieve_passage"]
        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        w = 0.8 / len(tools)
        for i, t in enumerate(tools):
            vals = [g.get_group(c)[f"tool_{t}"].sum() / max(1, traj[c]["n_claims"]) for c in vc]
            ax.bar([j + i * w for j in range(len(vc))], vals, width=w, label=t)
        ax.set_xticks([j + 0.4 - w / 2 for j in range(len(vc))], vc)
        ax.set_ylabel("tool calls per claim")
        ax.set_title("Evidence-tool usage (C3 fixed order vs adaptive) " + title_suffix, fontsize=9)
        ax.legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(out / "tool_usage.png", dpi=200)
        plt.close(fig)
    # 4 PROXY outcomes (explicitly labelled)
    o = df[df.proxy_level_UNVALIDATED.notna()]
    if len(o):
        fig, ax = plt.subplots(figsize=(6.5, 3.3))
        go = o.groupby("condition")
        bottom = [0] * len(conds)
        for key, lab, col in (("proxy_correct_UNVALIDATED", "match", "#4c72b0"), ("proxy_over_UNVALIDATED", "proxy > gold", "#dd8452"),
                              ("proxy_under_UNVALIDATED", "proxy < gold", "#55a868")):
            vals = [go.get_group(c)[key].mean() if c in go.groups else 0 for c in conds]
            ax.bar(conds, vals, bottom=bottom, label=lab, color=col)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_title(f"PROXY ONLY — lexical strength heuristic vs gold (UNVALIDATED, n={go.size().iloc[0]}/cond)\n"
                     "not human-scored; do not report as calibration accuracy", fontsize=8)
        ax.legend(frameon=False, fontsize=7, ncol=3)
        fig.tight_layout()
        fig.savefig(out / "PROXY_UNVALIDATED_strength_vs_gold.png", dpi=200)
        plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--gold", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--conditions", default="all")
    ap.add_argument("--private-out", default=str(ROOT / "private" / "auto_eval"))
    a = ap.parse_args()
    conds = list(ALL_CONDITIONS) if a.conditions == "all" else a.conditions.split(",")
    cases = {c.case_id: c for c in load_cases(ROOT / a.cases)}
    gold = load_gold([ROOT / g for g in a.gold])
    runs = [r for r in load_runs(ROOT / a.runs, conds) if r["case_id"] in cases]
    if any(r.get("is_mock") for r in runs):
        raise SystemExit("refusing to evaluate MOCK outputs as real results")
    df = pd.DataFrame([run_row(r, cases[r["case_id"]], gold.get(r["case_id"])) for r in runs])
    if "proxy_level_UNVALIDATED" in df:
        m = df.proxy_level_UNVALIDATED.notna()
        df.loc[m, "proxy_correct_UNVALIDATED"] = (df.loc[m, "proxy_level_UNVALIDATED"] == df.loc[m, "gold_level"]).astype(float)
        df.loc[m, "proxy_over_UNVALIDATED"] = (df.loc[m, "proxy_level_UNVALIDATED"] > df.loc[m, "gold_level"]).astype(float)
        df.loc[m, "proxy_under_UNVALIDATED"] = (df.loc[m, "proxy_level_UNVALIDATED"] < df.loc[m, "gold_level"]).astype(float)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    priv = Path(a.private_out)
    priv.mkdir(parents=True, exist_ok=True)
    df.to_csv(priv / f"per_run_rows_{out.name}.csv", index=False)  # contains gold levels -> private
    public_cols = [c for c in df.columns if c not in ("gold_level",) and "proxy_level" not in c and "proxy_start" not in c]
    df[public_cols].drop(columns=[c for c in public_cols if c.startswith("proxy_")], errors="ignore").to_csv(out / "per_run_rows_no_gold.csv", index=False)
    agg = {
        "n_runs": ("case_id", "count"), "n_completed": ("status", lambda s: int((s == "completed").sum())),
        "n_failed": ("status", lambda s: int((s != "completed").sum())),
        "mean_cost_usd": ("cost_usd", "mean"), "total_cost_usd": ("cost_usd", "sum"),
        "mean_model_calls": ("n_model_calls", "mean"), "mean_tool_calls": ("n_tool_calls", "mean"),
        "mean_latency_s": ("latency_s", "mean"), "mean_words": ("n_words", "mean"),
        "share_changed_from_start": ("changed_from_start", "mean"), "numbers_total": ("n_numbers", "sum"),
        "ungrounded_numbers_total": ("n_ungrounded_numbers", "sum"),
        "weaken": ("dec_WEAKEN", "sum"), "strengthen": ("dec_STRENGTHEN", "sum"), "remove": ("dec_REMOVE", "sum"),
        "flag": ("dec_FLAG", "sum"), "accept": ("dec_ACCEPT", "sum"), "invalid_decisions": ("n_invalid_decisions", "sum"),
        "protocol_errors": ("n_protocol_errors", "sum"), "ignored_parallel_calls": ("n_ignored_parallel_calls", "sum"),
    }
    if "num_value_recall" in df:
        agg["NUM_value_recall_rule"] = ("num_value_recall", "mean")
    for k in PROXY_METRICS + ["neg_proxy_recall_UNVALIDATED"]:
        if k in df:
            agg[k] = (k, "mean")
    summ = df.groupby("condition").agg(**agg).reindex([c for c in conds if c in set(df.condition)])
    summ.to_csv(out / "summary_by_condition.csv")
    comps = {}
    pairs = {cid: rec.pair_id for cid, rec in cases.items()}
    for name, (x, y) in COMPARISONS.items():
        if x not in set(df.condition) or y not in set(df.condition):
            continue
        res = {}
        for met in AUTO_METRICS + [m for m in PROXY_METRICS if m in df] + (["num_value_recall"] if "num_value_recall" in df else []):
            dx = {r.case_id: (float(r[met]) if pd.notna(r[met]) else None) for _, r in df[df.condition == x].iterrows()}
            dy = {r.case_id: (float(r[met]) if pd.notna(r[met]) else None) for _, r in df[df.condition == y].iterrows()}
            res[met] = {"case_bootstrap": paired_bootstrap(dx, dy), "matched_pair_bootstrap": cluster_bootstrap(dx, dy, pairs)}
        comps[name] = res
    (out / "comparisons.json").write_text(json.dumps(comps, indent=1))
    traj = trajectories(runs)
    (out / "trajectories.json").write_text(json.dumps(traj, indent=1))
    figures(df, traj, out / "figures", f"[{out.name}]")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 40)
    print(summ.round(4).T)
    return 0


if __name__ == "__main__":
    sys.exit(main())
