"""Per-person, per-stage annotation packets, viewers, personal instructions and zip archives.

Built ONLY from annotator-safe inputs: the original blinded packets (`annotation/blinded_synthetic.csv`,
`annotation/real/*.csv`), the original package files (`annotation/{pass1,pass2,real}/packages/*.md`, copied
byte-for-byte), the public DEV material, and `annotation/four_person/assignment.json`. No private file is
read here. Each person receives only their team's items; each stage is a separate folder and zip, so
Pass-2 checklists physically do not exist in the Pass-1 package.

Layout (packets/ and dist/ are gitignored; instructions/ is committed):
  annotation/four_person/instructions/README_<ID>_<Name>.md, SUBMISSION_CHECKLIST_<ID>_<Name>.md
  annotation/four_person/packets/<ID>_<Name>/{0_training,1_pass1,2_pass2,3_real}/
  annotation/four_person/dist/<ID>_<Name>__<stage dir>.zip
Re-running is idempotent (fixed seed, fixed zip timestamps). If any generated file would change, the
build stops unless force=True, which first moves the previous build to annotation/four_person/_backups/.
"""
from __future__ import annotations

import html
import json
import random
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

from evaluation.blinding import OVERALL_CALIBRATION, PASS1_FIELDS, PASS2_FIELDS, SUPPORT_LABELS, package_markdown
from evaluation.four_person.assignment import AssignmentError, load_assignment
from evaluation.four_person.roster import (ANNOTATORS, SESSION_EXPOSURE, STAGE_DIRS, STAGES, TEAMS, Paths, readme_name, sha_file,
                                           sheet_name, viewer_name, write_csv, zip_name)
from evaluation.four_person.submissions import (COLUMNS, DECLARATION_QUESTIONS, TIMELOG_STAGES, checklists_from_pass2_md,
                                                expected_sheet, original_rows)
from src.package_schema import ORDINAL_CATEGORIES, CaseRecord

ZIP_DATE = (2026, 1, 1, 0, 0, 0)
DEMO_CASE = re.compile(r"DEV case ([A-Z]{3}-p1[ab])")


class BuildConflict(RuntimeError):
    pass


# ----------------------------------------------------------------------------- rows in each person's order
def shuffled(rows: list[dict[str, Any]], seed: int, who: str, stage: str) -> list[dict[str, Any]]:
    out = sorted(rows, key=lambda r: r["output_id"])
    random.Random(f"{seed}:rows:{who}:{stage}").shuffle(out)
    return out


def person_sheets(orig: dict[str, list[dict[str, str]]], assignment: dict[str, Any], who: str) -> dict[str, list[dict[str, Any]]]:
    seed = assignment["seed"]
    p1 = shuffled(expected_sheet(orig, assignment, who, "pass1"), seed, who, "pass1")
    p2 = shuffled(expected_sheet(orig, assignment, who, "pass2"), seed, who, "pass2")
    ro = shuffled(expected_sheet(orig, assignment, who, "real_outputs"), seed, who, "real")
    order = {r["output_id"]: i for i, r in enumerate(ro)}
    rs = sorted(expected_sheet(orig, assignment, who, "real_sentences"),
                key=lambda s: (order[s["output_id"]], int(s["sentence_idx"])))
    return {"pass1": p1, "pass2": p2, "real_outputs": ro, "real_sentences": rs}


