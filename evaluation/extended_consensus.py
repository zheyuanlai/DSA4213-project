"""Disagreement detection, blind adjudication and consensus freezing (protocol §4 stages 6–7, §7).

Readings are shown to the adjudicator as "Reading 1/2" in a seeded random order, so it cannot tell which
judge (model family) wrote which. Agreed fields are final; only disputed fields are taken from the
adjudicator. Numeric verdicts always come from the deterministic checker.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation import atomic_claims as ac
from evaluation.extended_data import FamilyData
from evaluation.extended_pipeline import (
    EXT, _dump_jsonl, _parallel, data_segments, forbidden_texts, load_jsonl, passages_block,
)
from evaluation.judges import ADJUDICATOR, call_judge, fill, load_prompt
from evaluation.numeric_fidelity import EvidenceValues


def replicate_dirs(replicate: Optional[str]) -> tuple[Path, Optional[Path], str]:
    """(adjudication dir, raw-record dir, cache salt). A replicate re-asks the identical prompts with a new cache
    salt and writes only under annotation/ai_extended/replicates/<name>/; the primary files are never touched."""
    if not replicate:
        return EXT / "adjudication", None, ""
    base = EXT / "replicates" / replicate
    return base / "adjudication", base / "raw", f"replicate={replicate}"


def _order(key: str) -> dict[str, str]:
    """Seeded random assignment of judges A/B to 'Reading 1/2'."""
    r = random.Random(int(hashlib.sha256(f"adj|{key}".encode()).hexdigest()[:12], 16))
    return {"1": "A", "2": "B"} if r.random() < 0.5 else {"1": "B", "2": "A"}


def _ev(data: FamilyData, alias: str) -> EvidenceValues:
    inv = {v: k for k, v in data.aliases.items()}
    return EvidenceValues.from_package(data.cases[inv[alias]].package)


def _readings(fam: str, kind: str, judge: str) -> list[dict[str, Any]]:
    return load_jsonl(EXT / "readings" / f"{fam}_{kind}_{judge}.jsonl")


# ----------------------------------------------------------------------------- claims
def claim_dispute_table(data: FamilyData) -> tuple[list[dict[str, Any]], dict, dict, dict]:
    fam = data.family.name
    claims = load_jsonl(EXT / "claims" / f"{fam}.jsonl")
    ra = {r["claim_id"]: r for r in _readings(fam, "verify", "A")}
    rb = {r["claim_id"]: r for r in _readings(fam, "verify", "B")}
    evs = {a: _ev(data, a) for a in {c["alias"] for c in claims}}
    rows = []
    for c in claims:
        if c["claim_id"] not in ra or c["claim_id"] not in rb:
            raise ValueError(f"{c['claim_id']}: missing reading")
        if ra[c["claim_id"]].get("copied_from"):  # verified once as its representative; adjudicated there
            continue
        d = ac.claim_disputes(c, ra[c["claim_id"]], rb[c["claim_id"]], evs[c["alias"]])
        fields = list(d.fields)
        # label/entailment cannot change any metric when agreed numeric verdicts already make it a NUMERIC_ERROR
        agreed_num_error = any(ac.check_number(n, ra[c["claim_id"]]["numbers"][n["number_id"]], evs[c["alias"]]).is_error
                               for n in c["numbers"] if n["number_id"] not in d.numbers)
        skipped = []
        if agreed_num_error:
            skipped = [f for f in fields if f in ("label", "entailment")]
            fields = [f for f in fields if f not in ("label", "entailment")]
        if fields or d.numbers or skipped:
            rows.append({"claim_id": c["claim_id"], "alias": c["alias"], "fields": fields, "numbers": d.numbers,
                         "skipped_fields_numeric_error": skipped})
    return rows, {c["claim_id"]: c for c in claims}, ra, rb


def _fmt_mapping(m: dict[str, Any]) -> str:
    if m is None:
        return "(no mapping)"
    if m["source_type"] in ("cell", "test"):
        return f"{m['source_type']}: {m['expression']} (scale {m['scale']:g})"
    if m["source_type"] == "text":
        return f"text quote: \"{m['quote']}\" (scale {m['scale']:g})"
    return "none (no referenced source in the package)"


def run_claim_adjudication(data: FamilyData, packets: dict[str, Any], workers: int = 3,
                           replicate: Optional[str] = None) -> list[dict[str, Any]]:
    fam = data.family.name
    adj_dir, raw_dir, salt = replicate_dirs(replicate)
    rows, claims, ra, rb = claim_dispute_table(data)
    tmpl, _ = load_prompt("adjudicate_claims")
    inv = {v: k for k, v in data.aliases.items()}
    by_alias: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["fields"] or r["numbers"]:
            by_alias.setdefault(r["alias"], []).append(r)

    def job(alias: str) -> list[dict[str, Any]]:
        pk, ev = packets[alias], _ev(data, alias)
        blocks, maps, segs = [], {}, []
        for r in by_alias[alias]:
            c = claims[r["claim_id"]]
            order = _order(c["claim_id"])
            maps[c["claim_id"]] = order
            reading = {"A": ra[c["claim_id"]], "B": rb[c["claim_id"]]}
            lines = [f"### Item {c['claim_id']}",
                     f"Sentence [{c['unit_id']}]: \"{pk['units'][c['unit_id']]}\"",
                     f"Claim: {c['proposition']}  [span: \"{c['span']}\"]",
                     f"Disputed fields: {', '.join(r['fields'] + (['numbers ' + ', '.join(r['numbers'])] if r['numbers'] else []))}"]
            agreed = [f for f in ("label", "entailment") if f not in r["fields"]]
            if agreed:
                lines.append("Agreed (final): " + ", ".join(f"{f}={reading['A'][f]}" for f in agreed))
            for slot in ("1", "2"):
                x = reading[order[slot]]
                lines.append(f"Reading {slot}: label {x['label']}, entailment {x['entailment']}, extraction {x['extraction_flag']}; "
                             f"evidence {', '.join(x['evidence_ids']) or '-'}; \"{x['justification']}\"")
                for nid in r["numbers"]:
                    n = next(q for q in c["numbers"] if q["number_id"] == nid)
                    v = ac.check_number(n, x["numbers"].get(nid), ev)
                    res = v.status + (f" (expected {v.expected:g})" if v.expected is not None else "") + \
                        (f"; {v.note}" if v.note else "")
                    lines.append(f"   number {nid} \"{n['as_written']}\": {_fmt_mapping(x['numbers'].get(nid))} -> program: {res}")
                segs += [x["justification"], *x["evidence_ids"]]
                segs += [str((x["numbers"].get(nid) or {}).get(k) or "") for nid in r["numbers"] for k in ("expression", "quote")]
            blocks.append("\n".join(lines))
            segs += [c["proposition"], c["span"], pk["units"][c["unit_id"]]]
        prompt = fill(tmpl, PACKAGE=pk["package_markdown"], ITEMS="\n\n".join(blocks))
        want = {r["claim_id"]: r for r in by_alias[alias]}

        def validator(p):
            got = {d["item_id"]: d for d in p["decisions"]}
            if set(got) != set(want):
                return [f"item ids mismatch {sorted(set(want) ^ set(got))[:4]}"]
            probs = []
            for cid, r in want.items():
                if sorted(n["number_id"] for n in got[cid]["numbers"]) != sorted(r["numbers"]):
                    probs.append(f"{cid}: numbers mismatch")
            return probs

        res = call_judge(ADJUDICATOR, "adjudicate_claims", f"{fam}_{alias}", "adjudicate_claims", prompt, raw_dir=raw_dir, salt=salt,
                         data_segments=data_segments(pk, [claims[r["claim_id"]] for r in by_alias[alias]]) + segs,
                         forbidden_texts=forbidden_texts(fam, inv[alias]), validator=validator)
        return [{**d, "_reading_map": maps[d["item_id"]], "disputed_fields": want[d["item_id"]]["fields"],
                 "disputed_numbers": want[d["item_id"]]["numbers"]} for d in res.parsed["decisions"]]

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(by_alias)], workers) if by_alias else {}
    out = [d for a in sorted(res) for d in res[a]]
    _dump_jsonl(adj_dir / f"{fam}_claims.jsonl", out)
    _dump_jsonl(adj_dir / f"{fam}_claims_disputes.jsonl", rows)
    return out


# ----------------------------------------------------------------------------- coverage
def run_coverage_adjudication(data: FamilyData, packets: dict[str, Any], workers: int = 3,
                              replicate: Optional[str] = None) -> list[dict[str, Any]]:
    fam = data.family.name
    adj_dir, raw_dir, salt = replicate_dirs(replicate)
    if fam not in ("real", "diagnostic"):
        return []
    A = {(r["text_id"], r["item_id"]): r for r in _readings(fam, "coverage", "A")}
    B = {(r["text_id"], r["item_id"]): r for r in _readings(fam, "coverage", "B")}
    if set(A) != set(B):
        raise ValueError("coverage readings cover different items")
    checklists = json.loads((EXT / "checklists" / f"{fam}.json").read_text())["checklists"]
    from evaluation.extended_pipeline import coverage_items
    tmpl, _ = load_prompt("adjudicate_coverage")
    inv = {v: k for k, v in data.aliases.items()}
    disputes: dict[str, list[tuple[str, str]]] = {}
    for k in sorted(A):
        if A[k]["status"] != B[k]["status"]:
            disputes.setdefault(A[k]["alias"], []).append(k)

    def job(alias: str) -> list[dict[str, Any]]:
        pk = packets[alias]
        items = {i["item_id"]: i for i in coverage_items(data, alias, checklists[alias])}
        tid2lab = {p["text_id"]: p["label"] for p in pk["passages"]}
        blocks, maps, segs = [], {}, []
        for tid, iid in disputes[alias]:
            key = f"{tid2lab[tid]}::{iid}"
            order = _order(f"{fam}|{tid}|{iid}")
            maps[key] = order
            rd = {"A": A[(tid, iid)], "B": B[(tid, iid)]}
            blocks.append(f"### Item {key}\nFinding {iid} ({items[iid]['polarity']}): {items[iid]['description']}\n"
                          f"Passage {tid2lab[tid]}:\n" + passages_block(pk, {tid2lab[tid]}).split("\n", 1)[1] + "\n" +
                          "\n".join(f"Reading {s}: {rd[order[s]]['status']} - \"{rd[order[s]]['justification']}\"" for s in ("1", "2")))
            segs += [items[iid]["description"], rd["A"]["justification"], rd["B"]["justification"]]
        prompt = fill(tmpl, PACKAGE=pk["package_markdown"], ITEMS="\n\n".join(blocks))
        want = set(maps)
        res = call_judge(ADJUDICATOR, "adjudicate_coverage", f"{fam}_{alias}", "adjudicate_coverage", prompt, raw_dir=raw_dir, salt=salt,
                         data_segments=data_segments(pk) + segs, forbidden_texts=forbidden_texts(fam, inv[alias]),
                         validator=lambda p: [] if {d["item_id"] for d in p["decisions"]} == want else ["item ids mismatch"])
        lab2tid = {v: k for k, v in tid2lab.items()}
        return [{"text_id": lab2tid[d["item_id"].split("::")[0]], "item_id": d["item_id"].split("::")[1],
                 "status": d["status"], "rationale": d["rationale"], "_reading_map": maps[d["item_id"]]}
                for d in res.parsed["decisions"]]

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(disputes)], workers) if disputes else {}
    out = [d for a in sorted(res) for d in res[a]]
    _dump_jsonl(adj_dir / f"{fam}_coverage.jsonl", out)
    return out


# ----------------------------------------------------------------------------- alignment
def alignment_disputes(xa: dict[str, Any], xb: dict[str, Any]) -> bool:
    if xa["relation"] != xb["relation"]:
        return True
    if xa["relation"] == "MODIFIED" and xa["direction"] != xb["direction"]:
        return True
    return xa["relation"] != "DELETED" and set(xa["matched_y"]) != set(xb["matched_y"])


def run_alignment_adjudication(data: FamilyData, packets: dict[str, Any], workers: int = 3,
                               replicate: Optional[str] = None) -> list[dict[str, Any]]:
    fam = data.family.name
    adj_dir, raw_dir, salt = replicate_dirs(replicate)
    A = {r["pair_id"]: r for r in _readings(fam, "align", "A")}
    B = {r["pair_id"]: r for r in _readings(fam, "align", "B")}
    claims = {c["claim_id"]: c for c in load_jsonl(EXT / "claims" / f"{fam}.jsonl")}
    tmpl, _ = load_prompt("adjudicate_align")
    inv = {v: k for k, v in data.aliases.items()}
    disputes: dict[str, list[tuple[str, str]]] = {}
    for pid, pa in A.items():
        if pa["judge"] == "deterministic":
            continue
        xb = {x["claim_id"]: x for x in B[pid]["x_claims"]}
        for x in pa["x_claims"]:
            if alignment_disputes(x, xb[x["claim_id"]]):
                disputes.setdefault(pa["alias"], []).append((pid, x["claim_id"]))

    def job(alias: str) -> list[dict[str, Any]]:
        pk = packets[alias]
        blocks, maps, segs = [], {}, []
        for pid, cid in disputes[alias]:
            key = f"{pid}::{cid}"
            order = _order(key)
            maps[key] = order
            xa = next(x for x in A[pid]["x_claims"] if x["claim_id"] == cid)
            xb = next(x for x in B[pid]["x_claims"] if x["claim_id"] == cid)
            rd = {"A": xa, "B": xb}
            ys = A[pid]["y_claims"]
            blocks.append(f"### Item {key}\nVersion X claim {cid}: {claims[cid]['proposition']}\nVersion Y claims:\n" +
                          "\n".join(f"  - {y}: {claims[y]['proposition']}" for y in ys) + "\n" +
                          "\n".join(f"Reading {s}: relation {rd[order[s]]['relation']}, direction {rd[order[s]]['direction']}, "
                                    f"matched_y {rd[order[s]]['matched_y']}" for s in ("1", "2")))
            segs += [claims[cid]["proposition"]] + [claims[y]["proposition"] for y in ys]
        prompt = fill(tmpl, ITEMS="\n\n".join(blocks))
        want = set(maps)
        res = call_judge(ADJUDICATOR, "adjudicate_align", f"{fam}_{alias}", "adjudicate_align", prompt, raw_dir=raw_dir, salt=salt,
                         data_segments=data_segments(pk) + segs, forbidden_texts=forbidden_texts(fam, inv[alias]),
                         validator=lambda p: [] if {d["item_id"] for d in p["decisions"]} == want else ["item ids mismatch"])
        return [{"pair_id": d["item_id"].split("::")[0], "claim_id": d["item_id"].split("::")[1],
                 **{k: d[k] for k in ("relation", "direction", "matched_y", "rationale")}, "_reading_map": maps[d["item_id"]]}
                for d in res.parsed["decisions"]]

    res = _parallel([(a, (lambda a=a: job(a))) for a in sorted(disputes)], workers) if disputes else {}
    out = [d for a in sorted(res) for d in res[a]]
    _dump_jsonl(adj_dir / f"{fam}_align.jsonl", out)
    return out


def run_adjudication(data: FamilyData, packets: dict[str, Any], workers: int = 3, replicate: Optional[str] = None) -> None:
    run_claim_adjudication(data, packets, workers, replicate)
    run_coverage_adjudication(data, packets, workers, replicate)
    run_alignment_adjudication(data, packets, workers, replicate)


# ----------------------------------------------------------------------------- consensus
def build_consensus(data: FamilyData, packets: dict[str, Any], workers: int = 0,
                    replicate: Optional[str] = None) -> dict[str, Path]:
    """Freeze consensus files; with ``replicate``, build the alternative consensus from that replicate's
    adjudications under annotation/ai_extended/replicates/<name>/consensus/ instead."""
    fam = data.family.name
    adj_dir, _, _ = replicate_dirs(replicate)
    cons_dir = EXT / "consensus" if not replicate else EXT / "replicates" / replicate / "consensus"
    rows, claims, ra, rb = claim_dispute_table(data)
    adj = {d["item_id"]: d for d in load_jsonl(adj_dir / f"{fam}_claims.jsonl")} \
        if (adj_dir / f"{fam}_claims.jsonl").exists() else {}
    skipped = {r["claim_id"]: r["skipped_fields_numeric_error"] for r in rows}
    evs: dict[str, EvidenceValues] = {}
    final = []
    for cid, c in claims.items():
        ev = evs.setdefault(c["alias"], _ev(data, c["alias"]))
        a, b = ra[cid], rb[cid]
        rep = a.get("copied_from") or cid
        d = adj.get(rep)
        if d is not None and rep != cid:  # propagate the representative's decision; numbers map by position
            pos = {n["number_id"]: i for i, n in enumerate(claims[rep]["numbers"])}
            mine = [n["number_id"] for n in c["numbers"]]
            d = {**d, "numbers": [{**n, "number_id": mine[pos[n["number_id"]]]} for n in d["numbers"]]}
        if skipped.get(rep) and rep != cid:
            skipped[cid] = skipped[rep]
        if skipped.get(cid):  # disputed label/entailment that cannot change a NUMERIC_ERROR claim: keep A's value, mark it
            d = dict(d or {"numbers": [], "extraction_valid": True, "evidence_ids": [], "_reading_map": {"1": "A", "2": "B"}})
            for f in skipped[cid]:
                d[f] = a[f]
        rec = ac.finalize_claim(c, a, b, ev, d)
        rec["label_from_numeric_error_rule"] = skipped.get(cid, [])
        rec["readings"] = {"A": {k: a[k] for k in ("label", "entailment", "extraction_flag", "confidence")},
                           "B": {k: b[k] for k in ("label", "entailment", "extraction_flag", "confidence")}}
        rec["copied_from"] = a.get("copied_from")
        if d and rep in adj:
            rec["adjudication"] = {"rationale": d.get("rationale"), "reading_map": d.get("_reading_map"),
                                   "label": d.get("label"), "entailment": d.get("entailment"),
                                   "extraction_valid": d.get("extraction_valid")}
        final.append(rec)
    out = {"claims": cons_dir / f"{fam}_claims.jsonl"}
    _dump_jsonl(out["claims"], final)
    if fam in ("real", "diagnostic"):  # finding coverage is judged only for these families
        A = {(r["text_id"], r["item_id"]): r for r in _readings(fam, "coverage", "A")}
        B = {(r["text_id"], r["item_id"]): r for r in _readings(fam, "coverage", "B")}
        cadj = {(d["text_id"], d["item_id"]): d for d in load_jsonl(adj_dir / f"{fam}_coverage.jsonl")} \
            if (adj_dir / f"{fam}_coverage.jsonl").exists() else {}
        cov = []
        for k in sorted(A):
            if A[k]["status"] == B[k]["status"]:
                st, src = A[k]["status"], "agreed"
            else:
                if k not in cadj:
                    raise ValueError(f"coverage dispute {k} not adjudicated")
                st, src = cadj[k]["status"], "adjudicated"
            cov.append({"text_id": k[0], "item_id": k[1], "alias": A[k]["alias"], "status": st, "source": src,
                        "readings": {"A": A[k]["status"], "B": B[k]["status"]},
                        "adjudication_rationale": cadj.get(k, {}).get("rationale")})
        out["coverage"] = cons_dir / f"{fam}_coverage.jsonl"
        _dump_jsonl(out["coverage"], cov)
    A = {r["pair_id"]: r for r in _readings(fam, "align", "A")}
    B = {r["pair_id"]: r for r in _readings(fam, "align", "B")}
    aadj = {(d["pair_id"], d["claim_id"]): d for d in load_jsonl(adj_dir / f"{fam}_align.jsonl")} \
        if (adj_dir / f"{fam}_align.jsonl").exists() else {}
    aligned = []
    for pid, pa in sorted(A.items()):
        xs = []
        xb = {x["claim_id"]: x for x in B[pid]["x_claims"]}
        for x in pa["x_claims"]:
            if pa["judge"] == "deterministic" or not alignment_disputes(x, xb[x["claim_id"]]):
                xs.append({**x, "source": "agreed" if pa["judge"] != "deterministic" else "deterministic"})
            else:
                dd = aadj.get((pid, x["claim_id"]))
                if dd is None:
                    raise ValueError(f"alignment dispute {pid}/{x['claim_id']} not adjudicated")
                xs.append({"claim_id": x["claim_id"], "relation": dd["relation"], "direction": dd["direction"],
                           "matched_y": dd["matched_y"], "source": "adjudicated"})
        matched = {y for x in xs for y in x["matched_y"]}
        added = [y for y in pa["y_claims"] if y not in matched]
        aligned.append({k: pa[k] for k in ("pair_id", "alias", "draft_text_id", "final_text_id", "y_claims")} |
                       {"x_claims": xs, "added_y": added})
    out["alignment"] = cons_dir / f"{fam}_alignment.jsonl"
    _dump_jsonl(out["alignment"], aligned)
    manifest = cons_dir / f"MANIFEST_{fam}.json"
    manifest.write_text(json.dumps({k: {"path": str(p.relative_to(EXT.parent.parent)),
                                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for k, p in out.items()},
                                   indent=1))
    print(f"  consensus {fam}: {len(final)} claims, "
          f"{sum(r['final_label'] == 'UNRESOLVED' for r in final)} unresolved, "
          f"{sum(r['final_label'] == 'EXCLUDED' for r in final)} excluded")
    return out


# ----------------------------------------------------------------------------- agreement and provenance (§7)
def agreement_stats(data: FamilyData) -> dict[str, Any]:
    """AI–AI agreement before adjudication, and how adjudications sided. Not human reliability."""
    from evaluation.merge_annotations import cohen_kappa
    fam = data.family.name
    claims = {c["claim_id"]: c for c in load_jsonl(EXT / "claims" / f"{fam}.jsonl")}
    ra = {r["claim_id"]: r for r in _readings(fam, "verify", "A")}
    rb = {r["claim_id"]: r for r in _readings(fam, "verify", "B")}
    evs = {a: _ev(data, a) for a in {c["alias"] for c in claims.values()}}
    ids = sorted(claims)
    # copied readings duplicate their representative; agreement is computed on representative claims only
    reps = [i for i in ids if not ra[i].get("copied_from")]

    def block(xs, ys, labels=None):
        n = len(xs)
        return {"n": n, "pct_agree": (sum(x == y for x, y in zip(xs, ys)) / n) if n else None,
                "cohen_kappa": cohen_kappa(xs, ys, labels) if n else None,
                "confusion": dict(Counter(f"{x}|{y}" for x, y in zip(xs, ys)))}

    out: dict[str, Any] = {"family": fam, "provenance": "AI judge A vs AI judge B before adjudication; not human agreement",
                           "label": block([ra[i]["label"] for i in reps], [rb[i]["label"] for i in reps]),
                           "entailment": block([ra[i]["entailment"] for i in reps], [rb[i]["entailment"] for i in reps]),
                           "inconsistent_label_entailment": {"A": sum(not ra[i]["consistent"] for i in reps),
                                                             "B": sum(not rb[i]["consistent"] for i in reps)},
                           "extraction_flags": {"A": dict(Counter(ra[i]["extraction_flag"] for i in reps)),
                                                "B": dict(Counter(rb[i]["extraction_flag"] for i in reps))}}
    na, nb = [], []
    for i in reps:
        c = claims[i]
        for n in c["numbers"]:
            va = ac.check_number(n, ra[i]["numbers"].get(n["number_id"]), evs[c["alias"]])
            vb = ac.check_number(n, rb[i]["numbers"].get(n["number_id"]), evs[c["alias"]])
            na.append("INVALID" if va.status == "INVALID_MAPPING" else ("CORRECT" if va.correct else "ERROR"))
            nb.append("INVALID" if vb.status == "INVALID_MAPPING" else ("CORRECT" if vb.correct else "ERROR"))
    out["numeric_verdict"] = block(na, nb)
    if fam in ("real", "diagnostic"):
        A = {(r["text_id"], r["item_id"]): r["status"] for r in _readings(fam, "coverage", "A")}
        B = {(r["text_id"], r["item_id"]): r["status"] for r in _readings(fam, "coverage", "B")}
        ks = sorted(A)
        out["coverage"] = block([A[k] for k in ks], [B[k] for k in ks])
    A = {r["pair_id"]: r for r in _readings(fam, "align", "A")}
    B = {r["pair_id"]: r for r in _readings(fam, "align", "B")}
    xa, xb = [], []
    for pid, pa in A.items():
        if pa["judge"] == "deterministic":
            continue
        bx = {x["claim_id"]: x for x in B[pid]["x_claims"]}
        for x in pa["x_claims"]:
            xa.append(x["relation"])
            xb.append(bx[x["claim_id"]]["relation"])
    out["alignment_relation"] = block(xa, xb)
    # side-taking of the adjudicator (shares Judge A's model family)
    side = Counter()
    for kind, field in (("claims", "label"), ("claims", "entailment"), ("coverage", "status"), ("align", "relation")):
        p = EXT / "adjudication" / f"{fam}_{kind}.jsonl"
        if not p.exists():
            continue
        for d in load_jsonl(p):
            if kind == "claims" and field not in d.get("disputed_fields", []):
                continue
            if kind == "claims":
                a_val, b_val = ra[d["item_id"]][field], rb[d["item_id"]][field]
            elif kind == "coverage":
                a_val, b_val = A_cov(fam)[(d["text_id"], d["item_id"])], B_cov(fam)[(d["text_id"], d["item_id"])]
            else:
                pa = {x["claim_id"]: x for x in A[d["pair_id"]]["x_claims"]}[d["claim_id"]]
                pb = {x["claim_id"]: x for x in B[d["pair_id"]]["x_claims"]}[d["claim_id"]]
                a_val, b_val = pa["relation"], pb["relation"]
            val = d[field]
            key = "unresolved" if val == "UNRESOLVED" else ("both" if a_val == b_val == val else
                                                           "judge_A" if val == a_val else "judge_B" if val == b_val else "neither")
            side[f"{kind}.{field}.{key}"] += 1
    out["adjudication_sides"] = dict(side)
    nums = load_jsonl(EXT / "adjudication" / f"{fam}_claims.jsonl") if (EXT / "adjudication" / f"{fam}_claims.jsonl").exists() else []
    nside = Counter()
    for d in nums:
        for n in d["numbers"]:
            nside["own_mapping" if n["choice"] == "own" else "judge_" + d["_reading_map"][n["choice"]]] += 1
    out["adjudication_number_choices"] = dict(nside)
    return out


def A_cov(fam: str) -> dict:
    return {(r["text_id"], r["item_id"]): r["status"] for r in _readings(fam, "coverage", "A")}


def B_cov(fam: str) -> dict:
    return {(r["text_id"], r["item_id"]): r["status"] for r in _readings(fam, "coverage", "B")}


def provenance(raw_dir: Path | None = None) -> dict[str, Any]:
    """Per stage and judge: calls, models, settings, tokens, metered cost, latency, discarded tool use, failures."""
    from evaluation.judges import RAW_DIR
    raw_dir = raw_dir or RAW_DIR
    used = set()
    for f in (raw_dir / "used").glob("*.txt"):
        used |= set(f.read_text().split())
    rows: dict[str, Any] = {}
    total_cost = 0.0
    for p in sorted(raw_dir.rglob("*.json")):
        rel = str(p.relative_to(raw_dir))
        try:
            r = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        cost = float(r.get("cost_usd") or 0) + sum(float(a.get("cost_usd") or 0) for a in r.get("failed_attempts", []))
        total_cost += cost
        key = f"{'superseded/' if rel.startswith('_superseded') else ''}{r.get('stage')}/{r.get('judge')}"
        s = rows.setdefault(key, Counter())
        s["calls_ok" if r.get("status") == "ok" else "calls_failed_records"] += 1
        s["discarded_attempts"] += len(r.get("failed_attempts", []))
        s["used_in_results"] += rel in used
        s["cost_usd"] += cost
        u = r.get("usage") or {}
        s["input_tokens"] += int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0) + \
            int(u.get("cache_read_input_tokens") or 0)
        s["output_tokens"] += int(u.get("output_tokens") or 0)
        s["latency_s"] += float(r.get("latency_s") or 0)
        s["tool_use_discarded"] += sum(1 for a in r.get("failed_attempts", []) if "tool use" in str(a.get("error", "")))
        models = rows.setdefault(key + "#models", set())
        if r.get("model_reported"):
            models.add(f"{r.get('model_reported')} [{r.get('backend')}; settings {r.get('settings', {})}]")
    out = {k: (sorted(v) if isinstance(v, set) else dict(v)) for k, v in rows.items()}
    return {"by_stage_judge": out, "total_metered_cost_usd": round(total_cost, 4),
            "note": "Judge B (Claude CLI) cost is list price reported by the CLI; Judge A/adjudicator (Codex CLI, "
                    "ChatGPT subscription) has no per-call USD charge. No OpenRouter call was made."}
