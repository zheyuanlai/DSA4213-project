"""Stage orchestration for the AI-judged evaluation extension (protocol §4).

Builds blinded prompts from ``evaluation.extended_data`` and runs judges through ``evaluation.judges``.
Writes blinded packets, judge readings, checklists, adjudications and consensus files under
``annotation/ai_extended/``. Condition identities are never read here except through the lineage of draft
and final texts, which is needed to form "Version X / Version Y" pairs and is never shown as such.
"""
from __future__ import annotations

import hashlib
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Optional

from evaluation import atomic_claims as ac
from evaluation.extended_data import ROOT, FamilyData, unit_id
from evaluation.judges import (
    ADJUDICATOR, JUDGE_A, JUDGE_B, JudgeError, JudgeSpec, call_judge, fill, load_prompt,
)
from evaluation.numeric_fidelity import EvidenceValues, check_assertion, evaluate, ExpressionError
from src.render import render_package

EXT = ROOT / "annotation" / "ai_extended"


def _dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _seeded(alias: str, salt: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"{alias}|{salt}".encode()).hexdigest()[:12], 16))


# ----------------------------------------------------------------------------- packets
def build_packets(data: FamilyData, out_root: Path = EXT / "packets") -> dict[str, dict[str, Any]]:
    packets = {}
    for case_id, case in sorted(data.cases.items()):
        alias = data.aliases[case_id]
        texts = data.texts_of_case(case_id)
        order = list(range(len(texts)))
        _seeded(alias, "passages").shuffle(order)
        passages = []
        for label_idx, ti in enumerate(order):
            t = texts[ti]
            passages.append({"label": chr(ord("A") + label_idx), "text_id": t.text_id,
                             "sentences": [{"unit_id": unit_id(case_id, s), "text": s} for s in t.sentences]})
        units = {u["unit_id"]: u["text"] for p in passages for u in p["sentences"]}
        packets[alias] = {"family": data.family.name, "alias": alias, "package_markdown": render_package(case.package),
                          "passages": passages, "units": dict(sorted(units.items()))}
        path = out_root / data.family.name / f"{alias}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(packets[alias], indent=1, ensure_ascii=False), encoding="utf-8")
    return packets


def passages_block(packet: dict[str, Any], labels: Optional[set[str]] = None) -> str:
    out = []
    for p in packet["passages"]:
        if labels is not None and p["label"] not in labels:
            continue
        out.append(f"### Passage {p['label']}\n" + "\n".join(f"[{u['unit_id']}] {u['text']}" for u in p["sentences"]))
    return "\n\n".join(out)


def data_segments(packet: dict[str, Any], claims: list[dict[str, Any]] = ()) -> list[str]:
    segs = [packet["package_markdown"]] + list(packet["units"].values())
    for c in claims:
        segs += [c["span"], c["proposition"], *c["entities"], *c["metrics"], *c["datasets"], *c["qualifiers"]]
        segs += [n["as_written"] for n in c["numbers"]]
        segs += [str(n["unit"]) for n in c["numbers"] if n.get("unit")]
    return segs


def forbidden_texts(family: str, case_id: str) -> list[str]:
    """Gold and author text that must never reach a judge (checked as substrings)."""
    out: list[str] = []
    paths = {"synthetic": ROOT / "private" / "gold" / "test_gold.jsonl",
             "diagnostic": ROOT / "private" / "gold" / "diagnostic_gold.jsonl"}
    if family in paths and paths[family].exists():
        for r in load_jsonl(paths[family]):
            if r["case_id"] == case_id:
                out += [r.get("gold_decision", ""), r.get("justification", ""), r.get("focal_proposition", ""),
                        r.get("pair_contrast", "")]
                out += list((r.get("level_descriptors") or {}).values())
    if family == "real":
        p = ROOT / "private" / "real_papers" / "author_claims.jsonl"
        if p.exists():
            for r in load_jsonl(p):
                if r.get("case_id") == case_id:
                    out += [v for v in r.values() if isinstance(v, str) and len(v) > 40]
    return out


def _parallel(jobs: list[tuple[str, Callable[[], Any]]], workers: int) -> dict[str, Any]:
    results, errors = {}, {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn): key for key, fn in jobs}
        for f in as_completed(futs):
            key = futs[f]
            try:
                results[key] = f.result()
                print(f"  done {key}", flush=True)
            except (JudgeError, ValueError) as e:
                errors[key] = str(e)
                print(f"  FAILED {key}: {str(e)[:300]}", flush=True)
    if errors:
        raise RuntimeError(f"{len(errors)} job(s) failed: {sorted(errors)}")
    return results