# ----------------------------------------------------------------------------- personal instructions
def _fill(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", text)))
    if left:
        raise ValueError(f"unfilled template placeholders: {left}")
    return text


def template_values(assignment: dict[str, Any], who: str) -> dict[str, str]:
    a, p = ANNOTATORS[who], ANNOTATORS[ANNOTATORS[who].partner]
    team = assignment["teams"][a.team]
    other = next(t for t in TEAMS if t != a.team)
    cats = assignment["synthetic_case_category"]
    nout = assignment["synthetic_case_n_outputs"]
    case_list = ["| # | case_ref | category | outputs |", "|---|---|---|---|"]
    for i, ref in enumerate(sorted(team["synthetic_case_refs"], key=lambda r: (cats[r], r)), 1):
        case_list.append(f"| {i} | `{ref}` | {cats[ref]} | {nout[ref]} |")
    paper_list = ["| paper | outputs | sentences |", "|---|---|---|"]
    for pp in team["real_papers"]:
        st = assignment["real_paper_stats"][pp]
        paper_list.append(f"| `{pp}` | {st['n_outputs']} | {st['n_sentences']} |")
    order_note = {"A": "（先用 `intake` 接收自己的文件，并在群里公布 sha256）",
                  "B": "（等 Zheyuan 在群里公布他同一阶段文件的 sha256 之后再发）"}.get(who, "")
    c = team["counts"]
    ex = SESSION_EXPOSURE
    mine = set(team["synthetic_case_refs"]) | set(team["real_papers"])

    def split(refs: list[str]) -> str:
        own = [r for r in refs if r in mine]
        return (f"其中在你分配里的是 **{'、'.join(own)}**" if own else "都不在你的分配里") + \
            (f"，另外 {len(refs) - len(own)} 个属于 Team {other}" if len(refs) > len(own) else "")

    exposure = (f"生成本流程的 AI 助手会话（Claude Code，{ex['date']}）在检查文件结构时，曾在终端里显示过少量私有内容："
                f"`case_alias_map.csv` 的 {len(ex['alias_rows_case_refs'])} 行（case_ref 背后的 case ID；{split(ex['alias_rows_case_refs'])}）；"
                f"`condition_mapping.csv` 中 {sum(ex['condition_rows_synthetic'].values())} 条 synthetic output 的条件"
                f"（{split(list(ex['condition_rows_synthetic']))}）；`condition_mapping_real.csv` 中 "
                f"{sum(ex['condition_rows_real'].values())} 条 output 的条件（{split(list(ex['condition_rows_real']))}）；"
                f"以及 {ex['n_pass2_checklist_id_names']} 个 Pass 2 清单 ID 的名称（不含清单内容）。")
    return {"ID": who, "NAME": a.name, "TAG": a.tag, "TEAM": a.team, "OTHER_TEAM": other, "PARTNER_ID": p.id,
            "PARTNER_NAME": p.name, "N_CASES": str(c["synthetic_cases"]), "N_SYN": str(c["synthetic_outputs"]),
            "N_PAPERS": str(c["real_papers"]), "N_REAL_OUT": str(c["real_outputs"]), "N_REAL_SENT": str(c["real_sentences"]),
            "CASE_LIST": "\n".join(case_list), "PAPER_LIST": "\n".join(paper_list),
            "F_PASS1": sheet_name(who, "pass1"), "F_PASS2": sheet_name(who, "pass2"),
            "F_REAL_OUT": sheet_name(who, "real_outputs"), "F_REAL_SENT": sheet_name(who, "real_sentences"),
            "F_DECL": sheet_name(who, "declaration"), "F_TIME": sheet_name(who, "timelog"),
            "V_PASS1": viewer_name(who, "pass1"), "V_PASS2": viewer_name(who, "pass2"), "V_REAL": viewer_name(who, "real"),
            "Z_TRAINING": zip_name(who, "training"), "Z_PASS1": zip_name(who, "pass1"), "Z_PASS2": zip_name(who, "pass2"),
            "Z_REAL": zip_name(who, "real"), "README": readme_name(who), "CHECKLIST": f"SUBMISSION_CHECKLIST_{a.tag}.md",
            "ORDER_NOTE": order_note, "EXPOSURE_NOTE": exposure}


def render_instructions(templates: Path, assignment: dict[str, Any], who: str) -> tuple[str, str]:
    v = template_values(assignment, who)
    role = _fill((templates / f"ROLE_{who}.md").read_text(encoding="utf-8"), v)
    readme = _fill((templates / "README_PERSON.md").read_text(encoding="utf-8"), {**v, "ROLE_BLOCK": role.strip()})
    checklist = _fill((templates / "SUBMISSION_CHECKLIST.md").read_text(encoding="utf-8"), v)
    return readme, checklist


def start_here(assignment: dict[str, Any], who: str, stage: str) -> str:
    v = template_values(assignment, who)
    head = f"# {STAGE_DIRS[stage]} — Annotator {who} ({v['NAME']}, Team {v['TEAM']})\n\n"
    body = {
        "training": f"""## Stage 0：培训与盲态声明 / Training and blinding declaration

1. 读你的个人说明 `{v['README']}` 和 `ANNOTATION_GUIDE.md`。
2. 用浏览器打开 `dev_training_viewer.html`，学习 4 个 DEV 例子（也可直接看 `demo_example_NOT_TEST.md` 和 `dev_packages/`）。
3. 填写 `{v['F_DECL']}`（Q1–Q6：`yes`/`no`/`unsure`；Q7：`agree`/`disagree`；`yes`/`unsure` 要写 `details`），另存为 CSV UTF-8，发给协调人。
4. 保留 `{v['F_TIME']}`：每个阶段结束后记录总分钟数和次数，全部结束后提交。
5. `{v['CHECKLIST']}` 是你的提交清单。

本压缩包不含任何 TEST 条目。协调人接收你的声明之后才会发 Pass 1。
""",
        "pass1": f"""## Stage 1：Synthetic Pass 1（{v['N_SYN']} 行）

1. 用浏览器打开 `{v['V_PASS1']}`；用 Excel / Google Sheets 打开 `{v['F_PASS1']}`。
2. 每行：读研究包（`packages/<case_ref>.md`，viewer 里可展开）、焦点命题和等级描述，再读段落，填写
   `expressed_level`、`focal_addressed`（NUM/NEG 留空）、`unsupported_claims`、`numeric_errors`、`confidence_p1`、`notes_p1`。
3. 另存为 CSV UTF-8（文件名不变），用 viewer 顶部的 “Check my CSV file” 自检。
4. 发给协调人。**Pass 2 只在你的 Pass 1 被接收后发放。** 细节见 `{v['README']}` §4。
""",
        "pass2": f"""## Stage 2：Synthetic Pass 2（同样的 {v['N_SYN']} 条 output，顺序不同）

1. 用浏览器打开 `{v['V_PASS2']}`；打开 `{v['F_PASS2']}`。
2. 每行：对照研究包里的清单，填写 `findings_covered`、（NUM）`num_facts_correct`、（NEG）`neg_findings_reported` 和 `neg_reframed_positive`、`confidence_p2`、`notes_p2`。ID 用分号分隔；没有就留空。
3. **不要回头修改 Pass 1。**
4. 另存为 CSV UTF-8，自检，发给协调人。细节见 `{v['README']}` §5。
""",
        "real": f"""## Stage 3：真实论文（{v['N_PAPERS']} 篇，{v['N_REAL_OUT']} 段，{v['N_REAL_SENT']} 句）

1. 用浏览器打开 `{v['V_REAL']}`。
2. `{v['F_REAL_OUT']}`：每段填 `readability`（1–5）、`overall_calibration`、`confidence`、`notes`。
3. `{v['F_REAL_SENT']}`：每句填 `support_label`（`SUPPORTED` / `OVERSTATED` / `UNDERSTATED` / `UNSUPPORTED` / `NUMERIC_ERROR` / `NOT_A_CLAIM`）和可选的 `notes`。
4. 只以研究包为依据，不以原论文作者的结论为依据。
5. 两个文件都另存为 CSV UTF-8，自检，发给协调人。细节见 `{v['README']}` §6。
""",
    }[stage]
    return head + body


# ----------------------------------------------------------------------------- viewers
CSS = """
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;max-width:66rem;margin:0 auto;
padding:0 1rem 5rem;line-height:1.55;color:#1d1d1f;background:#fff}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #d0d0d0;padding:.5rem 0;z-index:5;display:flex;
gap:1rem;flex-wrap:wrap;align-items:center;font-size:.9rem}.bar form{display:flex;gap:.3rem}
.card{border:1px solid #c9c9c9;border-radius:8px;padding:.8rem 1rem;margin:1.1rem 0;scroll-margin-top:4rem}
.card.flash{box-shadow:0 0 0 3px #f5b400}.card h2{font-size:1.05rem;margin:.1rem 0 .5rem}
.out{background:#f3f4f6;padding:.75rem .9rem;border-radius:6px;white-space:pre-wrap}
pre.pkg{white-space:pre-wrap;font-size:.83rem;background:#fafafa;border:1px solid #e6e6e6;padding:.7rem;border-radius:6px;
font-family:ui-monospace,Menlo,Consolas,monospace;max-height:70vh;overflow:auto}
.hint{font-size:.86rem;background:#eef5ff;border-radius:6px;padding:.45rem .7rem;margin:.6rem 0}
.tag{display:inline-block;font-size:.75rem;padding:.05rem .45rem;border-radius:4px;background:#e5e7eb;margin-left:.3rem;
font-weight:500}.tag.sep{background:#fde7c8}
table.idx{border-collapse:collapse;font-size:.85rem;width:100%}table.idx td,table.idx th{border-bottom:1px solid #eee;
padding:.15rem .5rem;text-align:left}.box{border:2px dashed #8a8a8a;border-radius:8px;padding:.6rem 1rem;margin:1rem 0}
.ok{color:#0a7a2f;font-weight:600}.bad{color:#b00020;font-weight:600}ol.sents li{margin:.3rem 0}
code{background:#f0f0f0;padding:0 .25rem;border-radius:3px}.muted{color:#555;font-size:.88rem}
details summary{cursor:pointer;font-weight:600;margin:.3rem 0}
"""

# Offline CSV self-check. Mirrors evaluation/four_person/submissions.py (the coordinator's official check).
# Pure function FPCHECK.check(spec, kind, csvText) so tests can run it under node.
CHECKER_JS = r"""
var FPCHECK = (function () {
  var CONF = ["low", "medium", "high"];
  function norm(s) { return String(s == null ? "" : s).normalize("NFC").split(/\s+/).filter(Boolean).join(" "); }
  function t(s) { return String(s == null ? "" : s).trim(); }
  function parseCSV(x) {
    if (x.charCodeAt(0) === 0xFEFF) { x = x.slice(1); }
    var rows = [], row = [], f = "", q = false, i, c;
    for (i = 0; i < x.length; i++) {
      c = x[i];
      if (q) {
        if (c === '"') { if (x[i + 1] === '"') { f += '"'; i++; } else { q = false; } } else { f += c; }
      } else if (c === '"') { q = true; }
      else if (c === ",") { row.push(f); f = ""; }
      else if (c === "\n") { row.push(f); rows.push(row); row = []; f = ""; }
      else if (c !== "\r") { f += c; }
    }
    if (f !== "" || row.length) { row.push(f); rows.push(row); }
    return rows.filter(function (r) { return !(r.length === 1 && t(r[0]) === ""); });
  }
  function ids(s) { return String(s == null ? "" : s).replace(/,/g, ";").split(";").map(t).filter(Boolean); }
  function isInt(v) { return /^[0-9]+$/.test(v); }
  function keyOf(kind, r) { return kind === "real_sentences" ? r.output_id + "#" + t(r.sentence_idx) : r.output_id; }
  var RULES = {
    pass1: function (r, e, spec) {
      var m = [], lv = t(r.expressed_level), fa = t(r.focal_addressed).toLowerCase();
      if (spec.ordinal.indexOf(e.c) >= 0) {
        if (["0", "1", "2"].indexOf(lv) < 0) { m.push("expressed_level must be 0, 1 or 2"); }
        if (["yes", "no"].indexOf(fa) < 0) { m.push("focal_addressed must be yes or no"); }
        else if (fa === "no" && lv !== "" && lv !== "0") { m.push("focal_addressed = no requires expressed_level = 0"); }
      } else {
        if (lv) { m.push("expressed_level must be BLANK for " + e.c); }
        if (fa) { m.push("focal_addressed must be BLANK for " + e.c); }
      }
      ["unsupported_claims", "numeric_errors"].forEach(function (f) {
        if (!isInt(t(r[f]))) { m.push(f + " must be a whole number >= 0"); }
      });
      if (CONF.indexOf(t(r.confidence_p1).toLowerCase()) < 0) { m.push("confidence_p1 must be low, medium or high"); }
      return m;
    },
    pass2: function (r, e, spec) {
      var m = [], cl = spec.checklists[e.r] || {findings: [], facts: []};
      function bad(field, allowed) {
        var b = ids(r[field]).filter(function (x) { return allowed.indexOf(x) < 0; });
        if (b.length) { m.push(field + " has IDs not in this case's checklist: " + b.join(", ")); }
      }
      bad("findings_covered", cl.findings);
      if (e.c === "numerical_reporting") { bad("num_facts_correct", cl.facts); }
      else if (t(r.num_facts_correct)) { m.push("num_facts_correct must be BLANK (numerical_reporting only)"); }
      if (e.c === "negative_results") {
        bad("neg_findings_reported", cl.findings);
        if (["yes", "no"].indexOf(t(r.neg_reframed_positive).toLowerCase()) < 0) { m.push("neg_reframed_positive must be yes or no"); }
      } else if (t(r.neg_findings_reported) || t(r.neg_reframed_positive)) {
        m.push("neg_findings_reported / neg_reframed_positive must be BLANK (negative_results only)");
      }
      if (CONF.indexOf(t(r.confidence_p2).toLowerCase()) < 0) { m.push("confidence_p2 must be low, medium or high"); }
      return m;
    },
    real_outputs: function (r, e, spec) {
      var m = [];
      if (["1", "2", "3", "4", "5"].indexOf(t(r.readability)) < 0) { m.push("readability must be 1, 2, 3, 4 or 5"); }
      if (spec.calibration.indexOf(t(r.overall_calibration)) < 0) { m.push("overall_calibration must be one of " + spec.calibration.join(", ")); }
      if (CONF.indexOf(t(r.confidence).toLowerCase()) < 0) { m.push("confidence must be low, medium or high"); }
      return m;
    },
    real_sentences: function (r, e, spec) {
      return spec.support.indexOf(t(r.support_label)) < 0 ? ["support_label must be one of " + spec.support.join(", ")] : [];
    }
  };
  function check(spec, kind, text) {
    var K = spec.kinds[kind], E = [];
    if (!K) { return {errors: ["this viewer cannot check a '" + kind + "' file"], n: 0, expected: 0}; }
    var rows = parseCSV(text);
    if (!rows.length) { return {errors: ["the file is empty"], n: 0, expected: K.rows.length}; }
    var header = rows[0].map(t);
    var miss = K.columns.filter(function (c) { return header.indexOf(c) < 0; });
    var extra = header.filter(function (h) { return h && K.columns.indexOf(h) < 0; });
    if (miss.length) { E.push("missing column(s): " + miss.join(", ") + " (is this the right file?)"); }
    if (extra.length) { E.push("unexpected column(s): " + extra.join(", ") + " (do not add columns)"); }
    var exp = {}, seen = {}, recs;
    K.rows.forEach(function (e) { exp[e.k] = e; });
    recs = rows.slice(1).map(function (r) { var o = {}; header.forEach(function (h, i) { o[h] = r[i] === undefined ? "" : r[i]; }); return o; });
    var tcol = kind === "real_sentences" ? "sentence_text" : "output_text";
    recs.forEach(function (r, i) {
      var k = keyOf(kind, r), line = "row " + (i + 2) + " (" + k + ")", e = exp[k];
      if (seen[k]) { E.push(line + ": duplicated row"); return; }
      seen[k] = true;
      if (!e) { E.push(line + ": not one of your assigned rows"); return; }
      if (norm(r[tcol]) !== norm(e.t)) { E.push(line + ": " + tcol + " was changed (do not edit the text; re-save as 'CSV UTF-8')"); }
      if (norm(r.case_ref) !== norm(e.r)) { E.push(line + ": case_ref was changed"); }
      if (norm(r.package_file) !== "packages/" + e.r + ".md") { E.push(line + ": package_file was changed"); }
      if (e.c !== undefined && norm(r.category) !== norm(e.c)) { E.push(line + ": category was changed"); }
      RULES[kind](r, e, spec).forEach(function (m) { E.push(line + ": " + m); });
    });
    var missing = K.rows.filter(function (e) { return !seen[e.k]; }).map(function (e) { return e.k; });
    if (missing.length) { E.push(missing.length + " assigned row(s) missing, e.g. " + missing.slice(0, 5).join(", ")); }
    if (recs.length !== K.rows.length) { E.push("the file has " + recs.length + " rows; expected " + K.rows.length); }
    return {errors: E, n: recs.length, expected: K.rows.length};
  }
  return {check: check, parseCSV: parseCSV};
})();
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", function () {
    var spec = JSON.parse(document.getElementById("fp-spec").textContent);
    Array.prototype.forEach.call(document.querySelectorAll("input.fp-file"), function (inp) {
      inp.addEventListener("change", function () {
        var f = inp.files[0], out = document.getElementById(inp.getAttribute("data-out"));
        if (!f) { return; }
        var rd = new FileReader();
        rd.onload = function () {
          var res = FPCHECK.check(spec, inp.getAttribute("data-kind"), String(rd.result));
          out.innerHTML = "";
          var h = document.createElement("p");
          if (!res.errors.length) {
            h.className = "ok";
            h.textContent = "✓ No problems found in " + f.name + " (" + res.n + " rows checked). You can submit it.";
            out.appendChild(h);
            return;
          }
          h.className = "bad";
          h.textContent = "✗ " + res.errors.length + " problem(s) in " + f.name + ". Fix them and check again:";
          out.appendChild(h);
          var ul = document.createElement("ul");
          res.errors.slice(0, 400).forEach(function (m) { var li = document.createElement("li"); li.textContent = m; ul.appendChild(li); });
          out.appendChild(ul);
        };
        rd.readAsText(f, "utf-8");
      });
    });
    var j = document.getElementById("fp-jump");
    if (j) {
      j.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var v = document.getElementById("fp-jump-id").value.trim(), el = document.getElementById("o-" + v);
        if (el) { el.scrollIntoView(); el.classList.add("flash"); } else { window.alert("Not found in this viewer: " + v); }
      });
    }
  });
}
"""


def _json_script(obj: Any, sid: str) -> str:
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return f"<script type='application/json' id='{sid}'>{s}</script>"


def _page(title: str, body: str, spec: Any = None) -> str:
    scripts = (_json_script(spec, "fp-spec") + f"<script id='fp-checker'>{CHECKER_JS}</script>") if spec is not None else ""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}{scripts}</body></html>\n")


