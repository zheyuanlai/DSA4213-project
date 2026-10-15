"""Per-team validation, agreement, disagreement sheets, adjudication and team consensus.

All statistics come from the ORIGINAL, tested functions:
  synthetic  -> evaluation.merge_annotations.{validate, agreement, disagreements, consensus, validate_consensus_row}
  real paper -> evaluation.score_real_papers.{validate, agreement}; Cohen's kappa from merge_annotations.cohen_kappa
Only the reporting layer is new: a kappa whose value is undefined because both annotators used one
identical label throughout (the original helper returns 1.0 in that 0/0 case) is reported as undefined.
Each team is analysed on its own subset only; nothing here pools the two teams.
"""
from __future__ import annotations

import html
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from evaluation.blinding import OVERALL_CALIBRATION, SUPPORT_LABELS
from evaluation.four_person.assignment import load_assignment
from evaluation.four_person.packets import _c, _page, zip_dir
from evaluation.four_person.roster import ANNOTATORS, TEAMS, Paths, read_csv_any, sha_file, write_csv
from evaluation.four_person.submissions import (BLINDING_STATUS_TEXT, accepted_path, person_status, rubric_checklists,
                                                team_ready, validate_file)
from evaluation.merge_annotations import (INT_FIELDS, SCORED_FIELDS, _canon, _ids, agreement, cohen_kappa,
                                          consensus, disagreements, validate, validate_consensus_row)
from evaluation.score_real_papers import agreement as real_agreement
from evaluation.score_real_papers import validate as real_validate
from src.package_schema import ORDINAL_CATEGORIES

READABILITY = ["1", "2", "3", "4", "5"]


class TeamError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- loading
def join_passes_any(paths: list[Path]) -> list[dict[str, str]]:
    """Same semantics as merge_annotations.join_passes, but tolerant of an Excel UTF-8 BOM."""
    merged: dict[str, dict[str, str]] = {}
    order: list[str] = []
    dups: list[dict[str, str]] = []
    for p in paths:
        seen: set[str] = set()
        for r in read_csv_any(p):
            oid = r["output_id"]
            if oid in seen:
                dups.append(dict(r))
                continue
            seen.add(oid)
            if oid not in merged:
                merged[oid] = {}
                order.append(oid)
            merged[oid].update(r)
    return [merged[o] for o in order] + dups


