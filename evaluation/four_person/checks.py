"""Integrity, coverage, blinding and stage-separation invariants for the four-person workflow.

`run_all_checks` returns a list of (section, message) problems; an empty list means every invariant holds.
Messages never contain private content (no case_id, condition or gold value).
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

from evaluation.blinding import ANNOTATOR_META_LEAK, CHECKLIST_MARKERS
from evaluation.four_person.assignment import load_assignment
from evaluation.four_person.packets import check_sources_unchanged, person_sheets
from evaluation.four_person.roster import (ANNOTATORS, STAGE_DIRS, STAGES, TEAMS, Paths, csv_header, norm, read_csv_any,
                                           readme_name, sha_file, sheet_name, viewer_name, zip_name)
from evaluation.four_person.submissions import (COLUMNS, FILL_FIELDS, accepted_path, checklists_from_pass2_md, read_log,
                                                rubric_checklists, validate_file)
from src.package_schema import CATEGORIES

TEST_CASE_ID = re.compile(r"\b(?:SIG|ROB|GEN|CON|EFF|CIT|NUM|NEG)-p[23][ab]?\b")
OUTPUT_ID = re.compile(r"\b[SR][0-9a-f]{8}\b")
CASE_REF = re.compile(r"\bK\d{2}\b")
PAPER_REF = re.compile(r"\bRP-\d{2}\b")
CONTENT_BLOCK = re.compile(r"<(div|pre|span) class='[^']*\bfp-c\b[^']*'>(.*?)</\1>", re.S)
SPEC_BLOCK = re.compile(r"<script type='application/json' id='fp-spec'>(.*?)</script>", re.S)
CHECKER_BLOCK = re.compile(r"<script id='fp-checker'>.*?</script>", re.S)
TEXT_SUFFIXES = {".md", ".csv", ".html", ".txt", ".json"}

Problems = list[tuple[str, str]]


# ----------------------------------------------------------------------------- assignment
def reference_totals(paths: Paths) -> Optional[dict[str, int]]:
    """Row counts recorded by the ORIGINAL packet builder (private/packet_meta_*.json: 122 / 39 / 151 for this study),
    an independent reference for 'the union is exactly the original packet'."""
    ms, mr = paths.alias_map.parent / "packet_meta_synthetic.json", paths.alias_map.parent / "packet_meta_real.json"
    if not (ms.exists() and mr.exists()):
        return None
    s, r = json.loads(ms.read_text()), json.loads(mr.read_text())
    return {"synthetic": s["n_packet_rows"], "real_outputs": r["n_packet_rows"], "real_sentences": r["n_sentence_rows"]}


def check_assignment(paths: Paths, assignment: dict[str, Any]) -> Problems:
    P: Problems = []
    s = "assignment"
    syn = read_csv_any(paths.syn_packet)
    real = read_csv_any(paths.real_packet)
    sents = read_csv_any(paths.real_sent_packet)
    ref = reference_totals(paths)
    if ref is None:
        P.append(("private", "packet_meta_*.json not found: row totals cannot be re-checked against the original build"))
    else:
        for k, rows in (("synthetic", syn), ("real_outputs", real), ("real_sentences", sents)):
            if len(rows) != ref[k]:
                P.append((s, f"{k}: packet has {len(rows)} rows but the original build recorded {ref[k]}"))
    case_team = assignment["synthetic_case_team"]
    all_refs = {r["case_ref"] for r in syn}
    if len(all_refs) != 32 or set(case_team) != all_refs:
        P.append((s, f"expected exactly the 32 original TEST case refs; assignment has {len(case_team)}"))
    cat = {r["case_ref"]: r["category"] for r in syn}
    for t in TEAMS:
        refs = [r for r, x in case_team.items() if x == t]
        if len(refs) != 16:
            P.append((s, f"team {t} has {len(refs)} synthetic cases, expected 16"))
        per = Counter(cat.get(r) for r in refs)
        if set(per) != set(CATEGORIES) or set(per.values()) != {2}:
            P.append((s, f"team {t} does not have exactly 2 cases per category: {dict(per)}"))
        if sorted(refs) != sorted(assignment["teams"][t]["synthetic_case_refs"]):
            P.append((s, f"team {t} case list inconsistent with the case->team map"))
        want = sorted(r["output_id"] for r in syn if case_team.get(r["case_ref"]) == t)
        if want != sorted(assignment["teams"][t]["synthetic_output_ids"]):
            P.append((s, f"team {t} synthetic output ids are not exactly the outputs of its cases"))
    a_ids = [i for t in TEAMS for i in assignment["teams"][t]["synthetic_output_ids"]]
    if len(a_ids) != len(set(a_ids)):
        P.append((s, "a synthetic output id is assigned to both teams"))
    if set(a_ids) != {r["output_id"] for r in syn} or len(a_ids) != len(syn):
        P.append((s, f"synthetic union is not exactly the original {len(syn)} output ids"))
    if set(assignment["teams"]["AB"]["synthetic_case_refs"]) & set(assignment["teams"]["CD"]["synthetic_case_refs"]):
        P.append((s, "a synthetic case occurs in both teams"))
    # real papers
    paper_team = assignment["real_paper_team"]
    papers = {r["case_ref"] for r in real}
    if len(papers) != 12 or set(paper_team) != papers:
        P.append((s, f"expected exactly the 12 original real papers; assignment has {len(paper_team)}"))
    for t in TEAMS:
        pp = [p for p, x in paper_team.items() if x == t]
        if len(pp) != 6:
            P.append((s, f"team {t} has {len(pp)} real papers, expected 6"))
        want = sorted(r["output_id"] for r in real if paper_team.get(r["case_ref"]) == t)
        if want != sorted(assignment["teams"][t]["real_output_ids"]):
            P.append((s, f"team {t} real output ids are not exactly the outputs of its papers"))
    r_ids = [i for t in TEAMS for i in assignment["teams"][t]["real_output_ids"]]
    if len(r_ids) != len(set(r_ids)) or set(r_ids) != {r["output_id"] for r in real}:
        P.append((s, "real-paper outputs are not split exactly once each across teams"))
    out_paper = {r["output_id"]: r["case_ref"] for r in real}
    for x in sents:
        if out_paper.get(x["output_id"]) != x["case_ref"]:
            P.append((s, f"sentence {x['output_id']}#{x['sentence_idx']} is not attached to its paragraph's paper"))
    team_sent = Counter(paper_team.get(x["case_ref"]) for x in sents)
    for t in TEAMS:
        if team_sent[t] != assignment["teams"][t]["counts"]["real_sentences"]:
            P.append((s, f"team {t} sentence count inconsistent"))
    # coordinator-private: pairs intact, one pair per category per team
    if paths.assignment_private.exists():
        rows = read_csv_any(paths.assignment_private)
        by_pair: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            by_pair[r["pair_id"]].add(r["team"])
            if case_team.get(r["case_ref"]) != r["team"]:
                P.append((s, f"private assignment disagrees with public assignment for {r['case_ref']}"))
        if any(len(v) != 1 for v in by_pair.values()):
            P.append((s, "a matched pair is split between teams"))
        per = Counter((r["category"], r["team"]) for r in rows)
        if set(per.values()) != {2} or len(per) != 16:
            P.append((s, "matched pairs are not one per category per team"))
    else:
        P.append(("private", f"{paths.assignment_private} not found: matched-pair integrity cannot be re-checked here"))
    return P


# ----------------------------------------------------------------------------- packets
def _all_test_checklist_lines(paths: Paths) -> set[str]:
    """Checklist descriptions of every TEST case: lines of the pass-2-only section (the research package above it
    is shared with pass 1 and may itself contain `- `X`: ...` lines)."""
    lines = set()
    for p in paths.pass2_packages.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if "## Pass-2 checklists" not in text:
            continue
        for line in text.split("## Pass-2 checklists", 1)[1].splitlines():
            if re.match(r"^- `[^`]+`:", line):
                lines.add(line.split(":", 1)[1].strip())
    return {x for x in lines if len(x) > 12}


def _sheet_problems(sec: str, path: Path, rows_expected: list[dict[str, Any]], kind: str) -> Problems:
    P: Problems = []
    if not path.exists():
        return [(sec, f"missing {path.name}")]
    if csv_header(path) != COLUMNS[kind]:
        P.append((sec, f"{path.name}: header differs from the original schema"))
    rows = read_csv_any(path)
    keyf = (lambda r: f"{r['output_id']}#{r['sentence_idx']}") if kind == "real_sentences" else (lambda r: r["output_id"])
    if [keyf(r) for r in rows] != [keyf(r) for r in rows_expected]:
        P.append((sec, f"{path.name}: rows differ from the expected assigned rows/order"))
    exp = {keyf(r): r for r in rows_expected}
    for r in rows:
        e = exp.get(keyf(r))
        if e is None:
            continue
        for c in COLUMNS[kind]:
            if c in FILL_FIELDS[kind]:
                if (r.get(c) or "").strip():
                    P.append((sec, f"{path.name}: annotation field {c} pre-filled"))
            elif str(r.get(c, "")) != str(e.get(c, "")):
                P.append((sec, f"{path.name}: column {c} of {keyf(r)} differs from the original packet"))
        for k in ("output_id", "case_ref", "package_file"):
            if ANNOTATOR_META_LEAK.search(r.get(k) or ""):
                P.append((sec, f"{path.name}: metadata {k} may reveal identity"))
    if ANNOTATOR_META_LEAK.search(",".join(csv_header(path))):
        P.append((sec, f"{path.name}: header may reveal identity"))
    return P


def _viewer_problems(sec: str, path: Path, allowed_content: set[str], sheet_rows: dict[str, list[dict[str, Any]]],
                     checklists: Optional[dict[str, dict[str, list[str]]]]) -> Problems:
    P: Problems = []
    if not path.exists():
        return [(sec, f"missing {path.name}")]
    doc = path.read_text(encoding="utf-8")
    for _, body in CONTENT_BLOCK.findall(doc):
        if html.unescape(body) not in allowed_content:
            P.append((sec, f"{path.name}: displays text that is not one of this person's assigned items"))
            break
    m = SPEC_BLOCK.search(doc)
    if not m:
        P.append((sec, f"{path.name}: self-check data missing"))
    else:
        spec = json.loads(m.group(1).replace("<\\/", "</"))
        for kind, rows in sheet_rows.items():
            got = spec["kinds"].get(kind, {}).get("rows", [])
            keyf = (lambda r: f"{r['output_id']}#{r['sentence_idx']}") if kind == "real_sentences" else (lambda r: r["output_id"])
            tcol = "sentence_text" if kind == "real_sentences" else "output_text"
            if [(g["k"], g["r"], g["t"]) for g in got] != [(keyf(r), r["case_ref"], r[tcol]) for r in rows]:
                P.append((sec, f"{path.name}: self-check data does not match the {kind} sheet"))
        if set(spec["kinds"]) != set(sheet_rows):
            P.append((sec, f"{path.name}: self-check data covers {sorted(spec['kinds'])}, expected {sorted(sheet_rows)}"))
        if checklists is None and spec.get("checklists"):
            P.append((sec, f"{path.name}: contains checklist IDs although this is not a pass-2 viewer"))
        if checklists is not None and spec.get("checklists") != checklists:
            P.append((sec, f"{path.name}: checklist IDs differ from the pass-2 packages"))
    scaffold = CHECKER_BLOCK.sub("", SPEC_BLOCK.sub("", CONTENT_BLOCK.sub("", doc)))
    hit = ANNOTATOR_META_LEAK.search(scaffold)
    if hit:
        P.append((sec, f"{path.name}: viewer scaffolding contains a possibly identifying term {hit.group(0)!r}"))
    return P


def check_person_packets(paths: Paths, assignment: dict[str, Any], who: str,
                         orig_ids: dict[str, set[str]], test_checklist_lines: set[str]) -> Problems:
    P: Problems = []
    a = ANNOTATORS[who]
    sec = f"packet {a.tag}"
    team = assignment["teams"][a.team]
    refs, papers = set(team["synthetic_case_refs"]), set(team["real_papers"])
    syn_ids, real_ids = set(team["synthetic_output_ids"]), set(team["real_output_ids"])
    orig = {"synthetic": read_csv_any(paths.syn_packet), "real_outputs": read_csv_any(paths.real_packet),
            "real_sentences": read_csv_any(paths.real_sent_packet)}
    sheets = person_sheets(orig, assignment, who)
    base = paths.person_dir(who)
    if not base.exists():
        return [(sec, "packet folder missing; run `build`")]
    common = {"00_START_HERE.md", readme_name(who), "ANNOTATION_GUIDE.md", f"SUBMISSION_CHECKLIST_{a.tag}.md"}
    expected_files = {
        "training": common | {"demo_example_NOT_TEST.md", "dev_training_viewer.html", sheet_name(who, "declaration"),
                              sheet_name(who, "timelog")},
        "pass1": common | {sheet_name(who, "pass1"), viewer_name(who, "pass1")} | {f"packages/{r}.md" for r in refs},
        "pass2": common | {sheet_name(who, "pass2"), viewer_name(who, "pass2")} | {f"packages/{r}.md" for r in refs},
        "real": common | {sheet_name(who, "real_outputs"), sheet_name(who, "real_sentences"), viewer_name(who, "real")}
                | {f"packages/{p}.md" for p in papers},
    }
    guide = paths.guide.read_bytes()
    readme_live = paths.fp_dir / "instructions" / readme_name(who)
    for stage in STAGES:
        d = base / STAGE_DIRS[stage]
        files = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}
        exp = expected_files[stage]
        if stage == "training":
            files_cmp = {f for f in files if not f.startswith("dev_packages/")}
            if not any(f.startswith("dev_packages/") for f in files):
                P.append((sec, "training: DEV packages missing"))
        else:
            files_cmp = files
        if files_cmp != exp:
            P.append((sec, f"{stage}: unexpected file set (missing {sorted(exp - files_cmp)[:4]}, extra {sorted(files_cmp - exp)[:4]})"))
        if (d / "ANNOTATION_GUIDE.md").exists() and (d / "ANNOTATION_GUIDE.md").read_bytes() != guide:
            P.append((sec, f"{stage}: ANNOTATION_GUIDE.md differs from the frozen guide"))
        if readme_live.exists() and (d / readme_name(who)).exists() and (d / readme_name(who)).read_bytes() != readme_live.read_bytes():
            P.append((sec, f"{stage}: personal README differs from annotation/four_person/instructions/"))
        # every text file: no foreign items, no TEST case ids, no private file names
        for f in sorted(files):
            p = d / f
            if any(x in f.lower() for x in ("condition_mapping", "alias", "gold", "private")):
                P.append((sec, f"{stage}: suspicious file name {f}"))
            if p.suffix not in TEXT_SUFFIXES:
                P.append((sec, f"{stage}: unexpected file type {f}"))
                continue
            t = p.read_text(encoding="utf-8-sig")
            if TEST_CASE_ID.search(t):
                P.append((sec, f"{stage}/{f}: contains a TEST case id"))
            foreign = {x for x in OUTPUT_ID.findall(t) if x in orig_ids["all"] and x not in (syn_ids | real_ids)}
            if foreign:
                P.append((sec, f"{stage}/{f}: contains {len(foreign)} output id(s) of the other team"))
            # the frozen guide and DEV demo are byte-checked against the originals instead (the guide's generic
            # example alias "e.g. K07" refers to no particular assignment)
            if f not in ("ANNOTATION_GUIDE.md", "demo_example_NOT_TEST.md"):
                if {x for x in CASE_REF.findall(t) if x in orig_ids["refs"]} - refs:
                    P.append((sec, f"{stage}/{f}: mentions a case_ref assigned to the other team"))
                if {x for x in PAPER_REF.findall(t) if x in orig_ids["papers"]} - papers:
                    P.append((sec, f"{stage}/{f}: mentions a real paper assigned to the other team"))
            elif stage == "training" and f == "demo_example_NOT_TEST.md" and p.read_bytes() != paths.demo.read_bytes():
                P.append((sec, "training/demo_example_NOT_TEST.md differs from the original"))
            if stage in ("training", "pass1") and any(line in t for line in test_checklist_lines):
                P.append((sec, f"{stage}/{f}: contains TEST pass-2 checklist text"))
            if stage == "pass1" and any(mk in t for mk in CHECKLIST_MARKERS):
                P.append((sec, f"{stage}/{f}: contains a pass-2 checklist marker"))
            if stage == "training" and (OUTPUT_ID.search(t) and set(OUTPUT_ID.findall(t)) & orig_ids["all"]):
                P.append((sec, f"training/{f}: contains TEST/real output ids"))
        # package files byte-identical to the originals
        src = {"pass1": paths.pass1_packages, "pass2": paths.pass2_packages, "real": paths.real_packages}.get(stage)
        if src is not None:
            for f in files:
                if f.startswith("packages/") and (src / Path(f).name).exists() and \
                        (d / f).read_bytes() != (src / Path(f).name).read_bytes():
                    P.append((sec, f"{stage}/{f}: differs from the original package file"))
    # sheets
    d1, d2, d3 = (base / STAGE_DIRS[s] for s in ("pass1", "pass2", "real"))
    P += _sheet_problems(sec, d1 / sheet_name(who, "pass1"), sheets["pass1"], "pass1")
    P += _sheet_problems(sec, d2 / sheet_name(who, "pass2"), sheets["pass2"], "pass2")
    P += _sheet_problems(sec, d3 / sheet_name(who, "real_outputs"), sheets["real_outputs"], "real_outputs")
    P += _sheet_problems(sec, d3 / sheet_name(who, "real_sentences"), sheets["real_sentences"], "real_sentences")
    if {r["output_id"] for r in sheets["pass1"]} != syn_ids or {r["output_id"] for r in sheets["pass2"]} != syn_ids:
        P.append((sec, "pass-1 / pass-2 sets differ from the team's synthetic outputs"))
    if {r["output_id"] for r in sheets["real_outputs"]} != real_ids or \
            {r["output_id"] for r in sheets["real_sentences"]} != real_ids:
        P.append((sec, "real-paper sheets do not cover exactly the team's paragraphs"))
    # viewers
    p1md = {r: (paths.pass1_packages / f"{r}.md").read_text(encoding="utf-8") for r in refs}
    p2md = {r: (paths.pass2_packages / f"{r}.md").read_text(encoding="utf-8") for r in refs}
    rmd = {p: (paths.real_packages / f"{p}.md").read_text(encoding="utf-8") for p in papers}
    cls = {}
    for r in refs:
        c = checklists_from_pass2_md(p2md[r])
        cls[r] = {"findings": sorted(c["findings"]), "facts": sorted(c["facts"])}
    syn_text = {r["output_text"] for r in sheets["pass1"]}
    P += _viewer_problems(sec, d1 / viewer_name(who, "pass1"), syn_text | set(p1md.values()), {"pass1": sheets["pass1"]}, None)
    P += _viewer_problems(sec, d2 / viewer_name(who, "pass2"), syn_text | set(p2md.values()), {"pass2": sheets["pass2"]}, cls)
    P += _viewer_problems(sec, d3 / viewer_name(who, "real"),
                          {r["output_text"] for r in sheets["real_outputs"]} | {s["sentence_text"] for s in sheets["real_sentences"]}
                          | set(rmd.values()), {"real_outputs": sheets["real_outputs"], "real_sentences": sheets["real_sentences"]}, None)
    # zips mirror the stage folders exactly
    for stage in STAGES:
        z = paths.dist_dir / zip_name(who, stage)
        d = base / STAGE_DIRS[stage]
        if not z.exists():
            P.append((sec, f"missing archive {z.name}"))
            continue
        top = f"{a.tag}__{STAGE_DIRS[stage]}/"
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            want = sorted(top + p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
            if sorted(names) != want:
                P.append((sec, f"{z.name}: archive contents differ from {STAGE_DIRS[stage]}/"))
            else:
                for n in names:
                    if zf.read(n) != (d / n[len(top):]).read_bytes():
                        P.append((sec, f"{z.name}: {n} differs from the folder copy"))
                        break
            if stage in ("training", "pass1"):
                for n in names:
                    if n.endswith(("_pass2.csv", "_pass2_viewer.html")):
                        P.append((sec, f"{z.name}: contains pass-2 material {n}"))
                    if n.endswith(".csv") and any(f in zf.read(n).decode("utf-8-sig").splitlines()[0]
                                                  for f in ("findings_covered", "num_facts_correct", "neg_findings_reported")):
                        P.append((sec, f"{z.name}: {n} has pass-2 columns"))
    return P


def check_partners(paths: Paths, assignment: dict[str, Any]) -> Problems:
    """Both members of a team hold identical item sets (possibly in different orders)."""
    P: Problems = []
    for t, (x, y) in TEAMS.items():
        for stage, kind in (("pass1", "pass1"), ("pass2", "pass2"), ("real", "real_outputs"), ("real", "real_sentences")):
            fx = paths.stage_dir(x, stage) / sheet_name(x, kind)
            fy = paths.stage_dir(y, stage) / sheet_name(y, kind)
            if not (fx.exists() and fy.exists()):
                continue
            kx = [(r["output_id"], r.get("sentence_idx", ""), norm(r.get("output_text") or r.get("sentence_text"))) for r in read_csv_any(fx)]
            ky = [(r["output_id"], r.get("sentence_idx", ""), norm(r.get("output_text") or r.get("sentence_text"))) for r in read_csv_any(fy)]
            if sorted(kx) != sorted(ky):
                P.append((f"team {t}", f"{kind}: {x} and {y} do not have identical item sets"))
            elif kind in ("pass1", "pass2", "real_outputs") and len(kx) > 5 and kx == ky:
                P.append((f"team {t}", f"{kind}: {x} and {y} received the same row order"))
    return P


# ----------------------------------------------------------------------------- private files, git, logs
def check_private(paths: Paths) -> Problems:
    P: Problems = []
    if not paths.private_hashes.exists():
        P.append(("private", "no baseline of private-file hashes (run `assign`)"))
    else:
        base = json.loads(paths.private_hashes.read_text())
        for rel, h in base.items():
            p = paths.root / rel
            if not p.exists():
                P.append(("private", f"private file {rel} is missing"))
            elif sha_file(p) != h:
                P.append(("private", f"private file {rel} changed since the baseline"))
    bh = paths.root / "benchmarks" / "build_hashes.json"
    if paths.gold.exists() and bh.exists():
        if sha_file(paths.gold) != json.loads(bh.read_text()).get("gold_test_PRIVATE"):
            P.append(("private", "TEST gold does not match its frozen hash"))
    return P


def check_git_ignored(paths: Paths) -> Problems:
    if not (paths.root / ".git").exists():
        return []
    P: Problems = []
    for p in (paths.packets_dir, paths.dist_dir, paths.private_dir, paths.fp_dir / "_staging", paths.fp_dir / "_backups"):
        r = subprocess.run(["git", "check-ignore", "-q", str(p / "x")], cwd=paths.root)
        if r.returncode != 0:
            P.append(("git", f"{p.relative_to(paths.root)} is NOT gitignored"))
    tracked = subprocess.run(["git", "ls-files", str(paths.fp_dir.relative_to(paths.root))], cwd=paths.root,
                             capture_output=True, text=True).stdout.split()
    for t in tracked:
        if "/packets/" in t or "/dist/" in t:
            P.append(("git", f"generated packet file is tracked by git: {t}"))
    return P


def check_releases(paths: Paths) -> Problems:
    P: Problems = []
    for r in read_log(paths, "release_log.csv"):
        z = paths.dist_dir / r["file"]
        if not z.exists():
            P.append(("release", f"released archive {r['file']} no longer exists"))
        elif sha_file(z) != r["sha256"]:
            P.append(("release", f"{r['file']} changed after it was released to {r['name']} on {r['utc']}"))
    return P


def check_submissions(paths: Paths) -> Problems:
    """Re-validate every accepted submission (they are never modified, so this should stay clean)."""
    P: Problems = []
    try:
        cls = rubric_checklists(paths) if paths.alias_map.exists() else None
    except Exception:  # noqa: BLE001
        cls = None
    assignment = load_assignment(paths)
    for who in ANNOTATORS:
        for kind in ("declaration", "pass1", "pass2", "real_outputs", "real_sentences", "timelog"):
            p = accepted_path(paths, who, kind)
            if not p.exists():
                continue
            if kind == "pass2" and cls is None:
                P.append(("submissions", f"{who}/pass2: cannot re-validate without the private alias map"))
                continue
            errs, _ = validate_file(paths, who, kind, p, assignment, cls)
            P += [("submissions", e) for e in errs]
    return P


def run_all_checks(paths: Paths, packets: bool = True) -> Problems:
    assignment = load_assignment(paths)
    P: Problems = [("sources", e) for e in check_sources_unchanged(paths, assignment)]
    P += check_assignment(paths, assignment)
    if packets:
        syn = read_csv_any(paths.syn_packet)
        real = read_csv_any(paths.real_packet)
        orig_ids = {"all": {r["output_id"] for r in syn} | {r["output_id"] for r in real},
                    "refs": {r["case_ref"] for r in syn}, "papers": {r["case_ref"] for r in real}}
        lines = _all_test_checklist_lines(paths)
        for who in ANNOTATORS:
            P += check_person_packets(paths, assignment, who, orig_ids, lines)
        P += check_partners(paths, assignment)
        # the parsed (viewer) checklists must equal the frozen rubric's checklists
        if paths.alias_map.exists():
            rub = rubric_checklists(paths)
            for p in paths.pass2_packages.glob("*.md"):
                parsed = checklists_from_pass2_md(p.read_text(encoding="utf-8"))
                if parsed != rub.get(p.stem):
                    P.append(("checklists", f"pass-2 package {p.stem}: printed IDs differ from the rubric"))
    P += check_private(paths)
    P += check_git_ignored(paths)
    P += check_releases(paths)
    P += check_submissions(paths)
    return P