def _c(tag: str, cls: str, text: str) -> str:
    """Content element: every annotator-visible TEXT taken from the data lives inside an `fp-c` element,
    so `checks.py` can verify the content and scan the remaining scaffolding separately."""
    return f"<{tag} class='{cls} fp-c'>{html.escape(text)}</{tag}>"


def _checker_box(kinds: list[tuple[str, str]]) -> str:
    rows = "".join(f"<p><label>{html.escape(label)}: <input type='file' accept='.csv,text/csv' class='fp-file' "
                   f"data-kind='{k}' data-out='res-{k}'></label></p><div id='res-{k}'></div>" for k, label in kinds)
    return ("<div class='box'><h3>Check my CSV file / 检查我的 CSV</h3><p class='muted'>Choose your saved CSV. The check runs "
            "only inside this browser; nothing is uploaded. The coordinator runs the official check after you submit.</p>"
            f"{rows}</div>")


def _bar(n: int) -> str:
    return ("<div class='bar'><a href='#top'>Top</a><a href='#index'>Index</a>"
            "<form id='fp-jump'><input id='fp-jump-id' placeholder='output_id' size='12'><button>Go</button></form>"
            f"<span class='muted'>{n} rows; card number = CSV row number minus 1</span></div>")


def _index(rows: list[dict[str, Any]], with_cat: bool) -> str:
    head = "<tr><th>#</th><th>output_id</th><th>case_ref</th>" + ("<th>category</th>" if with_cat else "") + "</tr>"
    body = "".join(f"<tr><td>{i}</td><td><a href='#o-{r['output_id']}'><code>{r['output_id']}</code></a></td>"
                   f"<td>{r['case_ref']}</td>" + (f"<td>{r['category']}</td>" if with_cat else "") + "</tr>"
                   for i, r in enumerate(rows, 1))
    return f"<details id='index'><summary>Index of all rows</summary><table class='idx'>{head}{body}</table></details>"


