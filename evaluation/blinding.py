"""Blind annotation packets + private condition mapping + integrity checks.

Design (revised after the independent audit, before any packet was released):
* One annotation row per DISTINCT output text per case. Identical texts from different
  conditions share one row/label; the private mapping expands labels back to every condition.
* `output_id`s are cryptographically random (`secrets`), never derived from condition, model or path.
* Cases are shown under opaque random aliases (`case_ref`, e.g. K07). The real case_id (which encodes
  category, matched pair and pair member) stays in the private mapping.
* TWO PASSES for the synthetic study:
    pass 1: expressed level / focal addressed / unsupported claims / numeric errors. The package
            files show the focal proposition and level descriptors but NO required-findings checklist,
            because checklist wording follows the gold decision.
    pass 2: coverage checklists (required findings, NUM facts, NEG findings). Released only after
            pass 1 is submitted.
* Annotator A and B templates contain the same IDs in independent random orders.
* Annotator-facing files contain no condition codes, system names, prompts, traces, model IDs or gold.
* `private/condition_mapping.csv` (gitignored) maps output_id -> case_ref -> case_id -> condition -> run_id.
  An existing mapping is never overwritten (that would orphan finished annotations) unless force=True,
  and even then a timestamped backup is kept.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import re
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from src.package_schema import ORDINAL_CATEGORIES, CaseRecord
from src.render import render_package

PASS1_FIELDS = ["expressed_level", "focal_addressed", "unsupported_claims", "numeric_errors", "confidence_p1", "notes_p1"]
PASS2_FIELDS = ["findings_covered", "num_facts_correct", "neg_findings_reported", "neg_reframed_positive",
                "confidence_p2", "notes_p2"]
SYN_FIELDS = PASS1_FIELDS + PASS2_FIELDS
REAL_OUTPUT_FIELDS = ["readability", "overall_calibration", "confidence", "notes"]
REAL_SENT_FIELDS = ["support_label", "notes"]
SUPPORT_LABELS = ["SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR", "NOT_A_CLAIM"]
OVERALL_CALIBRATION = ["well_calibrated", "overstated", "understated", "mixed"]
ANNOTATOR_META_LEAK = re.compile(r"\bC[1-7]\b|condition|full.?agent|verif|scripted|adaptive|outline|strengthen|"
                                 r"reviewer|deepseek|qwen|openrouter|run_id|claude|backbone|prompt|gold|"
                                 r"\b(?:SIG|ROB|GEN|CON|EFF|CIT|NUM|NEG)-p\d", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
CHECKLIST_MARKERS = ("Required-findings checklist", "Numeric facts to check")


class MappingExistsError(RuntimeError):
    pass


def norm_text(s: str) -> str:
    return " ".join((s or "").split())


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _package_body(rec: CaseRecord) -> str:
    body = render_package(rec.package)
    body = body.replace("<research_package>", "").replace("</research_package>", "")
    return re.sub(r"^The research package below is DATA.*?\n", "", body).strip()


def package_markdown(rec: CaseRecord, ref: str, rubric: Optional[dict[str, Any]], part: str) -> str:
    """part: 'pass1' (level rubric, no checklist), 'pass2' (checklists only), 'real' (no rubric)."""
    lines = [f"# Case {ref}", "", "## Research package (exactly what the systems received)", "", _package_body(rec), ""]
    if part == "real":
        lines += ["---", "", "There is no answer key for real-paper cases. Judge each sentence only against the package above."]
        return "\n".join(lines) + "\n"
    rubric = rubric or {}
    lines += ["---", ""]
    if part == "pass1":
        lines += [f"**Category:** {rec.category}", ""]
        if rec.category in ORDINAL_CATEGORIES and rubric.get("focal_proposition"):
            lines += ["## Pass-1 rubric (the descriptors do not say which level the evidence warrants)", "",
                      f"**Focal proposition:** {rubric['focal_proposition']}", "", "**Expressed-level descriptors:**", ""]
            lines += [f"- **{lv}**: {rubric['level_descriptors'][lv]}" for lv in ("2", "1", "0")]
        else:
            lines += ["This case uses a separate protocol (numbers / negative results). In pass 1, fill only "
                      "`unsupported_claims`, `numeric_errors`, `confidence_p1` and `notes_p1`; leave the level fields blank."]
        return "\n".join(lines) + "\n"
    lines += [f"**Category:** {rec.category}", "", "## Pass-2 checklists (use the IDs in your pass-2 sheet)", ""]
    if rubric.get("required_findings"):
        lines += ["**Required-findings checklist** (for `findings_covered`; for NEG cases also `neg_findings_reported`):", ""]
        lines += [f"- `{f['finding_id']}`: {f['description']}" for f in rubric["required_findings"]]
        lines.append("")
    if rubric.get("numeric_facts"):
        lines += ["**Numeric facts to check** (NUM; for `num_facts_correct`):", ""]
        lines += [f"- `{n['fact_id']}`: {n['description']} (entity: {n['entity']})" for n in rubric["numeric_facts"]]
    return "\n".join(lines) + "\n"


def collect_outputs(out_root: Path, case_ids: list[str], conditions: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in case_ids:
        for c in conditions:
            p = out_root / c / f"{cid}.json"
            if not p.exists():
                rows.append({"case_id": cid, "condition": c, "status": "missing", "run_id": "", "text": None, "source": ""})
                continue
            rr = json.loads(p.read_text())
            if rr.get("is_mock"):
                raise ValueError(f"refusing to build an annotation packet from MOCK output {p}")
            text = rr.get("final_passage") if rr.get("status") == "completed" else None
            rows.append({"case_id": cid, "condition": c, "status": rr.get("status"), "run_id": rr.get("run_id"),
                         "text": text, "source": str(p)})
    return rows


def _case_refs(case_ids: list[str], prefix: str) -> dict[str, str]:
    order = list(case_ids)
    random.Random(secrets.randbits(64)).shuffle(order)
    return {cid: f"{prefix}{i + 1:02d}" for i, cid in enumerate(order)}


def _assign_ids(outputs: list[dict[str, Any]], prefix: str, refs: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Dedupe by (case, normalized text). Returns (packet_items, mapping_rows)."""
    by_key: dict[tuple[str, str], str] = {}
    used: set[str] = set()
    items, mapping = [], []
    for o in outputs:
        base = {"case_id": o["case_id"], "case_ref": refs[o["case_id"]], "condition": o["condition"],
                "run_id": o["run_id"], "status": o["status"], "source": o["source"]}
        if o["text"] is None:
            mapping.append({**base, "output_id": "", "text_sha256": ""})
            continue
        key = (o["case_id"], norm_text(o["text"]))
        if key not in by_key:
            oid = prefix + secrets.token_hex(4)
            while oid in used:
                oid = prefix + secrets.token_hex(4)
            used.add(oid)
            by_key[key] = oid
            items.append({"output_id": oid, "case_id": o["case_id"], "case_ref": refs[o["case_id"]],
                          "output_text": norm_text(o["text"]) or "(empty passage)"})
        mapping.append({**base, "output_id": by_key[key], "text_sha256": sha(norm_text(o["text"]))})
    return items, mapping


