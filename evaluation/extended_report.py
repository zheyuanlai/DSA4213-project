"""Tables and figures for the evaluation extension (results/ai_extended/{tables,figures}).

Every number comes from results/ai_extended/<family>/results.json; nothing is typed by hand. Figures mark
AI-judged quantities and deterministic quantities in their titles and state sample sizes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from evaluation.extended_data import ROOT

OUT = ROOT / "results" / "ai_extended"
FAMS = ("synthetic", "real", "diagnostic")
COND_ORDER = ["C1", "C2", "C6", "C7", "C3", "C4", "C5", "DRAFT"]
# reference categorical palette (validated: adjacent CVD dE >= 9.1, normal-vision >= 19.6 on light surface)
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FAM_LABEL = {"synthetic": "Synthetic TEST (32 cases)", "real": "Real papers (12; C3/C4 11)",
             "diagnostic": "Long diagnostic (8 cases)"}


def load(fam: str) -> dict[str, Any]:
    return json.loads((OUT / fam / "results.json").read_text())


def f3(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.3f}"


def ci(d: dict[str, Any]) -> str:
    if d.get("diff") is None:
        return "undefined"
    s = f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"
    if d.get("degenerate"):
        s += " (degenerate)"
    return s


def disc(d: dict[str, Any]) -> str:
    if not d.get("n"):
        return "—"
    return f"{d['n']} ({d.get('n_a_better', 0)}/{d.get('n_b_better', 0)}/{d.get('n_tied', 0)})"


def _conds(d: dict[str, Any]) -> list[str]:
    return sorted(d, key=lambda c: COND_ORDER.index(c) if c in COND_ORDER else 99)


# ----------------------------------------------------------------------------- tables
def table_metric_a(r: dict[str, Any]) -> str:
    a = r["metric_a"]
    keys = [("complete_correct", "complete & correct"), ("focal_correct", "focal exact (n=24)"),
            ("all_findings_covered", "all findings covered"), ("no_unsupported", "no unsupported claim"),
            ("no_numeric_error", "no numeric error"), ("num_facts_all_correct", "NUM all facts (n=4)"),
            ("neg_findings_all_reported", "NEG all reported (n=4)"), ("no_positive_reframing", "NEG no reframing (n=4)"),
            ("complete_correct_atomic", "complete & correct (atomic variant)")]
    lines = ["| condition | " + " | ".join(k[1] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for c in _conds(a["summary"]["ITT"]):
        s = a["summary"]["ITT"][c]
        lines.append(f"| {c} | " + " | ".join(f3(s.get(k)) for k, _ in keys) + " |")
    lines += ["", "Paired differences (first minus second), case bootstrap 95% CI; n (a better / b better / tied); "
              "matched-pair cluster CI as sensitivity.", "",
              "| comparison | complete & correct | n | matched-pair CI | atomic variant |", "|---|---|---|---|---|"]
    for name, comp in a["comparisons"].items():
        b = comp["complete_correct"]
        mp = b.get("matched_pair", {})
        lines.append(f"| {name.replace('_vs_', ' − ')} | {ci(b)} | {disc(b)} | "
                     f"[{mp.get('ci_low', 0):+.3f}, {mp.get('ci_high', 0):+.3f}] | {ci(comp['complete_correct_atomic'])} |")
    return "\n".join(lines)


def table_claims(r: dict[str, Any]) -> str:
    s = r["claims"]["summary"]
    cols = [("support_rate", "support"), ("factual_error_rate", "factual error"), ("overstated_rate", "over"),
            ("understated_rate", "under"), ("unsupported_rate", "unsupported"), ("numeric_error_claim_rate", "numeric err"),
            ("support_rate_result_claims", "support (result claims)")]
    lines = ["| condition | texts | assessable claims | " + " | ".join(c[1] for c in cols) +
             " | fully supported passages | factually clean passages | no assessable claim |",
             "|---|---|---|" + "---|" * len(cols) + "---|---|---|"]
    for c in _conds(s):
        x = s[c]
        lines.append(f"| {c} | {x['n_texts']} | {int(x['support_rate']['denominator'])} | " +
                     " | ".join(f3(x[k]['value']) for k, _ in cols) +
                     f" | {f3(x['fully_supported'])} | {f3(x['factually_clean'])} | {f3(x['no_assessable_claims'])} |")
    lines += ["", "Claim-pooled 95% CIs (case bootstrap) for support rate: " +
              "; ".join(f"{c} [{f3(s[c]['support_rate']['ci'][0])}, {f3(s[c]['support_rate']['ci'][1])}]" for c in _conds(s))]
    return "\n".join(lines)


def table_numeric(r: dict[str, Any]) -> str:
    s = r["claims"]["summary"]
    lines = ["| condition | numeric assertions | precision [95% CI] | required facts | recall [95% CI] | F1 (secondary) | "
             "error types |", "|---|---|---|---|---|---|---|"]
    for c in _conds(s):
        x = s[c]
        p, rc = x["numeric_precision"], x["numeric_recall"]
        lines.append(f"| {c} | {int(p['denominator'])} | {f3(p['value'])} [{f3(p['ci'][0])}, {f3(p['ci'][1])}] | "
                     f"{int(rc['denominator'])} | {f3(rc['value'])} [{f3(rc['ci'][0])}, {f3(rc['ci'][1])}] | "
                     f"{f3(x['numeric_f1_secondary'])} | "
                     + ", ".join(f"{k} {v}" for k, v in sorted(x["numeric_error_types"].items())) + " |")
    return "\n".join(lines)


def table_comparisons(r: dict[str, Any], keys: list[tuple[str, str]]) -> str:
    lines = ["| comparison | " + " | ".join(k[1] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for name, comp in r["claims"]["comparisons"].items():
        star = " *" if comp.get("planned_primary") else ""
        lines.append(f"| {name.replace('_vs_', ' − ')}{star} | " + " | ".join(
            f"{ci(comp[k])}<br>n={comp[k].get('n', 0)}" for k, _ in keys) + " |")
    return "\n".join(lines)


def table_edits(r: dict[str, Any]) -> str:
    e = r["edits"]["summary"]
    cols = [("initial_errors", "initial errors"), ("corrected", "corrected"), ("removed", "removed"),
            ("retained_unedited", "left in unedited sentences"), ("retained_edited", "left after edit"),
            ("substantive_edits", "substantive edits"), ("beneficial", "beneficial"), ("harmful", "harmful"),
            ("new_errors", "new errors"), ("new_unsupported", "new unsupported"), ("numeric_fixed", "numeric fixed"),
            ("numeric_introduced", "numeric introduced"), ("findings_lost", "required findings lost")]
    rates = [("repair_recall", "repair recall"), ("edit_precision", "edit precision"),
             ("harmful_edit_rate", "harmful-edit rate"), ("unnecessary_weakening_rate", "unnecessary weakening")]
    lines = ["| system (vs its own draft) | " + " | ".join(c[1] for c in cols + rates) + " |",
             "|---|" + "---|" * (len(cols) + len(rates))]
    for c in _conds(e):
        x = e[c]
        lines.append(f"| {c} | " + " | ".join(str(x.get(k, 0)) for k, _ in cols) + " | " +
                     " | ".join("undefined" if x.get(k) is None else f"{x[k]:.3f}" for k, _ in rates) + " |")
    d = r["edits"]["decisions"]
    lines += ["", "Verifier decisions (claims): " + "; ".join(f"{c}: " + ", ".join(f"{k} {v}" for k, v in sorted(d[c].items()))
                                                              for c in _conds(d)),
              f"STRENGTHEN decisions observed: {r['edits']['strengthen_observed']}."]
    return "\n".join(lines)


def table_completeness(r: dict[str, Any]) -> str:
    c = r["completeness"]
    s = c["summary"]
    keys = [("finding_recall", "finding recall"), ("core_finding_recall", "core recall"),
            ("negative_finding_recall", "negative/null recall"), ("finding_incorrect_rate", "misreported")]
    if "gold_required_recall" in next(iter(s.values())):
        keys.insert(0, ("gold_required_recall", "gold required-finding recall"))
    lines = ["| condition | texts | " + " | ".join(k[1] for k in keys) + " | all core findings (passage) | ITT finding recall |",
             "|---|---|" + "---|" * len(keys) + "---|---|"]
    for cond in _conds(s):
        x = s[cond]
        itt = x.get("finding_recall_ITT", {}).get("value")
        lines.append(f"| {cond} | {x['n_texts']} | " + " | ".join(
            f"{f3(x[k]['value'])} [{f3(x[k]['ci'][0])}, {f3(x[k]['ci'][1])}]" for k, _ in keys) +
            f" | {f3(x['paragraph_completeness_core'])} | {f3(itt) if itt is not None else 'same'} |")
    lines += ["", "| comparison | " + " | ".join(k[1] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for name, comp in c["comparisons"].items():
        lines.append(f"| {name.replace('_vs_', ' − ')} | " + " | ".join(ci(comp[k]) + f" (n={comp[k].get('n', 0)})" for k, _ in keys) + " |")
    if "spearman_recall_readability" in c:
        lines += ["", f"Spearman ρ, per-text finding recall vs AI readability (n={len(c['readability_points'])} texts): "
                  f"{f3(c['spearman_recall_readability'])}; recall vs atomic support rate: {f3(c['spearman_recall_support'])}."]
    return "\n".join(lines)


def table_efficiency(r: dict[str, Any]) -> str:
    e = r["efficiency"]
    ret = r["retrieval"]
    lines = ["| condition | cost USD/text | latency s/text | tool calls/text | tool calls/verified claim | "
             "cost per strict-success passage | cost per fully supported passage | repairs/100 tool calls | "
             "verification opportunities | all decisive evidence retrieved | any decisive evidence retrieved |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in _conds(e):
        x, rt = e[c], ret.get(c, {})
        lines.append(f"| {c} | {x['cost_usd_per_text']:.5f} | {x['latency_s_per_text']:.1f} | {x['tool_calls_per_text']:.2f} | "
                     f"{f3(x['tool_calls_per_verified_claim'])} | {_money(x.get('cost_per_complete_correct_passage'))} | "
                     f"{_money(x.get('cost_per_fully_supported_passage'))} | {f3(x.get('repairs_per_100_tool_calls'))} | "
                     f"{rt.get('opportunities', '—')} | {f3(rt.get('share_all_decisive'))} | {f3(rt.get('share_any_decisive'))} |")
    return "\n".join(lines)


def _money(x: Optional[float]) -> str:
    return "undefined" if x is None else f"{x:.5f}"


def write_tables() -> None:
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    keys_main = [("support_rate", "support rate"), ("factual_error_rate", "factual error rate"),
                 ("overstated_rate", "overstated"), ("understated_rate", "understated"),
                 ("numeric_precision", "numeric precision"), ("numeric_recall", "numeric recall"),
                 ("fully_supported", "fully supported passage")]
    for fam in FAMS:
        r = load(fam)
        parts = [f"# {FAM_LABEL[fam]}: AI-judged evaluation extension", "",
                 "AI judges (not human annotation). Numeric verdicts are deterministic checks of AI evidence mappings. "
                 "Exploratory, post-freeze; no multiplicity correction. * = planned primary comparison. "
                 "n (a better / b better / tied) counts paired units.", ""]
        if fam == "synthetic":
            parts += ["## Experiment 1: strict whole-passage success (existing AI labels)", "", table_metric_a(r), ""]
        parts += ["## Experiment 2: atomic claims", "", table_claims(r), "",
                  "## Experiment 3: numerical fidelity (deterministic checks)", "", table_numeric(r), "",
                  "## Paired comparisons (claim rates: pooled ratio difference; passages: mean difference)", "",
                  table_comparisons(r, keys_main), "",
                  "## Experiment 4: verifier edits (each system vs its own starting draft)", "", table_edits(r), ""]
        if fam != "synthetic":
            parts += ["## Experiment 5: finding completeness", "", table_completeness(r), ""]
        parts += ["## Experiment 7: efficiency (run logs)", "", table_efficiency(r), ""]
        if r.get("failed_runs"):
            parts += [f"Failed runs (excluded from completed-only rates; counted as 0 in ITT rows): {r['failed_runs']}.", ""]
        (OUT / "tables" / f"{fam}.md").write_text("\n".join(parts), encoding="utf-8")


# ----------------------------------------------------------------------------- figures
def _style(ax, title: str):
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def write_figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from evaluation.extended_stats import rate_ci
    plt.rcParams.update({"font.size": 8, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    R = {f: load(f) for f in FAMS}
    syn = R["synthetic"]

    # 1. focal accuracy vs strict whole-passage success (synthetic)
    conds = ["C1", "C2", "C6", "C7", "C3", "C4", "C5"]
    a = syn["metric_a"]
    series = [("focal_correct", "Focal exact accuracy (n=24)", SLOT[0]),
              ("complete_correct", "Strict complete & correct passage (n=32)", SLOT[1])]
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    w = 0.38
    x = np.arange(len(conds))
    for i, (k, lab, col) in enumerate(series):
        vals, lo, hi = [], [], []
        for c in conds:
            pc = a["per_case"][c]
            num = {cs: float(v[k]) for cs, v in pc.items() if v[k] is not None}
            v, l, h = rate_ci(num, {cs: 1.0 for cs in num})
            vals.append(v)
            lo.append(v - l)
            hi.append(h - v)
        ax.bar(x + (i - 0.5) * w, vals, w - 0.03, color=col, label=lab, edgecolor=SURFACE, linewidth=1)
        ax.errorbar(x + (i - 0.5) * w, vals, yerr=[lo, hi], fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
    fs = syn["claims"]["summary"]
    ax.plot(x, [fs[c]["fully_supported"] for c in conds], "D", color=SLOT[2], markersize=5, markeredgecolor=SURFACE,
            label="Fully supported passage, atomic claims (n=32)")
    ax.set_xticks(x, conds)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("share of TEST cases", color=INK2)
    _style(ax, "Focal-label ceiling vs whole-passage success (synthetic TEST; AI-judged labels, 95% case-bootstrap CI)")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.38))
    fig.tight_layout()
    fig.savefig(fig_dir / "fig1_focal_vs_passage_success.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # 2. numerical precision vs recall
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.8), sharey=True)
    for ax, fam in zip(axes, FAMS):
        s = R[fam]["claims"]["summary"]
        for c in _conds(s):
            p, rc = s[c]["numeric_precision"], s[c]["numeric_recall"]
            if p["value"] is None or rc["value"] is None:
                continue
            ax.errorbar(rc["value"], p["value"], xerr=[[rc["value"] - rc["ci"][0]], [rc["ci"][1] - rc["value"]]],
                        yerr=[[p["value"] - p["ci"][0]], [p["ci"][1] - p["value"]]], fmt="o", color=SLOT[0],
                        ecolor="#9ec5f4", elinewidth=0.8, markersize=4, markeredgecolor=SURFACE)
            ax.annotate(c, (rc["value"], p["value"]), xytext=(3, 3), textcoords="offset points", fontsize=7, color=INK)
        ax.set_xlabel("recall of required numeric facts", color=INK2)
        _style(ax, FAM_LABEL[fam])
        ax.set_xlim(0, 1.02)
    axes[0].set_ylabel("precision of reported numbers", color=INK2)
    axes[0].set_ylim(0.5, 1.02)
    fig.suptitle("Numerical precision vs recall (deterministic checks of AI evidence mappings; 95% CI)", fontsize=9,
                 x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig2_numeric_precision_recall.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # 3 + 5. atomic claim label distributions by family (synthetic vs real vs long)
    labs = [("n_supported", "Supported", SLOT[0]), ("n_overstated", "Overstated", SLOT[1]),
            ("n_understated", "Understated", SLOT[2]), ("n_unsupported", "Unsupported", SLOT[3]),
            ("n_numeric_error", "Numeric error", SLOT[4])]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.0), sharey=True, gridspec_kw={"width_ratios": [7, 5, 3]})
    for ax, fam in zip(axes, FAMS):
        pc = R[fam]["claims"]["per_case"]
        cs = _conds(pc)
        bottom = np.zeros(len(cs))
        for k, lab, col in labs:
            tot = np.array([sum(r["all"]["n_assessable"] for r in pc[c].values()) for c in cs], float)
            v = np.array([sum(r["all"][k] for r in pc[c].values()) for c in cs], float) / np.where(tot > 0, tot, 1)
            ax.bar(cs, v, 0.7, bottom=bottom, color=col, label=lab, edgecolor=SURFACE, linewidth=1)
            bottom += v
        ax.set_ylim(0.6 if fam != "diagnostic" else 0.6, 1.0)
        _style(ax, FAM_LABEL[fam].split(" (")[0] + f"\n(n claims={int(sum(sum(r['all']['n_assessable'] for r in pc[c].values()) for c in cs))})")
        ax.tick_params(axis="x", labelsize=7)
    axes[0].set_ylabel("share of assessable atomic claims (axis from 0.6)", color=INK2)
    axes[-1].legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.suptitle("Atomic claim labels by condition and dataset (AI-judged; numeric errors from deterministic checks)",
                 fontsize=9, x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig3_atomic_label_profiles.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # 4. beneficial vs harmful edits
    rows = []
    for fam in FAMS:
        for c, x in R[fam]["edits"]["summary"].items():
            rows.append((f"{fam[:3]}·{c}", x))
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    names = [r[0] for r in rows]
    ben = np.array([r[1].get("beneficial", 0) for r in rows])
    neu = np.array([r[1].get("neutral", 0) for r in rows])
    har = np.array([r[1].get("harmful", 0) for r in rows])
    ax.bar(names, ben, color=SLOT[0], label="beneficial (error corrected/removed)", edgecolor=SURFACE)
    ax.bar(names, neu, bottom=ben, color="#c3c2b7", label="neutral", edgecolor=SURFACE)
    ax.bar(names, har, bottom=ben + neu, color=SLOT[1], label="harmful (error introduced / content lost)", edgecolor=SURFACE)
    for i, r in enumerate(rows):
        ax.annotate(f"{r[1].get('initial_errors', 0)} init.\nerr.", (i, ben[i] + neu[i] + har[i]), xytext=(0, 2),
                    textcoords="offset points", ha="center", fontsize=6, color=INK2)
    ax.set_ylabel("substantive claim edits (count)", color=INK2)
    ax.tick_params(axis="x", labelsize=7, rotation=0)
    _style(ax, "Verifier and reviser edits vs their own starting draft (AI-judged before/after labels)")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(fig_dir / "fig4_edit_outcomes.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # 6. quality vs cost (synthetic strict success; real/long support rate)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    eff = syn["efficiency"]
    pts = [(eff[c]["cost_usd_per_text"], a["summary"]["ITT"][c]["complete_correct"], c, eff[c]["tool_calls_per_text"]) for c in conds]
    _pareto(axes[0], pts, "Synthetic: strict complete & correct (n=32)")
    rr = R["real"]
    pts = [(rr["efficiency"][c]["cost_usd_per_text"], rr["claims"]["summary"][c]["support_rate"]["value"], c,
            rr["efficiency"][c]["tool_calls_per_text"]) for c in ("C1", "C2", "C3", "C4")]
    _pareto(axes[1], pts, "Real papers: atomic support rate (completed runs)")
    for ax in axes:
        ax.set_xlabel("mean cost per text, USD (log scale)", color=INK2)
    axes[0].set_ylabel("quality (AI-judged)", color=INK2)
    fig.suptitle("Quality vs cost; marker area ∝ evidence-tool calls per text; line = Pareto frontier", fontsize=9,
                 x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig5_quality_vs_cost.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _pareto(ax, pts, title):
    import numpy as np
    pts = [p for p in pts if p[0] is not None and p[1] is not None]
    for cost, q, c, tools in pts:
        ax.scatter(cost, q, s=20 + 6 * (tools or 0), color=SLOT[0], edgecolor=SURFACE, linewidth=1, zorder=3)
        ax.annotate(c, (cost, q), xytext=(4, 3), textcoords="offset points", fontsize=7, color=INK)
    front, best = [], -1.0
    for cost, q, c, _ in sorted(pts):
        if q > best:
            front.append((cost, q))
            best = q
    ax.plot([p[0] for p in front], [p[1] for p in front], color=SLOT[1], linewidth=1.2, zorder=2)
    ax.set_xscale("log")
    lo = min(p[1] for p in pts)
    ax.set_ylim(max(0, lo - 0.08), min(1.0, max(p[1] for p in pts) + 0.05))
    _style(ax, title)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    _ = np


def write_summary() -> None:
    R = {f: load(f) for f in FAMS}
    L = ["# Evaluation extension: headline results (AI-judged, exploratory, post-freeze)", "",
         "Generated from `results/ai_extended/*/results.json`. Labels come from two AI judge families plus AI "
         "adjudication; numeric verdicts are deterministic. These are not human annotations. Rates pool claims or "
         "facts over cases; 95% intervals resample cases (papers for real) with 10,000 draws, seed 4213.", ""]
    for fam in FAMS:
        r = R[fam]
        s = r["claims"]["summary"]
        L += [f"## {FAM_LABEL[fam]}", ""]
        head = ["condition", "support rate", "factual error rate", "overstated", "understated", "unsupported",
                "numeric precision", "numeric recall", "fully supported passages"]
        if fam == "synthetic":
            head.insert(1, "strict complete & correct")
        else:
            head.insert(1, "finding recall")
        head.append("cost USD/text")
        L += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for c in _conds(s):
            x = s[c]
            first = (f3(r["metric_a"]["summary"]["ITT"][c]["complete_correct"]) if fam == "synthetic"
                     else f3(r["completeness"]["summary"][c]["finding_recall"]["value"]) if c in r["completeness"]["summary"] else "—")
            cost = r["efficiency"].get(c, {}).get("cost_usd_per_text")
            L.append(f"| {c} | {first} | " + " | ".join(f3(x[k]["value"]) for k in (
                "support_rate", "factual_error_rate", "overstated_rate", "understated_rate", "unsupported_rate",
                "numeric_precision", "numeric_recall")) + f" | {f3(x['fully_supported'])} | " +
                (f"{cost:.5f}" if cost is not None else "—") + " |")
        L += ["", "Planned and lineage contrasts (first minus second; 95% CI; * planned primary):", "",
              "| contrast | support rate | factual error rate | numeric precision | numeric recall | fully supported passage |"
              + (" strict complete & correct |" if fam == "synthetic" else " finding recall |"),
              "|---|---|---|---|---|---|---|"]
        for name, comp in r["claims"]["comparisons"].items():
            extra = (ci(r["metric_a"]["comparisons"][name]["complete_correct"]) if fam == "synthetic"
                     else ci(r["completeness"]["comparisons"][name]["finding_recall"]) if name in r["completeness"]["comparisons"] else "—")
            L.append(f"| {name.replace('_vs_', ' − ')}{' *' if comp.get('planned_primary') else ''} | " + " | ".join(
                ci(comp[k]) for k in ("support_rate", "factual_error_rate", "numeric_precision", "numeric_recall",
                                      "fully_supported")) + f" | {extra} |")
        L.append("")
    (OUT / "SUMMARY.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    write_tables()
    write_summary()
    write_figures()


if __name__ == "__main__":
    main()


def edit_examples(fam: str, limit: int = 40) -> list[dict[str, Any]]:
    """Concrete verifier edits with before/after sentences and consensus labels (for the results document)."""
    from evaluation.extended_data import load_family
    r = load(fam)
    data = load_family(fam)
    claims = {c["claim_id"]: c for c in (json.loads(l) for l in
              (ROOT / "annotation" / "ai_extended" / "consensus" / f"{fam}_claims.jsonl").read_text().splitlines() if l)}
    raw = {c["claim_id"]: c for c in (json.loads(l) for l in
           (ROOT / "annotation" / "ai_extended" / "claims" / f"{fam}.jsonl").read_text().splitlines() if l)}
    units = {}
    for t in data.texts.values():
        for s in t.sentences:
            from evaluation.extended_data import unit_id
            units[unit_id(t.case_id, s)] = s
    out = []
    for e in r["edits"]["examples"][:limit]:
        x = claims.get(e["claim_id"])
        ys = [claims[y] for y in e.get("matched_y", []) if y in claims]
        before = units.get(raw[e["claim_id"]]["unit_id"]) if e["relation"] != "ADDED" else None
        after = [units.get(raw[y["claim_id"]]["unit_id"]) for y in ys]
        out.append({"case": e["case_id"], "alias": e["alias"], "condition": e["condition"], "class": e["class"],
                    "relation": e["relation"], "direction": e["direction"], "before_label": e["before"],
                    "after_labels": e["after"], "before_sentence": before, "after_sentences": after,
                    "before_claim": raw[e["claim_id"]]["proposition"] if x else None,
                    "after_claims": [raw[y["claim_id"]]["proposition"] for y in ys],
                    "numbers_after": [(n["as_written"], n["verdict"], n.get("expected")) for y in ys for n in y["numbers"]
                                      if n["verdict"] != "CORRECT"]})
    return out
