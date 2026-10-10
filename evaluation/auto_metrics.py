"""Automatic (non-human) metrics for run outputs.

Two classes of metric, kept strictly apart in every output:

* RULE-VERIFIED (deterministic, checkable against the package): output validity,
  numeric grounding (every number in the final passage must be present in, or derivable
  from, the package), NUM-case numeric-fact value recall, costs, tokens, latency,
  tool trajectories, verifier decisions.
* PROXY / UNVALIDATED (lexical heuristics, NOT a substitute for human labels):
  lexical expressed-strength level `proxy_level` for SIG/ROB/GEN/CON/EFF focal claims
  and lexical negative-finding mention for NEG. Never report these as calibration accuracy;
  they exist to sanity-check pipelines and to be compared with human labels later.

Gold is read here (evaluation side), never by the inference code.
"""
from __future__ import annotations

import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Optional

from src.package_schema import CaseRecord, ResearchPackage
from src.render import render_package

NUM_RE = re.compile(r"(?<![A-Za-z@_\-\d.])[-−–]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![A-Za-z\d])|(?<![A-Za-z@_\-\d.])[-−–]?\d+(?:\.\d+)?(?![A-Za-z\d])")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _to_float(s: str) -> float:
    return float(s.replace(",", "").replace("−", "-").replace("–", "-"))


def _decimals(s: str) -> int:
    s = s.replace(",", "")
    return len(s.split(".")[1]) if "." in s else 0


def numbers_in(text: str) -> list[tuple[str, float]]:
    out = []
    for m in NUM_RE.finditer(text or ""):
        tok = m.group(0)
        try:
            out.append((tok, _to_float(tok)))
        except ValueError:
            pass
    return out


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text or "") if s.strip()]


# ----------------------------------------------------------------------------- grounding
def groundable_values(pkg: ResearchPackage) -> set[float]:
    """Numbers present in the package text plus a bounded set of derived values.

    Scale conversions are applied only to RAW values: x100 / /100 (fraction <-> percent) for any raw
    number, and x1000 / /1000 (ms <-> s) only for cells whose unit is a time unit."""
    raw: set[float] = {v for _, v in numbers_in(render_package(pkg))}
    derived: set[float] = set()
    time_vals: set[float] = set()
    for t in pkg.results_tables:
        cols = [c.column_id for c in t.columns]
        units = {c.column_id: (c.unit or "").lower() for c in t.columns}
        grid = [[(r.cells[c].value if c in r.cells else None) for c in cols] for r in t.rows]
        for r in t.rows:
            for c, cell in r.cells.items():
                if cell.value is not None and (units.get(c) in ("ms", "s", "sec", "seconds", "milliseconds")
                                               or re.search(r"\b(ms|s)\b", c)):
                    time_vals.add(cell.value)
        for row in grid:
            nums = [x for x in row if x is not None]
            for a, b in itertools.permutations(nums, 2):
                _add_derived(derived, a, b)
        for j in range(len(cols)):
            col = [row[j] for row in grid if row[j] is not None]
            for a, b in itertools.permutations(col, 2):
                _add_derived(derived, a, b)
            if col:
                derived.add(sum(col) / len(col))
        for r1, r2 in itertools.permutations(grid, 2):
            diffs = [a - b for a, b in zip(r1, r2) if a is not None and b is not None]
            if diffs:
                derived.add(sum(diffs) / len(diffs))
    for s in pkg.statistical_tests:
        for v in (s.ci_low, s.ci_high, s.p_value, s.statistic, s.df, s.n, s.alpha, s.ci_level):
            if v is not None:
                raw.add(float(v))
        if s.ci_low is not None and s.ci_high is not None:
            derived.add((s.ci_low + s.ci_high) / 2)
        if s.ci_level:
            raw.add(s.ci_level * 100)
    scaled = {v * k for v in raw for k in (100.0, 0.01)} | {v * k for v in time_vals for k in (1000.0, 0.001)}
    # differences of fractions reported in percentage points, and vice versa
    scaled |= {v * k for v in derived for k in (100.0, 0.01)}
    # Known limitation: with many derived values, a wrong number can coincide with a derivable one
    # (false "grounded"); the metric is therefore a LOWER bound on ungrounded numbers.
    return raw | derived | scaled


