"""Render aggregate automatic results as markdown tables (no hand transcription of numbers).

  python scripts/make_result_tables.py results/automatic/synthetic_test [more result dirs...]
Writes <dir>/TABLES.md for each directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROWS = [("n_completed", "completed runs", "{:.0f}"), ("n_failed", "failed runs", "{:.0f}"),
        ("mean_cost_usd", "mean cost / case (USD)", "{:.5f}"), ("mean_model_calls", "model calls / case", "{:.2f}"),
        ("mean_tool_calls", "evidence-tool calls / case", "{:.2f}"), ("mean_latency_s", "summed call latency / case (s)", "{:.1f}"),
        ("mean_words", "words in final passage", "{:.1f}"), ("share_changed_from_start", "share of passages changed from starting draft", "{:.3f}"),
        ("weaken", "WEAKEN decisions", "{:.0f}"), ("strengthen", "STRENGTHEN decisions", "{:.0f}"), ("remove", "REMOVE decisions", "{:.0f}"),
        ("flag", "FLAG decisions", "{:.0f}"), ("accept", "ACCEPT decisions", "{:.0f}"), ("invalid_decisions", "invalid decisions (fallback)", "{:.0f}"),
        ("protocol_errors", "protocol errors", "{:.0f}"), ("ignored_parallel_calls", "parallel tool calls not executed", "{:.0f}"),
        ("numbers_total", "numbers in final passages", "{:.0f}"), ("ungrounded_numbers_total", "numbers not derivable from package (rule)", "{:.0f}"),
        ("NUM_value_recall_rule", "NUM cases: share of gold numeric values present (rule)", "{:.3f}"),
        ("proxy_correct_UNVALIDATED", "PROXY lexical level = gold (UNVALIDATED)", "{:.3f}"),
        ("proxy_over_UNVALIDATED", "PROXY lexical level > gold (UNVALIDATED)", "{:.3f}"),
        ("proxy_under_UNVALIDATED", "PROXY lexical level < gold (UNVALIDATED)", "{:.3f}"),
        ("neg_proxy_recall_UNVALIDATED", "PROXY NEG-finding mention rate (UNVALIDATED)", "{:.3f}")]


def render(d: Path) -> str:
    s = pd.read_csv(d / "summary_by_condition.csv", index_col=0)
    conds = list(s.index)
    out = [f"### {d.name}: per-condition summary", "", "| metric | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
    for key, label, fmt in ROWS:
        if key in s.columns:
            out.append(f"| {label} | " + " | ".join("—" if pd.isna(s.loc[c, key]) else fmt.format(s.loc[c, key]) for c in conds) + " |")
    comp = d / "comparisons.json"
    if comp.exists():
        c = json.loads(comp.read_text())
        out += ["", f"### {d.name}: paired differences (first minus second condition), case-level bootstrap 95% CI "
                f"[matched-pair bootstrap CI]", "", "| comparison | metric | n | diff | 95% CI | pair-level CI |", "|---|---|---|---|---|---|"]
        for name, res in c.items():
            for met in ("cost_usd", "n_tool_calls", "n_model_calls", "latency_s", "changed_from_start", "num_value_recall",
                        "proxy_correct_UNVALIDATED", "proxy_over_UNVALIDATED", "proxy_under_UNVALIDATED"):
                if met in res and res[met]["case_bootstrap"]["n"]:
                    b, m = res[met]["case_bootstrap"], res[met]["matched_pair_bootstrap"]
                    out.append(f"| {name} | {met} | {b['n']} | {b['diff']:+.4f} | [{b['ci_low']:+.4f}, {b['ci_high']:+.4f}] | "
                               f"[{m['ci_low']:+.4f}, {m['ci_high']:+.4f}] |")
    tj = d / "trajectories.json"
    if tj.exists():
        t = json.loads(tj.read_text())
        out += ["", f"### {d.name}: verifier tool trajectories", "", "| condition | claims | tools / claim | tools-per-claim distribution | first tool | most common sequences |",
                "|---|---|---|---|---|---|"]
        for cond, v in t.items():
            seqs = "; ".join(f"{s} ({n})" for s, n in v["top_sequences"][:3])
            out.append(f"| {cond} | {v['n_claims']} | {v['mean_tools_per_claim']:.2f} | {v['dist_tools_per_claim']} | {v['first_tool']} | {seqs} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        d = Path(arg)
        (d / "TABLES.md").write_text(render(d))
        print("wrote", d / "TABLES.md")
