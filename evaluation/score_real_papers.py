"""Real-paper study (C1–C4): validate + merge two annotators, agreement, adjudication, and scoring.

Run ONLY after both annotators have submitted real files:

  python -m evaluation.score_real_papers merge \
      --a annotation/completed/annotator_A_real.csv,annotation/completed/annotator_A_real_sentences.csv \
      --b annotation/completed/annotator_B_real.csv,annotation/completed/annotator_B_real_sentences.csv \
      --out annotation/agreement_real
  # fill annotation/agreement_real/adjudication_real.csv (adjudicated_value; NONE not allowed here), then:
  python -m evaluation.score_real_papers merge ... --adjudicated annotation/agreement_real/adjudication_real.csv
  python -m evaluation.score_real_papers score --consensus-outputs annotation/agreement_real/consensus_real_outputs.csv \
      --consensus-sentences annotation/agreement_real/consensus_real_sentences.csv \
      --mapping private/condition_mapping_real.csv --out results/human_scored_real

There are NO gold labels for real papers: metrics are human judgements of sentence-level support
(SUPPORTED / OVERSTATED / UNDERSTATED / UNSUPPORTED / NUMERIC_ERROR / NOT_A_CLAIM) and readability (1–5).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.blinding import OVERALL_CALIBRATION, SUPPORT_LABELS, read_csv
from evaluation.merge_annotations import cohen_kappa
from evaluation.paired_bootstrap import paired_bootstrap


def _key(r: dict[str, str]) -> str:
    return f"{r['output_id']}#{r['sentence_idx']}"


def validate(out_rows, sent_rows, packet_out, packet_sent, who) -> list[str]:
    errs = []
    ids = [r["output_id"] for r in out_rows]
    if sorted(ids) != sorted(r["output_id"] for r in packet_out) or len(set(ids)) != len(ids):
        errs.append(f"{who}: output rows do not match the packet exactly once each")
    sk = [_key(r) for r in sent_rows]
    if sorted(sk) != sorted(_key(r) for r in packet_sent) or len(set(sk)) != len(sk):
        errs.append(f"{who}: sentence rows do not match the packet exactly once each")
    for r in out_rows:
        if (r.get("readability") or "").strip() not in ("1", "2", "3", "4", "5"):
            errs.append(f"{who}/{r['output_id']}: readability must be 1-5")
        if (r.get("overall_calibration") or "").strip() not in OVERALL_CALIBRATION:
            errs.append(f"{who}/{r['output_id']}: overall_calibration must be one of {OVERALL_CALIBRATION}")
        if (r.get("confidence") or "").strip().lower() not in ("low", "medium", "high"):
            errs.append(f"{who}/{r['output_id']}: confidence must be low/medium/high")
    for r in sent_rows:
        if (r.get("support_label") or "").strip() not in SUPPORT_LABELS:
            errs.append(f"{who}/{_key(r)}: support_label must be one of {SUPPORT_LABELS}")
    return errs


def agreement(Ao, Bo, As, Bs) -> dict[str, Any]:
    ids = sorted(set(Ao) & set(Bo))
    ra, rb = [int(Ao[i]["readability"]) for i in ids], [int(Bo[i]["readability"]) for i in ids]
    ks = sorted(set(As) & set(Bs))
    la, lb = [As[k]["support_label"] for k in ks], [Bs[k]["support_label"] for k in ks]
    oa, ob = [Ao[i]["overall_calibration"] for i in ids], [Bo[i]["overall_calibration"] for i in ids]
    return {"n_outputs": len(ids), "n_sentences": len(ks),
            "readability_kappa_quadratic": cohen_kappa(ra, rb, [1, 2, 3, 4, 5], "quadratic"),
            "readability_pct_exact": sum(x == y for x, y in zip(ra, rb)) / len(ids) if ids else None,
            "support_label_kappa": cohen_kappa(la, lb, SUPPORT_LABELS),
            "support_label_pct_agree": sum(x == y for x, y in zip(la, lb)) / len(ks) if ks else None,
            "overall_calibration_kappa": cohen_kappa(oa, ob, OVERALL_CALIBRATION)}


def merge(a_files: list[Path], b_files: list[Path], out: Path, adjudicated: Path | None,
          packet_dir: Path = Path("annotation/real")) -> int:
    po = read_csv(packet_dir / "blinded_real_papers.csv")
    ps = read_csv(packet_dir / "blinded_real_papers_sentences.csv")
    ao, as_, bo, bs = read_csv(a_files[0]), read_csv(a_files[1]), read_csv(b_files[0]), read_csv(b_files[1])
    errs = validate(ao, as_, po, ps, "A") + validate(bo, bs, po, ps, "B")
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation_report.txt").write_text("\n".join(errs) + ("\n" if errs else "OK\n"))
    if errs:
        print(f"{len(errs)} validation error(s); see {out/'validation_report.txt'}")
        return 1
    Ao, Bo = {r["output_id"]: r for r in ao}, {r["output_id"]: r for r in bo}
    As, Bs = {_key(r): r for r in as_}, {_key(r): r for r in bs}
    (out / "agreement.json").write_text(json.dumps(agreement(Ao, Bo, As, Bs), indent=1))
    dis = []
    for i in sorted(Ao):
        for f in ("readability", "overall_calibration"):
            if Ao[i][f].strip() != Bo[i][f].strip():
                dis.append({"item": i, "field": f, "value_A": Ao[i][f], "value_B": Bo[i][f], "adjudicated_value": "", "rationale": ""})
    for k in sorted(As):
        if As[k]["support_label"].strip() != Bs[k]["support_label"].strip():
            dis.append({"item": k, "field": "support_label", "value_A": As[k]["support_label"], "value_B": Bs[k]["support_label"],
                        "adjudicated_value": "", "rationale": ""})
    fields = ["item", "field", "value_A", "value_B", "adjudicated_value", "rationale"]
    with open(out / ("adjudication_real.csv" if adjudicated is None else "disagreements_recomputed.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dis)
    print(json.dumps({"n_disagreements": len(dis)}, indent=1))
    if adjudicated is None:
        return 0
    adj = {(r["item"], r["field"]): r["adjudicated_value"].strip() for r in read_csv(adjudicated)}
    cerrs, outs, sents = [], [], []
    for i in sorted(Ao):
        row = {"output_id": i, "case_ref": Ao[i]["case_ref"]}
        for f, allowed in (("readability", ["1", "2", "3", "4", "5"]), ("overall_calibration", OVERALL_CALIBRATION)):
            v = Ao[i][f].strip() if Ao[i][f].strip() == Bo[i][f].strip() else adj.get((i, f), "")
            if v not in allowed:
                cerrs.append(f"{i}/{f}: missing or invalid adjudicated value {v!r}")
            row[f] = v
        outs.append(row)
    for k in sorted(As):
        v = As[k]["support_label"].strip() if As[k]["support_label"].strip() == Bs[k]["support_label"].strip() else adj.get((k, "support_label"), "")
        if v not in SUPPORT_LABELS:
            cerrs.append(f"{k}/support_label: missing or invalid adjudicated value {v!r}")
        sents.append({"output_id": As[k]["output_id"], "sentence_idx": As[k]["sentence_idx"], "support_label": v})
    if cerrs:
        (out / "consensus_errors.txt").write_text("\n".join(cerrs))
        print(f"{len(cerrs)} consensus problem(s); consensus not written")
        return 1
    for name, rows, fl in (("consensus_real_outputs.csv", outs, ["output_id", "case_ref", "readability", "overall_calibration"]),
                           ("consensus_real_sentences.csv", sents, ["output_id", "sentence_idx", "support_label"])):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fl)
            w.writeheader()
            w.writerows(rows)
    print("consensus written")
    return 0


def score(cons_out: list[dict[str, str]], cons_sent: list[dict[str, str]], mapping: list[dict[str, str]]) -> dict[str, Any]:
    by_out = {r["output_id"]: r for r in cons_out}
    sents: dict[str, list[str]] = {}
    for r in cons_sent:
        sents.setdefault(r["output_id"], []).append(r["support_label"])
    completed = {m["output_id"] for m in mapping if m["status"] == "completed" and m["output_id"]}
    missing = completed - set(by_out)
    if missing:
        raise ValueError(f"{len(missing)} completed real-paper outputs lack consensus labels")
    per: dict[str, dict[str, dict[str, Any]]] = {}
    for m in mapping:
        if m["status"] != "completed":
            continue
        labs = [l for l in sents.get(m["output_id"], []) if l != "NOT_A_CLAIM"]
        n = len(labs)
        c = Counter(labs)
        per.setdefault(m["condition"], {})[m["case_id"]] = {
            "n_claims": n, "supported_rate": c["SUPPORTED"] / n if n else None,
            "overstated_rate": c["OVERSTATED"] / n if n else None, "understated_rate": c["UNDERSTATED"] / n if n else None,
            "unsupported_rate": c["UNSUPPORTED"] / n if n else None, "numeric_error_rate": c["NUMERIC_ERROR"] / n if n else None,
            "readability": int(by_out[m["output_id"]]["readability"]),
            "overall_calibration": by_out[m["output_id"]]["overall_calibration"]}
    summary = {}
    for cond, d in per.items():
        vals = list(d.values())

        def mean(k):
            xs = [v[k] for v in vals if v[k] is not None]
            return sum(xs) / len(xs) if xs else None

        summary[cond] = {k: mean(k) for k in ("supported_rate", "overstated_rate", "understated_rate", "unsupported_rate",
                                             "numeric_error_rate", "readability")}
        summary[cond]["n_papers"] = len(vals)
        summary[cond]["overall_calibration_counts"] = dict(Counter(v["overall_calibration"] for v in vals))
    comps = {}
    for x, y in (("C4", "C2"), ("C4", "C1"), ("C4", "C3")):
        if x in per and y in per:
            comps[f"{x}_vs_{y}"] = {k: paired_bootstrap({c: v[k] for c, v in per[x].items()}, {c: v[k] for c, v in per[y].items()})
                                    for k in ("supported_rate", "overstated_rate", "understated_rate", "readability")}
    return {"summary": summary, "comparisons": comps, "per_case": per}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--a", required=True)
    m.add_argument("--b", required=True)
    m.add_argument("--out", default="annotation/agreement_real")
    m.add_argument("--adjudicated", default=None)
    m.add_argument("--packet-dir", default="annotation/real")
    s = sub.add_parser("score")
    s.add_argument("--consensus-outputs", required=True)
    s.add_argument("--consensus-sentences", required=True)
    s.add_argument("--mapping", default="private/condition_mapping_real.csv")
    s.add_argument("--out", default="results/human_scored_real")
    a = ap.parse_args(argv)
    if a.cmd == "merge":
        return merge([Path(x) for x in a.a.split(",")], [Path(x) for x in a.b.split(",")], Path(a.out),
                     Path(a.adjudicated) if a.adjudicated else None, Path(a.packet_dir))
    res = score(read_csv(Path(a.consensus_outputs)), read_csv(Path(a.consensus_sentences)), read_csv(Path(a.mapping)))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "human_results_real.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