def _syn_hint(stage: str, cat: str, cl: dict[str, list[str]]) -> str:
    ordinal = cat in ORDINAL_CATEGORIES
    if stage == "pass1":
        if ordinal:
            return ("Fill: <code>expressed_level</code> (0/1/2) · <code>focal_addressed</code> (yes/no) · "
                    "<code>unsupported_claims</code> · <code>numeric_errors</code> · <code>confidence_p1</code> · <code>notes_p1</code>")
        return ("This category has no level: leave <code>expressed_level</code> and <code>focal_addressed</code> BLANK. Fill: "
                "<code>unsupported_claims</code> · <code>numeric_errors</code> · <code>confidence_p1</code> · <code>notes_p1</code>")
    f = ", ".join(cl.get("findings", [])) or "none"
    parts = [f"<code>findings_covered</code> (IDs: {html.escape(f)})"]
    if cat == "numerical_reporting":
        parts.append(f"<code>num_facts_correct</code> (IDs: {html.escape(', '.join(cl.get('facts', [])) or 'none')})")
    if cat == "negative_results":
        parts += ["<code>neg_findings_reported</code> (finding IDs)", "<code>neg_reframed_positive</code> (yes/no, required)"]
    parts += ["<code>confidence_p2</code>", "<code>notes_p2</code>"]
    tail = "" if cat in ("numerical_reporting", "negative_results") else \
        " Leave <code>num_facts_correct</code>, <code>neg_findings_reported</code>, <code>neg_reframed_positive</code> BLANK."
    return "Fill: " + " · ".join(parts) + ". Separate IDs with ';'. Leave blank if none." + tail