# ----------------------------------------------------------------------------- extraction
def run_extraction(data: FamilyData, packets: dict[str, dict[str, Any]], judge: JudgeSpec = JUDGE_A,
                   workers: int = 4) -> list[dict[str, Any]]:
    tmpl, _ = load_prompt("extract")
    inv = {v: k for k, v in data.aliases.items()}

    def job(alias: str) -> list[dict[str, Any]]:
        pk = packets[alias]
        units_block = "\n".join(f"- {uid}: \"{txt}\"" for uid, txt in pk["units"].items())
        prompt = fill(tmpl, PACKAGE=pk["package_markdown"], PASSAGES=passages_block(pk), UNITS=units_block)
        res = call_judge(judge, "extract", f"{data.family.name}_{alias}", "extract", prompt,
                         data_segments=data_segments(pk), forbidden_texts=forbidden_texts(data.family.name, inv[alias]),
                         validator=lambda p: ac.extraction_problems(p, pk["units"]))
        return ac.parse_extraction(res.parsed, pk["units"], data.family.name, alias)

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(packets)], workers)
    claims = [c for a in sorted(res) for c in res[a]]
    _dump_jsonl(EXT / "claims" / f"{data.family.name}.jsonl", claims)
    return claims


# ----------------------------------------------------------------------------- verification
def claims_block(pk: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_unit.setdefault(c["unit_id"], []).append(c)
    out = []
    for uid, cs in by_unit.items():
        out.append(f"[{uid}] \"{pk['units'][uid]}\"")
        for c in cs:
            out.append(f"  - claim {c['claim_id']} ({c['claim_type']}): span \"{c['span']}\" | proposition: {c['proposition']}")
            for n in c["numbers"]:
                out.append(f"      number {n['number_id']}: \"{n['as_written']}\" (value {n['value']:g}, comparator {n['comparator']}, "
                           f"role {n['role']}{', approximate' if n['approximate'] else ''})")
    return "\n".join(out)


def dedup_key(c: dict[str, Any]) -> tuple:
    """Claims of one case with the same self-contained proposition and the same numbers are verified once."""
    return (c["alias"], ac.norm_span(c["proposition"]),
            tuple((ac.norm_span(n["as_written"]), n["comparator"], n["role"]) for n in c["numbers"]))


def representatives(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """(representative claims, claim_id -> representative claim_id)."""
    reps: dict[tuple, dict[str, Any]] = {}
    rep_of: dict[str, str] = {}
    for c in claims:
        r = reps.setdefault(dedup_key(c), c)
        rep_of[c["claim_id"]] = r["claim_id"]
    return list(reps.values()), rep_of


def expand_readings(readings: dict[str, dict[str, Any]], claims: list[dict[str, Any]],
                    rep_of: dict[str, str]) -> dict[str, dict[str, Any]]:
    by_id = {c["claim_id"]: c for c in claims}
    out = {}
    for c in claims:
        rid = rep_of[c["claim_id"]]
        r = readings[rid]
        rep_nums = [n["number_id"] for n in by_id[rid]["numbers"]]
        nums = {n["number_id"]: r["numbers"][rep_nums[i]] for i, n in enumerate(c["numbers"])}
        out[c["claim_id"]] = {**r, "numbers": nums, "copied_from": rid if rid != c["claim_id"] else None}
    return out


def localize(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Short prompt-local IDs (c1, c1.n1) for one case; long hash IDs tokenize poorly and cost output tokens."""
    local, back = [], {}
    for i, c in enumerate(claims, start=1):
        cid = f"c{i}"
        back[cid] = c["claim_id"]
        nums = []
        for j, n in enumerate(c["numbers"], start=1):
            back[f"{cid}.n{j}"] = n["number_id"]
            nums.append({**n, "number_id": f"{cid}.n{j}"})
        local.append({**c, "claim_id": cid, "numbers": nums})
    return local, back


def run_verification(data: FamilyData, packets: dict[str, dict[str, Any]], claims: list[dict[str, Any]],
                     judge: JudgeSpec, workers: int = 3) -> dict[str, dict[str, Any]]:
    tmpl, _ = load_prompt("verify")
    inv = {v: k for k, v in data.aliases.items()}
    reps, rep_of = representatives(claims)
    by_alias: dict[str, list[dict[str, Any]]] = {}
    for c in reps:
        by_alias.setdefault(c["alias"], []).append(c)

    def job(alias: str) -> dict[str, dict[str, Any]]:
        pk = packets[alias]
        local, back = localize(by_alias[alias])
        prompt = fill(tmpl, PACKAGE=pk["package_markdown"], PASSAGES=passages_block(pk), CLAIMS=claims_block(pk, local))
        res = call_judge(judge, "verify", f"{data.family.name}_{alias}", "verify", prompt,
                         data_segments=data_segments(pk, local), forbidden_texts=forbidden_texts(data.family.name, inv[alias]),
                         validator=lambda p: ac.verification_problems(p, local))
        return {back[k]: {**v, "numbers": {back[n]: m for n, m in v["numbers"].items()}}
                for k, v in ac.parse_readings(res.parsed, judge.name).items()}

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(by_alias)], workers)
    rep_readings = {cid: r for a in sorted(res) for cid, r in res[a].items()}
    readings = expand_readings(rep_readings, claims, rep_of)
    _dump_jsonl(EXT / "readings" / f"{data.family.name}_verify_{judge.name}.jsonl",
                [{"claim_id": k, **v} for k, v in sorted(readings.items())])
    return readings


# ----------------------------------------------------------------------------- checklists
def run_checklists(data: FamilyData, packets: dict[str, dict[str, Any]], workers: int = 4) -> dict[str, Any]:
    build_t, _ = load_prompt("checklist_build")
    review_t, _ = load_prompt("checklist_review")
    inv = {v: k for k, v in data.aliases.items()}

    def job(alias: str) -> dict[str, Any]:
        case = data.cases[inv[alias]]
        pk = packets[alias]
        ev = EvidenceValues.from_package(case.package)
        from src.evidence_store import EvidenceStore
        store = EvidenceStore.from_package(case.package)
        b = call_judge(JUDGE_A, "checklist_build", f"{data.family.name}_{alias}", "checklist_build",
                       fill(build_t, PACKAGE=pk["package_markdown"]), data_segments=[pk["package_markdown"]],
                       forbidden_texts=forbidden_texts(data.family.name, inv[alias])).parsed
        items_md = "\n".join(f"- {f['finding_id']} [{f['polarity']}, {f['kind']}, {f['importance']}; evidence "
                             f"{', '.join(f['evidence_ids'])}]: {f['description']}" for f in b["findings"])
        r = call_judge(JUDGE_B, "checklist_review", f"{data.family.name}_{alias}", "checklist_review",
                       fill(review_t, PACKAGE=pk["package_markdown"], CHECKLIST=items_md),
                       data_segments=[pk["package_markdown"], items_md],
                       forbidden_texts=forbidden_texts(data.family.name, inv[alias])).parsed
        return merge_checklist(alias, b, r, ev, store.has)

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(packets)], workers)
    out = {"family": data.family.name, "procedure": "protocol §6: Judge A build, Judge B review, deterministic merge",
           "checklists": {a: res[a] for a in sorted(res)}}
    path = EXT / "checklists" / f"{data.family.name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=1, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    (path.with_suffix(".sha256")).write_text(hashlib.sha256(text.encode()).hexdigest() + "\n")
    return out


def merge_checklist(alias: str, build: dict[str, Any], review: dict[str, Any], ev: EvidenceValues,
                    has_id: Callable[[str], bool]) -> dict[str, Any]:
    """Deterministic merge rule of protocol §6 (every change logged)."""
    log: list[str] = []
    verdict = {r["item_id"]: r for r in review["item_reviews"]}
    findings = []
    for f in build["findings"]:
        v = verdict.get(f["finding_id"], {}).get("verdict", "VALID")
        bad_ids = [e for e in f["evidence_ids"] if not has_id(e)]
        if v == "UNSUPPORTED":
            log.append(f"dropped {f['finding_id']}: reviewer marked UNSUPPORTED ({verdict[f['finding_id']]['comment']})")
            continue
        if bad_ids:
            log.append(f"{f['finding_id']}: unknown evidence ids {bad_ids} removed")
        findings.append({**f, "evidence_ids": [e for e in f["evidence_ids"] if has_id(e)], "source": "build",
                         "review_verdict": v})
    k = len(build["findings"])
    for m in review["missing_core_findings"][:2]:
        ids = [e for e in m["evidence_ids"] if has_id(e)]
        if not ids:
            log.append(f"reviewer-proposed finding not added (no valid evidence ids): {m['description'][:60]}")
            continue
        k += 1
        findings.append({"finding_id": f"F{k}", "description": m["description"], "polarity": m["polarity"],
                         "kind": m["kind"], "importance": "core", "evidence_ids": ids, "source": "review",
                         "review_verdict": "PROPOSED"})
        log.append(f"added F{k} proposed by reviewer")
    facts = []
    kept_ids = {f["finding_id"] for f in findings}
    for n in build["numeric_facts"]:
        try:
            val, names = evaluate(n["expression"], ev)
        except ExpressionError as e:
            log.append(f"dropped {n['fact_id']}: expression invalid ({e})")
            continue
        tol = 0.5 * 10 ** -_decimals(n["value"]) + 1e-9
        if abs(val - float(n["value"])) > max(tol, 1e-6 * abs(val)):
            log.append(f"dropped {n['fact_id']}: expression gives {val:g}, stated {n['value']:g}")
            continue
        facts.append({**n, "computed_value": val, "operands": sorted(names.values()),
                      "finding_id": n["finding_id"] if n["finding_id"] in kept_ids else None})
    return {"alias": alias, "findings": findings, "numeric_facts": facts, "merge_log": log,
            "reviewer_comments": review["item_reviews"]}


def _decimals(v: float) -> int:
    s = f"{v:.10g}"
    return len(s.split(".")[1]) if "." in s and "e" not in s else 0


# ----------------------------------------------------------------------------- coverage
def coverage_items(data: FamilyData, alias: str, checklist: dict[str, Any]) -> list[dict[str, Any]]:
    items = [{"item_id": f["finding_id"], "description": f["description"], "polarity": f["polarity"],
              "importance": f["importance"], "source": "checklist"} for f in checklist["findings"]]
    if data.family.name == "diagnostic":
        inv = {v: k for k, v in data.aliases.items()}
        gold = {r["case_id"]: r for r in load_jsonl(ROOT / "private" / "gold" / "diagnostic_gold.jsonl")}[inv[alias]]
        items += [{"item_id": "G" + f["finding_id"].lstrip("f"), "description": f["description"],
                   "polarity": f.get("polarity", "neutral"), "importance": "core", "source": "gold_required"}
                  for f in gold["required_findings"]]
    return items


def run_coverage(data: FamilyData, packets: dict[str, dict[str, Any]], checklists: dict[str, Any], judge: JudgeSpec,
                 workers: int = 3) -> dict[tuple[str, str], dict[str, Any]]:
    tmpl, _ = load_prompt("coverage")
    inv = {v: k for k, v in data.aliases.items()}

    def job(alias: str):
        pk = packets[alias]
        items = coverage_items(data, alias, checklists["checklists"][alias])
        md = "\n".join(f"- {i['item_id']} ({i['polarity']}): {i['description']}" for i in items)
        labels = {p["label"] for p in pk["passages"]}
        prompt = fill(tmpl, PACKAGE=pk["package_markdown"], CHECKLIST=md, PASSAGES=passages_block(pk))

        def validator(p):
            got = {(j["passage"].replace("Passage ", "").strip(), j["item_id"]) for j in p["judgments"]}
            want = {(lab, i["item_id"]) for lab in labels for i in items}
            return [] if got == want and len(p["judgments"]) == len(want) else \
                [f"coverage pairs mismatch: missing {sorted(want - got)[:4]}, extra {sorted(got - want)[:4]}"]

        res = call_judge(judge, "coverage", f"{data.family.name}_{alias}", "coverage", prompt,
                         data_segments=data_segments(pk) + [md] + [i["description"] for i in items],
                         forbidden_texts=_forbidden_for_coverage(data.family.name, inv[alias]), validator=validator)
        lab2tid = {p["label"]: p["text_id"] for p in pk["passages"]}
        return {(lab2tid[j["passage"].replace("Passage ", "").strip()], j["item_id"]):
                {"status": j["status"], "justification": j["justification"], "judge": judge.name, "alias": alias}
                for j in res.parsed["judgments"]}

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(packets)], workers)
    out = {k: v for a in sorted(res) for k, v in res[a].items()}
    _dump_jsonl(EXT / "readings" / f"{data.family.name}_coverage_{judge.name}.jsonl",
                [{"text_id": k[0], "item_id": k[1], **v} for k, v in sorted(out.items())])
    return out


def _forbidden_for_coverage(family: str, case_id: str) -> list[str]:
    # required-finding descriptions are the checklist itself; gold level/decision/justification stay forbidden
    return forbidden_texts(family, case_id)


# ----------------------------------------------------------------------------- alignment
def alignment_pairs(data: FamilyData, claims: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """(draft, final) text pairs per case, restricted to claims in sentences that differ."""
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        by_unit.setdefault(c["unit_id"], []).append(c)
    pairs: dict[str, list[dict[str, Any]]] = {}
    seen = set()
    for (case_id, cond), rv in sorted(data.runs.items()):
        if rv.status != "completed" or not rv.draft_text_id or rv.draft_text_id == rv.final_text_id:
            continue
        key = (rv.draft_text_id, rv.final_text_id)
        if key in seen:
            continue
        seen.add(key)
        du, fu = data.texts[rv.draft_text_id].units, data.texts[rv.final_text_id].units
        xs = [c for u in du if u not in fu for c in by_unit.get(u, [])]
        ys = [c for u in fu if u not in du for c in by_unit.get(u, [])]
        pid = "P-" + hashlib.sha256(f"{key[0]}|{key[1]}".encode()).hexdigest()[:8]
        pairs.setdefault(data.aliases[case_id], []).append(
            {"pair_id": pid, "draft_text_id": key[0], "final_text_id": key[1], "x_claims": xs, "y_claims": ys})
    return pairs


def run_alignment(data: FamilyData, packets: dict[str, dict[str, Any]], claims: list[dict[str, Any]], judge: JudgeSpec,
                  workers: int = 3) -> dict[str, dict[str, Any]]:
    tmpl, _ = load_prompt("align")
    inv = {v: k for k, v in data.aliases.items()}
    pairs = alignment_pairs(data, claims)
    trivial: dict[str, dict[str, Any]] = {}

    def fmt(c):
        return f"    - {c['claim_id']}: {c['proposition']}  [span: \"{c['span']}\"]"

    jobs = []
    for alias, ps in sorted(pairs.items()):
        need = [p for p in ps if p["x_claims"] and p["y_claims"]]
        for p in ps:
            if not (p["x_claims"] and p["y_claims"]):  # all deleted or all added: no judgement needed
                trivial[p["pair_id"]] = {"pair_id": p["pair_id"], "judge": "deterministic",
                                         "x_claims": [{"claim_id": c["claim_id"], "relation": "DELETED", "direction": None,
                                                       "matched_y": []} for c in p["x_claims"]],
                                         "added_y": [c["claim_id"] for c in p["y_claims"]]}
        if not need:
            continue

        def job(alias=alias, need=need):
            pk = packets[alias]
            blocks = []
            for p in need:
                blocks.append(f"### Pair {p['pair_id']}\n  Version X claims:\n" + "\n".join(fmt(c) for c in p["x_claims"]) +
                              "\n  Version Y claims:\n" + "\n".join(fmt(c) for c in p["y_claims"]))
            prompt = fill(tmpl, PACKAGE=pk["package_markdown"], PAIRS="\n\n".join(blocks))
            want = {p["pair_id"]: ({c["claim_id"] for c in p["x_claims"]}, {c["claim_id"] for c in p["y_claims"]}) for p in need}

            def validator(parsed):
                probs = []
                got = {q["pair_id"]: q for q in parsed["pairs"]}
                if set(got) != set(want):
                    return [f"pair ids mismatch {sorted(set(want) ^ set(got))}"]
                for pid, (xs, ys) in want.items():
                    q = got[pid]
                    if sorted(x["claim_id"] for x in q["x_claims"]) != sorted(xs):
                        probs.append(f"{pid}: x claims mismatch")
                    for x in q["x_claims"]:
                        if not set(x["matched_y"]) <= ys:
                            probs.append(f"{pid}/{x['claim_id']}: unknown matched_y")
                    if not set(q["added_y"]) <= ys:
                        probs.append(f"{pid}: unknown added_y")
                return probs

            segs = data_segments(pk, [c for p in need for c in p["x_claims"] + p["y_claims"]])
            res = call_judge(judge, "align", f"{data.family.name}_{alias}", "align", prompt, data_segments=segs,
                             forbidden_texts=forbidden_texts(data.family.name, inv[alias]), validator=validator)
            return {q["pair_id"]: {**q, "judge": judge.name} for q in res.parsed["pairs"]}

        jobs.append((alias, job))
    res = _parallel(jobs, workers)
    out = dict(trivial)
    for a in res.values():
        out.update(a)
    meta = {p["pair_id"]: {k: p[k] for k in ("draft_text_id", "final_text_id")} | {"alias": alias,
            "x_claims": [c["claim_id"] for c in p["x_claims"]], "y_claims": [c["claim_id"] for c in p["y_claims"]]}
            for alias, ps in pairs.items() for p in ps}
    _dump_jsonl(EXT / "readings" / f"{data.family.name}_align_{judge.name}.jsonl",
                [{**meta[k], **v} for k, v in sorted(out.items())])
    return out