def team_context(paths: Paths, team: str, assignment: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    assignment = assignment or load_assignment(paths)
    if not paths.alias_map.exists():
        raise TeamError(f"{paths.alias_map} (coordinator-private) is required to look up each case's checklist")
    t = assignment["teams"][team]
    syn = [r for r in read_csv_any(paths.syn_packet) if r["output_id"] in set(t["synthetic_output_ids"])]
    alias = {r["case_ref"]: r["case_id"] for r in read_csv_any(paths.alias_map)}
    rubric = {json.loads(l)["case_id"]: json.loads(l) for l in paths.test_rubric.read_text().splitlines() if l.strip()}
    ids = set(t["real_output_ids"])
    return {"team": team, "members": TEAMS[team], "assignment": assignment,
            "syn_ids": {r["output_id"] for r in syn}, "cat_by_id": {r["output_id"]: r["category"] for r in syn},
            "ref_by_id": {r["output_id"]: r["case_ref"] for r in syn},
            "case_by_id": {r["output_id"]: alias[r["case_ref"]] for r in syn}, "rubric": rubric,
            "syn_rows": {r["output_id"]: r for r in syn},
            "real_out": [r for r in read_csv_any(paths.real_packet) if r["output_id"] in ids],
            "real_sent": [r for r in read_csv_any(paths.real_sent_packet) if r["output_id"] in ids]}


def load_team(paths: Paths, ctx: dict[str, Any]) -> dict[str, Any]:
    """Validate every accepted submission of both members with the ORIGINAL validators; raise on problems."""
    team = ctx["team"]
    missing = team_ready(paths, team)
    if missing:
        raise TeamError("not all independent submissions are in: " + "; ".join(missing))
    errs: list[str] = []
    data: dict[str, Any] = {}
    cls = rubric_checklists(paths)
    for who in ctx["members"]:
        tag = ANNOTATORS[who].tag
        for kind in ("pass1", "pass2", "real_outputs", "real_sentences"):
            e, _ = validate_file(paths, who, kind, accepted_path(paths, who, kind), ctx["assignment"], cls)
            errs += e
        syn = join_passes_any([accepted_path(paths, who, "pass1"), accepted_path(paths, who, "pass2")])
        errs += validate(syn, ctx["syn_ids"], ctx["rubric"], ctx["cat_by_id"], ctx["case_by_id"], tag)
        ro = read_csv_any(accepted_path(paths, who, "real_outputs"))
        rs = read_csv_any(accepted_path(paths, who, "real_sentences"))
        errs += real_validate(ro, rs, ctx["real_out"], ctx["real_sent"], tag)
        data[who] = {"syn": {r["output_id"]: r for r in syn}, "ro": {r["output_id"]: r for r in ro},
                     "rs": {f"{r['output_id']}#{r['sentence_idx']}": r for r in rs}}
    if errs:
        raise TeamError("validation failed:\n" + "\n".join(errs))
    return data


# ----------------------------------------------------------------------------- agreement reporting
def kappa_entry(a: list[Any], b: list[Any], labels: Optional[list[Any]], weights: Optional[str] = None) -> dict[str, Any]:
    n = len(a)
    if n == 0:
        return {"n": 0, "pct_agree": None, "kappa": None, "kappa_status": "not applicable: no items"}
    pct = sum(x == y for x, y in zip(a, b)) / n
    k = cohen_kappa(a, b, labels, weights)
    used = set(a) | set(b)
    if len(used) == 1:
        return {"n": n, "pct_agree": pct, "kappa": None,
                "kappa_status": "undefined: both annotators gave the same single label to every item (no variation)"}
    if k is None:
        return {"n": n, "pct_agree": pct, "kappa": None, "kappa_status": "undefined"}
    note = "ok"
    if len(set(a)) == 1 or len(set(b)) == 1:
        note = "one annotator used a single label throughout; kappa is not informative"
    return {"n": n, "pct_agree": pct, "kappa": k, "kappa_status": note}


def synthetic_agreement(A: dict[str, dict[str, str]], B: dict[str, dict[str, str]], ctx: dict[str, Any]) -> dict[str, Any]:
    rubric, cat, case = ctx["rubric"], ctx["cat_by_id"], ctx["case_by_id"]
    ids = sorted(set(A) & set(B))
    ordinal = [i for i in ids if cat[i] in ORDINAL_CATEGORIES]
    la, lb = [int(A[i]["expressed_level"]) for i in ordinal], [int(B[i]["expressed_level"]) for i in ordinal]
    fa, fb = [A[i]["focal_addressed"].strip().lower() for i in ordinal], [B[i]["focal_addressed"].strip().lower() for i in ordinal]
    out: dict[str, Any] = {"n_outputs": len(ids), "n_ordinal_outputs": len(ordinal), "stats": {}}
    S = out["stats"]
    S["expressed_level_unweighted"] = kappa_entry(la, lb, [0, 1, 2])
    S["expressed_level_linear"] = kappa_entry(la, lb, [0, 1, 2], "linear")
    S["expressed_level_quadratic"] = kappa_entry(la, lb, [0, 1, 2], "quadratic")
    S["focal_addressed"] = kappa_entry(fa, fb, ["no", "yes"])
    for f in INT_FIELDS:
        xa, xb = [int(A[i][f]) for i in ids], [int(B[i][f]) for i in ids]
        e = kappa_entry([x > 0 for x in xa], [y > 0 for y in xb], [False, True])
        e["pct_exact_count"] = sum(x == y for x, y in zip(xa, xb)) / len(ids) if ids else None
        e["mean_abs_diff"] = sum(abs(x - y) for x, y in zip(xa, xb)) / len(ids) if ids else None
        S[f"{f}_any"] = e

    def items(field: str, universe) -> dict[str, Any]:
        xa, xb = [], []
        for i in ids:
            for it in universe(i):
                xa.append(it in _ids(A[i].get(field)))
                xb.append(it in _ids(B[i].get(field)))
        return kappa_entry(xa, xb, [False, True])

    req = lambda i: [f["finding_id"] for f in rubric.get(case[i], {}).get("required_findings", [])]  # noqa: E731
    S["findings_covered_items"] = items("findings_covered", req)
    S["num_facts_correct_items"] = items("num_facts_correct", lambda i: [n["fact_id"] for n in rubric.get(case[i], {}).get(
        "numeric_facts", [])] if cat[i] == "numerical_reporting" else [])
    S["neg_findings_reported_items"] = items("neg_findings_reported", lambda i: req(i) if cat[i] == "negative_results" else [])
    neg = [i for i in ids if cat[i] == "negative_results"]
    S["neg_reframed_positive"] = kappa_entry([A[i]["neg_reframed_positive"].strip().lower() for i in neg],
                                             [B[i]["neg_reframed_positive"].strip().lower() for i in neg], ["no", "yes"])
    out["confusion_expressed_level_rows_first_cols_second"] = [
        [sum(1 for x, y in zip(la, lb) if x == r and y == c) for c in range(3)] for r in range(3)]
    # raw output of the original two-annotator function, kept for traceability
    out["original_agreement_function_output"] = agreement(A, B, rubric, cat, case)
    return out


def real_agreement_table(Ao, Bo, As, Bs) -> dict[str, Any]:
    ids, ks = sorted(set(Ao) & set(Bo)), sorted(set(As) & set(Bs))
    ra, rb = [int(Ao[i]["readability"]) for i in ids], [int(Bo[i]["readability"]) for i in ids]
    oa, ob = [Ao[i]["overall_calibration"].strip() for i in ids], [Bo[i]["overall_calibration"].strip() for i in ids]
    sa, sb = [As[k]["support_label"].strip() for k in ks], [Bs[k]["support_label"].strip() for k in ks]
    S = {"readability_quadratic": kappa_entry(ra, rb, [1, 2, 3, 4, 5], "quadratic"),
         "readability_unweighted": kappa_entry(ra, rb, [1, 2, 3, 4, 5]),
         "overall_calibration": kappa_entry(oa, ob, OVERALL_CALIBRATION),
         "support_label": kappa_entry(sa, sb, SUPPORT_LABELS)}
    S["readability_quadratic"]["mean_abs_diff"] = sum(abs(x - y) for x, y in zip(ra, rb)) / len(ids) if ids else None
    return {"n_outputs": len(ids), "n_sentences": len(ks), "stats": S,
            "original_agreement_function_output": real_agreement(Ao, Bo, As, Bs)}


def _fmt(x: Any) -> str:
    return "—" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def agreement_markdown(team: str, syn: dict[str, Any], real: dict[str, Any], statuses: dict[str, str],
                       n_dis: dict[str, Counter], sub_hashes: dict[str, str]) -> str:
    x, y = TEAMS[team]
    ax, ay = ANNOTATORS[x], ANNOTATORS[y]
    worst = "potentially_non_blind" if "potentially_non_blind" in statuses.values() else \
        ("unconfirmed" if "unconfirmed" in statuses.values() else
         ("self_reported_blind_with_private_access" if "self_reported_blind_with_private_access" in statuses.values()
          else "self_reported_blind"))
    L = [f"# Inter-annotator agreement — Team {team}: {x} ({ax.name}) × {y} ({ay.name})", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} from the accepted, independent submissions "
         f"(computed on Team {team}'s subset only; never pooled with the other team).", "",
         "## Blinding status", "",
         f"* {x} ({ax.name}): {BLINDING_STATUS_TEXT[statuses[x]]}",
         f"* {y} ({ay.name}): {BLINDING_STATUS_TEXT[statuses[y]]}",
         f"* **Team {team} label for the report:** independent double annotation; blinding = `{worst}`"
         + ("" if worst == "self_reported_blind" else " — do NOT describe these ratings as fully blind."), "",
         "## Synthetic study", "",
         f"Overlapping outputs: **{syn['n_outputs']}** (ordinal-category outputs: {syn['n_ordinal_outputs']}).", "",
         "| Statistic | n | % agreement | Cohen's κ | note |", "|---|---|---|---|---|"]
    names = {"expressed_level_unweighted": "expressed_level (unweighted κ)", "expressed_level_linear": "expressed_level (linear-weighted κ)",
             "expressed_level_quadratic": "expressed_level (quadratic-weighted κ)", "focal_addressed": "focal_addressed",
             "unsupported_claims_any": "unsupported_claims > 0", "numeric_errors_any": "numeric_errors > 0",
             "findings_covered_items": "findings_covered (per checklist item)", "num_facts_correct_items": "num_facts_correct (per fact)",
             "neg_findings_reported_items": "neg_findings_reported (per finding)", "neg_reframed_positive": "neg_reframed_positive"}
    for k, label in names.items():
        e = syn["stats"][k]
        extra = f"; exact count agreement {_fmt(e['pct_exact_count'])}" if "pct_exact_count" in e else ""
        L.append(f"| {label} | {e['n']} | {_fmt(e['pct_agree'])} | {_fmt(e['kappa'])} | {e['kappa_status']}{extra} |")
    cm = syn["confusion_expressed_level_rows_first_cols_second"]
    L += ["", f"expressed_level confusion (rows = {x}, columns = {y}; levels 0/1/2): `{cm}`", "",
          "## Real-paper study", "",
          f"Overlapping paragraphs: **{real['n_outputs']}**; sentences: **{real['n_sentences']}**.", "",
          "| Statistic | n | % agreement | Cohen's κ | note |", "|---|---|---|---|---|"]
    for k, label in (("readability_quadratic", "readability (quadratic-weighted κ)"), ("readability_unweighted", "readability (unweighted κ)"),
                     ("overall_calibration", "overall_calibration"), ("support_label", "support_label (per sentence)")):
        e = real["stats"][k]
        L.append(f"| {label} | {e['n']} | {_fmt(e['pct_agree'])} | {_fmt(e['kappa'])} | {e['kappa_status']} |")
    L += ["", "## Disagreements sent to adjudication", ""]
    for kind, c in n_dis.items():
        L.append(f"* {kind}: {sum(c.values())} field value(s)" + (f" — {dict(sorted(c.items()))}" if c else ""))
    L += ["", "## Submissions used (sha256)", ""] + [f"* `{k}`: `{v}`" for k, v in sorted(sub_hashes.items())]
    L += ["", "κ = Cohen's kappa from `evaluation.merge_annotations.cohen_kappa`. \"undefined\" means both annotators used "
              "one identical label for every item, so κ is 0/0; percent agreement is still reported."]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- disagreement sheets
