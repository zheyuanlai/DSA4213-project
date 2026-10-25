"""Score a Phase 4 TEST run (design: v2/docs/PHASE4_DESIGN.md section 5). Rules fixed before inference.

  python v2/scripts/phase4_score.py --run-dir v2/outputs/phase4/<tag>

Per run, with gold from v2/private/phase4/gold.json and labels from phase4_judge.py:

* a revision is **good** if its final label is SUPPORTED and its numeric status is not "error"; a REMOVE has no text;
* **correct strengthening** (gold STRENGTHEN): decision STRENGTHEN and the revision is good;
* **false strengthening** (gold not STRENGTHEN): decision STRENGTHEN;
* **overstatement corrected** (gold WEAKEN/REMOVE): decision REMOVE, or WEAKEN with a revision whose final label is not
  OVERSTATED/UNSUPPORTED and whose numeric status is not "error";
* **control preserved** (gold ACCEPT): ACCEPT or FLAG, or an edit whose revision is good;
* **harmful edit** (gold ACCEPT): REMOVE, or an edit whose revision is not good.

Rates are per-item means over repeats, averaged over items. The contrasts V2 C4 − V1 C4 and V2 C4 − V2 C5 use the
paired cluster bootstrap over pairs (V1's evaluation/paired_bootstrap.py). Raw counts are always reported.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.paired_bootstrap import cluster_bootstrap  # noqa: E402

CONDS = {"D0-tools-800": "V1 C4", "D1-tools": "V2 C4", "D1-tools-C5": "V2 C5"}
METRICS = ("correct_strengthen", "false_strengthen", "overstatement_corrected", "control_preserved", "harmful_edit",
           "decision_correct")


def opaque(case_id: str, text: str) -> str:
    return "x" + hashlib.sha256(f"{case_id}\n{text}".encode("utf-8")).hexdigest()[:10]


def run_outcomes(r: dict, g: dict, judged: dict) -> dict[str, float | None]:
    dec = r["decision"]
    exp = g["expected_decision"]
    j = judged.get(opaque(r["case_id"], (r.get("revised_text") or "").strip())) if dec in ("WEAKEN", "STRENGTHEN") else None
    good = bool(j) and j["final_label"] == "SUPPORTED" and j["numeric"] != "error"
    o: dict[str, float | None] = {m: None for m in METRICS}
    o["decision_correct"] = float(dec in g["acceptable_decisions"])
    if exp == "STRENGTHEN":
        o["correct_strengthen"] = float(dec == "STRENGTHEN" and good)
    else:
        o["false_strengthen"] = float(dec == "STRENGTHEN")
    if exp in ("WEAKEN", "REMOVE"):
        o["overstatement_corrected"] = float(dec == "REMOVE" or (dec == "WEAKEN" and bool(j) and j["numeric"] != "error"
                                                                and j["final_label"] not in ("OVERSTATED", "UNSUPPORTED")))
    if exp == "ACCEPT":
        edited = dec in ("WEAKEN", "STRENGTHEN")
        o["control_preserved"] = float(dec in ("ACCEPT", "FLAG") or (edited and good))
        o["harmful_edit"] = float(dec == "REMOVE" or (edited and not good))
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--gold", default=str(ROOT / "v2" / "private" / "phase4" / "gold.json"))
    ap.add_argument("--judged", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    tag = run_dir.name
    out = Path(a.out) if a.out else ROOT / "v2" / "results" / "phase4" / tag
    gold = {g["probe_id"]: g for g in json.loads(Path(a.gold).read_text(encoding="utf-8"))["probes"]}
    judged = json.loads(Path(a.judged or out / "judged.json").read_text(encoding="utf-8"))
    per_item: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    raw_counts: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    cost: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0, 0])
    for f in glob.glob(str(run_dir / "*" / "*.json")):
        r = json.loads(Path(f).read_text(encoding="utf-8"))
        if r.get("status") != "completed" or r["condition"] not in CONDS:
            continue
        g = gold[r["probe_id"]]
        for m, v in run_outcomes(r, g, judged).items():
            if v is not None:
                per_item[r["condition"]][m][r["probe_id"]].append(v)
                raw_counts[r["condition"]][m][0] += int(v)
                raw_counts[r["condition"]][m][1] += 1
        c = cost[r["condition"]]
        c[0] += r.get("cost_usd", 0)
        c[1] += sum(x.get("latency_s") or 0 for x in r.get("calls", []))
        c[2] += len(r.get("tools", []))
        c[3] += 1
    means = {c: {m: {pid: sum(v) / len(v) for pid, v in per_item[c][m].items()} for m in METRICS} for c in per_item}
    clusters = {pid: g["pair"] for pid, g in gold.items()}
    res: dict = {"run": tag, "conditions": {}, "contrasts": {}, "subgroups": {}}
    for c in per_item:
        res["conditions"][CONDS[c]] = {
            m: {"rate": (sum(means[c][m].values()) / len(means[c][m])) if means[c][m] else None,
                "runs": f"{raw_counts[c][m][0]}/{raw_counts[c][m][1]}", "items": len(means[c][m])} for m in METRICS}
        n = cost[c][3] or 1
        res["conditions"][CONDS[c]]["cost_usd_total"] = round(cost[c][0], 6)
        res["conditions"][CONDS[c]]["latency_s_per_run"] = round(cost[c][1] / n, 2)
        res["conditions"][CONDS[c]]["tool_calls_per_run"] = round(cost[c][2] / n, 2)
    for x, y in (("D1-tools", "D0-tools-800"), ("D1-tools", "D1-tools-C5")):
        if x in means and y in means:
            res["contrasts"][f"{CONDS[x]} - {CONDS[y]}"] = {
                m: cluster_bootstrap(means[x][m], means[y][m], clusters) for m in METRICS}
    for name, pred in (("pattern_new_vs_dev", lambda g: g.get("pattern_new_vs_dev")),
                       ("no_test_needed", lambda g: not g.get("needs_test"))):
        res["subgroups"][name] = {CONDS[c]: {
            "correct_strengthen": f"{sum(sum(v) for pid, v in per_item[c]['correct_strengthen'].items() if pred(gold[pid]))}"
                                  f"/{sum(len(v) for pid, v in per_item[c]['correct_strengthen'].items() if pred(gold[pid]))}"}
            for c in per_item}
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    lines = [f"# Phase 4 TEST results: {tag}", "", "| Metric (rate; runs) | " + " | ".join(res["conditions"]) + " |",
             "|---|" + "---|" * len(res["conditions"])]
    for m in METRICS:
        lines.append(f"| {m} | " + " | ".join(
            f"{v[m]['rate']:.2f} ({v[m]['runs']})" if v[m]["rate"] is not None else "n/a"
            for v in res["conditions"].values()) + " |")
    for k in ("cost_usd_total", "latency_s_per_run", "tool_calls_per_run"):
        lines.append(f"| {k} | " + " | ".join(str(v[k]) for v in res["conditions"].values()) + " |")
    lines += ["", "## Paired contrasts (cluster bootstrap over pairs, 95%)", ""]
    for k, ms in res["contrasts"].items():
        for m, b in ms.items():
            if b.get("diff") is not None:
                lines.append(f"* {k}, {m}: {b['diff']:+.3f} [{b['ci_low']:+.3f}, {b['ci_high']:+.3f}] (n={b['n']})")
    lines += ["", "## Subgroups (correct strengthening, runs)", ""]
    for name, d in res["subgroups"].items():
        lines.append(f"* {name}: " + "; ".join(f"{c} {v['correct_strengthen']}" for c, v in d.items()))
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