def synthetic_viewer(who: str, stage: str, rows: list[dict[str, Any]], pkg_md: dict[str, str],
                     checklists: dict[str, dict[str, list[str]]]) -> str:
    a = ANNOTATORS[who]
    fields = PASS1_FIELDS if stage == "pass1" else PASS2_FIELDS
    title = f"Annotator {who} ({a.name}) — synthetic {'Pass 1' if stage == 'pass1' else 'Pass 2'}"
    summary = ("Research package &amp; pass-1 rubric (focal proposition, level descriptors)" if stage == "pass1"
               else "Research package &amp; pass-2 checklists")
    cards = []
    for i, r in enumerate(rows, 1):
        sep = r["category"] not in ORDINAL_CATEGORIES
        cards.append(
            f"<section class='card' id='o-{r['output_id']}'><h2>{i}. <code>{r['output_id']}</code>"
            f"<span class='tag'>case {r['case_ref']}</span><span class='tag{' sep' if sep else ''}'>{r['category']}</span></h2>"
            + _c("div", "out", r["output_text"])
            + f"<div class='hint'>{_syn_hint(stage, r['category'], checklists.get(r['case_ref'], {}))}</div>"
            + f"<details><summary>{summary}</summary>{_c('pre', 'pkg', pkg_md[r['case_ref']])}</details>"
            + "<p class='muted'><a href='#top'>back to top</a></p></section>")
    intro = (f"<h1 id='top'>{html.escape(title)}</h1><p>Sheet: <code>{sheet_name(who, stage)}</code> · {len(rows)} rows · "
             f"Fields: {', '.join(f'<code>{f}</code>' for f in fields)}.</p><p class='muted'>Cards are in the same order as "
             "your CSV. Enter labels in the CSV, not here. Read your README and ANNOTATION_GUIDE.md first.</p>")
    spec = {"stage": stage, "ordinal": list(ORDINAL_CATEGORIES), "calibration": OVERALL_CALIBRATION, "support": SUPPORT_LABELS,
            "checklists": {ref: {"findings": sorted(v["findings"]), "facts": sorted(v["facts"])} for ref, v in checklists.items()}
            if stage == "pass2" else {},
            "kinds": {stage: {"columns": COLUMNS[stage],
                              "rows": [{"k": r["output_id"], "r": r["case_ref"], "c": r["category"], "t": r["output_text"]}
                                       for r in rows]}}}
    body = intro + _checker_box([(stage, f"{sheet_name(who, stage)}")]) + _index(rows, True) + _bar(len(rows)) + "".join(cards)
    return _page(title, body, spec)