def syn_sheet_fields(team: str) -> list[str]:
    x, y = TEAMS[team]
    return ["output_id", "case_ref", "category", "field", f"value_{x}", f"value_{y}", "adjudicated_value", "rationale"]


def real_sheet_fields(team: str) -> list[str]:
    x, y = TEAMS[team]
    return ["item", "case_ref", "field", "sentence_text", f"value_{x}", f"value_{y}", "adjudicated_value", "rationale"]


def synthetic_disagreements(data: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, str]]:
    x, y = ctx["members"]
    out = []
    for d in disagreements(data[x]["syn"], data[y]["syn"]):  # original function
        out.append({"output_id": d["output_id"], "case_ref": ctx["ref_by_id"][d["output_id"]],
                    "category": ctx["cat_by_id"][d["output_id"]], "field": d["field"], f"value_{x}": d["value_A"],
                    f"value_{y}": d["value_B"], "adjudicated_value": "", "rationale": ""})
    return out


def real_disagreements(data: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, str]]:
    """Same comparison as score_real_papers.merge (stripped string equality)."""
    x, y = ctx["members"]
    Ao, Bo, As, Bs = data[x]["ro"], data[y]["ro"], data[x]["rs"], data[y]["rs"]
    out = []
    for i in sorted(Ao):
        for f in ("readability", "overall_calibration"):
            if Ao[i][f].strip() != Bo[i][f].strip():
                out.append({"item": i, "case_ref": Ao[i]["case_ref"], "field": f, "sentence_text": "",
                            f"value_{x}": Ao[i][f].strip(), f"value_{y}": Bo[i][f].strip(), "adjudicated_value": "", "rationale": ""})
    for k in sorted(As, key=lambda s: (s.split("#")[0], int(s.split("#")[1]))):
        if As[k]["support_label"].strip() != Bs[k]["support_label"].strip():
            out.append({"item": k, "case_ref": As[k]["case_ref"], "field": "support_label", "sentence_text": As[k]["sentence_text"],
                        f"value_{x}": As[k]["support_label"].strip(), f"value_{y}": Bs[k]["support_label"].strip(),
                        "adjudicated_value": "", "rationale": ""})
    return out


