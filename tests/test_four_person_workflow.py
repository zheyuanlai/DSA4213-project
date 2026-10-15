"""Four-person annotation workflow, end to end, on a FAKE repository built in a temp dir.

!!! Every case, run output, packet, mapping, gold label and annotation label below is an invented TEST FIXTURE.
!!! None of it is real data or a human annotation, and nothing here is written into the repository.
"""
import csv
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import make_package  # noqa: E402  (tests/ is on sys.path via conftest)
from evaluation.blinding import build_real_packet, build_synthetic_packet
from evaluation.four_person import assignment as asg
from evaluation.four_person import checks, combine, packets, submissions, team_merge
from evaluation.four_person.roster import ANNOTATORS, TEAMS, Paths, read_csv_any, sheet_name, viewer_name, zip_name
from evaluation.score_human import load_jsonl, score
from evaluation.score_real_papers import score as score_real
from src.package_schema import CATEGORIES, ORDINAL_CATEGORIES, CaseRecord

ROOT = Path(__file__).resolve().parent.parent
CONDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
PFX = {"statistical_significance": "SIG", "robustness": "ROB", "generalization": "GEN", "consistency": "CON",
       "efficiency": "EFF", "citation_support": "CIT", "numerical_reporting": "NUM", "negative_results": "NEG"}
FIXTURE_NOTE = "DUMMY TEST FIXTURE - not a real annotation"


# ----------------------------------------------------------------------------- fake repository
def _write_run(root: Path, cid: str, cond: str, text: str) -> None:
    p = root / cond / f"{cid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"run_id": f"fx:{cond}:{cid}", "case_id": cid, "condition": cond, "status": "completed",
                             "final_passage": text, "is_mock": False}))


def build_fake_repo(root: Path) -> Paths:
    base = make_package().model_dump()
    cases, rub, gold = [], {}, []
    i = 0
    for cat in CATEGORIES:
        for p in (2, 3):
            for m in "ab":
                cid = f"{PFX[cat]}-p{p}{m}"
                cases.append(CaseRecord.model_validate({"case_id": cid, "category": cat, "split": "test",
                                                        "pair_id": f"{PFX[cat]}-p{p}", "package": base,
                                                        "source_manifest": {"origin": "synthetic_original"}}))
                facts = [{"fact_id": "n1", "description": f"value of metric one for fixture item {i}", "entity": "Method A"},
                         {"fact_id": "n2", "description": f"value of metric two for fixture item {i}", "entity": "Method B"}] \
                    if cat == "numerical_reporting" else []
                rub[cid] = {"case_id": cid, "focal_proposition": "Method A outperforms Method B on the metric.",
                            "level_descriptors": {"0": "no comparative claim", "1": "descriptive claim", "2": "significant claim"},
                            "required_findings": [{"finding_id": "f1", "description": f"reports the primary difference of fixture item {i}"},
                                                  {"finding_id": "f2", "description": f"reports the secondary result of fixture item {i}"}],
                            "numeric_facts": facts}
                g = {"case_id": cid, "category": cat,
                     "required_findings": [{"finding_id": "f1", "polarity": "positive"}, {"finding_id": "f2", "polarity": "negative"}]}
                if cat in ORDINAL_CATEGORIES:
                    g["gold_level"] = 2 if m == "a" else (1 if p == 2 else 0)
                gold.append(g)
                k = 2 + (i % 5)  # 2..6 distinct texts per case
                for j, c in enumerate(CONDS):
                    _write_run(root / "outputs" / "synthetic" / "fx", cid, c,
                               f"Method A reached a score of {70 + i}.{j % k} in run family {j % k}. The comparison is descriptive.")
                i += 1
    (root / "data" / "synthetic" / "rubrics").mkdir(parents=True)
    (root / "data" / "synthetic" / "test.jsonl").write_text("".join(c.model_dump_json() + "\n" for c in cases))
    (root / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rub.values()))
    for f in ("data/synthetic/dev.jsonl", "data/synthetic/rubrics/dev_rubric.jsonl", "annotation/ANNOTATION_GUIDE.md",
              "annotation/demo_example_NOT_TEST.md"):
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / f, root / f)
    shutil.copytree(ROOT / "annotation" / "four_person" / "templates", root / "annotation" / "four_person" / "templates")
    (root / "private" / "gold").mkdir(parents=True)
    (root / "private" / "gold" / "test_gold.jsonl").write_text("".join(json.dumps(g) + "\n" for g in gold))
    build_synthetic_packet(root / "outputs" / "synthetic" / "fx", cases, rub, CONDS, root / "annotation", root / "private")
    # 12 fake real papers with 2-4 distinct outputs and 2-5 sentences each
    rcases = []
    for n in range(1, 13):
        pid = f"RP-{n:02d}"
        rcases.append(CaseRecord.model_validate({"case_id": pid, "category": None, "split": "real", "pair_id": None,
                                                 "package": base, "source_manifest": {"origin": "synthetic_original"}}))
        k, ns = 2 + n % 3, 2 + n % 4
        for j, c in enumerate(["C1", "C2", "C3", "C4"]):
            sents = " ".join(f"Sentence {s} of paper {n} variant {j % k} states a result." for s in range(1, ns + 1 + (j % k)))
            _write_run(root / "outputs" / "real" / "fx", pid, c, sents)
    build_real_packet(root / "outputs" / "real" / "fx", rcases, ["C1", "C2", "C3", "C4"], root / "annotation", root / "private")
    return Paths.default(root)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("fakerepo")
    paths = build_fake_repo(root)
    asg.write_assignment(paths)
    packets.build_all(paths)
    return paths