def real_viewer(who: str, outs: list[dict[str, Any]], sents: list[dict[str, Any]], pkg_md: dict[str, str]) -> str:
    a = ANNOTATORS[who]
    title = f"Annotator {who} ({a.name}) — real-paper outputs"
    by_out: dict[str, list[dict[str, Any]]] = {}
    for s in sents:
        by_out.setdefault(s["output_id"], []).append(s)
    cards = []
    for i, r in enumerate(outs, 1):
        items = "".join(f"<li value='{s['sentence_idx']}'><b>[sentence_idx {s['sentence_idx']}]</b> "
                        + _c("span", "stext", s["sentence_text"]) + "</li>" for s in by_out[r["output_id"]])
        cards.append(
            f"<section class='card' id='o-{r['output_id']}'><h2>{i}. <code>{r['output_id']}</code>"
            f"<span class='tag'>paper {r['case_ref']}</span></h2>" + _c("div", "out", r["output_text"])
            + f"<div class='hint'>Paragraph sheet: <code>readability</code> (1–5) · <code>overall_calibration</code> · "
              f"<code>confidence</code> · <code>notes</code>. Sentence sheet: one <code>support_label</code> per numbered "
              f"sentence below.</div><ol class='sents'>{items}</ol>"
            + f"<details><summary>Research package</summary>{_c('pre', 'pkg', pkg_md[r['case_ref']])}</details>"
            + "<p class='muted'><a href='#top'>back to top</a></p></section>")
    intro = (f"<h1 id='top'>{html.escape(title)}</h1><p>Sheets: <code>{sheet_name(who, 'real_outputs')}</code> "
             f"({len(outs)} rows) and <code>{sheet_name(who, 'real_sentences')}</code> ({len(sents)} rows).</p>"
             "<p class='muted'>Judge only against the research package, not the original authors' conclusions. "
             f"Labels: {', '.join(f'<code>{x}</code>' for x in SUPPORT_LABELS)}; overall: "
             f"{', '.join(f'<code>{x}</code>' for x in OVERALL_CALIBRATION)}.</p>")
    spec = {"stage": "real", "ordinal": [], "calibration": OVERALL_CALIBRATION, "support": SUPPORT_LABELS, "checklists": {},
            "kinds": {"real_outputs": {"columns": COLUMNS["real_outputs"],
                                       "rows": [{"k": r["output_id"], "r": r["case_ref"], "t": r["output_text"]} for r in outs]},
                      "real_sentences": {"columns": COLUMNS["real_sentences"],
                                         "rows": [{"k": f"{s['output_id']}#{s['sentence_idx']}", "r": s["case_ref"],
                                                   "t": s["sentence_text"]} for s in sents]}}}
    body = (intro + _checker_box([("real_outputs", sheet_name(who, "real_outputs")),
                                  ("real_sentences", sheet_name(who, "real_sentences"))])
            + _index(outs, False) + _bar(len(outs)) + "".join(cards))
    return _page(title, body, spec)


