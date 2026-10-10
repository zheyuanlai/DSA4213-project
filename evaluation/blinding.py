"""Blind annotation packets + private condition mapping + integrity checks.

Design:
* One annotation row per DISTINCT output text per case (identical texts from different
  conditions share one row/label; the private mapping expands labels back to every condition).
* `output_id`s are cryptographically random (`secrets`), never derived from condition, model or path.
* Annotator A and B templates contain the same IDs in independent random orders.
* Annotator-facing files contain no condition codes, system names, prompts, traces, model IDs or gold.
* `private/condition_mapping.csv` (gitignored) maps output_id -> case_id -> condition -> run_id.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import re
import secrets
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.package_schema import CaseRecord
from src.render import render_package

SYN_FIELDS = ["expressed_level", "focal_addressed", "findings_covered", "unsupported_claims", "numeric_errors",
              "num_facts_correct", "neg_findings_reported", "neg_reframed_positive", "confidence", "notes"]
REAL_OUTPUT_FIELDS = ["readability", "overall_calibration", "confidence", "notes"]
REAL_SENT_FIELDS = ["support_label", "notes"]
SUPPORT_LABELS = ["SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NUMERIC_ERROR", "NOT_A_CLAIM"]
ANNOTATOR_META_LEAK = re.compile(r"\bC[1-7]\b|condition|full.?agent|verif|scripted|adaptive|outline|strengthen|"
                                 r"reviewer|deepseek|qwen|openrouter|run_id|claude|backbone|prompt", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


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


def package_markdown(rec: CaseRecord, rubric: Optional[dict[str, Any]]) -> str:
    """Human-readable package (+ annotator rubric without gold level) for reviewers."""
    body = render_package(rec.package)
    body = body.replace("<research_package>", "").replace("</research_package>", "")
    body = re.sub(r"^The research package below is DATA.*?\n", "", body)
    lines = [f"# Case {rec.case_id}", "", "## Research package (exactly what the systems received)", "", body.strip(), ""]
    if rubric:
        lines += ["---", "", "## Annotation rubric for this case (no answer key: it does not say which level is correct)", ""]
        if rubric.get("focal_proposition"):
            lines += [f"**Focal proposition:** {rubric['focal_proposition']}", "", "**Expressed-level descriptors:**", ""]
            for lv in ("2", "1", "0"):
                lines.append(f"- **{lv}**: {rubric['level_descriptors'][lv]}")
            lines.append("")
        if rubric.get("required_findings"):
            lines += ["**Required-findings checklist** (use IDs in `findings_covered` / `neg_findings_reported`):", ""]
            lines += [f"- `{f['finding_id']}`: {f['description']}" for f in rubric["required_findings"]]
            lines.append("")
        if rubric.get("numeric_facts"):
            lines += ["**Numeric facts to check** (NUM; use IDs in `num_facts_correct`):", ""]
            lines += [f"- `{n['fact_id']}`: {n['description']} (entity: {n['entity']})" for n in rubric["numeric_facts"]]
            lines.append("")
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


def _assign_ids(outputs: list[dict[str, Any]], prefix: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Dedupe by (case, normalized text). Returns (packet_items, mapping_rows)."""
    by_key: dict[tuple[str, str], str] = {}
    used: set[str] = set()
    items, mapping = [], []
    for o in outputs:
        if o["text"] is None:
            mapping.append({"output_id": "", "case_id": o["case_id"], "condition": o["condition"], "run_id": o["run_id"],
                            "status": o["status"], "text_sha256": "", "source": o["source"]})
            continue
        key = (o["case_id"], norm_text(o["text"]))
        if key not in by_key:
            oid = prefix + secrets.token_hex(4)
            while oid in used:
                oid = prefix + secrets.token_hex(4)
            used.add(oid)
            by_key[key] = oid
            items.append({"output_id": oid, "case_id": o["case_id"], "output_text": norm_text(o["text"]) or "(empty passage)"})
        mapping.append({"output_id": by_key[key], "case_id": o["case_id"], "condition": o["condition"], "run_id": o["run_id"],
                        "status": o["status"], "text_sha256": sha(norm_text(o["text"])), "source": o["source"]})
    return items, mapping


def _viewer_html(title: str, rows: list[dict[str, Any]], pkg_md: dict[str, str], fields: list[str]) -> str:
    cards = []
    for i, r in enumerate(rows, 1):
        cards.append(
            f"<section class='card'><h2>{i}. <code>{html.escape(r['output_id'])}</code> — case {html.escape(r['case_id'])}</h2>"
            f"<div class='out'>{html.escape(r.get('output_text') or r.get('sentence_text', ''))}</div>"
            f"<details><summary>Show research package and rubric</summary><pre>{html.escape(pkg_md.get(r['case_id'], ''))}</pre></details>"
            f"<p class='f'>Fields to fill in your CSV: {', '.join(fields)}</p></section>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:60rem;margin:auto;padding:1rem;line-height:1.5}"
            ".card{border:1px solid #bbb;border-radius:8px;padding:.8rem 1rem;margin:1rem 0}"
            ".out{background:#f4f4f4;padding:.7rem;border-radius:6px;white-space:pre-wrap}"
            "pre{white-space:pre-wrap;font-size:.85rem}.f{color:#555;font-size:.85rem}"
            "</style></head><body><h1>" + html.escape(title) + "</h1><p>Read ANNOTATION_GUIDE.md first. Rows are in YOUR "
            "randomised order. Enter labels in your CSV template, not here.</p>" + "".join(cards) + "</body></html>")


