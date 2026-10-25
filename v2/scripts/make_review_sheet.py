"""Build the targeted student review sheet for E1/E2/E2b (about 12 items).

  python v2/scripts/make_review_sheet.py

Writes v2/review/E2_REVIEW_SHEET.md (items with the original sentence, the relevant evidence quoted from the package,
the revised sentence and the questions) and v2/review/E2_REVIEW_ANSWERS.csv (blank answer sheet). Evidence text is pulled
from the DEV packages by ID, so nothing is transcribed by hand. The "AI preliminary check" column is the coordinating
agent's reading. It is NOT a student judgement and must not be reported as one.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evidence_store import EvidenceStore  # noqa: E402
from src.runner import load_cases  # noqa: E402

OUT_DIR = ROOT / "v2" / "review"

# (item, why selected, run, condition, probe, wanted decision, evidence ids, extra context key, AI preliminary check)
ITEMS = [
    ("S1", "successful strengthening (SIG, certainty)", "e2b_v1", "D1-oracle", "P-SIG-U-strong", "STRENGTHEN",
     ["T1.r1.bleu", "T1.r2.bleu", "S2"], None,
     "Level 2; numbers and test details match S2. Looks correct."),
    ("S2", "successful strengthening (CON, coverage)", "e2b_v1", "D1-oracle", "P-CON-U-strong", "STRENGTHEN",
     ["T1.r1", "T1.r2", "T1.r3", "T1.r4", "T1.r5", "T1.r6"], None,
     "Level 2; Ferrule is higher in all six rows. Looks correct."),
    ("S3", "successful strengthening (ROB, hedge removed)", "e2b_v1", "D1-oracle", "P-ROB-U2-strong", "STRENGTHEN",
     ["T2.r1.th_drop", "T2.r2.th_drop", "T2.r3.th_drop", "T2.r1.li_drop", "T2.r2.li_drop", "T2.r3.li_drop"], "setup",
     "Level 2; drops 0.6/1.3/1.8 are all within the 2.0-point criterion. It also ADDS a baseline comparison "
     "(Lindgren-Tagger 2.6/5.5/8.9) that the original did not make. The numbers are correct, but the prompt asks "
     "revisions not to add unverified content. Please judge whether the addition is acceptable."),
    ("S4", "successful strengthening (CIT, attribution magnitude)", "e2b_v1", "D1-oracle", "P-CIT-U-strong", "STRENGTHEN",
     ["P1"], None, "Level 2; the 31% figure and the three benchmarks are stated in P1. Looks correct."),
    ("S5", "successful strengthening (GEN, hedge removed)", "e2b_v1", "D1-oracle", "P-GEN-U2-strong", "STRENGTHEN",
     ["T1.r3", "T1.r4", "T1.r5"], None,
     "Level 2 within the three held-out domains; numbers correct. No test is reported, but the claim does not use "
     "significance language. Looks correct."),
    ("S6", "successful strengthening (EFF, same hardware)", "e2b_v1", "D1-oracle", "P-EFF-U2-strong", "STRENGTHEN",
     ["T1.r1.lat", "T1.r2.lat", "T1.r1.src", "T1.r2.src"], "table_note",
     "Level 2; both latencies were measured on the same setup. Looks correct."),
    ("F1", "FALSE strengthening (D2, comparability trap)", "e1e2_v1", "D2-oracle", "P-EFF-U2-partner", "STRENGTHEN",
     ["T1.r1.lat", "T1.r2.lat", "T1.r1.src", "T1.r2.src"], "table_note",
     "Overstated: an unqualified speed claim from latencies measured on different hardware (A2 fp16 vs A1 fp32). "
     "Level 2 where gold is 1. Error."),
    ("C1", "comparability: overstated sentence ACCEPTED (D1)", "e2b_v1", "D1-oracle", "P-EFF-S-partner", "ACCEPT",
     ["T1.r1.lat", "T1.r2.lat", "T1.r1.src", "T1.r2.src"], "table_note",
     "The accepted sentence asserts 'decodes faster' although the latencies are not comparable. It should have been "
     "weakened. Error (missed overstatement)."),
    ("C2", "comparability: WEAKEN revision (D1c)", "e2b_v1", "D1c-oracle", "P-EFF-S-partner", "WEAKEN",
     ["T1.r1.lat", "T1.r2.lat", "T1.r1.src", "T1.r2.src"], "table_note",
     "Level 1: reports both latencies and states the hardware difference, without claiming a speed-up. Looks correct."),
    ("C3", "comparability: caveat added to a hedged claim (D1c)", "e2b_v1", "D1c-oracle", "P-EFF-U2-partner", "WEAKEN",
     ["T1.r1.lat", "T1.r2.lat", "T1.r1.src", "T1.r2.src"], "table_note",
     "Borderline between levels 1 and 2. It now states 'is lower than' without 'may' (closer to the strong form), but "
     "it qualifies the comparison with the hardware difference. The caveat is accurate. Please judge the level."),
    ("A1", "CIT attribution: WEAKEN keeps 'about 30%' (D1)", "e1e2_v1", "D1-oracle", "P-CIT-S-partner", "WEAKEN",
     ["P1"], "methods_credited",
     "Borderline. 'Is credited with … about 30%' repeats the package's own framing (methods summary) and does not "
     "say that Varga & Sandoval reported it. But a reader may still take it as attributing the result, and the "
     "quoted excerpt reports no reduction at all."),
    ("A2", "label question: 'generally' weakened to 'five of six' (D1c)", "e2b_v1", "D1c-oracle", "P-CON-U2-partner",
     "WEAKEN", ["T1.r1", "T1.r2", "T1.r3", "T1.r4", "T1.r5", "T1.r6"], None,
     "Level 1 before and after; the revision is more precise and accurate. The probe's expected decision (ACCEPT "
     "only) may be too strict. Not an error."),
]

QUESTIONS = {
    "default": ["Expressed level of the REVISED sentence (0 / 1 / 2)?",
                "Does the revised sentence contain anything the evidence does not support (yes / no; what)?",
                "Was the verifier's decision appropriate (yes / no / borderline)?"],
    "ACCEPT": ["Expressed level of the ORIGINAL (accepted) sentence (0 / 1 / 2)?",
               "Is the accepted sentence supported by the evidence as written (yes / no; why)?",
               "Should the verifier have changed it (no / WEAKEN / REMOVE)?"],
}


def pick(run: str, cond: str, probe: str, decision: str) -> dict:
    for r in (1, 2, 3):
        rec = json.loads((ROOT / "v2" / "outputs" / "e1e2" / run / cond / f"{probe}__r{r}.json").read_text(encoding="utf-8"))
        if rec["decision"] == decision:
            return rec
    raise SystemExit(f"no {decision} run for {run}/{cond}/{probe}")


def context(pkg, key: str | None) -> str:
    if key == "table_note":
        return f"Table note: {pkg.results_tables[0].notes}"
    if key == "setup":
        s = pkg.experimental_setup
        i = s.find("Pre-specified robustness criterion")
        return "Setup: " + (s[i:] if i >= 0 else s)
    if key == "methods_credited":
        return f"Methods summary (package text, not the cited excerpt): {pkg.methods_summary}"
    return ""


def main() -> int:
    probes = {p["probe_id"]: p for p in json.loads(
        (ROOT / "v2" / "data" / "dev_probes_batch1.json").read_text(encoding="utf-8"))["probes"]}
    cases = {c.case_id: c for c in load_cases(ROOT / "data" / "synthetic" / "dev.jsonl")}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md = ["# E2 targeted review sheet (students)", "",
          "Twelve items selected from the DEV runs `e1e2_v1` and `e2b_v1`. Please answer the questions in "
          "`E2_REVIEW_ANSWERS.csv` (or below each item). Judge only from the evidence shown. Levels follow "
          "`docs/BENCHMARK_SPEC.md` section 4: 2 = the strong form, 1 = a narrower or qualified form, 0 = no claim of "
          "that kind. **The 'AI preliminary check' is the coordinating agent's reading, not a student judgement.** "
          "Please form your own view first, and record disagreements.", ""]
    rows = []
    for item, why, run, cond, pid, dec, ids, ctx_key, ai in ITEMS:
        rec = pick(run, cond, pid, dec)
        p = probes[pid]
        pkg = cases[p["case_id"]].package
        store = EvidenceStore.from_package(pkg)
        ev = []
        for i in ids:
            it = store.get(i)
            assert it is not None, (pid, i)
            ev.append(f"  * `{i}` ({it.label}): {it.text}")
        extra = context(pkg, ctx_key)
        qs = QUESTIONS["ACCEPT" if dec == "ACCEPT" else "default"]
        md += [f"## {item}. {why}", "",
               f"* Source: run `{run}`, {cond}, probe `{pid}` (case `{p['case_id']}`, gold level "
               f"{p['case_gold_level']}), repeat {rec['repeat']}; decision **{rec['decision']}**",
               f"* Research question: {pkg.question}",
               f"* **Original sentence:** {p['draft_text']}",
               "* **Relevant evidence:**", *ev]
        if extra:
            md.append(f"  * {extra}")
        md.append(f"* **Revised sentence:** {rec['revised_text'] if dec != 'ACCEPT' else '(accepted unchanged)'}")
        md += [f"* AI preliminary check (not a student judgement): {ai}", "", "Questions:", ""]
        md += [f"{k}. {q}" for k, q in enumerate(qs, 1)]
        md.append("")
        rows.append({"item": item, "probe_id": pid, "run": run, "condition": cond, "repeat": rec["repeat"],
                     "decision": rec["decision"], "q1_level": "", "q2_unsupported": "", "q3_decision_ok": "",
                     "reviewer": "", "notes": ""})
    (OUT_DIR / "E2_REVIEW_SHEET.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    with open(OUT_DIR / "E2_REVIEW_ANSWERS.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} items -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