def training_viewer(who: str, demo_md: str, dev_pkgs: list[tuple[str, str]]) -> str:
    title = f"DEV training material — Annotator {who} ({ANNOTATORS[who].name})"
    pk = "".join(f"<details><summary>DEV package {html.escape(cid)} (pass-1 rubric and pass-2 checklist)</summary>"
                 f"{_c('pre', 'pkg', md)}</details>" for cid, md in dev_pkgs)
    body = (f"<h1 id='top'>{html.escape(title)}</h1><p>These four examples come from the DEV split, never from the held-out "
            "TEST cases. The example labels are illustrations for training; you may disagree with them.</p>"
            f"<h2>Worked examples</h2>{_c('pre', 'pkg', demo_md)}<h2>The four DEV research packages</h2>{pk}")
    return _page(title, body)


# ----------------------------------------------------------------------------- DEV material
def dev_training_packages(paths: Paths) -> list[tuple[str, str]]:
    demo = paths.demo.read_text(encoding="utf-8")
    want = list(dict.fromkeys(DEMO_CASE.findall(demo)))
    recs = {}
    for line in paths.dev_cases.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = CaseRecord.model_validate_json(line)
            recs[rec.case_id] = rec
    rub = {json.loads(l)["case_id"]: json.loads(l) for l in paths.dev_rubric.read_text().splitlines() if l.strip()}
    out = []
    for cid in want:
        if cid not in recs:
            raise AssignmentError(f"demo references DEV case {cid} that is not in {paths.dev_cases}")
        p1 = package_markdown(recs[cid], cid, rub.get(cid), "pass1")
        p2 = package_markdown(recs[cid], cid, rub.get(cid), "pass2")
        out.append((cid, p1 + "\n" + p2[p2.index("## Pass-2 checklists"):]))
    return out


def blank_declaration() -> list[dict[str, str]]:
    return [{"question_id": q, "question_en": en, "question_zh": zh, "answer": "", "details": ""}
            for q, en, zh in DECLARATION_QUESTIONS]


def blank_timelog() -> list[dict[str, str]]:
    return [{"stage": s, "total_minutes": "", "n_sessions": "", "dates": "", "comments": ""} for s in TIMELOG_STAGES]


# ----------------------------------------------------------------------------- build
def build_person(paths: Paths, assignment: dict[str, Any], who: str, dest: Path, readme: str, checklist_md: str,
                 orig: dict[str, list[dict[str, str]]], dev_pkgs: list[tuple[str, str]]) -> None:
    a = ANNOTATORS[who]
    team = assignment["teams"][a.team]
    sheets = person_sheets(orig, assignment, who)
    refs, papers = team["synthetic_case_refs"], team["real_papers"]
    guide = paths.guide.read_bytes()
    checklist_name = f"SUBMISSION_CHECKLIST_{a.tag}.md"
    for stage in STAGES:
        d = dest / STAGE_DIRS[stage]
        d.mkdir(parents=True, exist_ok=True)
        (d / "00_START_HERE.md").write_text(start_here(assignment, who, stage), encoding="utf-8")
        (d / readme_name(who)).write_text(readme, encoding="utf-8")
        (d / "ANNOTATION_GUIDE.md").write_bytes(guide)
        (d / checklist_name).write_text(checklist_md, encoding="utf-8")
    # stage 0: training
    d = dest / STAGE_DIRS["training"]
    shutil.copyfile(paths.demo, d / "demo_example_NOT_TEST.md")
    (d / "dev_packages").mkdir(exist_ok=True)
    for cid, md in dev_pkgs:
        (d / "dev_packages" / f"{cid}.md").write_text(md, encoding="utf-8")
    (d / "dev_training_viewer.html").write_text(training_viewer(who, paths.demo.read_text(encoding="utf-8"), dev_pkgs),
                                                encoding="utf-8")
    write_csv(d / sheet_name(who, "declaration"), blank_declaration(),
              ["question_id", "question_en", "question_zh", "answer", "details"], bom=True)
    write_csv(d / sheet_name(who, "timelog"), blank_timelog(), ["stage", "total_minutes", "n_sessions", "dates", "comments"], bom=True)
    # stages 1 and 2: synthetic (packages copied byte-for-byte from the ORIGINAL pass folders)
    for stage, src in (("pass1", paths.pass1_packages), ("pass2", paths.pass2_packages)):
        d = dest / STAGE_DIRS[stage]
        (d / "packages").mkdir(exist_ok=True)
        pkg_md, cls = {}, {}
        for ref in refs:
            shutil.copyfile(src / f"{ref}.md", d / "packages" / f"{ref}.md")
            pkg_md[ref] = (src / f"{ref}.md").read_text(encoding="utf-8")
            c = checklists_from_pass2_md((paths.pass2_packages / f"{ref}.md").read_text(encoding="utf-8"))
            cls[ref] = {"findings": sorted(c["findings"]), "facts": sorted(c["facts"])}
        write_csv(d / sheet_name(who, stage), sheets[stage], COLUMNS[stage], bom=True)
        (d / viewer_name(who, stage)).write_text(
            synthetic_viewer(who, stage, sheets[stage], pkg_md, cls if stage == "pass2" else {}), encoding="utf-8")
    # stage 3: real papers
    d = dest / STAGE_DIRS["real"]
    (d / "packages").mkdir(exist_ok=True)
    pkg_md = {}
    for p in papers:
        shutil.copyfile(paths.real_packages / f"{p}.md", d / "packages" / f"{p}.md")
        pkg_md[p] = (paths.real_packages / f"{p}.md").read_text(encoding="utf-8")
    write_csv(d / sheet_name(who, "real_outputs"), sheets["real_outputs"], COLUMNS["real_outputs"], bom=True)
    write_csv(d / sheet_name(who, "real_sentences"), sheets["real_sentences"], COLUMNS["real_sentences"], bom=True)
    (d / viewer_name(who, "real")).write_text(real_viewer(who, sheets["real_outputs"], sheets["real_sentences"], pkg_md),
                                              encoding="utf-8")


