"""Descriptive cross-team summary and per-person contribution record (for the final report).

Kappa is reported per team only. The pooled numbers here are percent agreement weighted by n, labelled
as descriptive; no kappa is pooled across the two different annotator pairs.
"""
from __future__ import annotations

import json
import time
from typing import Any

from evaluation.four_person.assignment import load_assignment
from evaluation.four_person.roster import ANNOTATORS, TEAMS, Paths, read_csv_any
from evaluation.four_person.submissions import (BLINDING_STATUS_TEXT, accepted_path, person_status, read_log)


def _team_agreement(paths: Paths, team: str) -> dict[str, Any] | None:
    p = paths.team_dir(team) / f"agreement_Team{team}.json"
    return json.loads(p.read_text()) if p.exists() else None


def human_tables(paths: Paths, suffix: str = "") -> str:
    """Markdown tables rendered from the ORIGINAL scorers' JSON (results/human_scored*/); no number is recomputed."""
    hs, hr = paths.root / "results" / f"human_scored{suffix}", paths.root / "results" / f"human_scored_real{suffix}"
    f = lambda x, d=3: "—" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))  # noqa: E731
    L = [f"# Human-scored results (rendered from {hs.name}/ and {hr.name}/ JSON)", ""]
    if suffix:
        L += ["**SENSITIVITY ANALYSIS** — not the primary result: see the variant recorded in its combine_manifest.json.", ""]
    for policy in ("ITT", "completed_only"):
        p = hs / f"human_results_{policy}.json"
        if not p.exists():
            raise FileNotFoundError(f"{p} not found; run `python -m evaluation.four_person score` first")
        r = json.loads(p.read_text())
        s = r["summary"]
        keys = [("calibration_accuracy", "calib. acc."), ("overstatement_rate", "over"), ("understatement_rate", "under"),
                ("omission_rate", "omitted"), ("strong_understatement", "under | strong"), ("nonstrong_overstatement", "over | non-strong"),
                ("coverage_pooled", "coverage"), ("unsupported_mean", "unsupported / output"), ("numeric_errors_mean", "numeric errors / output"),
                ("num_fact_accuracy", "NUM fact acc."), ("neg_recall", "NEG recall"), ("neg_reframed_rate", "NEG reframed")]
        L += [f"## Synthetic TEST, {policy} (N ordinal = {next(iter(s.values()))['n_ordinal']})", "",
              "| condition | " + " | ".join(k[1] for k in keys) + " |", "|---" * (len(keys) + 1) + "|"]
        L += [f"| {c} | " + " | ".join(f(v[k]) for k, _ in keys) + " |" for c, v in s.items()]
        L += ["", "| comparison | metric | diff | 95% CI (case) | 95% CI (matched pair) | n |", "|---|---|---|---|---|---|"]
        for name, comp in r["comparisons"].items():
            for metric, v in comp.items():
                cb, mp = v["case_bootstrap"], v["matched_pair_bootstrap"]
                L.append(f"| {name} | {metric} | {f(cb['diff'])} | [{f(cb['ci_low'])}, {f(cb['ci_high'])}] | "
                         f"[{f(mp['ci_low'])}, {f(mp['ci_high'])}] | {cb['n']} |")
        L.append("")
    p = hr / "human_results_real.json"
    if p.exists():
        r = json.loads(p.read_text())
        keys = ["supported_rate", "overstated_rate", "understated_rate", "unsupported_rate", "numeric_error_rate", "readability", "n_papers"]
        L += ["## Real papers (no gold; human support labels)", "", "| condition | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
        L += [f"| {c} | " + " | ".join(f(v[k]) for k in keys) + " |" for c, v in r["summary"].items()]
        L += ["", "| comparison | metric | diff | 95% CI | n |", "|---|---|---|---|---|"]
        for name, comp in r["comparisons"].items():
            for metric, v in comp.items():
                L.append(f"| {name} | {metric} | {f(v['diff'])} | [{f(v['ci_low'])}, {f(v['ci_high'])}] | {v['n']} |")
    return "\n".join(L) + "\n"


def summary(paths: Paths) -> tuple[dict[str, Any], str]:
    assignment = load_assignment(paths)
    ag = {t: _team_agreement(paths, t) for t in TEAMS}
    L = ["# Four-person human annotation — summary", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}. Agreement is computed separately for each "
         "annotator pair on its own half of the data; the 'pooled' column is descriptive percent agreement only.", ""]
    pooled: dict[str, Any] = {}
    if all(ag.values()):
        L += ["## Agreement by team", "", "| Statistic | AB n | AB % | AB κ | CD n | CD % | CD κ | pooled % (descriptive) |",
              "|---|---|---|---|---|---|---|---|"]
        for study in ("synthetic", "real"):
            for k in ag["AB"][study]["stats"]:
                a, c = ag["AB"][study]["stats"][k], ag["CD"][study]["stats"][k]
                n = (a["n"] or 0) + (c["n"] or 0)
                pct = ((a["pct_agree"] or 0) * a["n"] + (c["pct_agree"] or 0) * c["n"]) / n if n else None
                pooled[f"{study}.{k}"] = {"n": n, "pct_agree": pct}
                f = lambda x: "—" if x is None else f"{x:.3f}"  # noqa: E731
                L.append(f"| {study}: {k} | {a['n']} | {f(a['pct_agree'])} | {f(a['kappa'])} | {c['n']} | "
                         f"{f(c['pct_agree'])} | {f(c['kappa'])} | {f(pct)} |")
        L.append("")
    else:
        L += ["Agreement not available yet for: " + ", ".join(t for t, v in ag.items() if not v), ""]
    L += ["## Blinding status (from the declarations)", ""]
    for who, a in ANNOTATORS.items():
        L.append(f"* {who} {a.name} (Team {a.team}): {BLINDING_STATUS_TEXT[person_status(paths, who)]}")
    L += ["", "## Contribution record", "",
          "| Annotator | Team | synthetic outputs (×2 passes) | real paragraphs | real sentences | accepted files (UTC) | "
          "reported minutes / sessions |", "|---|---|---|---|---|---|---|"]
    sublog = read_log(paths, "submission_log.csv")
    people: dict[str, Any] = {}
    for who, a in ANNOTATORS.items():
        c = assignment["teams"][a.team]["counts"]
        acc = {r["kind"]: r["utc"] for r in sublog if r["annotator"] == who and r["accepted"] == "True"}
        mins = sess = 0
        tl = accepted_path(paths, who, "timelog")
        if tl.exists():
            for r in read_csv_any(tl):
                mins += int(r.get("total_minutes") or 0)
                sess += int(r.get("n_sessions") or 0)
        people[who] = {"name": a.name, "team": a.team, "assigned": c, "accepted_utc": acc,
                       "reported_minutes": mins if tl.exists() else None, "reported_sessions": sess if tl.exists() else None}
        L.append(f"| {who} {a.name} | {a.team} | {c['synthetic_outputs']} | {c['real_outputs']} | {c['real_sentences']} | "
                 + "; ".join(f"{k} {v}" for k, v in sorted(acc.items())) + " | "
                 + (f"{mins} / {sess}" if tl.exists() else "not submitted") + " |")
    for t in TEAMS:
        s = paths.team_dir(t) / f"adjudication_summary_Team{t}.json"
        if s.exists():
            d = json.loads(s.read_text())
            L.append(f"\nTeam {t} adjudication: {d['n_synthetic']} synthetic and {d['n_real']} real-paper values resolved; "
                     f"resolved to the value of: {d['resolved_to_value_of']}")
    data = {"pooled_descriptive": pooled, "people": people,
            "blinding": {w: person_status(paths, w) for w in ANNOTATORS}}
    return data, "\n".join(L) + "\n"
