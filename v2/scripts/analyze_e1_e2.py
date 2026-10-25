"""Analyse a V2 E1/E2 run (design: v2/docs/E1_E2_DESIGN.md, sections 6-7).

  python v2/scripts/analyze_e1_e2.py --run-dir v2/outputs/e1e2/<run_tag>

Writes to v2/results/e1e2/<run_tag>/ (or --out):
  summary.json, TABLES.md        automatic measures and the descriptive rule checks R1-R4
  failure_coding.csv             every non-strengthened run on a STRENGTHEN probe, with a SUGGESTED failure stage
                                 (F0 not retrieved [tools only], F1 not noticed, F2 noticed / wrong standard,
                                 F3 judged understated / wrong action). The keyword-based suggestion is only a
                                 starting point: the coded_stage column is filled by hand and checked by a student.
  revision_review.csv            every WEAKEN/STRENGTHEN revision, for the human check of expressed level and new errors
Rules never assign a root cause automatically; see the design document.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v2.verifier_oracle import action_consistent  # noqa: E402

ORDER = ("D0-tools", "D0-oracle", "D1-oracle", "D2-oracle", "D1c-oracle", "D0-tools-800", "D1-tools")
STRUCTURED = ("D1-oracle", "D2-oracle", "D1c-oracle", "D1-tools")
TOOL_CONDITIONS = ("D0-tools", "D0-tools-800", "D1-tools")
# POST-HOC subgroup (decided 2026-10-25 after e1e2_v1): these drafts state an accurate sub-claim, so "strengthening"
# means broadening scope, not strengthening the same proposition. Reported separately; original results are kept.
SCOPE_ANCHORING = {"P-GEN-U-strong", "P-ROB-U-strong", "P-EFF-U-strong"}
# Phrases that suggest the decisive fact was mentioned. Suggestions only; final coding is manual.
DECISIVE_MARKERS = {
    "SIG": ["0.017", "S2", "t-test", "t test"],
    "CON": ["all six", "6/6", "six of six", "all 6", "every dataset", "each of the six", "93.7"],
    "EFF": ["latency", "41 ms", "41 vs", "Corvex A2", "same hardware", "wall-clock"],
    "GEN": ["Telecom", "Utilities", "all three", "three held-out"],
    "ROB": ["20%", "30%", "1.3", "1.8", "every noise", "all noise", "all tested", "each noise"],
    "CIT": ["31%", "31 %", "31 percent", "three news"],
}


def load_runs(run_dir: Path) -> list[dict[str, Any]]:
    runs = []
    for cond in ORDER:
        for f in sorted((run_dir / cond).glob("*.json")):
            runs.append(json.loads(f.read_text(encoding="utf-8")))
    return runs


def majority(values: list[str]) -> str:
    if not values:
        return "MISSING"
    v, n = Counter(values).most_common(1)[0]
    return v if n > len(values) / 2 else "NO_MAJORITY"


def mentions(text: str, pair: str) -> bool:
    t = (text or "").lower()
    return any(m.lower() in t for m in DECISIVE_MARKERS[pair])


def decisive_retrieved(run: dict[str, Any], probe: dict[str, Any]) -> bool:
    """True if a tool returned a decisive ID or anything inside it (a row ID such as T1.r3 matches cell T1.r3.wren)."""
    got = run.get("returned_ids", [])
    return any(g == d or g.startswith(d + ".") for d in probe["decisive_evidence_ids"] for g in got)


def suggest_stage(run: dict[str, Any], probe: dict[str, Any]) -> str:
    cond = run["condition"]
    if cond in TOOL_CONDITIONS and not decisive_retrieved(run, probe):
        return "F0"
    j = run.get("judgement") or {}
    if cond in STRUCTURED:
        if j.get("support_relation") == "STRONGER_SUPPORTED":
            return "F3"
        return "F2" if mentions(j.get("strongest_supported", ""), probe["pair"]) else "F1"
    return "F2" if mentions(run.get("rationale", ""), probe["pair"]) else "F1"


def analyse(runs: list[dict[str, Any]], probes: list[dict[str, Any]]) -> dict[str, Any]:
    pmap = {p["probe_id"]: p for p in probes}
    by = defaultdict(list)
    for r in runs:
        if r.get("status") == "completed":
            by[(r["condition"], r["probe_id"])].append(r)
    conds = [c for c in ORDER if any(k[0] == c for k in by)]
    out: dict[str, Any] = {"n_probes": len(probes), "conditions": {}}
    for c in conds:
        rows = []
        for p in probes:
            rs = sorted(by.get((c, p["probe_id"]), []), key=lambda r: r["repeat"])
            decs = [r["decision"] for r in rs]
            maj = majority(decs)
            rel_maj = majority([(r.get("judgement") or {}).get("support_relation") or "NONE" for r in rs])
            incons = [action_consistent(r.get("judgement") or {}, r["decision"]) is False for r in rs]
            rows.append({
                "probe_id": p["probe_id"], "expected": p["expected_decision"], "acceptable": p["acceptable_decisions"],
                "subgroup": p["subgroup"], "decisions": decs, "majority": maj,
                "correct": maj in p["acceptable_decisions"], "stable": len(set(decs)) == 1 and len(decs) > 0,
                "relation_majority": rel_maj, "relation_correct": rel_maj in p["expected_support_relation"],
                "inconsistent_majority": sum(incons) > len(incons) / 2 if incons else False,
                "n_runs": len(rs),
            })
        s = [x for x in rows if x["expected"] == "STRENGTHEN"]
        s_main = [x for x in s if x["subgroup"] == "claim_strength"]
        s_claim = [x for x in s if x["probe_id"] not in SCOPE_ANCHORING]
        a_ = [x for x in rows if x["expected"] == "ACCEPT"]
        w = [x for x in rows if x["expected"] in ("WEAKEN", "REMOVE")]
        non_s = [x for x in rows if x["expected"] != "STRENGTHEN"]
        crs = [r for k, v in by.items() if k[0] == c for r in v]
        structured = c in STRUCTURED
        stages = Counter()
        for x in s:
            for r in by.get((c, x["probe_id"]), []):
                if r["decision"] != "STRENGTHEN":
                    stages[suggest_stage(r, pmap[x["probe_id"]])] += 1
        out["conditions"][c] = {
            "n_runs": len(crs),
            "decision_accuracy": f"{sum(x['correct'] for x in rows)}/{len(rows)}",
            "correct_strengthen": f"{sum(x['correct'] for x in s)}/{len(s)}",
            "correct_strengthen_excl_proxy": f"{sum(x['correct'] for x in s_main)}/{len(s_main)}",
            "correct_strengthen_claim_level_posthoc": f"{sum(x['correct'] for x in s_claim)}/{len(s_claim)}",
            "correct_strengthen_scope_subgroup_posthoc": f"{sum(x['correct'] for x in s if x['probe_id'] in SCOPE_ANCHORING)}/{len(SCOPE_ANCHORING)}",
            "accept_accuracy": f"{sum(x['correct'] for x in a_)}/{len(a_)}",
            "weaken_remove_accuracy": f"{sum(x['correct'] for x in w)}/{len(w)}",
            "false_strengthen": f"{sum(x['majority'] == 'STRENGTHEN' for x in non_s)}/{len(non_s)}",
            "run_level_strengthen_rate_on_S_probes": f"{sum(r['decision'] == 'STRENGTHEN' for x in s for r in by.get((c, x['probe_id']), []))}/{sum(x['n_runs'] for x in s)}",
            "run_level_false_strengthen": f"{sum(r['decision'] == 'STRENGTHEN' for x in non_s for r in by.get((c, x['probe_id']), []))}/{sum(x['n_runs'] for x in non_s)}",
            "stable_probes": f"{sum(x['stable'] for x in rows)}/{len(rows)}",
            "relation_accuracy_S": f"{sum(x['relation_correct'] for x in s)}/{len(s)}" if structured else None,
            "relation_accuracy_all": f"{sum(x['relation_correct'] for x in rows)}/{len(rows)}" if structured else None,
            "action_inconsistent_probes": sum(x["inconsistent_majority"] for x in rows) if structured else None,
            "suggested_failure_stages_on_S_runs": dict(sorted(stages.items())),
            "invalid_decisions": sum(1 for r in crs if not r.get("valid", True)),
            "cost_usd": round(sum(r.get("cost_usd", 0) for r in crs), 6),
            "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in crs),
            "completion_tokens": sum(r.get("completion_tokens", 0) for r in crs),
            "per_probe": rows,
        }
    out["rule_checks"] = rule_checks(out["conditions"])
    out["e5_attribution"] = e5_attribution(out["conditions"], by, pmap)
    return out


def _num(frac: str) -> int:
    return int(frac.split("/")[0])


def rule_checks(cs: dict[str, Any]) -> dict[str, str]:
    """Descriptive only. None of these assigns a root cause (design section 7)."""
    out = {}
    d0 = cs.get("D0-oracle")
    if d0:
        k = _num(d0["correct_strengthen"])
        out["R1"] = (f"D0-oracle strengthened {d0['correct_strengthen']} STRENGTHEN probes: "
                     + ("full evidence alone does not fix V1 (reference threshold <= 3 met). " if k <= 3 else
                        "above the reference threshold of 3. ")
                     + f"Suggested failure stages (runs): {d0['suggested_failure_stages_on_S_runs']}")
    base_w = _num(d0["weaken_remove_accuracy"]) if d0 else None
    for c in ("D1-oracle", "D2-oracle"):
        x = cs.get(c)
        if not x:
            continue
        ok = (_num(x["correct_strengthen"]) >= 9 and _num(x["false_strengthen"]) <= 2
              and (base_w is None or _num(x["weaken_remove_accuracy"]) >= base_w - 1))
        out[f"R2 {c}"] = ("automatic part MET; human check of revisions pending" if ok else "automatic part NOT met") + (
            f" (strengthen {x['correct_strengthen']}, false {x['false_strengthen']}, "
            f"weaken/remove {x['weaken_remove_accuracy']} vs D0-oracle {d0['weaken_remove_accuracy'] if d0 else 'n/a'})")
        st = x["suggested_failure_stages_on_S_runs"]
        top = max(st, key=st.get) if st else None
        out[f"R3 {c}"] = (f"F3 most common or >=3 inconsistent probes: "
                          f"{'YES - consider D3' if top == 'F3' or x['action_inconsistent_probes'] >= 3 else 'no'} "
                          f"(stages {st}, inconsistent probes {x['action_inconsistent_probes']})")
    s1, s2 = (cs.get("D1-oracle") or {}).get("suggested_failure_stages_on_S_runs"), \
        (cs.get("D2-oracle") or {}).get("suggested_failure_stages_on_S_runs")
    if s1 is not None and s2 is not None:
        def f12(st):
            tot = sum(st.values())
            return tot > 0 and (st.get("F1", 0) + st.get("F2", 0)) > tot / 2
        out["R4"] = ("F1/F2 dominate remaining failures in both D1 and D2: stop and discuss"
                     if f12(s1) and f12(s2) else "F1/F2 do not dominate in both")
    return out


def e5_attribution(cs: dict[str, Any], by: dict, pmap: dict) -> list[dict[str, Any]]:
    """Probes right in D1-oracle but wrong in D1-tools (majority), with per-run retrieval status (E5)."""
    if "D1-oracle" not in cs or "D1-tools" not in cs:
        return []
    ok = {x["probe_id"]: x for x in cs["D1-oracle"]["per_probe"]}
    out = []
    for x in cs["D1-tools"]["per_probe"]:
        o = ok[x["probe_id"]]
        if o["correct"] and not x["correct"]:
            p = pmap[x["probe_id"]]
            runs = sorted(by.get(("D1-tools", x["probe_id"]), []), key=lambda r: r["repeat"])
            per_run = [{"repeat": r["repeat"], "decision": r["decision"],
                        "decisive_retrieved": decisive_retrieved(r, p) if p["decisive_evidence_ids"] else None,
                        "relation": (r.get("judgement") or {}).get("support_relation"),
                        "suggested_stage": suggest_stage(r, p) if p["expected_decision"] == "STRENGTHEN" else None}
                       for r in runs]
            n_ret = sum(1 for r in per_run if r["decisive_retrieved"])
            kind = ("not applicable (no decisive-evidence list)" if not p["decisive_evidence_ids"] else
                    "retrieval loss" if n_ret == 0 else "decision loss" if n_ret == len(per_run) else "mixed")
            out.append({"probe_id": x["probe_id"], "expected": x["expected"], "oracle": o["decisions"],
                        "tools": x["decisions"], "attribution": kind, "runs": per_run})
    return out


def write_tables(res: dict[str, Any], path: Path) -> None:
    cs = res["conditions"]
    keys = ["n_runs", "decision_accuracy", "correct_strengthen", "correct_strengthen_excl_proxy",
            "correct_strengthen_claim_level_posthoc", "correct_strengthen_scope_subgroup_posthoc", "accept_accuracy",
            "weaken_remove_accuracy", "false_strengthen", "run_level_strengthen_rate_on_S_probes",
            "run_level_false_strengthen", "stable_probes", "relation_accuracy_S", "relation_accuracy_all",
            "action_inconsistent_probes", "suggested_failure_stages_on_S_runs", "invalid_decisions", "cost_usd"]
    lines = ["# E1/E2 results (DEV only, exploratory)", "",
             "Probe-level figures use the majority decision over repeats. Failure stages are keyword-based SUGGESTIONS "
             "pending manual coding (failure_coding.csv).", "",
             "| Measure | " + " | ".join(cs) + " |", "|---|" + "---|" * len(cs)]
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(str(cs[c].get(k)) for c in cs) + " |")
    lines += ["", "## Rule checks (descriptive; no automatic root cause)", ""]
    lines += [f"* **{k}**: {v}" for k, v in res["rule_checks"].items()]
    if res.get("e5_attribution") is not None and "D1-tools" in cs:
        lines += ["", "## E5: probes right in D1-oracle but wrong in D1-tools", ""]
        if not res["e5_attribution"]:
            lines.append("(none)")
        for a in res["e5_attribution"]:
            lines.append(f"* **{a['probe_id']}** (expected {a['expected']}): oracle {a['oracle']}, tools {a['tools']} "
                         f"-> {a['attribution']}; runs: " + "; ".join(
                             f"r{r['repeat']} {r['decision']} retrieved={r['decisive_retrieved']} rel={r['relation']}"
                             for r in a["runs"]))
    lines += ["", "## Per-probe majority decisions", "",
              "| Probe | Expected | " + " | ".join(cs) + " |", "|---|---|" + "---|" * len(cs)]
    for i, p in enumerate(next(iter(cs.values()))["per_probe"]):
        cells = []
        for c in cs:
            x = cs[c]["per_probe"][i]
            mark = "" if x["correct"] else " ✗"
            cells.append(f"{x['majority']}{mark} ({','.join(d[:2] for d in x['decisions'])})")
        lines.append(f"| {p['probe_id']} | {'/'.join(p['acceptable'])} | " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _sheet_path(out: Path, name: str) -> Path:
    """Never overwrite a review sheet that may hold manual coding: write a .regenerated copy beside it instead."""
    p = out / name
    return p.with_name(p.stem + ".regenerated.csv") if p.exists() else p


def write_sheets(runs: list[dict[str, Any]], probes: list[dict[str, Any]], out: Path) -> None:
    pmap = {p["probe_id"]: p for p in probes}
    with open(_sheet_path(out, "failure_coding.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "probe_id", "repeat", "decision", "support_relation", "strongest_supported",
                    "rationale", "decisive_fact", "decisive_retrieved_tools_only", "suggested_stage", "coded_stage",
                    "coder", "student_check", "notes"])
        for r in runs:
            p = pmap.get(r["probe_id"])
            if not p or p["expected_decision"] != "STRENGTHEN" or r.get("status") != "completed" \
                    or r["decision"] == "STRENGTHEN":
                continue
            j = r.get("judgement") or {}
            retrieved = decisive_retrieved(r, p) if r["condition"] in TOOL_CONDITIONS else ""
            w.writerow([r["condition"], r["probe_id"], r["repeat"], r["decision"], j.get("support_relation", ""),
                        j.get("strongest_supported", ""), r.get("rationale", ""), p["decisive_fact"], retrieved,
                        suggest_stage(r, p), "", "", "", ""])
    seen: dict[tuple, dict[str, Any]] = {}
    for r in runs:
        if r.get("status") != "completed" or r["decision"] not in ("WEAKEN", "STRENGTHEN"):
            continue
        k = (r["condition"], r["probe_id"], r["revised_text"])
        if k in seen:
            seen[k]["n_runs"] += 1
            continue
        p = pmap[r["probe_id"]]
        seen[k] = {"condition": r["condition"], "probe_id": r["probe_id"], "decision": r["decision"],
                   "case_gold_level": p["case_gold_level"], "target_level": p["target_level_after_edit"],
                   "original": r["draft_text"], "revised": r["revised_text"], "n_runs": 1}
    with open(_sheet_path(out, "revision_review.csv"), "w", newline="", encoding="utf-8") as f:
        cols = ["condition", "probe_id", "decision", "case_gold_level", "target_level", "original", "revised", "n_runs",
                "expressed_level_after", "new_factual_error", "reviewer", "notes"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for v in seen.values():
            w.writerow({**v, "expressed_level_after": "", "new_factual_error": "", "reviewer": "", "notes": ""})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--probes", default=str(ROOT / "v2" / "data" / "dev_probes_batch1.json"))
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    probes = json.loads(Path(a.probes).read_text(encoding="utf-8"))["probes"]
    runs = load_runs(run_dir)
    res = analyse(runs, probes)
    out = Path(a.out) if a.out else ROOT / "v2" / "results" / "e1e2" / run_dir.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    write_tables(res, out / "TABLES.md")
    write_sheets(runs, probes, out)
    for c, x in res["conditions"].items():
        print(f"{c:10s} strengthen {x['correct_strengthen']:>5s}  false {x['false_strengthen']:>5s}  "
              f"accept {x['accept_accuracy']:>5s}  weaken/remove {x['weaken_remove_accuracy']:>5s}  ${x['cost_usd']}")
    for k, v in res["rule_checks"].items():
        print(f"{k}: {v}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