def zip_dir(src: Path, zpath: Path, top: str) -> None:
    """Deterministic zip (sorted entries, fixed timestamps) so rebuilding gives identical bytes."""
    zpath.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(x for x in src.rglob("*") if x.is_file()):
            zi = zipfile.ZipInfo(f"{top}/{p.relative_to(src).as_posix()}", date_time=ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, p.read_bytes())


def _tree(d: Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): sha_file(p) for p in sorted(d.rglob("*")) if p.is_file()} if d.exists() else {}


def check_sources_unchanged(paths: Paths, assignment: dict[str, Any]) -> list[str]:
    errs = []
    for rel, h in assignment["source_sha256"].items():
        p = paths.root / rel
        if not p.exists():
            errs.append(f"original file {rel} is missing")
        elif sha_file(p) != h:
            errs.append(f"original file {rel} changed since the assignment was made")
    return errs


def build_all(paths: Paths, templates: Path | None = None, force: bool = False) -> dict[str, Any]:
    assignment = load_assignment(paths)
    errs = check_sources_unchanged(paths, assignment)
    if errs:
        raise BuildConflict("; ".join(errs))
    templates = templates or paths.fp_dir / "templates"
    orig = original_rows(paths)
    dev_pkgs = dev_training_packages(paths)
    staging = paths.fp_dir / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    for who in ANNOTATORS:
        readme, cl = render_instructions(templates, assignment, who)
        (staging / "instructions").mkdir(parents=True, exist_ok=True)
        (staging / "instructions" / readme_name(who)).write_text(readme, encoding="utf-8")
        (staging / "instructions" / f"SUBMISSION_CHECKLIST_{ANNOTATORS[who].tag}.md").write_text(cl, encoding="utf-8")
        pdir = staging / "packets" / ANNOTATORS[who].tag
        build_person(paths, assignment, who, pdir, readme, cl, orig, dev_pkgs)
        for stage in STAGES:
            zip_dir(pdir / STAGE_DIRS[stage], staging / "dist" / zip_name(who, stage),
                    f"{ANNOTATORS[who].tag}__{STAGE_DIRS[stage]}")
    live = {"instructions": paths.fp_dir / "instructions", "packets": paths.packets_dir, "dist": paths.dist_dir}
    changed = []
    for name, d in live.items():
        old, new = _tree(d), _tree(staging / name)
        if name == "dist":  # adjudication bundles are produced later by team_merge; leave them alone
            old = {k: v for k, v in old.items() if not k.startswith("adjudication_")}
        if old and old != new:
            changed += sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    if changed and not force:
        shutil.rmtree(staging)
        raise BuildConflict(f"{len(changed)} generated file(s) would change (e.g. {changed[:4]}); packets may already have "
                            f"been distributed. Re-run with --force only if nothing was released (old build is backed up).")
    if changed:
        bk = paths.fp_dir / "_backups" / f"build_{int(time.time())}"
        bk.mkdir(parents=True, exist_ok=True)
        for name, d in live.items():
            if d.exists():
                shutil.copytree(d, bk / name)
    for name, d in live.items():
        keep = {p.name: p.read_bytes() for p in d.glob("adjudication_*")} if name == "dist" and d.exists() else {}
        if d.exists():
            shutil.rmtree(d)
        shutil.move(str(staging / name), d)
        for fn, data in keep.items():
            (d / fn).write_bytes(data)
    shutil.rmtree(staging)
    return {"status": "rebuilt (previous build backed up)" if changed else "built (identical to any previous build)",
            "people": {who: {"dir": str(paths.person_dir(who).relative_to(paths.root)) if paths.root in paths.person_dir(who).parents
                             else str(paths.person_dir(who)),
                             "zips": [zip_name(who, s) for s in STAGES]} for who in ANNOTATORS}}
