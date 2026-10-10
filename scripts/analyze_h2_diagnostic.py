"""Analyze the EXPLORATORY H2 diagnostic traces (pre-registered measures in docs/H2_DIAGNOSTIC.md).

  python scripts/analyze_h2_diagnostic.py
Writes results/h2_diagnostic/{per_run.csv,summary.json,TABLES.md}. All inputs are DEV cases (public gold).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.auto_metrics import focal_terms_from_gold, method_terms, proxy_level  # noqa: E402
from src.runner import load_cases  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "h2_diagnostic" / "deepseek__deepseek-v4-flash-0731"
# Pre-registered: rationale phrases indicating the verifier noticed the claim is weaker than the evidence allows.
RECOGNITION = re.compile(r"understat|could be stronger|stronger (?:claim|statement|conclusion)|could (?:also )?(?:be )?"
                         r"(?:strengthen|mention|note|add|report|state)|does not (?:mention|report|state|include|note)|"
                         r"\bomit|not mentioned|more informative|weaker than|incomplete|but (?:the claim )?(?:only|does not)", re.I)


def decisive_hit(returned: set[str], decisive: list[str]) -> bool:
    for d in decisive:
        if d in returned or any(r.startswith(d + ".") for r in returned):
            return True
    return False


def main() -> int:
    drafts = {d["draft_id"]: d for d in json.loads((ROOT / "data/diagnostic/h2_counterfactual_drafts.json").read_text())}
    cases = {c.case_id: c for c in load_cases(ROOT / "data/synthetic/dev.jsonl")}
    gold = {json.loads(l)["case_id"]: json.loads(l) for l in (ROOT / "data/synthetic/gold/dev_gold.jsonl").read_text().splitlines()}
    rows = []
    for cond in ("C4", "C5"):
        for did, d in drafts.items():
            r = json.loads((OUT_ROOT / cond / f"{did}.json").read_text())
            t = r["claim_traces"][0]
            dec = t["decision"]
            returned = {i for o in t["observations"] for i in o["returned_ids"]}
            pkg = cases[d["case_id"]].package
            cat = cases[d["case_id"]].category
            ft, ot = focal_terms_from_gold(gold[d["case_id"]], pkg), method_terms(pkg)
            p_draft = proxy_level(cat, d["draft_text"], ft, ot)
            p_final = proxy_level(cat, r["final_passage"], ft, ot)
            rows.append({
                "draft_id": did, "pair": d["pair"], "role": d["role"], "case_id": d["case_id"], "gold": d["dev_gold_level"],
                "condition": cond, "decision": dec["decision"], "valid": dec["valid"],
                "tools": " > ".join(a["tool"] for a in t["actions"]), "n_tools": len(t["actions"]),
                "ignored_parallel": t.get("ignored_parallel_calls", 0),
                "decisive_retrieved": decisive_hit(returned, d["decisive_evidence_ids"]) if d["role"] == "understated" else "",
                "recognized_understatement_regex": bool(RECOGNITION.search(dec["rationale"] or "")),
                "text_changed": r["final_passage"].strip() != d["draft_text"].strip(),
                "proxy_draft_UNVALIDATED": p_draft, "proxy_final_UNVALIDATED": p_final,
                "rationale": dec["rationale"], "final_text": r["final_passage"], "cost_usd": r["cost_usd"],
            })
    out = ROOT / "results" / "h2_diagnostic"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "per_run.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    by = {(x["draft_id"], x["condition"]): x for x in rows}
    und = [d for d in drafts if drafts[d]["role"] == "understated"]
    ctl = [d for d in drafts if drafts[d]["role"] == "control"]
    summ = {}
    for cond in ("C4", "C5"):
        summ[cond] = {
            "strengthen_on_understated": sum(by[(d, cond)]["decision"] == "STRENGTHEN" for d in und),
            "strengthen_on_controls_FALSE": sum(by[(d, cond)]["decision"] == "STRENGTHEN" for d in ctl),
            "decisive_evidence_retrieved_understated": sum(bool(by[(d, cond)]["decisive_retrieved"]) for d in und),
            "accept_on_understated": sum(by[(d, cond)]["decision"] == "ACCEPT" for d in und),
            "recognized_but_accept_understated_regex": sum(by[(d, cond)]["decision"] == "ACCEPT" and by[(d, cond)]["recognized_understatement_regex"] for d in und),
            "decisions_understated": {d: by[(d, cond)]["decision"] for d in und},
            "decisions_controls": {d: by[(d, cond)]["decision"] for d in ctl},
            "mean_tools_per_claim": sum(by[(d, cond)]["n_tools"] for d in drafts) / len(drafts),
            "cost_usd": round(sum(by[(d, cond)]["cost_usd"] for d in drafts), 6),
        }
    summ["C4_vs_C5_identical_final_text"] = sum(by[(d, "C4")]["final_text"].strip() == by[(d, "C5")]["final_text"].strip() for d in drafts)
    summ["C4_vs_C5_proxy_final_differs_UNVALIDATED"] = sum(
        by[(d, "C4")]["proxy_final_UNVALIDATED"] != by[(d, "C5")]["proxy_final_UNVALIDATED"] for d in drafts
        if by[(d, "C4")]["proxy_final_UNVALIDATED"] is not None)
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    lines = ["| draft | role | gold | cond | decision | tools | decisive evidence retrieved | recognition phrase in rationale | text changed | PROXY draft→final |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['draft_id']} | {x['role']} | {x['gold']} | {x['condition']} | {x['decision']} | {x['tools']} | "
                     f"{x['decisive_retrieved']} | {x['recognized_understatement_regex']} | {x['text_changed']} | "
                     f"{x['proxy_draft_UNVALIDATED']}→{x['proxy_final_UNVALIDATED']} |")
    (out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
