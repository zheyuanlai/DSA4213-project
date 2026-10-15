"""Expected sheets, stage-level validation, intake (never overwriting) and the release/submission logs.

Stage validators mirror `evaluation.merge_annotations.validate` / `evaluation.score_real_papers.validate`
for the fields of one stage, so a person's pass-1 sheet can be checked before pass 2 is released.
The original validators remain the authority when a team's passes are merged (see team_merge.py).
Student files are copied byte-for-byte; nothing here edits a submission.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation.blinding import (OVERALL_CALIBRATION, PASS1_FIELDS, PASS2_FIELDS, REAL_OUTPUT_FIELDS, REAL_SENT_FIELDS,
                                 SUPPORT_LABELS)
from evaluation.four_person.assignment import load_assignment
from evaluation.four_person.roster import (ANNOTATORS, STAGES, TEAMS, Paths, csv_header, norm, read_csv_any, sha_file,
                                           sheet_name, write_csv)
from evaluation.merge_annotations import _ids
from src.package_schema import ORDINAL_CATEGORIES

SYN_BASE = ["output_id", "case_ref", "category", "package_file", "output_text"]
REAL_BASE = ["output_id", "case_ref", "package_file", "output_text"]
SENT_BASE = ["output_id", "sentence_idx", "case_ref", "package_file", "sentence_text"]
COLUMNS = {"pass1": SYN_BASE + PASS1_FIELDS, "pass2": SYN_BASE + PASS2_FIELDS,
           "real_outputs": REAL_BASE + REAL_OUTPUT_FIELDS, "real_sentences": SENT_BASE + REAL_SENT_FIELDS}
FILL_FIELDS = {"pass1": PASS1_FIELDS, "pass2": PASS2_FIELDS, "real_outputs": REAL_OUTPUT_FIELDS,
               "real_sentences": REAL_SENT_FIELDS}
CONF = ("low", "medium", "high")

DECLARATION_QUESTIONS = [
    ("Q1_test_gold", "Have you ever viewed TEST gold labels (e.g. private/gold/test_gold.jsonl, private/benchmark_source/, "
                     "or gold levels quoted in a file, chat or terminal)?",
     "你是否看过 TEST 的 gold 标签（例如 private/gold/test_gold.jsonl、private/benchmark_source/，或文件/聊天/终端里出现的 gold level）？"),
    ("Q2_condition_mapping", "Have you ever viewed the mapping between individual outputs (output_id or text) and "
                             "experimental conditions/systems (e.g. private/condition_mapping*.csv, private/case_alias_map.csv)?",
     "你是否看过 output（output_id 或文本）与实验条件/系统之间的对应关系（例如 private/condition_mapping*.csv、private/case_alias_map.csv）？"),
    ("Q3_raw_outputs_with_conditions", "Have you ever viewed raw TEST or real-paper outputs together with their condition "
                                       "identities (e.g. outputs/synthetic/, outputs/real_papers*/, run logs, "
                                       "private/auto_eval/TEST_edit_examples.md)?",
     "你是否看过带有条件标识的 TEST 或真实论文原始输出（例如 outputs/synthetic/、outputs/real_papers*/、运行日志、private/auto_eval/TEST_edit_examples.md）？"),
    ("Q4_auto_scores_revealing_labels", "Have you ever viewed automated TEST scoring results that reveal correct labels "
                                        "(e.g. private/auto_eval/per_run_rows*.csv, per-case automatic results)?",
     "你是否看过会暴露正确标签的 TEST 自动评分结果（例如 private/auto_eval/per_run_rows*.csv、逐 case 的自动评测结果）？"),
    ("Q5_private_file_access", "Do you currently have, or have you had, access to the coordinator-private files "
                               "(the private/ folder or the withheld outputs/ folders), even if you did not open them?",
     "你现在或过去是否能访问协调人私有文件（private/ 目录或被保留的 outputs/ 目录），即使你没有打开？"),
    ("Q6_discussed_test_items", "Have you discussed specific TEST outputs, their systems or their correct labels with "
                                "anyone who has seen the material above?",
     "你是否与看过上述材料的人讨论过具体的 TEST 输出、其所属系统或正确标签？"),
    ("Q7_commitment", "I will not open gold labels, private mappings, raw outputs, automatic results, my partner's labels "
                      "or the next stage's material before I am allowed to, and I will annotate independently. (agree / disagree)",
     "我承诺：在被允许之前，不打开 gold 标签、私有映射、原始输出、自动评测结果、搭档的标注或下一阶段材料，并独立完成标注。（agree / disagree）"),
]
EXPOSURE_QS = ("Q1_test_gold", "Q2_condition_mapping", "Q3_raw_outputs_with_conditions", "Q4_auto_scores_revealing_labels",
               "Q6_discussed_test_items")
TIMELOG_STAGES = ("training", "pass1", "pass2", "real", "adjudication")


# ----------------------------------------------------------------------------- expected content
def original_rows(paths: Paths) -> dict[str, list[dict[str, str]]]:
    return {"synthetic": read_csv_any(paths.syn_packet), "real_outputs": read_csv_any(paths.real_packet),
            "real_sentences": read_csv_any(paths.real_sent_packet)}


def expected_sheet(orig: dict[str, list[dict[str, str]]], assignment: dict[str, Any], who: str,
                   kind: str) -> list[dict[str, str]]:
    """Blank rows (unshuffled, sorted by id) a person should hand back for `kind`."""
    team = assignment["teams"][ANNOTATORS[who].team]
    if kind in ("pass1", "pass2"):
        ids = set(team["synthetic_output_ids"])
        rows = [r for r in orig["synthetic"] if r["output_id"] in ids]
        out = [{**{k: r[k] for k in ("output_id", "case_ref", "category", "output_text")},
                "package_file": f"packages/{r['case_ref']}.md"} for r in rows]
        return sorted(out, key=lambda r: r["output_id"])
    ids = set(team["real_output_ids"])
    if kind == "real_outputs":
        rows = [r for r in orig["real_outputs"] if r["output_id"] in ids]
        return sorted([{**{k: r[k] for k in ("output_id", "case_ref", "output_text")},
                        "package_file": f"packages/{r['case_ref']}.md"} for r in rows], key=lambda r: r["output_id"])
    rows = [r for r in orig["real_sentences"] if r["output_id"] in ids]
    return sorted([{**{k: r[k] for k in ("output_id", "sentence_idx", "case_ref", "sentence_text")},
                    "package_file": f"packages/{r['case_ref']}.md"} for r in rows],
                  key=lambda r: (r["output_id"], int(r["sentence_idx"])))


CHECKLIST_LINE = re.compile(r"^- `([^`]+)`:")


def checklists_from_pass2_md(text: str) -> dict[str, set[str]]:
    """Checklist IDs as printed in an ORIGINAL pass-2 package (used by viewers; the coordinator's
    authoritative validation uses the rubric, and `check` cross-checks the two)."""
    out = {"findings": set(), "facts": set()}
    section: Optional[str] = None
    for line in text.splitlines():
        if line.startswith("**Required-findings checklist**"):
            section = "findings"
        elif line.startswith("**Numeric facts to check**"):
            section = "facts"
        elif section and (m := CHECKLIST_LINE.match(line)):
            out[section].add(m.group(1))
    return out


def rubric_checklists(paths: Paths) -> dict[str, dict[str, set[str]]]:
    """case_ref -> checklist IDs from the frozen rubric (needs the private alias map)."""
    alias = {r["case_ref"]: r["case_id"] for r in read_csv_any(paths.alias_map)}
    rub = {json.loads(l)["case_id"]: json.loads(l) for l in paths.test_rubric.read_text().splitlines() if l.strip()}
    return {ref: {"findings": {f["finding_id"] for f in rub.get(cid, {}).get("required_findings", [])},
                  "facts": {n["fact_id"] for n in rub.get(cid, {}).get("numeric_facts", [])}}
            for ref, cid in alias.items()}


def key_of(r: dict[str, str], kind: str) -> str:
    return f"{r['output_id']}#{(r.get('sentence_idx') or '').strip()}" if kind == "real_sentences" else r["output_id"]


# ----------------------------------------------------------------------------- validators
def _structure(kind: str, header: list[str], rows: list[dict[str, str]], expected: list[dict[str, str]], who: str) -> list[str]:
    errs = []
    cols = COLUMNS[kind]
    missing, extra = [c for c in cols if c not in header], [c for c in header if c and c not in cols]
    if missing:
        errs.append(f"{who}: missing column(s) {missing}")
    if extra:
        errs.append(f"{who}: unexpected column(s) {extra} (do not add columns)")
    if len(header) != len(set(header)):
        errs.append(f"{who}: duplicated column names")
    exp = {key_of(r, kind): r for r in expected}
    keys = [key_of(r, kind) for r in rows]
    dup = sorted(k for k, n in Counter(keys).items() if n > 1)
    if dup:
        errs.append(f"{who}: duplicated row(s) {dup[:5]}")
    miss, unk = sorted(set(exp) - set(keys)), sorted(set(keys) - set(exp))
    if miss:
        errs.append(f"{who}: {len(miss)} assigned row(s) missing (e.g. {miss[:3]})")
    if unk:
        errs.append(f"{who}: {len(unk)} row(s) not assigned to you (e.g. {unk[:3]})")
    if len(rows) != len(expected):
        errs.append(f"{who}: {len(rows)} rows, expected {len(expected)}")
    text_col = "sentence_text" if kind == "real_sentences" else "output_text"
    for r in rows:
        e = exp.get(key_of(r, kind))
        if e is None:
            continue
        for c in ("case_ref", "category", "package_file", "sentence_idx", text_col):
            if c in e and c in r and norm(r[c]) != norm(e[c]):
                hint = " (if only special symbols look wrong, the file was saved in the wrong encoding: re-save as 'CSV UTF-8')" \
                    if c == text_col else ""
                errs.append(f"{who}/{key_of(r, kind)}: column {c} was changed{hint}")
    return errs


def validate_pass1(r: dict[str, str], cat: str, who: str) -> list[str]:
    """Pass-1 subset of merge_annotations.validate."""
    errs, oid = [], r["output_id"]
    lv = (r.get("expressed_level") or "").strip()
    fa = (r.get("focal_addressed") or "").strip().lower()
    if cat in ORDINAL_CATEGORIES:
        if lv not in ("0", "1", "2"):
            errs.append(f"{who}/{oid}: expressed_level must be 0/1/2 for {cat}, got {lv!r}")
        if fa not in ("yes", "no"):
            errs.append(f"{who}/{oid}: focal_addressed must be yes/no")
        elif fa == "no" and lv not in ("", "0"):
            errs.append(f"{who}/{oid}: focal_addressed=no requires expressed_level=0")
    else:
        if lv:
            errs.append(f"{who}/{oid}: expressed_level must be blank for {cat}")
        if fa:
            errs.append(f"{who}/{oid}: focal_addressed must be blank for {cat}")
    for f in ("unsupported_claims", "numeric_errors"):
        v = (r.get(f) or "").strip()
        if not v.isdigit():
            errs.append(f"{who}/{oid}: {f} must be a non-negative integer, got {v!r}")
    if (r.get("confidence_p1") or "").strip().lower() not in CONF:
        errs.append(f"{who}/{oid}: confidence_p1 must be low/medium/high")
    return errs


def validate_pass2(r: dict[str, str], cat: str, checklist: dict[str, set[str]], who: str) -> list[str]:
    """Pass-2 subset of merge_annotations.validate."""
    errs, oid = [], r["output_id"]
    fids, nids = checklist.get("findings", set()), checklist.get("facts", set())
    bad = _ids(r.get("findings_covered")) - fids
    if bad:
        errs.append(f"{who}/{oid}: findings_covered has unknown ids {sorted(bad)}")
    if cat == "numerical_reporting":
        bad = _ids(r.get("num_facts_correct")) - nids
        if bad:
            errs.append(f"{who}/{oid}: num_facts_correct has unknown ids {sorted(bad)}")
    elif (r.get("num_facts_correct") or "").strip():
        errs.append(f"{who}/{oid}: num_facts_correct only for numerical_reporting rows")
    if cat == "negative_results":
        bad = _ids(r.get("neg_findings_reported")) - fids
        if bad:
            errs.append(f"{who}/{oid}: neg_findings_reported has unknown ids {sorted(bad)}")
        if (r.get("neg_reframed_positive") or "").strip().lower() not in ("yes", "no"):
            errs.append(f"{who}/{oid}: neg_reframed_positive must be yes/no for negative_results")
    elif (r.get("neg_findings_reported") or "").strip() or (r.get("neg_reframed_positive") or "").strip():
        errs.append(f"{who}/{oid}: neg_findings_reported / neg_reframed_positive only for negative_results rows")
    if (r.get("confidence_p2") or "").strip().lower() not in CONF:
        errs.append(f"{who}/{oid}: confidence_p2 must be low/medium/high")
    return errs


def validate_real_output(r: dict[str, str], who: str) -> list[str]:
    errs, oid = [], r["output_id"]
    if (r.get("readability") or "").strip() not in ("1", "2", "3", "4", "5"):
        errs.append(f"{who}/{oid}: readability must be 1-5")
    if (r.get("overall_calibration") or "").strip() not in OVERALL_CALIBRATION:
        errs.append(f"{who}/{oid}: overall_calibration must be one of {OVERALL_CALIBRATION}")
    if (r.get("confidence") or "").strip().lower() not in CONF:
        errs.append(f"{who}/{oid}: confidence must be low/medium/high")
    return errs


def validate_real_sentence(r: dict[str, str], who: str) -> list[str]:
    if (r.get("support_label") or "").strip() not in SUPPORT_LABELS:
        return [f"{who}/{key_of(r, 'real_sentences')}: support_label must be one of {SUPPORT_LABELS}"]
    return []


def validate_sheet(kind: str, header: list[str], rows: list[dict[str, str]], expected: list[dict[str, str]], who: str,
                   checklists: Optional[dict[str, dict[str, set[str]]]] = None) -> list[str]:
    errs = _structure(kind, header, rows, expected, who)
    exp = {key_of(r, kind): r for r in expected}
    for r in rows:
        e = exp.get(key_of(r, kind))
        if e is None:
            continue
        if kind == "pass1":
            errs += validate_pass1(r, e["category"], who)
        elif kind == "pass2":
            if checklists is None:
                raise ValueError("pass-2 validation needs the case checklists")
            errs += validate_pass2(r, e["category"], checklists.get(e["case_ref"], {}), who)
        elif kind == "real_outputs":
            errs += validate_real_output(r, who)
        else:
            errs += validate_real_sentence(r, who)
    return errs


def validate_declaration(rows: list[dict[str, str]], who: str) -> list[str]:
    errs = []
    got = {r.get("question_id", "").strip(): (r.get("answer") or "").strip().lower() for r in rows}
    for qid, _, _ in DECLARATION_QUESTIONS:
        v = got.get(qid)
        allowed = ("agree", "disagree") if qid == "Q7_commitment" else ("yes", "no", "unsure")
        if v not in allowed:
            errs.append(f"{who}: {qid} answer must be one of {allowed}, got {v!r}")
    if got.get("Q7_commitment") == "disagree":
        errs.append(f"{who}: the independence/blinding commitment (Q7) was not agreed; do not release annotation material")
    for r in rows:
        if r.get("question_id", "").strip() in EXPOSURE_QS and (r.get("answer") or "").strip().lower() in ("yes", "unsure") \
                and not (r.get("details") or "").strip():
            errs.append(f"{who}: {r['question_id']} answered yes/unsure: please describe what was seen in 'details'")
    return errs


def validate_timelog(rows: list[dict[str, str]], who: str) -> list[str]:
    errs = []
    for r in rows:
        st = (r.get("stage") or "").strip()
        if st not in TIMELOG_STAGES:
            errs.append(f"{who}: unknown time-log stage {st!r}")
        for f in ("total_minutes", "n_sessions"):
            v = (r.get(f) or "").strip()
            if v and not v.isdigit():
                errs.append(f"{who}/{st}: {f} must be a whole number")
    return errs


def blinding_status(answers: Optional[dict[str, str]], coordinator_access: bool) -> str:
    """unconfirmed | potentially_non_blind | self_reported_blind_with_private_access | self_reported_blind."""
    if not answers:
        return "unconfirmed"
    if any(answers.get(q) in ("yes", "unsure") for q in EXPOSURE_QS):
        return "potentially_non_blind"
    if coordinator_access or answers.get("Q5_private_file_access") in ("yes", "unsure"):
        return "self_reported_blind_with_private_access"
    return "self_reported_blind"


BLINDING_STATUS_TEXT = {
    "unconfirmed": "UNCONFIRMED: no blinding declaration on file",
    "potentially_non_blind": "POTENTIALLY NON-BLIND: declared (or unsure about) prior exposure to gold labels, condition "
                             "identities, raw outputs with conditions, label-revealing automatic scores, or discussion of them",
    "self_reported_blind_with_private_access": "SELF-REPORTED BLIND, NOT VERIFIABLE: declared no exposure but had access to "
                                               "the coordinator-private files",
    "self_reported_blind": "SELF-REPORTED BLIND: declared no exposure and no access to private files",
}


# ----------------------------------------------------------------------------- logs, intake, release
LOG_FIELDS = {"release_log.csv": ["utc", "annotator", "name", "stage", "file", "sha256", "note"],
              "submission_log.csv": ["utc", "annotator", "name", "kind", "received_as", "sha256", "n_rows", "valid",
                                     "accepted", "n_errors"],
              "blinding_declarations.csv": ["annotator", "name", "team", "utc", "status"] + [q for q, _, _ in DECLARATION_QUESTIONS]}


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_log(paths: Paths, name: str, row: dict[str, Any]) -> None:
    p = paths.logs_dir / name
    rows = read_csv_any(p) if p.exists() else []
    rows.append({k: str(v) for k, v in row.items()})
    write_csv(p, rows, LOG_FIELDS[name])


def read_log(paths: Paths, name: str) -> list[dict[str, str]]:
    p = paths.logs_dir / name
    return read_csv_any(p) if p.exists() else []


def accepted_path(paths: Paths, who: str, kind: str) -> Path:
    return paths.submissions_dir / who / sheet_name(who, kind)


def accepted(paths: Paths, who: str, kind: str) -> bool:
    return accepted_path(paths, who, kind).exists()


def declarations(paths: Paths) -> dict[str, dict[str, str]]:
    """Latest declaration answers per annotator (from the accepted declaration files)."""
    out = {}
    for who in ANNOTATORS:
        p = accepted_path(paths, who, "declaration")
        if p.exists():
            out[who] = {r.get("question_id", "").strip(): (r.get("answer") or "").strip().lower() for r in read_csv_any(p)}
    return out


def person_status(paths: Paths, who: str) -> str:
    return blinding_status(declarations(paths).get(who), ANNOTATORS[who].coordinator_access)


class GateError(RuntimeError):
    pass


def validate_file(paths: Paths, who: str, kind: str, file: Path, assignment: Optional[dict[str, Any]] = None,
                  checklists: Optional[dict[str, dict[str, set[str]]]] = None) -> tuple[list[str], int]:
    rows = read_csv_any(file)
    if kind == "declaration":
        return validate_declaration(rows, ANNOTATORS[who].tag), len(rows)
    if kind == "timelog":
        return validate_timelog(rows, ANNOTATORS[who].tag), len(rows)
    assignment = assignment or load_assignment(paths)
    expected = expected_sheet(original_rows(paths), assignment, who, kind)
    if kind == "pass2" and checklists is None:
        checklists = rubric_checklists(paths)
    return validate_sheet(kind, csv_header(file), rows, expected, ANNOTATORS[who].tag, checklists), len(rows)


def intake(paths: Paths, who: str, kind: str, file: Path, replace: bool = False,
           checklists: Optional[dict[str, dict[str, set[str]]]] = None) -> tuple[bool, list[str], str]:
    """Copy a returned file into private/four_person/submissions/<who>/ (byte-for-byte), validate it and log it.
    Every received version is kept under received/; the accepted copy is never overwritten unless replace=True,
    in which case the previous accepted copy is moved to superseded/ first."""
    a = ANNOTATORS[who]
    if kind in ("pass1", "pass2", "real_outputs", "real_sentences"):
        if not accepted(paths, who, "declaration"):
            raise GateError(f"no accepted blinding declaration for {a.tag}; take in the declaration first")
        if kind == "pass2" and not accepted(paths, who, "pass1"):
            raise GateError(f"{a.tag}'s pass-1 sheet has not been accepted; pass 2 cannot be taken in before pass 1")
        partner = ANNOTATORS[a.partner]
        if partner.coordinator_access and not accepted(paths, partner.id, kind):
            raise GateError(f"{partner.tag} is both coordinator and {a.tag}'s partner: take in {partner.tag}'s own {kind} "
                            f"sheet first (and post its sha256 in the group chat) before receiving {a.tag}'s, so the "
                            f"coordinator's labels are fixed before the partner's are seen")
    if not file.exists():
        raise FileNotFoundError(file)
    errs, n = validate_file(paths, who, kind, file, checklists=checklists)
    digest = sha_file(file)
    ts = _utc()
    recv = paths.submissions_dir / who / "received" / f"{ts.replace(':', '')}__{file.name}"
    recv.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, recv)
    target = accepted_path(paths, who, kind)
    acc, msg = False, ""
    if errs:
        msg = f"NOT accepted: {len(errs)} problem(s). Send the list back to {a.name}; the file was archived as {recv.name}."
    elif target.exists() and sha_file(target) == digest:
        acc, msg = True, "identical to the already accepted file; nothing changed"
    elif target.exists() and not replace:
        msg = (f"a different accepted {kind} file already exists for {a.tag}; refusing to overwrite. Use --replace to "
               f"supersede it (the old copy is kept in superseded/).")
    else:
        if target.exists():
            sup = target.parent / "superseded" / f"{ts.replace(':', '')}__{target.name}"
            sup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), sup)
        shutil.copy2(file, target)
        acc, msg = True, f"accepted as {target.relative_to(paths.root) if paths.root in target.parents else target}"
    append_log(paths, "submission_log.csv", {"utc": ts, "annotator": who, "name": a.name, "kind": kind,
                                              "received_as": recv.name, "sha256": digest, "n_rows": n,
                                              "valid": not errs, "accepted": acc, "n_errors": len(errs)})
    if acc and kind == "declaration":
        ans = {r.get("question_id", "").strip(): (r.get("answer") or "").strip().lower() for r in read_csv_any(target)}
        rows = [r for r in read_log(paths, "blinding_declarations.csv") if r["annotator"] != who]
        rows.append({"annotator": who, "name": a.name, "team": a.team, "utc": ts,
                     "status": blinding_status(ans, a.coordinator_access), **{q: ans.get(q, "") for q, _, _ in DECLARATION_QUESTIONS}})
        write_csv(paths.logs_dir / "blinding_declarations.csv", sorted(rows, key=lambda r: r["annotator"]),
                  LOG_FIELDS["blinding_declarations.csv"])
    return acc, errs, f"{msg}\nsha256 {digest}"


def release_gate(paths: Paths, who: str, stage: str) -> None:
    a = ANNOTATORS[who]
    if stage == "training":
        return
    if not accepted(paths, who, "declaration"):
        raise GateError(f"{a.tag} has no accepted blinding declaration; release only the training stage first")
    if stage == "pass2" and not accepted(paths, who, "pass1"):
        raise GateError(f"{a.tag}'s pass-1 sheet has not been accepted yet: pass 2 (checklists) must not be released")


def released(paths: Paths, who: str, stage: str) -> list[dict[str, str]]:
    return [r for r in read_log(paths, "release_log.csv") if r["annotator"] == who and r["stage"] == stage]


def stage_progress(paths: Paths) -> list[dict[str, str]]:
    out = []
    for who, a in ANNOTATORS.items():
        row = {"annotator": who, "name": a.name, "team": a.team, "blinding": person_status(paths, who)}
        for st in STAGES:
            row[f"released_{st}"] = "yes" if released(paths, who, st) else ""
        for k in ("declaration", "pass1", "pass2", "real_outputs", "real_sentences", "timelog"):
            row[f"accepted_{k}"] = "yes" if accepted(paths, who, k) else ""
        out.append(row)
    return out


def team_ready(paths: Paths, team: str) -> list[str]:
    missing = []
    for who in TEAMS[team]:
        for k in ("pass1", "pass2", "real_outputs", "real_sentences"):
            if not accepted(paths, who, k):
                missing.append(f"{ANNOTATORS[who].tag}: {k}")
    return missing