def _add_derived(vals: set[float], a: float, b: float) -> None:
    vals.add(a - b)
    vals.add(abs(a - b))
    if b != 0:
        vals.add(a / b)
        vals.add((a - b) / abs(b) * 100)
        vals.add(abs(a - b) / abs(b) * 100)


def is_grounded(tok: str, x: float, vals: set[float]) -> bool:
    if float(x).is_integer() and 0 <= abs(x) <= 10:
        return True  # small counts ("4 of 5", "three seeds") are not checked
    tol = 0.5 * 10 ** (-_decimals(tok)) + 1e-9
    ax = abs(x)
    return any(abs(ax - abs(v)) <= tol for v in vals)


def numeric_grounding(passage: str, pkg: ResearchPackage) -> dict[str, Any]:
    vals = groundable_values(pkg)
    nums = numbers_in(passage)
    ungrounded = [tok for tok, x in nums if not is_grounded(tok, x, vals)]
    return {"n_numbers": len(nums), "n_ungrounded": len(ungrounded), "ungrounded": ungrounded}


def numeric_fact_recall(passage: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    """NUM cases: value presence only (entity/row association needs human review)."""
    nums = numbers_in(passage)
    hits = []
    for f in facts:
        v, tol = float(f["value"]), float(f["tolerance"])
        found = False
        for tok, x in nums:
            for k in (1.0, 100.0, 0.01, 1000.0, 0.001):
                # tolerance scales with the conversion factor; never looser than the written precision
                t = max(tol * k, 0.5 * 10 ** (-_decimals(tok))) + 1e-9
                if abs(abs(x) - abs(v * k)) <= t:
                    found = True
        hits.append({"fact_id": f["fact_id"], "value_present": found})
    n = len(hits)
    return {"n_facts": n, "n_value_present": sum(h["value_present"] for h in hits),
            "value_recall": (sum(h["value_present"] for h in hits) / n) if n else None, "facts": hits}


# ---------------------------------------------------------------------- PROXY lexical levels
NEG = re.compile(r"\b(not|no|non|without|cannot|can't|unable|lack(?:s|ing)?|absence|absent|neither|nor|unclear|"
                 r"inconclusive|insufficient|unknown|untested|unevaluated|n't|never)\b|\bnon-", re.I)
NONSIG = re.compile(r"not (?:statistically )?significant|non-?significant|no (?:statistically )?significant|"
                    r"did not reach|not reach(?:ed)? significance|was not significant|were not significant", re.I)
PATTERNS = {
    "statistical_significance": {"l2": re.compile(r"significan|statistically|reliabl|p\s*[<=≤]\s*0?\.\d", re.I),
                                 "l1": re.compile(r"higher|better|outperform|exceed|improv|surpass|gain|advantage|"
                                                  r"lower (?:error|wer|mae|loss)|ahead", re.I)},
    "robustness": {"l2": re.compile(r"robust|stable|stability|maintain|resilien|insensitive|withstand", re.I),
                   "restrict": re.compile(r"\bonly\b|mild|moderate|up to|except|but\b|fail|exceed|severe|beyond|"
                                          r"degrad|somewhat|partial|largely", re.I)},
    "generalization": {"l2": re.compile(r"generali[sz]|transfer|carr(?:y|ies|ied) over|out-of-domain|"
                                        r"(?:held-out|unseen|new|other) (?:domain|famil|map|text domain|collection)|beyond the training|"
                                        r"out-of-distribution", re.I),
                       "restrict": re.compile(r"\bonly\b|single|\bone held-out|\bone (?:new |unseen )?domain|may|"
                                              r"might|suggest|preliminary", re.I)},
    "consistency": {"l2": re.compile(r"\ball (?:\w+ ){0,2}(?:datasets|benchmarks|graphs|tasks|suites|domains|sets|"
                                     r"collections)|\bevery\b|consistent|uniform|across the board|each of the", re.I)},
    "efficiency": {"l2": re.compile(r"faster|speed-?up|lower (?:\w+ )?latency|reduc\w* (?:\w+ )?(?:latency|runtime|"
                                    r"wall-clock|time)|quicker|less time|shorter (?:runtime|time)|"
                                    r"\d(?:\.\d+)?\s*[×x]\s*(?:faster|lower|speed)|reduction in (?:\w+ ){0,2}(?:latency|runtime|time)|"
                                    r"(?:latency|runtime|time) (?:was|is|were) (?:\w+ ){0,3}(?:lower|shorter|reduced)", re.I),
                   "l1": re.compile(r"fewer (?:\w+ ){0,2}(?:steps|nfe|function evaluations|flops|tflops|passes|"
                                    r"evaluations)|less compute|lower (?:\w+ ){0,2}(?:nfe|flops)|reduc\w* (?:\w+ ){0,2}(?:nfe|flops|"
                                    r"steps|passes)", re.I),
                   "deny": re.compile(r"not faster|slower|no (?:wall-clock )?speed|not (?:a )?(?:wall-clock )?speed|"
                                      r"comparable latency|not translate|did not (?:reduce|yield|translate)|"
                                      r"higher (?:\w+ )?latency than", re.I),
                   "qualify": re.compile(r"not (?:directly )?comparable|cannot be (?:directly )?compared|confound|"
                                         r"different (?:hardware|accelerator|precision)|not establish|may |might |could ", re.I)},
}
KOFN = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight)\s+(?:out\s+)?of\s+(?:the\s+)?(\d+|two|three|four|five|six|seven|eight)\b", re.I)
WORD2NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}


