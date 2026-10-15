"""Deterministic split of the human-evaluation data between Team AB and Team CD.

Synthetic study — unit = TEST case, grouped by intact MATCHED PAIR:
  * pair identity comes from the `pair_id` field of the public `data/synthetic/test.jsonl` records,
    joined to the opaque `case_ref` through the coordinator-private `private/case_alias_map.csv`
    (never from row order);
  * every category has exactly two TEST pairs; each team gets one intact pair per category, so each
    team gets 2 cases x 8 categories = 16 cases. By the frozen benchmark design every TEST pair holds
    exactly one strong (l=2) member, so each team receives one strong and one non-strong case per
    ordinal category without the gold file ever being read;
  * among the 2^8 allocations, those minimising the difference in distinct outputs between teams are
    kept and one is drawn with the fixed seed.

Real-paper study — unit = paper (all its outputs and sentences move together):
  * exhaustive search over the 462 distinct 6/6 partitions of the 12 papers, minimising, in this order,
    |difference in outputs|, |difference in sentences|, |difference in words to read| (package + outputs);
    ties broken with the fixed seed, which also decides which half goes to Team AB.

Nothing here reads gold labels or the condition mapping.
"""
from __future__ import annotations

import itertools
import json
import random
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evaluation.four_person.roster import (ANNOTATORS, ASSIGNMENT_VERSION, SEED, TEAMS, Paths, read_csv_any,
                                           sha_file, write_csv)
from src.package_schema import CATEGORIES


class AssignmentError(RuntimeError):
    pass


def _load_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


