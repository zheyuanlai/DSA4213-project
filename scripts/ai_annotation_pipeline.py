"""Validate, reconcile, and score the explicitly AI-generated annotation track.

This pipeline deliberately does not write to the human-annotation submission folders.  It
reuses the frozen packets, rubrics, agreement functions, and scorers, but keeps provenance in
``annotation/ai`` and ``results/ai_*``.  System identities and TEST gold are read only after
independent labels and adjudications have been fixed.

Typical use::

    python scripts/ai_annotation_pipeline.py validate
    python scripts/ai_annotation_pipeline.py agreement
    # fill annotation/ai/adjudication/team_{AB,CD}_{synthetic,real}.csv
    python scripts/ai_annotation_pipeline.py combine
    python scripts/ai_annotation_pipeline.py score
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.blinding import OVERALL_CALIBRATION, SUPPORT_LABELS
from evaluation.merge_annotations import (
    SCORED_FIELDS,
    agreement as synthetic_agreement,
    consensus as synthetic_consensus,
    disagreements as synthetic_disagreements,
    validate as validate_synthetic,
)
from evaluation.score_human import load_jsonl, score as score_synthetic
from evaluation.score_real_papers import (
    agreement as real_agreement,
    score as score_real,
    validate as validate_real,
)


ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / "annotation" / "ai"
RESULTS_AGREEMENT = ROOT / "results" / "ai_agreement"
RESULTS_SCORED = ROOT / "results" / "ai_scored"

ROSTER = {"A": "A_Zheyuan", "B": "B_Yuxin", "C": "C_Jiajun", "D": "D_Xinkai"}
TEAMS = {"AB": ("A", "B"), "CD": ("C", "D")}
KINDS = {
    "pass1": ("1_pass1", "pass1_labels.csv", "pass1"),
    "pass2": ("2_pass2", "pass2_labels.csv", "pass2"),
    "real_outputs": ("3_real", "real_outputs_labels.csv", "real_outputs"),
    "real_sentences": ("3_real", "real_sentences_labels.csv", "real_sentences"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_adjudication_preserving(path: Path, rows: list[dict[str, Any]], fields: list[str],
                                  key_fields: tuple[str, ...]) -> None:
    """Rewrite a disagreement sheet without erasing completed decisions."""
    prior = {}
    if path.exists():
        prior = {tuple(r.get(k, "") for k in key_fields): r for r in read_csv(path)}
    for row in rows:
        old = prior.get(tuple(row.get(k, "") for k in key_fields))
        if old and all(old.get(k, "") == row.get(k, "") for k in fields if k.startswith("value_")):
            row["adjudicated_value"] = old.get("adjudicated_value", "")
            row["rationale"] = old.get("rationale", "")
    write_csv(path, rows, fields)


def _source_path(who: str, kind: str) -> Path:
    stage, _, suffix = KINDS[kind]
    stem = ROSTER[who]
    return ROOT / "annotation" / "four_person" / "packets" / stem / stage / f"{stem}_{suffix}.csv"


def _label_path(who: str, kind: str) -> Path:
    return AI_DIR / "independent" / who / KINDS[kind][1]


def _key(kind: str, row: dict[str, str]) -> tuple[str, ...]:
    return (row["output_id"], row["sentence_idx"]) if kind == "real_sentences" else (row["output_id"],)


def _load_and_check(who: str, kind: str) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    src_path, lab_path = _source_path(who, kind), _label_path(who, kind)
    errs: list[str] = []
    if not lab_path.exists():
        return read_csv(src_path), [], [f"{who}/{kind}: missing {lab_path.relative_to(ROOT)}"]
    src, lab = read_csv(src_path), read_csv(lab_path)
    src_keys, lab_keys = [_key(kind, r) for r in src], [_key(kind, r) for r in lab]
    if len(set(lab_keys)) != len(lab_keys):
        errs.append(f"{who}/{kind}: duplicate item keys")
    missing, extra = set(src_keys) - set(lab_keys), set(lab_keys) - set(src_keys)
    if missing:
        errs.append(f"{who}/{kind}: {len(missing)} assigned item(s) missing")
    if extra:
        errs.append(f"{who}/{kind}: {len(extra)} unassigned item(s) present")
    src_by, lab_by = {_key(kind, r): r for r in src}, {_key(kind, r): r for r in lab}
    for k in set(src_by) & set(lab_by):
        if lab_by[k].get("case_ref") != src_by[k].get("case_ref"):
            errs.append(f"{who}/{kind}/{k}: case_ref changed")
    return src, lab, errs


def load_annotator(who: str) -> tuple[dict[str, Any], list[str]]:
    loaded: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]] = {}
    errs: list[str] = []
    for kind in KINDS:
        src, lab, e = _load_and_check(who, kind)
        loaded[kind] = (src, lab)
        errs.extend(e)
    if errs:
        return {}, errs

    p1s, p1l = loaded["pass1"]
    p2s, p2l = loaded["pass2"]
    p1 = {r["output_id"]: r for r in p1l}
    p2 = {r["output_id"]: r for r in p2l}
    syn = []
    for src in p1s:
        oid = src["output_id"]
        row = dict(src)
        row.update(p1[oid])
        row.update(p2[oid])
        syn.append(row)

    ros, rol = loaded["real_outputs"]
    rss, rsl = loaded["real_sentences"]
    ro_lab = {r["output_id"]: r for r in rol}
    rs_lab = {(r["output_id"], r["sentence_idx"]): r for r in rsl}
    real_out = [dict(r, **ro_lab[r["output_id"]]) for r in ros]
    real_sent = [dict(r, **rs_lab[(r["output_id"], r["sentence_idx"])]) for r in rss]
    return {"syn": syn, "real_outputs": real_out, "real_sentences": real_sent}, []


def context() -> dict[str, Any]:
    alias = {r["case_ref"]: r["case_id"] for r in read_csv(ROOT / "private" / "case_alias_map.csv")}
    rubric = load_jsonl(ROOT / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl")
    return {"alias": alias, "rubric": rubric}


def validate_all(write_report: bool = True) -> tuple[dict[str, dict[str, Any]], list[str]]:
    ctx = context()
    people: dict[str, dict[str, Any]] = {}
    errs: list[str] = []
    for who in ROSTER:
        data, load_errs = load_annotator(who)
        errs.extend(load_errs)
        if load_errs:
            continue
        people[who] = data
        packet_ids = {r["output_id"] for r in data["syn"]}
        cat = {r["output_id"]: r["category"] for r in data["syn"]}
        case = {r["output_id"]: ctx["alias"][r["case_ref"]] for r in data["syn"]}
        errs.extend(validate_synthetic(data["syn"], packet_ids, ctx["rubric"], cat, case, f"AI-{who}"))
        errs.extend(validate_real(data["real_outputs"], data["real_sentences"],
                                  read_csv(_source_path(who, "real_outputs")),
                                  read_csv(_source_path(who, "real_sentences")), f"AI-{who}"))
    if write_report:
        report = AI_DIR / "validation_report.txt"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("\n".join(errs) + ("\n" if errs else "OK\n"), encoding="utf-8")
    return people, errs


def _real_disagreements(left: dict[str, Any], right: dict[str, Any], x: str, y: str) -> list[dict[str, str]]:
    lo = {r["output_id"]: r for r in left["real_outputs"]}
    ro = {r["output_id"]: r for r in right["real_outputs"]}
    ls = {f"{r['output_id']}#{r['sentence_idx']}": r for r in left["real_sentences"]}
    rs = {f"{r['output_id']}#{r['sentence_idx']}": r for r in right["real_sentences"]}
    rows: list[dict[str, str]] = []
    for oid in sorted(lo):
        for field in ("readability", "overall_calibration"):
            if lo[oid][field].strip() != ro[oid][field].strip():
                rows.append({"item": oid, "case_ref": lo[oid]["case_ref"], "field": field,
                             f"value_{x}": lo[oid][field].strip(), f"value_{y}": ro[oid][field].strip(),
                             "sentence_text": "", "adjudicated_value": "", "rationale": ""})
    for item in sorted(ls, key=lambda z: (z.split("#")[0], int(z.split("#")[1]))):
        if ls[item]["support_label"].strip() != rs[item]["support_label"].strip():
            rows.append({"item": item, "case_ref": ls[item]["case_ref"], "field": "support_label",
                         f"value_{x}": ls[item]["support_label"].strip(), f"value_{y}": rs[item]["support_label"].strip(),
                         "sentence_text": ls[item]["sentence_text"], "adjudicated_value": "", "rationale": ""})
    return rows


def agreement_stage() -> int:
    people, errs = validate_all()
    if errs:
        print(f"{len(errs)} validation error(s); see annotation/ai/validation_report.txt")
        return 1
    ctx = context()
    RESULTS_AGREEMENT.mkdir(parents=True, exist_ok=True)
    adj_dir = AI_DIR / "adjudication"
    summary: dict[str, Any] = {"provenance": "AI annotators; not human annotation", "teams": {}}
    for team, (x, y) in TEAMS.items():
        A, B = people[x], people[y]
        sa, sb = {r["output_id"]: r for r in A["syn"]}, {r["output_id"]: r for r in B["syn"]}
        ids = set(sa)
        cat = {i: sa[i]["category"] for i in ids}
        case = {i: ctx["alias"][sa[i]["case_ref"]] for i in ids}
        syn_ag = synthetic_agreement(sa, sb, ctx["rubric"], cat, case)
        ao, bo = ({r["output_id"]: r for r in z["real_outputs"]} for z in (A, B))
        ass, bss = ({f"{r['output_id']}#{r['sentence_idx']}": r for r in z["real_sentences"]} for z in (A, B))
        real_ag = real_agreement(ao, bo, ass, bss)
        syn_dis = []
        for d in synthetic_disagreements(sa, sb):
            syn_dis.append({"output_id": d["output_id"], "case_ref": sa[d["output_id"]]["case_ref"],
                            "category": sa[d["output_id"]]["category"], "field": d["field"],
                            f"value_{x}": d["value_A"], f"value_{y}": d["value_B"],
                            "adjudicated_value": "", "rationale": ""})
        real_dis = _real_disagreements(A, B, x, y)
        write_adjudication_preserving(
            adj_dir / f"team_{team}_synthetic.csv", syn_dis,
            ["output_id", "case_ref", "category", "field", f"value_{x}", f"value_{y}",
             "adjudicated_value", "rationale"], ("output_id", "field"))
        write_adjudication_preserving(
            adj_dir / f"team_{team}_real.csv", real_dis,
            ["item", "case_ref", "field", "sentence_text", f"value_{x}", f"value_{y}",
             "adjudicated_value", "rationale"], ("item", "field"))
        summary["teams"][team] = {"members": [x, y], "synthetic": syn_ag, "real": real_ag,
                                  "n_synthetic_disagreements": len(syn_dis), "n_real_disagreements": len(real_dis)}
    (RESULTS_AGREEMENT / "agreement.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({t: {"synthetic_disagreements": v["n_synthetic_disagreements"],
                          "real_disagreements": v["n_real_disagreements"]}
                      for t, v in summary["teams"].items()}, indent=2))
    return 0


def _checked_adjudications(team: str, kind: str, expected: list[dict[str, str]], x: str, y: str) -> list[dict[str, str]]:
    path = AI_DIR / "adjudication" / f"team_{team}_{kind}.csv"
    rows = read_csv(path)
    key_fields = ("output_id", "field") if kind == "synthetic" else ("item", "field")
    keys = lambda rr: tuple(rr[k] for k in key_fields)  # noqa: E731
    if {keys(r) for r in rows} != {keys(r) for r in expected} or len(rows) != len(expected):
        raise ValueError(f"{path}: adjudication row set changed")
    exp = {keys(r): r for r in expected}
    for r in rows:
        e = exp[keys(r)]
        for c in (f"value_{x}", f"value_{y}"):
            if r.get(c, "") != e.get(c, ""):
                raise ValueError(f"{path}: source value changed for {keys(r)}/{c}")
        if not r.get("adjudicated_value", "").strip() or not r.get("rationale", "").strip():
            raise ValueError(f"{path}: unresolved row {keys(r)}")
    return rows


def combine_stage() -> int:
    people, errs = validate_all()
    if errs:
        print(f"{len(errs)} validation error(s); see annotation/ai/validation_report.txt")
        return 1
    ctx = context()
    all_syn: list[dict[str, str]] = []
    all_ro: list[dict[str, str]] = []
    all_rs: list[dict[str, str]] = []
    for team, (x, y) in TEAMS.items():
        A, B = people[x], people[y]
        sa, sb = {r["output_id"]: r for r in A["syn"]}, {r["output_id"]: r for r in B["syn"]}
        expected_syn = []
        for d in synthetic_disagreements(sa, sb):
            expected_syn.append({"output_id": d["output_id"], "field": d["field"],
                                 f"value_{x}": d["value_A"], f"value_{y}": d["value_B"]})
        syn_adj = _checked_adjudications(team, "synthetic", expected_syn, x, y)
        generic_adj = [{"output_id": r["output_id"], "field": r["field"],
                        "adjudicated_value": r["adjudicated_value"]} for r in syn_adj]
        rows, syn_errs = synthetic_consensus(sa, sb, generic_adj)
        if syn_errs:
            raise ValueError("; ".join(syn_errs))
        for r in rows:
            r["case_id"] = ctx["alias"][sa[r["output_id"]]["case_ref"]]
            r["category"] = sa[r["output_id"]]["category"]
        all_syn.extend(rows)

        expected_real = _real_disagreements(A, B, x, y)
        real_adj = _checked_adjudications(team, "real", expected_real, x, y)
        decisions = {(r["item"], r["field"]): r["adjudicated_value"].strip() for r in real_adj}
        ao, bo = ({r["output_id"]: r for r in z["real_outputs"]} for z in (A, B))
        ass, bss = ({f"{r['output_id']}#{r['sentence_idx']}": r for r in z["real_sentences"]} for z in (A, B))
        for oid in sorted(ao):
            vals = {}
            for field in ("readability", "overall_calibration"):
                vals[field] = ao[oid][field] if ao[oid][field] == bo[oid][field] else decisions[(oid, field)]
            if vals["readability"] not in {"1", "2", "3", "4", "5"} or vals["overall_calibration"] not in OVERALL_CALIBRATION:
                raise ValueError(f"invalid real-output consensus for {oid}")
            all_ro.append({"output_id": oid, "case_ref": ao[oid]["case_ref"], **vals})
        for item in sorted(ass, key=lambda z: (z.split("#")[0], int(z.split("#")[1]))):
            val = ass[item]["support_label"] if ass[item]["support_label"] == bss[item]["support_label"] \
                else decisions[(item, "support_label")]
            if val not in SUPPORT_LABELS:
                raise ValueError(f"invalid sentence consensus for {item}: {val}")
            oid, idx = item.split("#")
            all_rs.append({"output_id": oid, "sentence_idx": idx, "support_label": val})

    if len({r["output_id"] for r in all_syn}) != 122 or len(all_ro) != 39 or len(all_rs) != 151:
        raise ValueError("combined consensus coverage mismatch")
    cons_dir = AI_DIR / "consensus"
    write_csv(cons_dir / "consensus_synthetic.csv", all_syn,
              ["output_id", "case_id", "category"] + SCORED_FIELDS)
    write_csv(cons_dir / "consensus_real_outputs.csv", all_ro,
              ["output_id", "case_ref", "readability", "overall_calibration"])
    write_csv(cons_dir / "consensus_real_sentences.csv", all_rs,
              ["output_id", "sentence_idx", "support_label"])
    (cons_dir / "PROVENANCE.md").write_text(
        "# AI annotation consensus\n\n"
        "These labels were produced on 2026-10-18 by four blinded AI annotator roles in two pairs "
        "(AB and CD), followed by evidence-based adjudication. The roles were executed through Codex "
        "agents in one project session; their errors may therefore be correlated. No human validated "
        "the labels during this run.\n\n"
        "These are not human annotations and must not be reported as such. See "
        "`docs/AI_ANNOTATION_RESULTS.md` for the protocol, agreement, limitations, and results.\n",
        encoding="utf-8")
    print("combined AI consensus: 122 synthetic outputs, 39 real outputs, 151 real sentences")
    return 0


def _fmt(v: Any) -> str:
    return "—" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def _tables(syn: dict[str, Any], real: dict[str, Any]) -> str:
    metrics = [
        ("calibration_accuracy", "exact accuracy"), ("macro_f1", "macro-F1"),
        ("ordinal_mae", "ordinal MAE"), ("severe_error_rate", "|error|=2"),
        ("overstatement_rate", "overstatement"), ("understatement_rate", "understatement"),
        ("omission_rate", "omission"), ("coverage_pooled", "finding coverage"),
        ("pct_outputs_with_unsupported", "outputs w/ unsupported"),
        ("numeric_errors_mean", "numeric errors/output"), ("num_fact_accuracy", "NUM fact accuracy"),
        ("neg_recall", "NEG recall"), ("neg_reframed_rate", "NEG reframed"),
    ]
    lines = ["# AI-scored results", "", "These are multi-agent AI judgments, not human annotations.", "",
             "## Synthetic TEST (ITT)", "", "| condition | " + " | ".join(x[1] for x in metrics) + " |",
             "|---|" + "---|" * len(metrics)]
    for cond, row in syn["summary"].items():
        lines.append(f"| {cond} | " + " | ".join(_fmt(row.get(k)) for k, _ in metrics) + " |")
    lines += ["", "## Real papers", "",
              "| condition | supported | overstated | understated | unsupported | numeric error | readability | papers |",
              "|---|---|---|---|---|---|---|---|"]
    for cond, row in real["summary"].items():
        lines.append("| " + cond + " | " + " | ".join(_fmt(row.get(k)) for k in
                     ("supported_rate", "overstated_rate", "understated_rate", "unsupported_rate",
                      "numeric_error_rate", "readability", "n_papers")) + " |")
    lines += ["", "## Synthetic paired comparisons (first minus second; case-bootstrap 95% CI)", "",
              "| comparison | metric | diff | 95% CI | n |", "|---|---|---|---|---|"]
    for name, comp in syn["comparisons"].items():
        for metric in ("correct", "abs_error", "severe_error", "over", "under", "coverage", "unsupported",
                       "numeric_errors", "num_fact_acc", "neg_recall", "neg_reframed"):
            if metric in comp:
                b = comp[metric]["case_bootstrap"]
                lines.append(f"| {name} | {metric} | {_fmt(b['diff'])} | [{_fmt(b['ci_low'])}, {_fmt(b['ci_high'])}] | {b['n']} |")
    lines += ["", "## Real-paper paired comparisons (first minus second; case-bootstrap 95% CI)", "",
              "| comparison | metric | diff | 95% CI | n |", "|---|---|---|---|---|"]
    for name, comp in real["comparisons"].items():
        for metric, b in comp.items():
            lines.append(f"| {name} | {metric} | {_fmt(b['diff'])} | [{_fmt(b['ci_low'])}, {_fmt(b['ci_high'])}] | {b['n']} |")
    return "\n".join(lines) + "\n"


def score_stage() -> int:
    cons = AI_DIR / "consensus"
    syn_rows = read_csv(cons / "consensus_synthetic.csv")
    real_out = read_csv(cons / "consensus_real_outputs.csv")
    real_sent = read_csv(cons / "consensus_real_sentences.csv")
    mapping = read_csv(ROOT / "private" / "condition_mapping.csv")
    real_mapping = read_csv(ROOT / "private" / "condition_mapping_real.csv")
    gold = load_jsonl(ROOT / "private" / "gold" / "test_gold.jsonl")
    rubric = load_jsonl(ROOT / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl")
    out_syn, out_real = RESULTS_SCORED / "synthetic", RESULTS_SCORED / "real"
    out_syn.mkdir(parents=True, exist_ok=True)
    out_real.mkdir(parents=True, exist_ok=True)
    syn_itt = score_synthetic(syn_rows, mapping, gold, rubric,
                              ROOT / "outputs" / "synthetic" / "deepseek__deepseek-v4-flash-0731", itt=True)
    syn_co = score_synthetic(syn_rows, mapping, gold, rubric,
                             ROOT / "outputs" / "synthetic" / "deepseek__deepseek-v4-flash-0731", itt=False)
    real = score_real(real_out, real_sent, real_mapping)
    (out_syn / "ai_results_ITT.json").write_text(json.dumps(syn_itt, indent=2), encoding="utf-8")
    (out_syn / "ai_results_completed_only.json").write_text(json.dumps(syn_co, indent=2), encoding="utf-8")
    (out_real / "ai_results_real.json").write_text(json.dumps(real, indent=2), encoding="utf-8")
    (RESULTS_SCORED / "TABLES_AI.md").write_text(_tables(syn_itt, real), encoding="utf-8")
    print(f"AI-scored results written to {RESULTS_SCORED.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("validate", "agreement", "combine", "score"))
    args = ap.parse_args(argv)
    if args.stage == "validate":
        _, errs = validate_all()
        print("OK" if not errs else "\n".join(errs))
        return int(bool(errs))
    if args.stage == "agreement":
        return agreement_stage()
    if args.stage == "combine":
        return combine_stage()
    return score_stage()


if __name__ == "__main__":
    sys.exit(main())
