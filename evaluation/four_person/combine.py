"""Combine the two teams' adjudicated consensus at the ITEM level into the exact files the original
scoring scripts read, then (optionally) confirm that those scripts accept them.

  private/four_person/final/consensus_synthetic.csv       -> evaluation.score_human --consensus
  private/four_person/final/consensus_real_outputs.csv    -> evaluation.score_real_papers score --consensus-outputs
  private/four_person/final/consensus_real_sentences.csv  -> evaluation.score_real_papers score --consensus-sentences

Condition-level metrics are then computed once, over all items, by the unchanged scoring code with the
original private mappings and gold; team-level metrics are never averaged.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.blinding import OVERALL_CALIBRATION, SUPPORT_LABELS
from evaluation.four_person.assignment import load_assignment
from evaluation.four_person.roster import TEAMS, Paths, read_csv_any, write_csv
from evaluation.four_person.submissions import rubric_checklists
from evaluation.four_person.team_merge import READABILITY, strict_consensus_row
from evaluation.merge_annotations import SCORED_FIELDS

SYN_FIELDS = ["output_id", "case_id", "category"] + SCORED_FIELDS
OUT_FIELDS = ["output_id", "case_ref", "readability", "overall_calibration"]
SENT_FIELDS = ["output_id", "sentence_idx", "support_label"]


class CombineError(RuntimeError):
    pass


def team_files(paths: Paths, team: str) -> dict[str, Path]:
    d = paths.team_dir(team)
    return {"synthetic": d / f"consensus_synthetic_Team{team}.csv", "real_outputs": d / f"consensus_real_outputs_Team{team}.csv",
            "real_sentences": d / f"consensus_real_sentences_Team{team}.csv"}


def combine_rows(paths: Paths, team_rows: dict[str, dict[str, list[dict[str, str]]]],
                 assignment: dict[str, Any]) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    """team_rows[team][kind] -> rows. Returns combined rows and every problem found (empty = OK)."""
    errs: list[str] = []
    syn_pkt = read_csv_any(paths.syn_packet)
    real_pkt = read_csv_any(paths.real_packet)
    sent_pkt = read_csv_any(paths.real_sent_packet)
    if not paths.alias_map.exists():
        raise CombineError(f"{paths.alias_map} (coordinator-private) is required to validate the consensus")
    alias = {r["case_ref"]: r["case_id"] for r in read_csv_any(paths.alias_map)}
    cls = rubric_checklists(paths)
    ref_by = {r["output_id"]: r["case_ref"] for r in syn_pkt}
    cat_by = {r["output_id"]: r["category"] for r in syn_pkt}
    out: dict[str, list[dict[str, str]]] = {"synthetic": [], "real_outputs": [], "real_sentences": []}
    for team in TEAMS:
        t = assignment["teams"][team]
        rows = team_rows[team]
        syn_ids = [r["output_id"] for r in rows["synthetic"]]
        if sorted(syn_ids) != sorted(t["synthetic_output_ids"]):
            errs.append(f"Team {team}: synthetic consensus does not cover exactly its {len(t['synthetic_output_ids'])} "
                        f"assigned outputs once each (has {len(syn_ids)}, {len(set(syn_ids))} distinct)")
        for r in rows["synthetic"]:
            oid = r["output_id"]
            if oid not in cat_by:
                errs.append(f"unknown synthetic output_id {oid}")
                continue
            if r.get("category") != cat_by[oid]:
                errs.append(f"{oid}: category differs from the packet")
            if r.get("case_id") != alias[ref_by[oid]]:
                errs.append(f"{oid}: case_id inconsistent with the private alias map")
            missing_cols = [f for f in SCORED_FIELDS if f not in r]
            if missing_cols:
                errs.append(f"{oid}: column(s) {missing_cols} missing")
                continue
            errs += strict_consensus_row(r, cat_by[oid], cls[ref_by[oid]])
        ro_ids = [r["output_id"] for r in rows["real_outputs"]]
        if sorted(ro_ids) != sorted(t["real_output_ids"]):
            errs.append(f"Team {team}: real-paper paragraph consensus does not cover exactly its assigned paragraphs")
        for r in rows["real_outputs"]:
            if r.get("readability") not in READABILITY or r.get("overall_calibration") not in OVERALL_CALIBRATION:
                errs.append(f"{r['output_id']}: missing or invalid readability/overall_calibration")
        for r in rows["real_sentences"]:
            if r.get("support_label") not in SUPPORT_LABELS:
                errs.append(f"{r['output_id']}#{r.get('sentence_idx')}: missing or invalid support_label")
        out["synthetic"] += rows["synthetic"]
        out["real_outputs"] += rows["real_outputs"]
        out["real_sentences"] += rows["real_sentences"]
    ids = Counter(r["output_id"] for r in out["synthetic"])
    if set(ids) != {r["output_id"] for r in syn_pkt} or any(v != 1 for v in ids.values()):
        errs.append(f"combined synthetic consensus must hold each of the {len(syn_pkt)} original outputs exactly once "
                    f"(has {sum(ids.values())} rows, {len(ids)} distinct)")
    rid = Counter(r["output_id"] for r in out["real_outputs"])
    if set(rid) != {r["output_id"] for r in real_pkt} or any(v != 1 for v in rid.values()):
        errs.append(f"combined real-paper paragraph consensus must hold each of the {len(real_pkt)} paragraphs exactly once")
    want = Counter(f"{r['output_id']}#{r['sentence_idx']}" for r in sent_pkt)
    got = Counter(f"{r['output_id']}#{r['sentence_idx']}" for r in out["real_sentences"])
    if got != want:
        errs.append(f"combined sentence consensus must hold each of the {len(sent_pkt)} original sentences exactly once "
                    f"(missing {len(set(want) - set(got))}, extra/duplicated {sum((got - want).values())})")
    out["synthetic"].sort(key=lambda r: r["output_id"])
    out["real_outputs"].sort(key=lambda r: r["output_id"])
    out["real_sentences"].sort(key=lambda r: (r["output_id"], int(r["sentence_idx"])))
    return out, errs


def scoring_acceptance(paths: Paths, combined: dict[str, list[dict[str, str]]]) -> list[str]:
    """Run the ORIGINAL scoring functions in memory on the combined files and report only whether they accept them.
    No metric is printed or stored here."""
    from evaluation.score_human import load_jsonl, score
    from evaluation.score_real_papers import score as score_real

    errs = []
    if not (paths.condition_mapping.exists() and paths.gold.exists()):
        return [f"private mapping/gold not available ({paths.condition_mapping}, {paths.gold}): acceptance by "
                f"evaluation.score_human could not be confirmed here"]
    mapping = read_csv_any(paths.condition_mapping)
    completed = {m["output_id"] for m in mapping if m["status"] == "completed" and m["output_id"]}
    have = {r["output_id"] for r in combined["synthetic"]}
    if completed != have:
        errs.append(f"synthetic consensus ids differ from the completed outputs in the private mapping "
                    f"({len(completed - have)} missing, {len(have - completed)} extra)")
    gold, rubric = load_jsonl(paths.gold), load_jsonl(paths.test_rubric)
    for itt in (True, False):
        try:
            score(combined["synthetic"], mapping, gold, rubric, None, itt=itt)
        except Exception as e:  # noqa: BLE001
            errs.append(f"evaluation.score_human.score rejected the combined consensus: {e}")
    if paths.condition_mapping_real.exists():
        mreal = read_csv_any(paths.condition_mapping_real)
        try:
            score_real(combined["real_outputs"], combined["real_sentences"], mreal)
        except Exception as e:  # noqa: BLE001
            errs.append(f"evaluation.score_real_papers.score rejected the combined consensus: {e}")
    else:
        errs.append(f"{paths.condition_mapping_real} missing: real-paper acceptance not confirmed")
    return errs


def single_annotator_rows(paths: Paths, team: str, who: str) -> dict[str, list[dict[str, str]]]:
    """One team member's own validated, UNADJUDICATED labels in consensus format (sensitivity analysis only)."""
    from evaluation.four_person.team_merge import load_team, team_context
    from evaluation.merge_annotations import _canon

    if who not in TEAMS[team]:
        raise CombineError(f"{who} is not a member of Team {team}")
    ctx = team_context(paths, team)
    d = load_team(paths, ctx)[who]
    syn = [{"output_id": oid, "case_id": ctx["case_by_id"][oid], "category": ctx["cat_by_id"][oid],
            **{f: _canon(f, r.get(f, "")) for f in SCORED_FIELDS}} for oid, r in sorted(d["syn"].items())]
    outs = [{"output_id": oid, "case_ref": r["case_ref"], "readability": r["readability"].strip(),
             "overall_calibration": r["overall_calibration"].strip()} for oid, r in sorted(d["ro"].items())]
    sents = [{"output_id": r["output_id"], "sentence_idx": r["sentence_idx"], "support_label": r["support_label"].strip()}
             for r in d["rs"].values()]
    return {"synthetic": syn, "real_outputs": outs, "real_sentences": sents}