def _viewer_html(title: str, rows: list[dict[str, Any]], pkg_md: dict[str, str], fields: list[str]) -> str:
    cards = []
    for i, r in enumerate(rows, 1):
        cards.append(
            f"<section class='card'><h2>{i}. <code>{html.escape(r['output_id'])}</code> — case {html.escape(r['case_ref'])}</h2>"
            f"<div class='out'>{html.escape(r.get('output_text') or r.get('sentence_text', ''))}</div>"
            f"<details><summary>Show research package and rubric</summary><pre>{html.escape(pkg_md.get(r['case_ref'], ''))}</pre></details>"
            f"<p class='f'>Fields to fill in your CSV: {', '.join(fields)}</p></section>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:60rem;margin:auto;padding:1rem;line-height:1.5}"
            ".card{border:1px solid #bbb;border-radius:8px;padding:.8rem 1rem;margin:1rem 0}"
            ".out{background:#f4f4f4;padding:.7rem;border-radius:6px;white-space:pre-wrap}"
            "pre{white-space:pre-wrap;font-size:.85rem}.f{color:#555;font-size:.85rem}"
            "</style></head><body><h1>" + html.escape(title) + "</h1><p>Read ANNOTATION_GUIDE.md first. Rows are in YOUR "
            "randomised order. Enter labels in your CSV sheet, not here.</p>" + "".join(cards) + "</body></html>")