def adjudication_viewer(paths: Paths, ctx: dict[str, Any], data: dict[str, Any], syn_dis: list[dict[str, str]],
                        real_dis: list[dict[str, str]]) -> str:
    team, (x, y) = ctx["team"], ctx["members"]
    nx, ny = ANNOTATORS[x].name, ANNOTATORS[y].name
    cards = []
    by_out: dict[str, list[dict[str, str]]] = {}
    for d in syn_dis:
        by_out.setdefault(d["output_id"], []).append(d)
    for oid, ds in by_out.items():
        ref = ctx["ref_by_id"][oid]
        rows = "".join(f"<tr><td><code>{d['field']}</code></td><td>{html.escape(d[f'value_{x}']) or '(empty)'}</td>"
                       f"<td>{html.escape(d[f'value_{y}']) or '(empty)'}</td></tr>" for d in ds)
        notes = "".join(f"<p class='muted'><b>{who} notes</b>: "
                        + _c("span", "note", " | ".join(v for v in (data[who]['syn'][oid].get('notes_p1', ''),
                                                                   data[who]['syn'][oid].get('notes_p2', '')) if v.strip()) or "(none)")
                        + "</p>" for who in (x, y))
        p1 = (paths.pass1_packages / f"{ref}.md").read_text(encoding="utf-8")
        p2 = (paths.pass2_packages / f"{ref}.md").read_text(encoding="utf-8")
        cards.append(f"<section class='card' id='o-{oid}'><h2><code>{oid}</code><span class='tag'>case {ref}</span>"
                     f"<span class='tag'>{ctx['cat_by_id'][oid]}</span></h2>" + _c("div", "out", ctx["syn_rows"][oid]["output_text"])
                     + f"<table class='idx'><tr><th>field</th><th>{x} ({nx})</th><th>{y} ({ny})</th></tr>{rows}</table>{notes}"
                     + f"<details><summary>Research package, pass-1 rubric</summary>{_c('pre', 'pkg', p1)}</details>"
                     + f"<details><summary>Research package, pass-2 checklists</summary>{_c('pre', 'pkg', p2)}</details></section>")
    real_by: dict[str, list[dict[str, str]]] = {}
    for d in real_dis:
        real_by.setdefault(d["item"].split("#")[0], []).append(d)
    text = {r["output_id"]: r for r in ctx["real_out"]}
    for oid, ds in real_by.items():
        ref = text[oid]["case_ref"]
        rows = "".join(f"<tr><td><code>{html.escape(d['item'])}</code> <code>{d['field']}</code></td><td>{html.escape(d[f'value_{x}'])}</td>"
                       f"<td>{html.escape(d[f'value_{y}'])}</td></tr>" for d in ds)
        pkg = (paths.real_packages / f"{ref}.md").read_text(encoding="utf-8")
        cards.append(f"<section class='card' id='o-{oid}'><h2><code>{oid}</code><span class='tag'>paper {ref}</span></h2>"
                     + _c("div", "out", text[oid]["output_text"])
                     + f"<table class='idx'><tr><th>item / field</th><th>{x} ({nx})</th><th>{y} ({ny})</th></tr>{rows}</table>"
                     + f"<details><summary>Research package</summary>{_c('pre', 'pkg', pkg)}</details></section>")
    body = (f"<h1 id='top'>Team {team} adjudication — {x} ({nx}) and {y} ({ny})</h1>"
            f"<p>{len(syn_dis)} synthetic and {len(real_dis)} real-paper field values differ. Matching labels are kept "
            "automatically and are not listed. For every row of the two CSV sheets, agree on <code>adjudicated_value</code> "
            "using the research package and ANNOTATION_GUIDE.md, and write a short <code>rationale</code>. In the synthetic "
            "sheet write <code>NONE</code> for an empty list. Item identities of the texts stay hidden.</p>" + "".join(cards))
    return _page(f"Team {team} adjudication", body)