def final_dir_for(paths: Paths, single: dict[str, str] | None) -> Path:
    if not single:
        return paths.final_dir
    return paths.private_dir / ("final_sensitivity_" + "_".join(f"{t}_{w}_only" for t, w in sorted(single.items())))


def combine(paths: Paths, check_scoring: bool = True, single: dict[str, str] | None = None) -> tuple[bool, list[str], dict[str, Path]]:
    """single={'AB': 'B'} builds the blind-member SENSITIVITY variant: Team AB's items carry B's independent labels
    instead of the adjudicated consensus; it is written to a separate folder and never replaces the primary files."""
    assignment = load_assignment(paths)
    single = single or {}
    missing = [str(p) for t in TEAMS if t not in single for p in team_files(paths, t).values() if not p.exists()]
    if missing:
        raise CombineError("team consensus missing (run `consensus` for both teams first): " + "; ".join(missing))
    team_rows = {t: (single_annotator_rows(paths, t, single[t]) if t in single else
                     {k: read_csv_any(p) for k, p in team_files(paths, t).items()}) for t in TEAMS}
    combined, errs = combine_rows(paths, team_rows, assignment)
    if not errs and check_scoring:
        errs += scoring_acceptance(paths, combined)
    out = final_dir_for(paths, single)
    files = {"synthetic": out / "consensus_synthetic.csv", "real_outputs": out / "consensus_real_outputs.csv",
             "real_sentences": out / "consensus_real_sentences.csv"}
    if errs:
        out.mkdir(parents=True, exist_ok=True)
        (out / "combine_errors.txt").write_text("\n".join(errs) + "\n")
        return False, errs, files
    write_csv(files["synthetic"], combined["synthetic"], SYN_FIELDS)
    write_csv(files["real_outputs"], combined["real_outputs"], OUT_FIELDS)
    write_csv(files["real_sentences"], combined["real_sentences"], SENT_FIELDS)
    (out / "combine_manifest.json").write_text(json.dumps(
        {"n_synthetic": len(combined["synthetic"]), "n_real_outputs": len(combined["real_outputs"]),
         "n_real_sentences": len(combined["real_sentences"]),
         "variant": "primary (adjudicated consensus of both teams)" if not single else
         "SENSITIVITY: " + ", ".join(f"Team {t} = independent labels of {w} only (not adjudicated)" for t, w in single.items()),
         "teams": {t: (f"single annotator {single[t]}" if t in single else
                       {k: str(p.relative_to(paths.root)) if paths.root in p.parents else str(p)
                        for k, p in team_files(paths, t).items()}) for t in TEAMS}}, indent=1))
    if (out / "combine_errors.txt").exists():
        (out / "combine_errors.txt").unlink()
    return True, [], files