@pytest.fixture
def env(built, tmp_path):
    """A private, mutable copy of the built fake repository for one test."""
    dst = tmp_path / "repo"
    shutil.copytree(built.root, dst)
    return Paths.default(dst)


# ----------------------------------------------------------------------------- dummy labels (fixtures)
def _write(path: Path, rows: list[dict], bom: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def dummy_fill(paths: Paths, who: str, out: Path, flip: float = 0.0, seed: int = 0) -> dict[str, Path]:
    """Fill a person's blank sheets with DUMMY fixture labels. Partners share a base seed; `flip` perturbs labels."""
    rng = random.Random(seed)
    team = ANNOTATORS[who].team
    files = {}
    p2md = {p.stem: p.read_text() for p in paths.pass2_packages.glob("*.md")}
    for kind, stage in (("pass1", "pass1"), ("pass2", "pass2"), ("real_outputs", "real"), ("real_sentences", "real")):
        rows = read_csv_any(paths.stage_dir(who, stage) / sheet_name(who, kind))
        for r in sorted(rows, key=lambda r: (r["output_id"], r.get("sentence_idx", ""))):
            base = random.Random(f"{team}:{r['output_id']}:{r.get('sentence_idx', '')}")  # same for both partners
            alt = rng.random() < flip
            if kind == "pass1":
                if r["category"] in ORDINAL_CATEGORIES:
                    lv = base.choice("012")
                    r["expressed_level"] = str((int(lv) + 1) % 3) if alt else lv
                    r["focal_addressed"] = "yes"
                r.update(unsupported_claims=str(base.choice([0, 0, 1])), numeric_errors="0", confidence_p1="high", notes_p1=FIXTURE_NOTE)
            elif kind == "pass2":
                cl = submissions.checklists_from_pass2_md(p2md[r["case_ref"]])
                fids = sorted(cl["findings"])
                r["findings_covered"] = ";".join(fids[:1] if alt else fids)
                if r["category"] == "numerical_reporting":
                    r["num_facts_correct"] = ";".join(sorted(cl["facts"]))
                if r["category"] == "negative_results":
                    r["neg_findings_reported"] = fids[-1]
                    r["neg_reframed_positive"] = "no"
                r.update(confidence_p2="medium", notes_p2=FIXTURE_NOTE)
            elif kind == "real_outputs":
                r.update(readability=str(base.randint(3, 5) - (1 if alt else 0)), overall_calibration="well_calibrated",
                         confidence="high", notes=FIXTURE_NOTE)
            else:
                lab = base.choice(["SUPPORTED", "SUPPORTED", "OVERSTATED", "NOT_A_CLAIM"])
                r.update(support_label="UNSUPPORTED" if alt else lab, notes=FIXTURE_NOTE)
        files[kind] = _write(out / who / sheet_name(who, kind), rows)
    decl = read_csv_any(paths.stage_dir(who, "training") / sheet_name(who, "declaration"))
    for r in decl:
        r["answer"] = "agree" if r["question_id"] == "Q7_commitment" else (
            "yes" if (who == "A" and r["question_id"] == "Q5_private_file_access") else "no")
    files["declaration"] = _write(out / who / sheet_name(who, "declaration"), decl)
    tl = read_csv_any(paths.stage_dir(who, "training") / sheet_name(who, "timelog"))
    for r in tl:
        r.update(total_minutes="60", n_sessions="2")
    files["timelog"] = _write(out / who / sheet_name(who, "timelog"), tl)
    return files


def intake_all(paths: Paths, filled: dict[str, dict[str, Path]]) -> None:
    for who in "ABCD":  # A (coordinator) before B, as the gate requires
        ok, errs, _ = submissions.intake(paths, who, "declaration", filled[who]["declaration"])
        assert ok, errs
    for kind in ("pass1", "pass2", "real_outputs", "real_sentences", "timelog"):
        for who in "ABCD":
            ok, errs, _ = submissions.intake(paths, who, kind, filled[who][kind])
            assert ok, (who, kind, errs[:5])


def dummy_adjudicate(sheet: Path, out: Path, mode: str = "x") -> Path:
    """Fill an adjudication sheet with DUMMY decisions: take the first annotator's value ('x'), or leave blank ('blank')."""
    rows = read_csv_any(sheet)
    vcol = [c for c in rows[0] if c.startswith("value_")][0] if rows else None
    for r in rows:
        if mode != "blank":
            r["adjudicated_value"] = r[vcol] or "NONE"
            r["rationale"] = FIXTURE_NOTE
    if not rows:
        with open(sheet, encoding="utf-8-sig") as f:
            out.write_text(f.read(), encoding="utf-8")
        return out
    return _write(out, rows)


# ----------------------------------------------------------------------------- assignment
def test_assignment_invariants(built):
    a = asg.load_assignment(built)
    assert checks.check_assignment(built, a) == []
    syn = read_csv_any(built.syn_packet)
    ab, cd = (set(a["teams"][t]["synthetic_output_ids"]) for t in ("AB", "CD"))
    assert not ab & cd and ab | cd == {r["output_id"] for r in syn}
    for t in TEAMS:
        assert a["teams"][t]["counts"]["synthetic_cases"] == 16 and a["teams"][t]["counts"]["real_papers"] == 6
        assert set(a["teams"][t]["synthetic_cases_per_category"].values()) == {2}
    priv = read_csv_any(built.assignment_private)
    teams_by_pair = {}
    for r in priv:
        teams_by_pair.setdefault(r["pair_id"], set()).add(r["team"])
    assert all(len(v) == 1 for v in teams_by_pair.values())  # matched pairs intact
    public = built.assignment_json.read_text() + (built.fp_dir / "assignment_manifest.csv").read_text()
    import re
    hit = re.search(r".{20}\b[A-Z]{3}-p[23][ab]?\b.{5}", public)
    assert hit is None, hit.group(0)  # no case or pair ids
    assert "gold_level" not in public and "condition" not in public.lower()


def test_assignment_is_deterministic_and_protected(env):
    old = env.assignment_json.read_text()
    _, status = asg.write_assignment(env)
    assert status.startswith("unchanged") and env.assignment_json.read_text() == old
    d = json.loads(old)
    d["synthetic_case_team"] = {k: ("CD" if v == "AB" else "AB") for k, v in d["synthetic_case_team"].items()}
    env.assignment_json.write_text(json.dumps(d))
    with pytest.raises(asg.AssignmentError):
        asg.write_assignment(env)
    _, status = asg.write_assignment(env, force=True)
    assert status.startswith("replaced") and list(env.fp_dir.glob("assignment.backup_*.json"))


def test_real_partition_is_balanced_and_exhaustive():
    rows = [{"paper": f"RP-{i:02d}", "n_outputs": o, "n_sentences": s, "words_to_read": w}
            for i, (o, s, w) in enumerate([(4, 14, 1340), (2, 6, 1223), (3, 12, 1345), (3, 11, 1241), (3, 12, 1283), (4, 17, 1631),
                                           (3, 11, 1226), (4, 17, 1505), (3, 10, 1372), (3, 12, 1316), (3, 13, 1495), (4, 16, 1589)], 1)]
    t1, t2 = asg.allocate_real(rows), asg.allocate_real(rows)
    assert t1 == t2 and sorted(set(t1.values())) == ["AB", "CD"] and sum(v == "AB" for v in t1.values()) == 6
    ab = [r for r in rows if t1[r["paper"]] == "AB"]
    assert abs(2 * sum(r["n_outputs"] for r in ab) - 39) == 1 and abs(2 * sum(r["n_sentences"] for r in ab) - 152) <= 2


def test_missing_private_alias_map_is_reported_not_rebuilt(env):
    env.alias_map.unlink()
    with pytest.raises(asg.AssignmentError, match="Do NOT rebuild"):
        asg.compute_assignment(env)
    assert not env.alias_map.exists()


# ----------------------------------------------------------------------------- packets and blinding
def test_packets_pass_every_check(built):
    assert checks.run_all_checks(built) == []


def test_partners_get_identical_sets_in_different_orders(built):
    for x, y in TEAMS.values():
        for stage, kind in (("pass1", "pass1"), ("pass2", "pass2"), ("real", "real_outputs")):
            rx = [r["output_id"] for r in read_csv_any(built.stage_dir(x, stage) / sheet_name(x, kind))]
            ry = [r["output_id"] for r in read_csv_any(built.stage_dir(y, stage) / sheet_name(y, kind))]
            assert sorted(rx) == sorted(ry) and rx != ry
        p1 = {r["output_id"] for r in read_csv_any(built.stage_dir(x, "pass1") / sheet_name(x, "pass1"))}
        p2 = {r["output_id"] for r in read_csv_any(built.stage_dir(x, "pass2") / sheet_name(x, "pass2"))}
        assert p1 == p2


def test_stage_separation_and_no_foreign_items(built):
    a = asg.load_assignment(built)
    other = set(a["teams"]["CD"]["synthetic_output_ids"]) | set(a["teams"]["CD"]["real_output_ids"])
    for stage in ("training", "pass1"):
        z = built.dist_dir / zip_name("A", stage)
        import zipfile
        with zipfile.ZipFile(z) as zf:
            blob = "".join(zf.read(n).decode("utf-8-sig") for n in zf.namelist())
        if stage == "pass1":
            assert "Required-findings checklist" not in blob and "Numeric facts to check" not in blob
        assert "fixture item" not in blob  # no TEST checklist description in training or pass 1
        assert not any(o in blob for o in other)
    v1 = (built.stage_dir("A", "pass1") / viewer_name("A", "pass1")).read_text()
    v2 = (built.stage_dir("A", "pass2") / viewer_name("A", "pass2")).read_text()
    assert "fixture item" not in v1 and "fixture item" in v2
    for leak in ("C1", "C4", "run_id", "SIG-p2", "gold_level", "condition"):
        assert leak not in v1


def test_checks_detect_tampering(env):
    a = asg.load_assignment(env)
    foreign = a["teams"]["CD"]["synthetic_output_ids"][0]
    v = env.stage_dir("A", "pass1") / viewer_name("A", "pass1")
    v.write_text(v.read_text().replace("</body>", f"<p>{foreign}</p></body>"))
    pkg = sorted((env.stage_dir("B", "pass1") / "packages").glob("*.md"))[0]
    shutil.copyfile(env.pass2_packages / pkg.name, pkg)  # pass-2 checklist smuggled into pass 1
    (env.stage_dir("C", "pass2") / "extra.csv").write_text("x\n")
    rows = read_csv_any(env.stage_dir("D", "real") / sheet_name("D", "real_sentences"))
    rows[0]["support_label"] = "SUPPORTED"  # pre-filled label
    _write(env.stage_dir("D", "real") / sheet_name("D", "real_sentences"), rows)
    with open(env.condition_mapping, "a") as f:
        f.write("\n")
    probs = "\n".join(m for _, m in checks.run_all_checks(env))
    assert "output id(s) of the other team" in probs
    assert "pass-2 checklist" in probs and "differs from the original package file" in probs
    assert "unexpected file set" in probs
    assert "pre-filled" in probs
    assert "changed since the baseline" in probs
    assert "archive" in probs  # zips no longer mirror the edited folders


def test_rebuild_is_idempotent_and_refuses_silent_overwrite(env):
    before = {p: p.read_bytes() for p in env.dist_dir.glob("*.zip")}
    assert packets.build_all(env)["status"].startswith("built")
    assert before == {p: p.read_bytes() for p in env.dist_dir.glob("*.zip")}
    t = env.fp_dir / "templates" / "ROLE_C.md"
    t.write_text(t.read_text() + "\nchanged\n")
    with pytest.raises(packets.BuildConflict):
        packets.build_all(env)
    assert packets.build_all(env, force=True)["status"].startswith("rebuilt")
    assert list((env.fp_dir / "_backups").iterdir())


# ----------------------------------------------------------------------------- submissions
def test_gates_and_intake_validation(env, tmp_path):
    filled = {w: dummy_fill(env, w, tmp_path / "sub", seed=1) for w in "ABCD"}
    with pytest.raises(submissions.GateError):
        submissions.release_gate(env, "B", "pass1")  # no declaration yet
    with pytest.raises(submissions.GateError):
        submissions.intake(env, "B", "pass1", filled["B"]["pass1"])
    for w in "AB":
        assert submissions.intake(env, w, "declaration", filled[w]["declaration"])[0]
    with pytest.raises(submissions.GateError, match="coordinator"):
        submissions.intake(env, "B", "pass1", filled["B"]["pass1"])  # partner of the coordinator before A
    with pytest.raises(submissions.GateError):
        submissions.release_gate(env, "A", "pass2")  # pass 1 not accepted
    # invalid pass-1 sheet: level on a NUM row, edited text, missing row
    rows = read_csv_any(filled["A"]["pass1"])
    num = next(r for r in rows if r["category"] == "numerical_reporting")
    num["expressed_level"] = "1"
    rows[0]["output_text"] += " edited"
    drop = next(r for r in rows[1:] if r is not num)
    bad = _write(tmp_path / "bad" / sheet_name("A", "pass1"), [r for r in rows if r is not drop])
    ok, errs, _ = submissions.intake(env, "A", "pass1", bad)
    joined = "\n".join(errs)
    assert not ok and "must be blank" in joined and "was changed" in joined and "missing" in joined
    assert not submissions.accepted(env, "A", "pass1")
    assert submissions.intake(env, "A", "pass1", filled["A"]["pass1"])[0]
    submissions.release_gate(env, "A", "pass2")
    # a different later file is not silently accepted over the first one
    rows = read_csv_any(filled["A"]["pass1"])
    rows[0]["notes_p1"] = "changed note"
    ok, _, msg = submissions.intake(env, "A", "pass1", _write(tmp_path / "v2" / sheet_name("A", "pass1"), rows))
    assert not ok and "refusing to overwrite" in msg
    assert submissions.intake(env, "A", "pass1", tmp_path / "v2" / sheet_name("A", "pass1"), replace=True)[0]
    assert list((env.submissions_dir / "A" / "superseded").iterdir())
    assert submissions.person_status(env, "A") == "self_reported_blind_with_private_access"
    assert submissions.person_status(env, "B") == "self_reported_blind"
    assert submissions.person_status(env, "C") == "unconfirmed"


def test_stage_validators_agree_with_the_original_validator():
    from evaluation.merge_annotations import validate
    rub = {"NEG-x": {"required_findings": [{"finding_id": "f1"}, {"finding_id": "f2"}], "numeric_facts": []},
           "SIG-x": {"required_findings": [{"finding_id": "f1"}], "numeric_facts": []}}
    cl = {"NEG-x": {"findings": {"f1", "f2"}, "facts": set()}, "SIG-x": {"findings": {"f1"}, "facts": set()}}
    rows = [{"output_id": "S1", "expressed_level": "", "focal_addressed": "", "unsupported_claims": "0", "numeric_errors": "1",
             "confidence_p1": "low", "findings_covered": "f2", "num_facts_correct": "", "neg_findings_reported": "f2",
             "neg_reframed_positive": "no", "confidence_p2": "high"},
            {"output_id": "S2", "expressed_level": "1", "focal_addressed": "yes", "unsupported_claims": "2", "numeric_errors": "0",
             "confidence_p1": "medium", "findings_covered": "", "num_facts_correct": "", "neg_findings_reported": "",
             "neg_reframed_positive": "", "confidence_p2": "low"}]
    cat = {"S1": "negative_results", "S2": "statistical_significance"}
    case = {"S1": "NEG-x", "S2": "SIG-x"}
    for r in rows:
        assert submissions.validate_pass1(r, cat[r["output_id"]], "x") == []
        assert submissions.validate_pass2(r, cat[r["output_id"]], cl[case[r["output_id"]]], "x") == []
    assert validate(rows, {"S1", "S2"}, rub, cat, case, "x") == []
    rows[1]["focal_addressed"] = "no"
    assert submissions.validate_pass1(rows[1], "statistical_significance", "x") and validate(rows, {"S1", "S2"}, rub, cat, case, "x")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_viewer_self_check_matches_python(built, tmp_path):
    filled = dummy_fill(built, "C", tmp_path / "sub", seed=3)
    rows = read_csv_any(filled["pass1"])
    ordinal = next(r for r in rows if r["category"] in ORDINAL_CATEGORIES)
    ordinal["expressed_level"] = "3"
    bad = _write(tmp_path / "bad.csv", rows)
    harness = tmp_path / "h.js"
    harness.write_text(r"""
const fs = require('fs'), vm = require('vm');
const [html, kind, csvf] = process.argv.slice(2);
const doc = fs.readFileSync(html, 'utf8');
const js = doc.match(/<script id='fp-checker'>([\s\S]*?)<\/script>/)[1];
const spec = JSON.parse(doc.match(/<script type='application\/json' id='fp-spec'>([\s\S]*?)<\/script>/)[1].replace(/<\\\//g, '</'));
const ctx = {}; vm.createContext(ctx); vm.runInContext(js, ctx);
console.log(JSON.stringify(ctx.FPCHECK.check(spec, kind, fs.readFileSync(csvf, 'utf8'))));
""")

    def run(stage, kind, f):
        out = subprocess.run(["node", str(harness), str(built.stage_dir("C", stage) / viewer_name("C", stage)), kind, str(f)],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    for stage, kind in (("pass1", "pass1"), ("pass2", "pass2"), ("real", "real_outputs"), ("real", "real_sentences")):
        assert run(stage, kind, filled[kind])["errors"] == [], kind
        py, _ = submissions.validate_file(built, "C", kind, filled[kind],
                                          checklists=submissions.rubric_checklists(built) if kind == "pass2" else None)
        assert py == []
    res = run("pass1", "pass1", bad)
    assert len(res["errors"]) == 1 and "expressed_level" in res["errors"][0]
    py, _ = submissions.validate_file(built, "C", "pass1", bad)
    assert len(py) == 1


# ----------------------------------------------------------------------------- agreement, adjudication, combination
def test_kappa_entry_reports_undefined_instead_of_one():
    e = team_merge.kappa_entry(["yes"] * 5, ["yes"] * 5, ["no", "yes"])
    assert e["kappa"] is None and "undefined" in e["kappa_status"] and e["pct_agree"] == 1.0
    assert team_merge.kappa_entry([], [], ["no", "yes"])["kappa_status"].startswith("not applicable")
    assert team_merge.kappa_entry([0, 1, 2, 2], [0, 1, 2, 1], [0, 1, 2])["kappa"] is not None


def test_full_workflow_end_to_end(env, tmp_path):
    filled = {w: dummy_fill(env, w, tmp_path / "sub", flip=0.2 if w in "BD" else 0.0, seed=7) for w in "ABCD"}
    intake_all(env, filled)
    ok, errs = team_merge.build_team_consensus(env, "AB")  # no adjudication yet -> refused, nothing written
    assert not ok and "not found" in errs[0]
    res = {t: team_merge.agree(env, t) for t in TEAMS}
    for t, (x, y) in TEAMS.items():
        rep = json.loads((env.team_dir(t) / f"agreement_Team{t}.json").read_text())
        assert rep["synthetic"]["n_outputs"] == len(asg.load_assignment(env)["teams"][t]["synthetic_output_ids"])
        orig = rep["synthetic"]["original_agreement_function_output"]
        for k, ok in (("expressed_level_unweighted", "kappa"), ("expressed_level_quadratic", "kappa_quadratic")):
            if rep["synthetic"]["stats"][k]["kappa"] is not None:
                assert rep["synthetic"]["stats"][k]["kappa"] == pytest.approx(orig["expressed_level"][ok])
        md = (env.team_dir(t) / f"agreement_report_Team{t}.md").read_text()
        assert f"{x} ({ANNOTATORS[x].name}) × {y} ({ANNOTATORS[y].name})" in md
        assert res[t]["n_synthetic_disagreements"] > 0 and res[t]["n_real_disagreements"] > 0
    assert "do NOT describe these ratings as fully blind" in (env.team_dir("AB") / "agreement_report_TeamAB.md").read_text()
    # the adjudication bundle of one team holds none of the other team's items
    import zipfile
    a = asg.load_assignment(env)
    with zipfile.ZipFile(env.dist_dir / "adjudication_TeamAB.zip") as zf:
        blob = "".join(zf.read(n).decode("utf-8-sig") for n in zf.namelist())
    assert not any(o in blob for o in a["teams"]["CD"]["synthetic_output_ids"] + a["teams"]["CD"]["real_output_ids"])
    # incomplete adjudication blocks consensus; nothing is chosen automatically
    for t in TEAMS:
        b = env.team_dir(t) / "adjudication_bundle"
        blank_s = dummy_adjudicate(b / f"adjudication_synthetic_Team{t}.csv", tmp_path / f"blank_s_{t}.csv", "blank")
        blank_r = dummy_adjudicate(b / f"adjudication_real_Team{t}.csv", tmp_path / f"blank_r_{t}.csv", "blank")
        ok, errs = team_merge.build_team_consensus(env, t, blank_s, blank_r)
        n_dis = len(read_csv_any(b / f"adjudication_synthetic_Team{t}.csv")) + len(read_csv_any(b / f"adjudication_real_Team{t}.csv"))
        assert (not ok and errs) if n_dis else ok
        assert not (env.team_dir(t) / f"consensus_synthetic_Team{t}.csv").exists() or not n_dis
    # invalid adjudicated value is rejected
    b = env.team_dir("CD") / "adjudication_bundle"
    rows = read_csv_any(b / "adjudication_real_TeamCD.csv")
    assert rows, "fixture should produce real-paper disagreements"
    for r in rows:
        r.update(adjudicated_value="MAYBE", rationale=FIXTURE_NOTE)
    ok, errs = team_merge.build_team_consensus(env, "CD", dummy_adjudicate(b / "adjudication_synthetic_TeamCD.csv", tmp_path / "s.csv"),
                                               _write(tmp_path / "r_bad.csv", rows))
    assert not ok and any("MAYBE" in e for e in errs)
    # valid adjudication -> team consensus
    for t in TEAMS:
        b = env.team_dir(t) / "adjudication_bundle"
        ok, errs = team_merge.build_team_consensus(
            env, t, dummy_adjudicate(b / f"adjudication_synthetic_Team{t}.csv", tmp_path / f"s_{t}.csv"),
            dummy_adjudicate(b / f"adjudication_real_Team{t}.csv", tmp_path / f"r_{t}.csv"))
        assert ok, errs[:5]
    with pytest.raises(team_merge.TeamError):  # agreement sheets cannot be silently regenerated after adjudication
        team_merge.agree(env, "AB")
    # combine -> exact original schema, accepted by the original scorers
    ok, errs, files = combine.combine(env)
    assert ok, errs
    syn = read_csv_any(files["synthetic"])
    assert len(syn) == len(read_csv_any(env.syn_packet)) and len({r["output_id"] for r in syn}) == len(syn)
    assert list(syn[0]) == combine.SYN_FIELDS
    assert len(read_csv_any(files["real_sentences"])) == len(read_csv_any(env.real_sent_packet))
    res = score(syn, read_csv_any(env.condition_mapping), load_jsonl(env.gold), load_jsonl(env.test_rubric))
    assert set(res["summary"]) == set(CONDS) and all(res["summary"][c]["n_ordinal"] == 24 for c in CONDS)
    rres = score_real(read_csv_any(files["real_outputs"]), read_csv_any(files["real_sentences"]),
                      read_csv_any(env.condition_mapping_real))
    assert set(rres["summary"]) == {"C1", "C2", "C3", "C4"}
    assert checks.run_all_checks(env) == []
    # blind-member sensitivity variant: Team AB items carry B's own (unadjudicated) labels, in a separate folder
    ok, errs, sfiles = combine.combine(env, single={"AB": "B"})
    assert ok, errs
    assert sfiles["synthetic"].parent != files["synthetic"].parent and files["synthetic"].exists()
    sens = {r["output_id"]: r for r in read_csv_any(sfiles["synthetic"])}
    b_rows = {r["output_id"]: r for r in read_csv_any(env.submissions_dir / "B" / sheet_name("B", "pass1"))}
    ab_ids = asg.load_assignment(env)["teams"]["AB"]["synthetic_output_ids"]
    assert all(sens[i]["expressed_level"] == b_rows[i]["expressed_level"].strip() for i in ab_ids)
    assert len(sens) == len(syn)
    # a missing label is an explicit error, never a zero
    p = env.team_dir("AB") / "consensus_synthetic_TeamAB.csv"
    rows = read_csv_any(p)
    rows[0]["unsupported_claims"] = ""
    _write(p, rows, bom=False)
    ok, errs, _ = combine.combine(env)
    assert not ok and any("unsupported_claims" in e for e in errs)
    rows = rows[1:]
    _write(p, rows, bom=False)
    ok, errs, _ = combine.combine(env)
    assert not ok and any("exactly once" in e or "exactly its" in e for e in errs)


def test_report_never_pools_kappa(env, tmp_path):
    from evaluation.four_person.report import summary
    filled = {w: dummy_fill(env, w, tmp_path / "sub", flip=0.3 if w in "BD" else 0.0, seed=11) for w in "ABCD"}
    intake_all(env, filled)
    for t in TEAMS:
        team_merge.agree(env, t)
    data, md = summary(env)
    assert "descriptive" in md and all("kappa" not in v for v in data["pooled_descriptive"].values())
    assert data["people"]["A"]["reported_minutes"] == 300