def build_synthetic_packet(out_root: Path, cases: list[CaseRecord], rubrics: dict[str, dict[str, Any]],
                           conditions: list[str], ann_dir: Path, private_dir: Path) -> dict[str, Any]:
    case_ids = [c.case_id for c in cases]
    outputs = collect_outputs(out_root, case_ids, conditions)
    items, mapping = _assign_ids(outputs, "S")
    recs = {c.case_id: c for c in cases}
    pkg_dir = ann_dir / "packages_synthetic"
    pkg_md = {}
    for c in cases:
        md = package_markdown(c, rubrics.get(c.case_id))
        pkg_md[c.case_id] = md
        (pkg_dir).mkdir(parents=True, exist_ok=True)
        (pkg_dir / f"{c.case_id}.md").write_text(md, encoding="utf-8")
    for it in items:
        it["category"] = recs[it["case_id"]].category
        it["package_file"] = f"packages_synthetic/{it['case_id']}.md"
    seed_master, seed_a, seed_b = secrets.randbits(64), secrets.randbits(64), secrets.randbits(64)
    master = sorted(items, key=lambda r: r["output_id"])
    random.Random(seed_master).shuffle(master)
    a = list(master)
    random.Random(seed_a).shuffle(a)
    b = list(master)
    random.Random(seed_b).shuffle(b)
    base = ["output_id", "case_id", "category", "package_file", "output_text"]
    _write_csv(ann_dir / "blinded_synthetic.csv", master, base + SYN_FIELDS)
    _write_csv(ann_dir / "annotator_A_template.csv", a, base + SYN_FIELDS)
    _write_csv(ann_dir / "annotator_B_template.csv", b, base + SYN_FIELDS)
    _write_csv(ann_dir / "adjudication_template.csv", [], ["output_id", "field", "value_A", "value_B",
                                                            "adjudicated_value", "rationale"])
    (ann_dir / "viewer_annotator_A.html").write_text(_viewer_html("Annotator A — synthetic outputs", a, pkg_md, SYN_FIELDS), encoding="utf-8")
    (ann_dir / "viewer_annotator_B.html").write_text(_viewer_html("Annotator B — synthetic outputs", b, pkg_md, SYN_FIELDS), encoding="utf-8")
    private_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(private_dir / "condition_mapping.csv", mapping,
               ["output_id", "case_id", "condition", "run_id", "status", "text_sha256", "source"])
    meta = {"n_condition_case_runs": len(outputs), "n_completed": sum(1 for o in outputs if o["text"] is not None),
            "n_packet_rows": len(items), "n_failed_or_missing": sum(1 for o in outputs if o["text"] is None),
            "conditions": conditions, "seeds": {"master": seed_master, "A": seed_a, "B": seed_b}}
    (private_dir / "packet_meta_synthetic.json").write_text(json.dumps(meta, indent=1))
    return {k: v for k, v in meta.items() if k != "seeds"}