# ----------------------------------------------------------------------------- synthetic
def synthetic_case_table(syn_packet: list[dict[str, str]], alias: dict[str, str],
                         test_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per case_ref: case_id, pair_id, category, n_outputs. Raises on any structural surprise."""
    by_case = {c["case_id"]: c for c in test_cases}
    n_out = Counter(r["case_ref"] for r in syn_packet)
    cat_seen = {r["case_ref"]: r["category"] for r in syn_packet}
    if set(n_out) != set(alias):
        raise AssignmentError(f"case refs in packet ({len(n_out)}) and alias map ({len(alias)}) differ")
    rows = []
    for ref in sorted(alias):
        cid = alias[ref]
        if cid not in by_case:
            raise AssignmentError(f"alias {ref} points to a case that is not in the TEST split")
        c = by_case[cid]
        if c["category"] != cat_seen[ref]:
            raise AssignmentError(f"category mismatch for {ref}")
        rows.append({"case_ref": ref, "case_id": cid, "pair_id": c["pair_id"], "category": c["category"],
                     "n_outputs": n_out[ref]})
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        pairs[r["pair_id"]].append(r)
    for pid, members in pairs.items():
        if len(members) != 2 or len({m["category"] for m in members}) != 1:
            raise AssignmentError(f"pair {pid} does not have exactly two same-category cases")
    per_cat = Counter(r["category"] for r in rows)
    if len(rows) != 32 or set(per_cat) != set(CATEGORIES) or set(per_cat.values()) != {4}:
        raise AssignmentError(f"expected 32 TEST cases, 4 per category; got {dict(per_cat)}")
    return rows


def allocate_synthetic(case_rows: list[dict[str, Any]], seed: int = SEED) -> dict[str, str]:
    """case_ref -> team. One intact pair per category per team; output-count balanced; seeded tie-break."""
    pairs_by_cat: dict[str, list[str]] = defaultdict(list)
    out_by_pair: Counter = Counter()
    refs_by_pair: dict[str, list[str]] = defaultdict(list)
    for r in case_rows:
        if r["pair_id"] not in pairs_by_cat[r["category"]]:
            pairs_by_cat[r["category"]].append(r["pair_id"])
        out_by_pair[r["pair_id"]] += r["n_outputs"]
        refs_by_pair[r["pair_id"]].append(r["case_ref"])
    cats = sorted(pairs_by_cat)
    for c in cats:
        pairs_by_cat[c].sort()
        if len(pairs_by_cat[c]) != 2:
            raise AssignmentError(f"category {c} must have exactly two TEST pairs")
    total = sum(out_by_pair.values())
    options = []
    for bits in itertools.product((0, 1), repeat=len(cats)):
        ab_pairs = tuple(pairs_by_cat[c][b] for c, b in zip(cats, bits))
        n_ab = sum(out_by_pair[p] for p in ab_pairs)
        options.append((abs(2 * n_ab - total), ab_pairs))
    best = min(o[0] for o in options)
    candidates = sorted(o[1] for o in options if o[0] == best)
    chosen = set(random.Random(f"{seed}:synthetic-allocation").choice(candidates))
    return {ref: ("AB" if pid in chosen else "CD") for pid, refs in refs_by_pair.items() for ref in refs}


# ----------------------------------------------------------------------------- real papers
def real_paper_table(real_packet: list[dict[str, str]], real_sents: list[dict[str, str]],
                     packages_dir: Path) -> list[dict[str, Any]]:
    n_out = Counter(r["case_ref"] for r in real_packet)
    n_sent = Counter(r["case_ref"] for r in real_sents)
    out_words: Counter = Counter()
    for r in real_packet:
        out_words[r["case_ref"]] += len(r["output_text"].split())
    rows = []
    for p in sorted(n_out):
        pkg = packages_dir / f"{p}.md"
        if not pkg.exists():
            raise AssignmentError(f"missing real-paper package {pkg}")
        rows.append({"paper": p, "n_outputs": n_out[p], "n_sentences": n_sent[p],
                     "words_to_read": len(pkg.read_text(encoding="utf-8").split()) + out_words[p]})
    if len(rows) != 12:
        raise AssignmentError(f"expected 12 real papers, got {len(rows)}")
    return rows


def allocate_real(paper_rows: list[dict[str, Any]], seed: int = SEED) -> dict[str, str]:
    papers = sorted(r["paper"] for r in paper_rows)
    by = {r["paper"]: r for r in paper_rows}
    tot = {k: sum(r[k] for r in paper_rows) for k in ("n_outputs", "n_sentences", "words_to_read")}
    half = len(papers) // 2
    options = []
    for combo in itertools.combinations(papers, half):
        if papers[0] not in combo:  # each partition once
            continue
        cost = tuple(abs(2 * sum(by[p][k] for p in combo) - tot[k]) for k in ("n_outputs", "n_sentences", "words_to_read"))
        options.append((cost, combo))
    best = min(o[0] for o in options)
    candidates = sorted(o[1] for o in options if o[0] == best)
    rng = random.Random(f"{seed}:real-allocation")
    side = set(rng.choice(candidates))
    if rng.random() < 0.5:
        side = set(papers) - side
    return {p: ("AB" if p in side else "CD") for p in papers}


# ----------------------------------------------------------------------------- build + persist
def compute_assignment(paths: Paths, seed: int = SEED) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Returns (annotator-safe assignment, coordinator-private case rows)."""
    if not paths.alias_map.exists():
        raise AssignmentError(f"coordinator-private alias map {paths.alias_map} is missing: the matched-pair "
                              f"split cannot be computed. Do NOT rebuild it (that would orphan the packet); "
                              f"restore it from the coordinator's backup.")
    syn = read_csv_any(paths.syn_packet)
    alias = {r["case_ref"]: r["case_id"] for r in read_csv_any(paths.alias_map)}
    cases = synthetic_case_table(syn, alias, _load_jsonl(paths.test_cases))
    syn_team = allocate_synthetic(cases, seed)
    real_out, real_sent = read_csv_any(paths.real_packet), read_csv_any(paths.real_sent_packet)
    papers = real_paper_table(real_out, real_sent, paths.real_packages)
    real_team = allocate_real(papers, seed)

    teams: dict[str, Any] = {}
    for t, members in TEAMS.items():
        refs = sorted(r for r, x in syn_team.items() if x == t)
        cat = {c["case_ref"]: c["category"] for c in cases}
        ids = sorted(r["output_id"] for r in syn if syn_team[r["case_ref"]] == t)
        pps = sorted(p for p, x in real_team.items() if x == t)
        rids = sorted(r["output_id"] for r in real_out if real_team[r["case_ref"]] == t)
        teams[t] = {
            "members": {m: ANNOTATORS[m].name for m in members},
            "synthetic_case_refs": refs,
            "synthetic_cases_per_category": dict(sorted(Counter(cat[r] for r in refs).items())),
            "synthetic_output_ids": ids,
            "real_papers": pps,
            "real_output_ids": rids,
            "counts": {"synthetic_cases": len(refs), "synthetic_outputs": len(ids),
                       "pass1_rows": len(ids), "pass2_rows": len(ids),
                       "real_papers": len(pps), "real_outputs": len(rids),
                       "real_sentences": sum(1 for s in real_sent if real_team[s["case_ref"]] == t),
                       "real_words_to_read": sum(p["words_to_read"] for p in papers if real_team[p["paper"]] == t)},
        }
    public = {
        "version": ASSIGNMENT_VERSION, "seed": seed,
        "procedure": {
            "synthetic": "unit = TEST case; one intact matched pair (public pair_id) per category per team; among the "
                         "256 allocations, those minimising |outputs_AB - outputs_CD| kept; one drawn with "
                         f"random.Random('{seed}:synthetic-allocation'). Gold labels never read.",
            "real": "unit = paper; exhaustive search over the 462 distinct 6/6 partitions minimising "
                    "(|d outputs|, |d sentences|, |d words to read|) lexicographically; ties and the AB/CD side drawn "
                    f"with random.Random('{seed}:real-allocation').",
            "row_order": f"each person's rows shuffled with random.Random('{seed}:rows:<annotator>:<stage>') after "
                         "sorting by output_id; partners therefore see the same items in different orders.",
        },
        "annotators": {a.id: {"name": a.name, "team": a.team, "partner": a.partner} for a in ANNOTATORS.values()},
        "teams": teams,
        "synthetic_case_team": dict(sorted(syn_team.items())),
        "synthetic_case_category": {c["case_ref"]: c["category"] for c in cases},
        "synthetic_case_n_outputs": {c["case_ref"]: c["n_outputs"] for c in cases},
        "real_paper_team": dict(sorted(real_team.items())),
        "real_paper_stats": {p["paper"]: {k: p[k] for k in ("n_outputs", "n_sentences", "words_to_read")} for p in papers},
        "totals": {"synthetic_cases": len(cases), "synthetic_outputs": len(syn), "real_papers": len(papers),
                   "real_outputs": len(real_out), "real_sentences": len(real_sent)},
        "source_sha256": {str(p.relative_to(paths.root)): sha_file(p) for p in paths.original_packet_files()},
    }
    private_rows = [{**c, "team": syn_team[c["case_ref"]]} for c in cases]
    return public, private_rows


def _same_assignment(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = ("seed", "synthetic_case_team", "real_paper_team")
    return all(a.get(k) == b.get(k) for k in keys) and all(
        a["teams"][t][k] == b["teams"][t][k] for t in TEAMS for k in ("synthetic_output_ids", "real_output_ids"))


def write_assignment(paths: Paths, seed: int = SEED, force: bool = False) -> tuple[dict[str, Any], str]:
    """Write the assignment once. Re-running recomputes and must reproduce the stored file exactly;
    a different result is refused unless force=True (a timestamped backup is kept)."""
    public, private_rows = compute_assignment(paths, seed)
    status = "created"
    if paths.assignment_json.exists():
        old = json.loads(paths.assignment_json.read_text(encoding="utf-8"))
        if _same_assignment(old, public):
            if old.get("source_sha256") != public["source_sha256"]:
                raise AssignmentError("the ORIGINAL packet files changed since the assignment was made "
                                      "(source_sha256 mismatch); investigate before continuing")
            write_manifest_md(paths, old)
            return old, "unchanged (recomputed assignment is identical to the stored one)"
        if not force:
            raise AssignmentError(f"{paths.assignment_json} exists and the recomputed assignment differs; refusing to "
                                  f"overwrite (packets may already be distributed). Use --force only before any release.")
        bk = paths.assignment_json.with_name(f"assignment.backup_{int(time.time())}.json")
        shutil.copy2(paths.assignment_json, bk)
        status = f"replaced (backup: {bk.name})"
    public["created_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    paths.fp_dir.mkdir(parents=True, exist_ok=True)
    paths.assignment_json.write_text(json.dumps(public, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_manifest_csv(paths, public)
    write_manifest_md(paths, public)
    write_csv(paths.assignment_private, private_rows,
              ["case_ref", "case_id", "pair_id", "category", "n_outputs", "team"])
    record_private_hashes(paths)
    return public, status


def write_manifest_csv(paths: Paths, public: dict[str, Any]) -> None:
    """Coordinator-facing, annotator-safe manifest: no case_id, pair_id, gold or condition."""
    rows = []
    for ref, team in public["synthetic_case_team"].items():
        n = public["synthetic_case_n_outputs"][ref]
        rows.append({"team": team, "kind": "synthetic_case", "ref": ref, "category": public["synthetic_case_category"][ref],
                     "n_outputs": n, "n_pass1_rows": n, "n_pass2_rows": n, "n_sentences": ""})
    for p, team in public["real_paper_team"].items():
        st = public["real_paper_stats"][p]
        rows.append({"team": team, "kind": "real_paper", "ref": p, "category": "", "n_outputs": st["n_outputs"],
                     "n_pass1_rows": "", "n_pass2_rows": "", "n_sentences": st["n_sentences"]})
    rows.sort(key=lambda r: (r["team"], r["kind"], r["category"], r["ref"]))
    write_csv(paths.fp_dir / "assignment_manifest.csv", rows,
              ["team", "kind", "ref", "category", "n_outputs", "n_pass1_rows", "n_pass2_rows", "n_sentences"])


def write_manifest_md(paths: Paths, public: dict[str, Any]) -> Path:
    """Human-readable, annotator-safe assignment (case_ref / category / counts only)."""
    L = ["# Four-person annotation — assignment manifest", "",
         f"Generated by `python -m evaluation.four_person assign` (version `{public['version']}`, seed `{public['seed']}`, "
         f"created {public.get('created_at_utc', '?')}). Coordinator-facing; contains no case_id, pair_id, gold label or "
         "condition. The case_ref → case_id → matched-pair map is coordinator-only (`private/four_person/assignment_private.csv`).",
         "", "## Procedure", ""] + [f"* **{k}:** {v}" for k, v in public["procedure"].items()] + ["", "## Totals", ""]
    L += ["| Team | Annotators | Synthetic cases | Synthetic outputs (= Pass 1 rows = Pass 2 rows, per person) | Real papers | "
          "Real paragraphs | Real sentences | Real words to read |", "|---|---|---|---|---|---|---|---|"]
    for t, v in public["teams"].items():
        c = v["counts"]
        L.append(f"| {t} | {', '.join(f'{k} {n}' for k, n in v['members'].items())} | {c['synthetic_cases']} | "
                 f"{c['synthetic_outputs']} | {c['real_papers']} | {c['real_outputs']} | {c['real_sentences']} | {c['real_words_to_read']} |")
    tot = public["totals"]
    L += [f"| all | | {tot['synthetic_cases']} | {tot['synthetic_outputs']} | {tot['real_papers']} | {tot['real_outputs']} | "
          f"{tot['real_sentences']} | |", "", "## Synthetic cases by team", "",
          "| category | Team AB (case_ref: outputs) | Team CD (case_ref: outputs) |", "|---|---|---|"]
    cats = sorted(set(public["synthetic_case_category"].values()))
    for cat in cats:
        cell = {t: ", ".join(f"`{r}`: {public['synthetic_case_n_outputs'][r]}" for r in public["teams"][t]["synthetic_case_refs"]
                             if public["synthetic_case_category"][r] == cat) for t in public["teams"]}
        L.append(f"| {cat} | {cell['AB']} | {cell['CD']} |")
    L += ["", "## Real papers by team", "", "| paper | team | paragraphs | sentences | words to read |", "|---|---|---|---|---|"]
    for p, t in public["real_paper_team"].items():
        s = public["real_paper_stats"][p]
        L.append(f"| `{p}` | {t} | {s['n_outputs']} | {s['n_sentences']} | {s['words_to_read']} |")
    out = paths.fp_dir / "ASSIGNMENT.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def record_private_hashes(paths: Paths) -> dict[str, str]:
    """Baseline sha256 of the original private files; `check` verifies they never change."""
    hashes = {str(p.relative_to(paths.root)): sha_file(p) for p in paths.protected_private_files() if p.exists()}
    if paths.private_hashes.exists():
        old = json.loads(paths.private_hashes.read_text())
        if old != hashes:
            raise AssignmentError("private files differ from the recorded baseline; refusing to re-baseline")
        return old
    paths.private_hashes.parent.mkdir(parents=True, exist_ok=True)
    paths.private_hashes.write_text(json.dumps(hashes, indent=1) + "\n")
    return hashes


def load_assignment(paths: Paths) -> dict[str, Any]:
    if not paths.assignment_json.exists():
        raise AssignmentError(f"{paths.assignment_json} not found; run `python -m evaluation.four_person assign` first")
    return json.loads(paths.assignment_json.read_text(encoding="utf-8"))


def items_for(assignment: dict[str, Any], who: str) -> dict[str, list[str]]:
    t = assignment["teams"][ANNOTATORS[who].team]
    return {"case_refs": t["synthetic_case_refs"], "synthetic_ids": t["synthetic_output_ids"],
            "papers": t["real_papers"], "real_ids": t["real_output_ids"]}