ADJ_START = """# Stage 5 — Team {team} adjudication ({x} {nx} + {y} {ny})

你们两人的独立标注都已提交并固定。本包只包含 **Team {team}** 中两人**不一致**的字段；一致的标签已自动保留。

1. 用浏览器打开 `adjudication_viewer_Team{team}.html`：每条 output 显示段落、两人的取值、各自的 notes，以及研究包（Pass 1 rubric 和 Pass 2 清单）。
2. 两人一起逐行讨论，依据**研究包证据**和 `ANNOTATION_GUIDE.md`（不要猜测系统身份）。
3. 在 `{syn}` 和 `{real}` 的每一行填写：
   * `adjudicated_value`：最终取值（必须是该字段允许的值；synthetic 表里“清单为空”写 `NONE`）。
   * `rationale`：一两句理由，引用研究包或 guide 条款。
4. 不要增删行，不要改其他列。另存为 CSV UTF-8，文件名不变，交给协调人。
5. 有空行、非法取值或缺少理由时，协调人的检查会拒绝生成共识，并把问题发回。

Synthetic 表：{n_syn} 行；真实论文表：{n_real} 行。
"""


def agree(paths: Paths, team: str, force: bool = False) -> dict[str, Any]:
    tdir = paths.team_dir(team)
    if (tdir / "adjudicated").exists() and any((tdir / "adjudicated").glob("*.csv")) and not force:
        raise TeamError(f"Team {team} adjudication has already been taken in; re-running `agree` would regenerate the "
                        f"disagreement sheets. Use --force only if a submission was legitimately replaced.")
    ctx = team_context(paths, team)
    data = load_team(paths, ctx)
    x, y = ctx["members"]
    syn = synthetic_agreement(data[x]["syn"], data[y]["syn"], ctx)
    real = real_agreement_table(data[x]["ro"], data[y]["ro"], data[x]["rs"], data[y]["rs"])
    sdis, rdis = synthetic_disagreements(data, ctx), real_disagreements(data, ctx)
    statuses = {w: person_status(paths, w) for w in (x, y)}
    hashes = {f"{w}/{k}": sha_file(accepted_path(paths, w, k)) for w in (x, y)
              for k in ("pass1", "pass2", "real_outputs", "real_sentences")}
    n_dis = {"synthetic": Counter(d["field"] for d in sdis), "real": Counter(d["field"] for d in rdis)}
    result = {"team": team, "annotators": {w: ANNOTATORS[w].name for w in (x, y)}, "blinding_status": statuses,
              "synthetic": syn, "real": real, "n_disagreements": {k: dict(v) for k, v in n_dis.items()},
              "submission_sha256": hashes, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f"agreement_Team{team}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    md = agreement_markdown(team, syn, real, statuses, n_dis, hashes)
    (tdir / f"agreement_report_Team{team}.md").write_text(md, encoding="utf-8")
    res_dir = paths.root / "results" / "human_agreement" / "four_person"
    res_dir.mkdir(parents=True, exist_ok=True)
    pub = {k: v for k, v in result.items() if k != "submission_sha256"}
    (res_dir / f"agreement_Team{team}.json").write_text(json.dumps(pub, indent=1, ensure_ascii=False))
    (res_dir / f"agreement_report_Team{team}.md").write_text(md, encoding="utf-8")
    # student-facing adjudication bundle
    bdir = tdir / "adjudication_bundle"
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir(parents=True)
    syn_name, real_name = f"adjudication_synthetic_Team{team}.csv", f"adjudication_real_Team{team}.csv"
    write_csv(bdir / syn_name, sdis, syn_sheet_fields(team), bom=True)
    write_csv(bdir / real_name, rdis, real_sheet_fields(team), bom=True)
    (bdir / f"adjudication_viewer_Team{team}.html").write_text(adjudication_viewer(paths, ctx, data, sdis, rdis), encoding="utf-8")
    shutil.copyfile(paths.guide, bdir / "ANNOTATION_GUIDE.md")
    (bdir / "00_START_HERE.md").write_text(ADJ_START.format(team=team, x=x, y=y, nx=ANNOTATORS[x].name, ny=ANNOTATORS[y].name,
                                                            syn=syn_name, real=real_name, n_syn=len(sdis), n_real=len(rdis)),
                                           encoding="utf-8")
    zip_dir(bdir, paths.dist_dir / f"adjudication_Team{team}.zip", f"adjudication_Team{team}")
    return {"team": team, "n_synthetic_disagreements": len(sdis), "n_real_disagreements": len(rdis),
            "report": str(tdir / f"agreement_report_Team{team}.md"), "bundle": str(paths.dist_dir / f"adjudication_Team{team}.zip")}


# ----------------------------------------------------------------------------- adjudication -> team consensus
def check_adjudicated_synthetic(rows: list[dict[str, str]], expected: list[dict[str, str]], team: str) -> list[str]:
    x, y = TEAMS[team]
    errs = []
    exp = {(d["output_id"], d["field"]): d for d in expected}
    got = {}
    for r in rows:
        k = (r.get("output_id", "").strip(), r.get("field", "").strip())
        if k in got:
            errs.append(f"duplicated adjudication row {k[0]}/{k[1]}")
        got[k] = r
    for k in sorted(set(exp) - set(got)):
        errs.append(f"missing adjudication row {k[0]}/{k[1]}")
    for k in sorted(set(got) - set(exp)):
        errs.append(f"row {k[0]}/{k[1]} is not a disagreement (do not add rows)")
    for k in sorted(set(got) & set(exp)):
        r, e = got[k], exp[k]
        for col in (f"value_{x}", f"value_{y}"):
            if col in r and _canon(k[1], r[col]) != e[col]:
                errs.append(f"{k[0]}/{k[1]}: column {col} does not match the submitted labels (stale or edited sheet)")
        if not (r.get("adjudicated_value") or "").strip():
            errs.append(f"{k[0]}/{k[1]}: adjudicated_value is empty (write NONE for an empty list)")
        if not (r.get("rationale") or "").strip():
            errs.append(f"{k[0]}/{k[1]}: rationale is empty")
    return errs


def strict_consensus_row(row: dict[str, str], cat: str, checklist: dict[str, set[str]]) -> list[str]:
    """Value rules of merge_annotations.validate applied to an adjudicated consensus row."""
    oid = row["output_id"]
    errs = validate_consensus_row(row, cat)  # original
    fa, lv = row.get("focal_addressed", ""), row.get("expressed_level", "")
    if cat in ORDINAL_CATEGORIES and fa == "no" and lv not in ("", "0"):
        errs.append(f"{oid}: focal_addressed=no requires expressed_level=0")
    if cat not in ORDINAL_CATEGORIES and fa:
        errs.append(f"{oid}: focal_addressed must be blank for {cat}")
    bad = _ids(row.get("findings_covered")) - checklist.get("findings", set())
    if bad:
        errs.append(f"{oid}: findings_covered has unknown ids {sorted(bad)}")
    if cat == "numerical_reporting":
        if _ids(row.get("num_facts_correct")) - checklist.get("facts", set()):
            errs.append(f"{oid}: num_facts_correct has unknown ids")
    elif row.get("num_facts_correct"):
        errs.append(f"{oid}: num_facts_correct only for numerical_reporting")
    if cat == "negative_results":
        if _ids(row.get("neg_findings_reported")) - checklist.get("findings", set()):
            errs.append(f"{oid}: neg_findings_reported has unknown ids")
        if row.get("neg_reframed_positive") not in ("yes", "no"):
            errs.append(f"{oid}: neg_reframed_positive must be yes/no")
    elif row.get("neg_findings_reported") or row.get("neg_reframed_positive"):
        errs.append(f"{oid}: NEG fields only for negative_results")
    return errs


def check_adjudicated_real(rows: list[dict[str, str]], expected: list[dict[str, str]], team: str) -> tuple[dict, list[str]]:
    x, y = TEAMS[team]
    errs, vals = [], {}
    exp = {(d["item"], d["field"]): d for d in expected}
    got = {}
    for r in rows:
        k = (r.get("item", "").strip(), r.get("field", "").strip())
        if k in got:
            errs.append(f"duplicated adjudication row {k[0]}/{k[1]}")
        got[k] = r
    for k in sorted(set(exp) - set(got)):
        errs.append(f"missing adjudication row {k[0]}/{k[1]}")
    for k in sorted(set(got) - set(exp)):
        errs.append(f"row {k[0]}/{k[1]} is not a disagreement (do not add rows)")
    allowed = {"readability": READABILITY, "overall_calibration": OVERALL_CALIBRATION, "support_label": SUPPORT_LABELS}
    for k in sorted(set(got) & set(exp)):
        r, e = got[k], exp[k]
        for col in (f"value_{x}", f"value_{y}"):
            if col in r and r[col].strip() != e[col]:
                errs.append(f"{k[0]}/{k[1]}: column {col} does not match the submitted labels (stale or edited sheet)")
        v = (r.get("adjudicated_value") or "").strip()
        if v not in allowed[k[1]]:
            errs.append(f"{k[0]}/{k[1]}: adjudicated_value {v!r} must be one of {allowed[k[1]]}")
        if not (r.get("rationale") or "").strip():
            errs.append(f"{k[0]}/{k[1]}: rationale is empty")
        vals[k] = v
    return vals, errs


def _accept_adjudication(paths: Paths, team: str, kind: str, file: Path, replace: bool) -> Path:
    d = paths.team_dir(team) / "adjudicated"
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    (d / "received").mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, d / "received" / f"{ts}__{file.name}")
    target = d / f"adjudicated_{kind}_Team{team}.csv"
    if target.exists() and sha_file(target) != sha_file(file):
        if not replace:
            raise TeamError(f"a different accepted {kind} adjudication exists for Team {team}; use --replace to supersede it")
        (d / "superseded").mkdir(exist_ok=True)
        shutil.move(str(target), d / "superseded" / f"{ts}__{target.name}")
    shutil.copy2(file, target)
    return target