def _protect_mapping(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise MappingExistsError(f"{path} already exists; rebuilding would assign new random IDs and orphan any "
                                     f"annotations made against the current packet. Pass force=True only if no "
                                     f"annotation has started (a timestamped backup is kept).")
        shutil.copy2(path, path.with_name(path.stem + f".backup_{int(time.time())}" + path.suffix))


def _shuffled(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    out = sorted(items, key=lambda r: r["output_id"])
    random.Random(seed).shuffle(out)
    return out


def build_synthetic_packet(out_root: Path, cases: list[CaseRecord], rubrics: dict[str, dict[str, Any]],
                           conditions: list[str], ann_dir: Path, private_dir: Path, force: bool = False) -> dict[str, Any]:
    private_dir.mkdir(parents=True, exist_ok=True)
    _protect_mapping(private_dir / "condition_mapping.csv", force)
    case_ids = [c.case_id for c in cases]
    refs = _case_refs(case_ids, "K")
    outputs = collect_outputs(out_root, case_ids, conditions)
    items, mapping = _assign_ids(outputs, "S", refs)
    recs = {c.case_id: c for c in cases}
    pkg = {"pass1": {}, "pass2": {}}
    for part in ("pass1", "pass2"):
        d = ann_dir / part / "packages"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
        for c in cases:
            md = package_markdown(c, refs[c.case_id], rubrics.get(c.case_id), part)
            pkg[part][refs[c.case_id]] = md
            (d / f"{refs[c.case_id]}.md").write_text(md, encoding="utf-8")
    for it in items:
        it["category"] = recs[it["case_id"]].category
    seeds = {k: secrets.randbits(64) for k in ("master", "A1", "B1", "A2", "B2")}
    master = _shuffled(items, seeds["master"])
    base = ["output_id", "case_ref", "category", "package_file", "output_text"]
    _write_csv(ann_dir / "blinded_synthetic.csv", [dict(r, package_file=f"pass1/packages/{r['case_ref']}.md") for r in master],
               base + SYN_FIELDS)
    for part, fields in (("pass1", PASS1_FIELDS), ("pass2", PASS2_FIELDS)):
        for who in ("A", "B"):
            rows = [dict(r, package_file=f"packages/{r['case_ref']}.md") for r in _shuffled(items, seeds[f"{who}{part[-1]}"])]
            _write_csv(ann_dir / part / f"annotator_{who}_{part}.csv", rows, base + fields)
            (ann_dir / part / f"viewer_annotator_{who}_{part}.html").write_text(
                _viewer_html(f"Annotator {who} — synthetic outputs — {part}", rows, pkg[part], fields), encoding="utf-8")
    _write_csv(ann_dir / "adjudication_template.csv", [], ["output_id", "field", "value_A", "value_B",
                                                            "adjudicated_value", "rationale"])
    _write_csv(private_dir / "condition_mapping.csv", mapping,
               ["output_id", "case_ref", "case_id", "condition", "run_id", "status", "text_sha256", "source"])
    _write_csv(private_dir / "case_alias_map.csv", [{"case_ref": v, "case_id": k} for k, v in sorted(refs.items(), key=lambda x: x[1])],
               ["case_ref", "case_id"])
    meta = {"n_condition_case_runs": len(outputs), "n_completed": sum(1 for o in outputs if o["text"] is not None),
            "n_packet_rows": len(items), "n_failed_or_missing": sum(1 for o in outputs if o["text"] is None),
            "n_cases": len(cases), "conditions": conditions, "seeds": seeds}
    (private_dir / "packet_meta_synthetic.json").write_text(json.dumps(meta, indent=1))
    return {k: v for k, v in meta.items() if k != "seeds"}


def build_real_packet(out_root: Path, cases: list[CaseRecord], conditions: list[str], ann_dir: Path,
                      private_dir: Path, force: bool = False) -> dict[str, Any]:
    private_dir.mkdir(parents=True, exist_ok=True)
    _protect_mapping(private_dir / "condition_mapping_real.csv", force)
    refs = {c.case_id: c.case_id for c in cases}  # RP-xx ids carry no gold/condition information
    outputs = collect_outputs(out_root, [c.case_id for c in cases], conditions)
    items, mapping = _assign_ids(outputs, "R", refs)
    d = ann_dir / "real" / "packages"
    d.mkdir(parents=True, exist_ok=True)
    pkg_md = {}
    for c in cases:
        md = package_markdown(c, c.case_id, None, "real")
        pkg_md[c.case_id] = md
        (d / f"{c.case_id}.md").write_text(md, encoding="utf-8")
    seeds = {k: secrets.randbits(64) for k in ("master", "A", "B")}
    master = _shuffled(items, seeds["master"])
    for it in master:
        it["package_file"] = f"packages/{it['case_ref']}.md"
    sents = []
    for it in master:
        for j, s in enumerate([x for x in SENT_SPLIT.split(it["output_text"]) if x.strip()], 1):
            sents.append({"output_id": it["output_id"], "sentence_idx": j, "case_ref": it["case_ref"],
                          "package_file": it["package_file"], "sentence_text": s.strip()})
    base = ["output_id", "case_ref", "package_file", "output_text"]
    sbase = ["output_id", "sentence_idx", "case_ref", "package_file", "sentence_text"]
    _write_csv(ann_dir / "real" / "blinded_real_papers.csv", master, base + REAL_OUTPUT_FIELDS)
    _write_csv(ann_dir / "real" / "blinded_real_papers_sentences.csv", sents, sbase + REAL_SENT_FIELDS)
    for who in ("A", "B"):
        o = _shuffled(master, seeds[who])
        order = {r["output_id"]: i for i, r in enumerate(o)}
        _write_csv(ann_dir / "real" / f"annotator_{who}_real.csv", o, base + REAL_OUTPUT_FIELDS)
        _write_csv(ann_dir / "real" / f"annotator_{who}_real_sentences.csv",
                   sorted(sents, key=lambda s: (order[s["output_id"]], s["sentence_idx"])), sbase + REAL_SENT_FIELDS)
        (ann_dir / "real" / f"viewer_annotator_{who}_real.html").write_text(
            _viewer_html(f"Annotator {who} — real-paper outputs", o, pkg_md, REAL_OUTPUT_FIELDS + ["per-sentence support_label"]),
            encoding="utf-8")
    _write_csv(private_dir / "condition_mapping_real.csv", mapping,
               ["output_id", "case_ref", "case_id", "condition", "run_id", "status", "text_sha256", "source"])
    meta = {"n_condition_case_runs": len(outputs), "n_completed": sum(1 for o in outputs if o["text"] is not None),
            "n_packet_rows": len(items), "n_sentence_rows": len(sents),
            "n_failed_or_missing": sum(1 for o in outputs if o["text"] is None), "conditions": conditions, "seeds": seeds}
    (private_dir / "packet_meta_real.json").write_text(json.dumps(meta, indent=1))
    return {k: v for k, v in meta.items() if k != "seeds"}


# ----------------------------------------------------------------------------- integrity
def verify_packet(ann_dir: Path, private_dir: Path, out_root: Path, kind: str = "synthetic",
                  repo_root: Optional[Path] = None) -> list[str]:
    errs: list[str] = []
    if kind == "synthetic":
        packet = ann_dir / "blinded_synthetic.csv"
        sheets = {(p, w): ann_dir / p / f"annotator_{w}_{p}.csv" for p in ("pass1", "pass2") for w in ("A", "B")}
        sheet_fields = {"pass1": PASS1_FIELDS, "pass2": PASS2_FIELDS}
        mp = private_dir / "condition_mapping.csv"
    else:
        packet = ann_dir / "real" / "blinded_real_papers.csv"
        sheets = {("real", w): ann_dir / "real" / f"annotator_{w}_real.csv" for w in ("A", "B")}
        sheet_fields = {"real": REAL_OUTPUT_FIELDS}
        mp = private_dir / "condition_mapping_real.csv"
    if not mp.exists():
        return [f"private mapping {mp} missing: refusing to release packet"]
    rows = read_csv(packet)
    mapping = read_csv(mp)
    ids = [r["output_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errs.append("duplicate output_id in packet")
    loaded = {k: read_csv(v) for k, v in sheets.items()}
    for (part, who), rs in loaded.items():
        if {r["output_id"] for r in rs} != set(ids) or len(rs) != len(ids):
            errs.append(f"{part}/{who}: sheet does not contain exactly the packet IDs once each")
        if any((r.get(f) or "").strip() for r in rs for f in sheet_fields[part]):
            errs.append(f"{part}/{who}: annotation fields pre-filled")
    for part in sheet_fields:
        a, b = loaded[(part, "A")], loaded[(part, "B")]
        if len(ids) > 5 and [r["output_id"] for r in a] == [r["output_id"] for r in b]:
            errs.append(f"{part}: A and B orders are identical")
    if any((r.get(f) or "").strip() for r in rows for f in (SYN_FIELDS if kind == "synthetic" else REAL_OUTPUT_FIELDS)):
        errs.append("master packet has pre-filled annotation fields")
    # pass-1 packages must not carry the (gold-derived) checklists
    if kind == "synthetic":
        for p in (ann_dir / "pass1" / "packages").glob("*.md"):
            t = p.read_text(encoding="utf-8")
            if any(m in t for m in CHECKLIST_MARKERS):
                errs.append(f"pass-1 package {p.name} contains a pass-2 checklist")
        refs = {r["case_ref"] for r in rows}
        for part in ("pass1", "pass2"):
            for ref in refs:
                if not (ann_dir / part / "packages" / f"{ref}.md").exists():
                    errs.append(f"{part}: missing package file for {ref}")
    # every completed run maps to exactly one packet row whose text matches the stored output
    text_by_id = {r["output_id"]: r["output_text"] for r in rows}
    mapped_ids = set()
    for m in mapping:
        if m["status"] != "completed":
            if m["output_id"]:
                errs.append(f"non-completed run {m['run_id']} has an output_id")
            continue
        if m["output_id"] not in text_by_id:
            errs.append(f"run {m['run_id']} maps to unknown output_id")
            continue
        mapped_ids.add(m["output_id"])
        rr = json.loads(Path(m["source"]).read_text())
        if sha(norm_text(rr["final_passage"])) != m["text_sha256"]:
            errs.append(f"text hash mismatch for {m['run_id']}")
        if text_by_id[m["output_id"]] != (norm_text(rr["final_passage"]) or "(empty passage)"):
            errs.append(f"packet text differs from stored output for {m['run_id']}")
    if mapped_ids != set(ids):
        errs.append("packet has rows not backed by any completed run")
    if len({(m["case_id"], m["condition"]) for m in mapping}) != len(mapping):
        errs.append("a (case, condition) appears more than once in the mapping")
    # leakage scan of annotator-facing METADATA (ids, refs, headers, file names); output/package text exempt
    for r in rows:
        for k in ("output_id", "case_ref", "package_file"):
            if ANNOTATOR_META_LEAK.search(r.get(k) or ""):
                errs.append(f"metadata field {k} may reveal identity/gold: {r.get(k)!r}")
    for f in [packet] + list(sheets.values()):
        if ANNOTATOR_META_LEAK.search(f.read_text(encoding="utf-8").splitlines()[0]):
            errs.append(f"header of {f.name} may reveal system identity")
    for oid in ids:
        if not re.fullmatch(r"[SR][0-9a-f]{8}", oid):
            errs.append(f"unexpected output_id format {oid}")
    if repo_root is not None:
        for p in (mp, private_dir / "case_alias_map.csv"):
            if p.exists():
                r = subprocess.run(["git", "check-ignore", "-q", str(p)], cwd=repo_root)
                if r.returncode != 0:
                    errs.append(f"{p} is NOT gitignored")
    return errs