def _as_int(tok: str) -> int:
    return int(tok) if tok.isdigit() else WORD2NUM[tok.lower()]


def _focal_sentences(passage: str, focal_terms: list[str], other_terms: Optional[list[str]] = None) -> list[str]:
    """Sentences about the focal proposition: those naming every focal term, plus sentences that name
    no non-focal method/row (anaphoric follow-ups such as 'This advantage ...'). Sentences that only
    discuss a distractor (e.g. a weak baseline) are excluded."""
    ss = sentences(passage)
    if not focal_terms:
        return ss
    low = [s.lower() for s in ss]
    others = [o.lower() for o in (other_terms or []) if o.lower() not in {t.lower() for t in focal_terms}]
    keep = [s for s, l in zip(ss, low)
            if all(t.lower() in l for t in focal_terms) or not any(o in l for o in others)]
    return keep or ss


def _affirmed(rx: re.Pattern, s: str, after_neg: Optional[re.Pattern] = None) -> bool:
    """True if some match of rx in s is not locally negated (negation within 70 chars before the cue,
    or an optional category-specific negation right after it)."""
    for m in rx.finditer(s):
        before = s[max(0, m.start() - 70):m.start()]
        after = s[m.end():m.end() + 80]
        if NEG.search(before) or re.search(r"\bwhether\b", before, re.I):  # negated, or merely posed as a question
            continue
        if after_neg is not None and after_neg.search(after):
            continue
        return True
    return False


NOT_EVAL_AFTER = re.compile(r"\b(?:cannot|can't|could not|was not|were not|is not|are not|has not|have not|not)\s+"
                            r"(?:be\s+|been\s+)?(?:assessed|evaluated|established|determined|claimed|supported|tested|"
                            r"measured|examined|studied|addressed|inferred|concluded|answered)|\bunanswerable\b", re.I)


def proxy_level(category: str, passage: str, focal_terms: list[str], other_terms: Optional[list[str]] = None) -> Optional[int]:
    """PROXY / UNVALIDATED lexical estimate of the expressed focal strength (0/1/2)."""
    if not passage.strip():
        return 0
    ss = _focal_sentences(passage, focal_terms, other_terms)
    p = PATTERNS.get(category)
    if p is None:
        return None
    if category == "statistical_significance":
        if any(NONSIG.search(s) for s in ss) and not any(_affirmed(p["l2"], s) and not NONSIG.search(s) for s in ss):
            return 0
        if any(_affirmed(p["l2"], s) and not NONSIG.search(s) for s in ss):
            return 2
        return 1 if any(_affirmed(p["l1"], s) for s in ss) else 0
    if category in ("robustness", "generalization"):
        aff = [s for s in ss if _affirmed(p["l2"], s, NOT_EVAL_AFTER)]
        if not aff:
            return 0
        return 1 if all(p["restrict"].search(s) for s in aff) else 2
    if category == "consistency":
        if any(_affirmed(p["l2"], s) for s in ss):
            return 2
        for s in ss:
            for m in KOFN.finditer(s):
                k, n = _as_int(m.group(1)), _as_int(m.group(2))
                if k and n and k > n / 2 and k < n:
                    return 1
        if any(_affirmed(re.compile(r"\bmost\b|majority|generally|overall (?:better|higher)", re.I), s) for s in ss):
            return 1
        return 0
    if category == "efficiency":
        if any(p["deny"].search(s) for s in ss):
            return 0
        speed = [s for s in ss if _affirmed(p["l2"], s)]
        if speed:
            return 1 if any(p["qualify"].search(s) for s in ss) else 2
        return 1 if any(_affirmed(p["l1"], s) for s in ss) else 0
    return None