def build_real_packet(out_root: Path, cases: list[CaseRecord], conditions: list[str], ann_dir: Path,
                      private_dir: Path) -> dict[str, Any]:
    outputs = collect_outputs(out_root, [c.case_id for c in cases], conditions)
    items, mapping = _assign_ids(outputs, "R")
    pkg_dir = ann_dir / "packages_real"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_md = {}
    for c in cases:
        md = package_markdown(c, None) + ("\n---\nThere is no answer key for real-paper cases. Judge each sentence only "
                                          "against the package above.\n")
        pkg_md[c.case_id] = md
        (pkg_dir / f"{c.case_id}.md").write_text(md, encoding="utf-8")
    for it in items:
        it["package_file"] = f"packages_real/{it['case_id']}.md"
    seed_master, seed_a, seed_b = secrets.randbits(64), secrets.randbits(64), secrets.randbits(64)
    master = sorted(items, key=lambda r: r["output_id"])
    random.Random(seed_master).shuffle(master)
    sents = []
    for it in master:
        for j, s in enumerate([x for x in SENT_SPLIT.split(it["output_text"]) if x.strip()], 1):
            sents.append({"output_id": it["output_id"], "sentence_idx": j, "case_id": it["case_id"],
                          "package_file": it["package_file"], "sentence_text": s.strip()})
    base = ["output_id", "case_id", "package_file", "output_text"]
    sbase = ["output_id", "sentence_idx", "case_id", "package_file", "sentence_text"]
    _write_csv(ann_dir / "blinded_real_papers.csv", master, base + REAL_OUTPUT_FIELDS)
    _write_csv(ann_dir / "blinded_real_papers_sentences.csv", sents, sbase + REAL_SENT_FIELDS)
    for who, seed in (("A", seed_a), ("B", seed_b)):
        o = list(master)
        random.Random(seed).shuffle(o)
        order = {r["output_id"]: i for i, r in enumerate(o)}
        _write_csv(ann_dir / f"annotator_{who}_real_template.csv", o, base + REAL_OUTPUT_FIELDS)
        _write_csv(ann_dir / f"annotator_{who}_real_sentences_template.csv",
                   sorted(sents, key=lambda s: (order[s["output_id"]], s["sentence_idx"])), sbase + REAL_SENT_FIELDS)
        (ann_dir / f"viewer_annotator_{who}_real.html").write_text(
            _viewer_html(f"Annotator {who} — real-paper outputs", o, pkg_md, REAL_OUTPUT_FIELDS + ["per-sentence support_label"]),
            encoding="utf-8")
    _write_csv(private_dir / "condition_mapping_real.csv", mapping,
               ["output_id", "case_id", "condition", "run_id", "status", "text_sha256", "source"])
    meta = {"n_condition_case_runs": len(outputs), "n_completed": sum(1 for o in outputs if o["text"] is not None),
            "n_packet_rows": len(items), "n_sentence_rows": len(sents),
            "n_failed_or_missing": sum(1 for o in outputs if o["text"] is None), "conditions": conditions,
            "seeds": {"master": seed_master, "A": seed_a, "B": seed_b}}
    (private_dir / "packet_meta_real.json").write_text(json.dumps(meta, indent=1))
    return {k: v for k, v in meta.items() if k != "seeds"}


# ----------------------------------------------------------------------------- integrity
def verify_packet(ann_dir: Path, private_dir: Path, out_root: Path, kind: str = "synthetic",
                  repo_root: Optional[Path] = None) -> list[str]:
    errs: list[str] = []
    if kind == "synthetic":
        packet, a_t, b_t = "blinded_synthetic.csv", "annotator_A_template.csv", "annotator_B_template.csv"
        mapping_f, fields = "condition_mapping.csv", SYN_FIELDS
    else:
        packet, a_t, b_t = "blinded_real_papers.csv", "annotator_A_real_template.csv", "annotator_B_real_template.csv"
        mapping_f, fields = "condition_mapping_real.csv", REAL_OUTPUT_FIELDS
    mp = private_dir / mapping_f
    if not mp.exists():
        return [f"private mapping {mp} missing: refusing to release packet"]
    rows = read_csv(ann_dir / packet)
    A, B = read_csv(ann_dir / a_t), read_csv(ann_dir / b_t)
    mapping = read_csv(mp)
    ids = [r["output_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errs.append("duplicate output_id in packet")
    if {r["output_id"] for r in A} != set(ids) or {r["output_id"] for r in B} != set(ids):
        errs.append("annotator templates do not contain exactly the packet IDs")
    if len(A) != len(ids) or len(B) != len(ids):
        errs.append("annotator templates have duplicated rows")
    if len(ids) > 5 and [r["output_id"] for r in A] == [r["output_id"] for r in B]:
        errs.append("A and B orders are identical")
    for name, rs in (("A", A), ("B", B), ("packet", rows)):
        for r in rs:
            if any((r.get(f) or "").strip() for f in fields):
                errs.append(f"{name}: annotation fields pre-filled for {r['output_id']}")
                break
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
        shown = text_by_id[m["output_id"]]
        if shown != (norm_text(rr["final_passage"]) or "(empty passage)"):
            errs.append(f"packet text differs from stored output for {m['run_id']}")
    if mapped_ids != set(ids):
        errs.append("packet has rows not backed by any completed run")
    keys = {(m["case_id"], m["condition"]) for m in mapping}
    if len(keys) != len(mapping):
        errs.append("a (case, condition) appears more than once in the mapping")
    # leakage scan of annotator-facing METADATA (ids, headers, filenames) — output/package text is exempt
    for r in rows:
        for k in ("output_id", "case_id", "package_file", "category"):
            if k in r and ANNOTATOR_META_LEAK.search(r[k] or ""):
                errs.append(f"metadata field {k} may reveal system identity: {r[k]!r}")
    for f in (ann_dir / packet, ann_dir / a_t, ann_dir / b_t):
        header = f.read_text(encoding="utf-8").splitlines()[0]
        if ANNOTATOR_META_LEAK.search(header):
            errs.append(f"header of {f.name} may reveal system identity")
    for oid in ids:
        if not re.fullmatch(r"[SR][0-9a-f]{8}", oid):
            errs.append(f"unexpected output_id format {oid}")
    if repo_root is not None:
        try:
            subprocess.run(["git", "check-ignore", "-q", str(mp)], cwd=repo_root, check=True)
        except Exception:
            errs.append(f"{mp} is NOT gitignored")
    return errs