def build_team_consensus(paths: Paths, team: str, syn_file: Optional[Path] = None, real_file: Optional[Path] = None,
                         replace: bool = False) -> tuple[bool, list[str]]:
    """Validate adjudication sheets against the recomputed disagreements; only if BOTH are valid are they accepted and
    the team consensus written. Nothing is ever chosen automatically for a disagreement."""
    ctx = team_context(paths, team)
    data = load_team(paths, ctx)
    x, y = ctx["members"]
    tdir = paths.team_dir(team)
    adir = tdir / "adjudicated"
    syn_src = syn_file or adir / f"adjudicated_synthetic_Team{team}.csv"
    real_src = real_file or adir / f"adjudicated_real_Team{team}.csv"
    errs = []
    for p in (syn_src, real_src):
        if not p.exists():
            errs.append(f"adjudication file {p} not found")
    if errs:
        return False, errs
    sdis, rdis = synthetic_disagreements(data, ctx), real_disagreements(data, ctx)
    srows, rrows = read_csv_any(syn_src), read_csv_any(real_src)
    errs += check_adjudicated_synthetic(srows, sdis, team)
    rvals, rerrs = check_adjudicated_real(rrows, rdis, team)
    errs += rerrs
    # synthetic consensus through the ORIGINAL consensus() (matching values kept, adjudicated values used, NONE -> empty)
    adj = [{"output_id": r.get("output_id", "").strip(), "field": r.get("field", "").strip(),
            "adjudicated_value": r.get("adjudicated_value", "")} for r in srows]
    cons, cerrs = consensus(data[x]["syn"], data[y]["syn"], adj)
    errs += cerrs
    cls = rubric_checklists(paths)
    for r in cons:
        r["case_id"], r["category"] = ctx["case_by_id"][r["output_id"]], ctx["cat_by_id"][r["output_id"]]
        errs += strict_consensus_row(r, r["category"], cls[ctx["ref_by_id"][r["output_id"]]])
    if errs:
        (tdir / "consensus_errors.txt").write_text("\n".join(errs) + "\n")
        return False, errs
    if syn_file:
        _accept_adjudication(paths, team, "synthetic", syn_file, replace)
    if real_file:
        _accept_adjudication(paths, team, "real", real_file, replace)
    Ao, Bo, As, Bs = data[x]["ro"], data[y]["ro"], data[x]["rs"], data[y]["rs"]
    outs = [{"output_id": i, "case_ref": Ao[i]["case_ref"],
             **{f: (Ao[i][f].strip() if Ao[i][f].strip() == Bo[i][f].strip() else rvals[(i, f)])
                for f in ("readability", "overall_calibration")}} for i in sorted(Ao)]
    sents = [{"output_id": As[k]["output_id"], "sentence_idx": As[k]["sentence_idx"],
              "support_label": As[k]["support_label"].strip() if As[k]["support_label"].strip() == Bs[k]["support_label"].strip()
              else rvals[(k, "support_label")]} for k in sorted(As, key=lambda s: (s.split("#")[0], int(s.split("#")[1])))]
    write_csv(tdir / f"consensus_synthetic_Team{team}.csv", sorted(cons, key=lambda r: r["output_id"]),
              ["output_id", "case_id", "category"] + SCORED_FIELDS)
    write_csv(tdir / f"consensus_real_outputs_Team{team}.csv", outs, ["output_id", "case_ref", "readability", "overall_calibration"])
    write_csv(tdir / f"consensus_real_sentences_Team{team}.csv", sents, ["output_id", "sentence_idx", "support_label"])
    # how disagreements were resolved (for an honest report of adjudication, e.g. coordinator influence)
    summ: dict[str, Counter] = {"synthetic": Counter(), "real": Counter()}
    for r in srows:
        f = r["field"].strip()
        v = _canon(f, "" if r["adjudicated_value"].strip().upper() == "NONE" else r["adjudicated_value"])
        vx, vy = _canon(f, r.get(f"value_{x}", "")), _canon(f, r.get(f"value_{y}", ""))
        summ["synthetic"][x if v == vx else (y if v == vy else "neither")] += 1
    for r in rrows:
        v = r["adjudicated_value"].strip()
        summ["real"][x if v == r.get(f"value_{x}", "").strip() else (y if v == r.get(f"value_{y}", "").strip() else "neither")] += 1
    (tdir / f"adjudication_summary_Team{team}.json").write_text(json.dumps(
        {"team": team, "resolved_to_value_of": {k: dict(v) for k, v in summ.items()},
         "n_synthetic": len(srows), "n_real": len(rrows)}, indent=1))
    if (tdir / "consensus_errors.txt").exists():
        (tdir / "consensus_errors.txt").unlink()
    return True, []
