"""Coordinator CLI for the four-person annotation workflow. See annotation/four_person/README_COORDINATOR.md.

  python -m evaluation.four_person assign                      # once: deterministic team split
  python -m evaluation.four_person build                       # per-person stage folders, viewers, zips
  python -m evaluation.four_person check                       # every integrity / blinding invariant
  python -m evaluation.four_person release --who B --stage pass1
  python -m evaluation.four_person intake  --who B --kind pass1 --file ~/Downloads/B_Yuxin_pass1.csv
  python -m evaluation.four_person status
  python -m evaluation.four_person agree --team AB             # agreement + disagreement sheets
  python -m evaluation.four_person consensus --team AB --synthetic FILE --real FILE
  python -m evaluation.four_person combine                     # both teams -> original scoring schema
  python -m evaluation.four_person score                       # runs the ORIGINAL scoring scripts (unblinds)
  python -m evaluation.four_person report                      # descriptive summary + contribution record
  python -m evaluation.four_person tables                      # Markdown tables from the original scorers' JSON

All commands except `score` print only aggregate counts and never a case_id, condition or gold value; `score`
unblinds (condition-level results) and is run only after every adjudication is final.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from evaluation.four_person.roster import ANNOTATORS, STAGES, SUBMISSION_KINDS, TEAMS, Paths, sha_file, zip_name


def _p(a) -> Paths:
    return Paths.default(Path(a.root).resolve() if a.root else None)


def cmd_assign(a) -> int:
    from evaluation.four_person.assignment import write_assignment

    pub, status = write_assignment(_p(a), force=a.force)
    print(f"assignment {status}: {_p(a).assignment_json}")
    for t, v in pub["teams"].items():
        print(f"  Team {t} {v['members']}: {v['counts']}")
    print("  coordinator-only pair map:", _p(a).assignment_private)
    return 0


def cmd_build(a) -> int:
    from evaluation.four_person.packets import build_all

    res = build_all(_p(a), force=a.force)
    print(res["status"])
    for who, v in res["people"].items():
        print(f"  {who}: {v['dir']}  ->  dist/{', dist/'.join(v['zips'])}")
    print("Now run: python -m evaluation.four_person check")
    return 0


def cmd_check(a) -> int:
    from evaluation.four_person.checks import run_all_checks

    probs = run_all_checks(_p(a), packets=not a.no_packets)
    hard = [p for p in probs if not (p[0] == "private" and "cannot be re-checked" in p[1])]
    for sec, msg in probs:
        print(f"[{sec}] {msg}")
    print("ALL CHECKS PASSED" if not hard else f"{len(hard)} PROBLEM(S) FOUND")
    return 0 if not hard else 1


def cmd_release(a) -> int:
    from evaluation.four_person.assignment import load_assignment
    from evaluation.four_person.checks import _all_test_checklist_lines, check_person_packets
    from evaluation.four_person.roster import read_csv_any
    from evaluation.four_person.submissions import append_log, release_gate, released

    paths = _p(a)
    release_gate(paths, a.who, a.stage)
    syn, real = read_csv_any(paths.syn_packet), read_csv_any(paths.real_packet)
    orig_ids = {"all": {r["output_id"] for r in syn} | {r["output_id"] for r in real},
                "refs": {r["case_ref"] for r in syn}, "papers": {r["case_ref"] for r in real}}
    probs = check_person_packets(paths, load_assignment(paths), a.who, orig_ids, _all_test_checklist_lines(paths))
    if probs:
        for sec, msg in probs:
            print(f"[{sec}] {msg}")
        print("packet checks failed: NOT released")
        return 1
    z = paths.dist_dir / zip_name(a.who, a.stage)
    digest = sha_file(z)
    prev = released(paths, a.who, a.stage)
    if prev and prev[-1]["sha256"] != digest and not a.rerelease:
        print(f"{z.name} differs from the copy released on {prev[-1]['utc']}; use --rerelease if this is intended")
        return 1
    append_log(paths, "release_log.csv", {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                          "annotator": a.who, "name": ANNOTATORS[a.who].name, "stage": a.stage,
                                          "file": z.name, "sha256": digest, "note": a.note or ""})
    print(f"OK to send to {ANNOTATORS[a.who].name}: {z}\nsha256 {digest}")
    return 0


def cmd_intake(a) -> int:
    from evaluation.four_person.submissions import intake

    ok, errs, msg = intake(_p(a), a.who, a.kind, Path(a.file).expanduser(), replace=a.replace)
    for e in errs[:200]:
        print("  -", e)
    if len(errs) > 200:
        print(f"  ... and {len(errs) - 200} more")
    print(msg)
    return 0 if ok else 1


def cmd_status(a) -> int:
    from evaluation.four_person.submissions import stage_progress

    rows = stage_progress(_p(a))
    cols = ["annotator", "name", "team", "blinding"] + [f"released_{s}" for s in STAGES] + \
           [f"accepted_{k}" for k in ("declaration", "pass1", "pass2", "real_outputs", "real_sentences", "timelog")]
    print("\t".join(cols))
    for r in rows:
        print("\t".join(r[c] or "-" for c in cols))
    return 0


def cmd_agree(a) -> int:
    from evaluation.four_person.team_merge import agree

    res = agree(_p(a), a.team, force=a.force)
    print(json.dumps(res, indent=1))
    print(f"Send {res['bundle']} to both members of Team {a.team} (and only to them).")
    return 0


def cmd_consensus(a) -> int:
    from evaluation.four_person.team_merge import build_team_consensus

    ok, errs = build_team_consensus(_p(a), a.team, Path(a.synthetic).expanduser() if a.synthetic else None,
                                    Path(a.real).expanduser() if a.real else None, replace=a.replace)
    for e in errs[:200]:
        print("  -", e)
    print(f"Team {a.team} consensus written to {_p(a).team_dir(a.team)}" if ok else
          f"{len(errs)} problem(s): consensus NOT written; send the list back to Team {a.team}")
    return 0 if ok else 1


def _single(a) -> dict:
    """--single-annotator AB=B  ->  {'AB': 'B'} (sensitivity variant)."""
    out = {}
    for item in getattr(a, "single_annotator", None) or []:
        team, who = item.split("=")
        out[team.strip()] = who.strip()
    return out


def cmd_combine(a) -> int:
    from evaluation.four_person.combine import combine

    ok, errs, files = combine(_p(a), check_scoring=not a.no_scoring_check, single=_single(a))
    for e in errs:
        print("  -", e)
    if not ok:
        print("combined consensus NOT written")
        return 1
    print("combined consensus written (accepted by the original scoring functions):")
    for k, p in files.items():
        print(f"  {k}: {p}")
    return 0


def cmd_score(a) -> int:
    from evaluation import score_human, score_real_papers

    from evaluation.four_person.combine import final_dir_for

    paths = _p(a)
    single = _single(a)
    f = final_dir_for(paths, single)
    suffix = "" if not single else "_sensitivity_" + "_".join(f"{t}_{w}_only" for t, w in sorted(single.items()))
    if not (f / "combine_manifest.json").exists():
        print(f"run `combine{' --single-annotator ' + ' '.join(f'{t}={w}' for t, w in single.items()) if single else ''}` first")
        return 1
    runs = paths.root / "outputs" / "synthetic" / "deepseek__deepseek-v4-flash-0731"
    args = ["--consensus", str(f / "consensus_synthetic.csv"), "--mapping", str(paths.condition_mapping),
            "--gold", str(paths.gold), "--rubric", str(paths.test_rubric), "--out", str(paths.root / "results" / f"human_scored{suffix}")]
    if runs.exists():
        args += ["--runs", str(runs)]
    print("python -m evaluation.score_human " + " ".join(args))
    rc = score_human.main(args)
    rargs = ["score", "--consensus-outputs", str(f / "consensus_real_outputs.csv"), "--consensus-sentences",
             str(f / "consensus_real_sentences.csv"), "--mapping", str(paths.condition_mapping_real),
             "--out", str(paths.root / "results" / f"human_scored_real{suffix}")]
    print("python -m evaluation.score_real_papers " + " ".join(rargs))
    return rc or score_real_papers.main(rargs)


def cmd_report(a) -> int:
    from evaluation.four_person.report import summary

    paths = _p(a)
    data, md = summary(paths)
    out = paths.root / "results" / "human_agreement" / "four_person"
    out.mkdir(parents=True, exist_ok=True)
    (out / "SUMMARY.md").write_text(md, encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(md)
    print(f"written: {out / 'SUMMARY.md'}")
    return 0


def cmd_tables(a) -> int:
    from evaluation.four_person.report import human_tables

    paths = _p(a)
    single = _single(a)
    suffix = "" if not single else "_sensitivity_" + "_".join(f"{t}_{w}_only" for t, w in sorted(single.items()))
    md = human_tables(paths, suffix)
    out = paths.root / "results" / f"human_scored{suffix}" / "TABLES_HUMAN.md"
    out.write_text(md, encoding="utf-8")
    print(f"written: {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m evaluation.four_person", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="repository root (default: this checkout)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("assign", help="deterministic team split (writes once)")
    s.add_argument("--force", action="store_true", help="replace a DIFFERENT existing assignment (backup kept)")
    s = sub.add_parser("build", help="per-person stage folders, viewers and zips")
    s.add_argument("--force", action="store_true", help="replace a changed build (backup kept); never after release")
    s = sub.add_parser("check", help="run every integrity, coverage, blinding and stage-separation check")
    s.add_argument("--no-packets", action="store_true")
    s = sub.add_parser("release", help="gate + verify + log one stage archive for one person")
    s.add_argument("--who", choices=list(ANNOTATORS), required=True)
    s.add_argument("--stage", choices=list(STAGES), required=True)
    s.add_argument("--note", default="")
    s.add_argument("--rerelease", action="store_true")
    s = sub.add_parser("intake", help="take in a returned file (validated; never overwrites)")
    s.add_argument("--who", choices=list(ANNOTATORS), required=True)
    s.add_argument("--kind", choices=list(SUBMISSION_KINDS), required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--replace", action="store_true", help="supersede a different accepted file (old copy kept)")
    sub.add_parser("status", help="who has received / returned what")
    s = sub.add_parser("agree", help="team agreement + disagreement sheets + adjudication bundle")
    s.add_argument("--team", choices=list(TEAMS), required=True)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("consensus", help="validate a team's adjudication and write its consensus")
    s.add_argument("--team", choices=list(TEAMS), required=True)
    s.add_argument("--synthetic", default=None)
    s.add_argument("--real", default=None)
    s.add_argument("--replace", action="store_true")
    s = sub.add_parser("combine", help="combine both teams' consensus into the original scoring schema")
    s.add_argument("--no-scoring-check", action="store_true")
    s.add_argument("--single-annotator", nargs="*", metavar="TEAM=ID",
                   help="SENSITIVITY variant, e.g. AB=B: use B's independent labels for Team AB (separate output folder)")
    s = sub.add_parser("score", help="run the original scoring scripts on the combined consensus (unblinds)")
    s.add_argument("--single-annotator", nargs="*", metavar="TEAM=ID", help="score the sensitivity variant instead")
    sub.add_parser("report", help="descriptive summary and contribution record")
    s = sub.add_parser("tables", help="render the original scorers' JSON results as Markdown tables")
    s.add_argument("--single-annotator", nargs="*", metavar="TEAM=ID", help="render the sensitivity variant")
    a = ap.parse_args(argv)
    try:
        return {"assign": cmd_assign, "build": cmd_build, "check": cmd_check, "release": cmd_release,
                "intake": cmd_intake, "status": cmd_status, "agree": cmd_agree, "consensus": cmd_consensus,
                "combine": cmd_combine, "score": cmd_score, "report": cmd_report,
                "tables": cmd_tables}[a.cmd](a)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