NEG_CUES = re.compile(r"lower|worse|underperform|below|regress|decrease|drop|declin|fell|falls|hurt|reduc|degrad|"
                      r"superior|exception|except|ahead|beat|outperformed by|favou?r(?:ed|s)? (?:the )?baseline|"
                      r"not significant|non-?significant|no significant|did not|does not|fail|loss|lost|trail|behind|"
                      r"higher (?:error|wer|mae|latency|loss)|−|-\d", re.I)


def finding_terms(desc: str, pkg: ResearchPackage) -> list[str]:
    """Entity terms (row labels / column headers / dataset-like names) mentioned in a finding description."""
    cands = set()
    for t in pkg.results_tables:
        for r in t.rows:
            cands.add(re.sub(r"\s*\(.*?\)", "", r.label).strip())
        for c in t.columns:
            cands.add(re.sub(r"\s*\(.*?\)", "", c.header).strip())
    return sorted({c for c in cands if len(c) >= 3 and c.lower() in desc.lower()}, key=len, reverse=True)


def proxy_negative_mentions(passage: str, findings: list[dict[str, Any]], pkg: ResearchPackage) -> dict[str, Any]:
    """PROXY: a negative finding counts as 'mentioned' if one sentence names its entity and has a negative cue."""
    ss = sentences(passage)
    res = []
    for f in findings:
        if f.get("polarity") not in ("negative", "null", "mixed"):
            continue
        terms = finding_terms(f["description"], pkg)
        hit = any(any(t.lower() in s.lower() for t in terms) and NEG_CUES.search(s) for s in ss) if terms else None
        res.append({"finding_id": f["finding_id"], "terms": terms, "mentioned_proxy": hit})
    scorable = [r for r in res if r["mentioned_proxy"] is not None]
    return {"n_negative_findings": len(res), "n_scorable": len(scorable),
            "proxy_recall": (sum(r["mentioned_proxy"] for r in scorable) / len(scorable)) if scorable else None,
            "findings": res}


def focal_terms_from_gold(gold: dict[str, Any], pkg: ResearchPackage) -> list[str]:
    fp = gold.get("focal_proposition") or ""
    return finding_terms(fp, pkg)


def method_terms(pkg: ResearchPackage) -> list[str]:
    """Method names: sides of 'A vs B' in the package's comparison descriptions, matched to table
    row labels / column headers (so dataset names are not mistaken for distractor methods)."""
    cands = {re.sub(r"\s*\(.*?\)", "", x).strip() for t in pkg.results_tables
             for x in [r.label for r in t.rows] + [c.header for c in t.columns]} - {""}
    sides: set[str] = set()
    for e in pkg.experiments:
        for c in e.comparisons:
            for m in re.finditer(r"([^:;,()]+?)\s+(?:vs\.?|versus)\s+([^:;,()]+)", c.description):
                sides |= {m.group(1).strip().lower(), m.group(2).strip().lower()}
    out = {c for c in cands if any(sd.startswith(c.lower()) or c.lower().startswith(sd) for sd in sides if len(sd) >= 3)}
    return sorted(out)


# ----------------------------------------------------------------------------- per-run rows
def run_row(rr: dict[str, Any], rec: CaseRecord, gold: Optional[dict[str, Any]]) -> dict[str, Any]:
    t = rr.get("totals", {})
    passage = rr.get("final_passage", "") or ""
    start = (rr.get("drafts") or [{}])[0].get("passage", "")
    row: dict[str, Any] = {
        "case_id": rr["case_id"], "condition": rr["condition"], "category": rec.category, "split": rec.split,
        "pair_id": rec.pair_id, "status": rr["status"], "failure": rr.get("failure"),
        "n_sentences": len(rr.get("final_sentences") or []), "n_words": len(passage.split()),
        "changed_from_start": passage.strip() != start.strip(),
        "cost_usd": t.get("cost_usd"), "cost_usd_condition_only": t.get("cost_usd_condition_only"),
        "n_model_calls": t.get("n_model_calls"), "n_tool_calls": t.get("n_tool_calls"),
        "prompt_tokens": t.get("prompt_tokens"), "completion_tokens": t.get("completion_tokens"),
        "reasoning_tokens": t.get("reasoning_tokens"), "latency_s": t.get("latency_s"),
        "n_claims": t.get("n_claims"), "n_invalid_decisions": t.get("n_invalid_decisions"),
        "n_protocol_errors": t.get("n_protocol_errors"), "n_ignored_parallel_calls": t.get("n_ignored_parallel_calls", 0),
        "any_cost_estimated": t.get("any_cost_estimated"),
    }
    for d in ("ACCEPT", "WEAKEN", "STRENGTHEN", "REMOVE", "FLAG"):
        row[f"dec_{d}"] = (t.get("decision_counts") or {}).get(d, 0)
    for tool in ("lookup_table", "get_test_metadata", "retrieve_passage", "compare_numbers"):
        row[f"tool_{tool}"] = (t.get("tool_counts") or {}).get(tool, 0)
    g = numeric_grounding(passage, rec.package)
    row.update({"n_numbers": g["n_numbers"], "n_ungrounded_numbers": g["n_ungrounded"],
                "ungrounded_numbers": "|".join(g["ungrounded"])})
    row["proxy_level_UNVALIDATED"] = None
    row["gold_level"] = None
    if gold is not None:
        row["gold_level"] = gold.get("gold_level")
        if rec.category in ("statistical_significance", "robustness", "generalization", "consistency", "efficiency"):
            ft, ot = focal_terms_from_gold(gold, rec.package), method_terms(rec.package)
            row["proxy_level_UNVALIDATED"] = proxy_level(rec.category, passage, ft, ot)
            row["proxy_start_level_UNVALIDATED"] = proxy_level(rec.category, start, ft, ot)
        if rec.category == "numerical_reporting":
            nr = numeric_fact_recall(passage, gold.get("numeric_facts", []))
            row["num_value_recall"] = nr["value_recall"]
        if rec.category == "negative_results":
            nm = proxy_negative_mentions(passage, gold.get("required_findings", []), rec.package)
            row["neg_proxy_recall_UNVALIDATED"] = nm["proxy_recall"]
    return row


def load_runs(out_root: Path, conditions: Iterable[str]) -> list[dict[str, Any]]:
    runs = []
    for c in conditions:
        for p in sorted((out_root / c).glob("*.json")):
            runs.append(json.loads(p.read_text()))
    return runs


def load_gold(paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
    g = {}
    for p in paths:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip():
                    d = json.loads(line)
                    g[d["case_id"]] = d
    return g


def trajectories(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Tool-selection behaviour per condition: first tool, sequences, tools/claim, stop reasons."""
    out: dict[str, Any] = {}
    for c in sorted({r["condition"] for r in runs}):
        firsts, seqs, ncalls, stops, decs = Counter(), Counter(), [], Counter(), Counter()
        for r in runs:
            if r["condition"] != c:
                continue
            for tr in r.get("claim_traces") or []:
                tools = [a["tool"] for a in tr["actions"]]
                firsts[tools[0] if tools else "(none)"] += 1
                seqs[" > ".join(tools) or "(none)"] += 1
                ncalls.append(len(tools))
                stops[tr.get("stop_reason", "")] += 1
                if tr.get("decision"):
                    decs[tr["decision"]["decision"]] += 1
        if ncalls:
            out[c] = {"n_claims": len(ncalls), "mean_tools_per_claim": sum(ncalls) / len(ncalls),
                      "dist_tools_per_claim": dict(Counter(ncalls)), "first_tool": dict(firsts),
                      "top_sequences": seqs.most_common(8), "stop_reasons": dict(stops), "decisions": dict(decs)}
    return out
