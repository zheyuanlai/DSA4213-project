"""Blinded AI judging of revised sentences from a Phase 4 TEST run (design: v2/docs/PHASE4_DESIGN.md section 5).

  python v2/scripts/phase4_judge.py --run-dir v2/outputs/phase4/<tag> [--mock]

This is a simplified version of V1's evidence-level evaluation:

* Only **distinct revised sentences** (WEAKEN/STRENGTHEN) are judged, deduplicated over conditions and repeats.
  Sentences under shuffled opaque IDs are grouped by member package. Judges never see the condition, run, item ID or
  gold; V1's `check_leakage` enforces this.
* Each sentence is one claim. Judge A (GPT-5.6) and Judge B (Claude Haiku 5.5) use the **unchanged V1 prompt**
  `annotation/ai_extended/prompts/verify.md` and V1's output schema.
* A label disagreement goes to a GPT-5.6 adjudication call using V1's `adjudicate_claims.md`.
* Numbers are checked by V1's deterministic `check_assertion`, once under each judge's mapping: "error" if both
  mappings give an error, "uncertain" if only one does.

Outputs: v2/results/phase4/<tag>/judged.json (blinded IDs) and v2/private/phase4/judge_registry_<tag>.json (ID →
case/text).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.extended_pipeline import claims_block  # noqa: E402
from evaluation.judges import SCHEMAS, check_leakage  # noqa: E402
from evaluation.numeric_fidelity import Assertion, EvidenceValues, Mapping, check_assertion, numbers_in  # noqa: E402
from src.runner import load_cases  # noqa: E402
from v2 import or_judge  # noqa: E402
from v2.verifier_oracle import oracle_evidence  # noqa: E402

V1P = ROOT / "annotation" / "ai_extended" / "prompts"
PRIVATE = ROOT / "v2" / "private" / "phase4"


def collect(run_dir: Path) -> dict[tuple[str, str], list[str]]:
    """(case_id, revised text) -> run ids that produced it."""
    out: dict[tuple[str, str], list[str]] = {}
    for f in glob.glob(str(run_dir / "*" / "*.json")):
        r = json.loads(Path(f).read_text(encoding="utf-8"))
        if r.get("status") == "completed" and r["decision"] in ("WEAKEN", "STRENGTHEN") and r.get("revised_text"):
            out.setdefault((r["case_id"], r["revised_text"].strip()), []).append(r["run_id"])
    return out


def opaque(case_id: str, text: str) -> str:
    return "x" + hashlib.sha256(f"{case_id}\n{text}".encode("utf-8")).hexdigest()[:10]


def build_claims(texts: dict[str, str]) -> tuple[dict, list[dict]]:
    units, claims = {}, []
    for k, (oid, text) in enumerate(texts.items(), 1):
        uid, cid = f"u{k}", f"c{k}"
        units[uid] = text
        nums = [{"number_id": f"{cid}.n{i}", "as_written": tok, "value": val, "comparator": "=", "approximate": False,
                 "role": "result", "unit": None} for i, (tok, val) in enumerate(numbers_in(text), 1)]
        claims.append({"unit_id": uid, "claim_id": cid, "oid": oid, "claim_type": "other", "span": text,
                       "proposition": text, "numbers": nums})
    return {"units": units}, claims


def schema_suffix(schema: dict) -> str:
    """V1's Claude backend (evaluation/judges.py::_claude_call) appends the output schema to the prompt; do the same."""
    return ("\n\n## Output format\nReturn exactly one JSON object, with no text before or after it, "
            "that validates against this JSON Schema:\n" + json.dumps(schema, separators=(",", ":")))


def call_validated(model: str, item_key: str, system: str, prompt: str, schema: dict, max_tokens: int) -> tuple[dict, list]:
    """Call with the schema appended; on a schema violation, one repair turn (deviation D1, PHASE4_DEVIATIONS.md)."""
    full = prompt + schema_suffix(schema)
    call = or_judge.call_json(model, "p4_judge", item_key, system, full, max_tokens=max_tokens)
    calls = [{"raw": call.raw_path, "cost_usd": call.cost_usd}]
    try:
        out = or_judge.parse_json(call.content)
        jsonschema.validate(out, schema)
        return out, calls
    except (ValueError, jsonschema.ValidationError) as e:
        msg = str(e).splitlines()[0][:400]
    history = [{"role": "user", "content": full}, {"role": "assistant", "content": call.content}]
    fix = f"Your JSON does not validate against the schema ({msg}). Return the corrected JSON object only."
    call2 = or_judge.call_json(model, "p4_judge", item_key + ":repair", system, fix, max_tokens=max_tokens,
                               history=history)
    calls.append({"raw": call2.raw_path, "cost_usd": call2.cost_usd})
    out = or_judge.parse_json(call2.content)
    jsonschema.validate(out, schema)
    return out, calls


def verify_call(model: str, case_id: str, pkg, texts: dict[str, str], tag: str) -> tuple[dict, list[dict], dict]:
    pk, claims = build_claims(texts)
    package = oracle_evidence(pkg)
    passages = "\n".join(f"[{u}] {t}" for u, t in pk["units"].items())
    cblock = claims_block(pk, claims)
    prompt = ((V1P / "verify.md").read_text(encoding="utf-8").replace("{{PACKAGE}}", package)
              .replace("{{PASSAGES}}", passages).replace("{{CLAIMS}}", cblock))
    check_leakage(prompt, [package, passages, cblock], [])
    system = (V1P / "system.md").read_text(encoding="utf-8").strip()
    out, calls = call_validated(model, f"{tag}:{case_id}:{model}", system, prompt, SCHEMAS["verify"], 16000)
    return {c["claim_id"]: c for c in out["claims"]}, claims, {"calls": calls}


def numeric_status(claim: dict, reading: dict, ev: EvidenceValues) -> list[str]:
    maps = {n["number_id"]: n for n in reading.get("numbers", [])}
    out = []
    for n in claim["numbers"]:
        m = maps.get(n["number_id"])
        if m is None:
            out.append("unmapped")
            continue
        v = check_assertion(Assertion(n["as_written"], n["value"]),
                            Mapping(m["source_type"], m.get("expression"), m.get("quote"), m.get("scale") or 1.0), ev)
        out.append("correct" if v.correct else "invalid" if v.status == "INVALID_MAPPING" else "error")
    return out


def adjudicate(case_id: str, pkg, disputes: list[dict], tag: str) -> dict[str, dict]:
    rng = random.Random(f"{tag}:{case_id}")
    lines = []
    for d in disputes:
        ra, rb = d["A"], d["B"]
        first, second = (ra, rb) if rng.random() < 0.5 else (rb, ra)
        lines.append(f"* item {d['claim_id']}: \"{d['text']}\"\n  disputed: label, entailment\n"
                     f"  reading 1: label {first['label']}, entailment {first['entailment']}; {first['justification']}\n"
                     f"  reading 2: label {second['label']}, entailment {second['entailment']}; {second['justification']}")
    package = oracle_evidence(pkg)
    prompt = ((V1P / "adjudicate_claims.md").read_text(encoding="utf-8").replace("{{PACKAGE}}", package)
              .replace("{{ITEMS}}", "\n".join(lines)))
    model_text = [d["text"] for d in disputes] + [str(r.get("justification") or "") for d in disputes
                                                    for r in (d["A"], d["B"])]
    check_leakage(prompt, [package, "\n".join(lines)] + model_text, [])
    system = (V1P / "system.md").read_text(encoding="utf-8").strip()
    out, _ = call_validated(or_judge.JUDGE_A_MODEL, f"{tag}:{case_id}:adj", system, prompt,
                            SCHEMAS["adjudicate_claims"], 4000)
    return {d["item_id"]: d for d in out["decisions"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--cases", default=str(ROOT / "v2" / "benchmarks" / "test_v2" / "cases.jsonl"))
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    tag = run_dir.name
    cases = {c.case_id: c for c in load_cases(Path(a.cases))}
    found = collect(run_dir)
    registry = {opaque(c, t): {"case_id": c, "text": t, "runs": runs} for (c, t), runs in found.items()}
    by_case: dict[str, dict[str, str]] = {}
    for oid, r in registry.items():
        by_case.setdefault(r["case_id"], {})[oid] = r["text"]
    judged = {}
    for case_id, texts in sorted(by_case.items()):
        rng = random.Random(f"{tag}:{case_id}:order")
        order = list(texts.items())
        rng.shuffle(order)
        texts = dict(order)
        pkg = cases[case_id].package
        ev = EvidenceValues.from_package(pkg)
        ra, claims, ca = verify_call(or_judge.JUDGE_A_MODEL, case_id, pkg, texts, tag)
        rb, _, cb = verify_call(or_judge.JUDGE_B_MODEL, case_id, pkg, texts, tag)
        disputes = []
        for c in claims:
            A, B = ra.get(c["claim_id"], {}), rb.get(c["claim_id"], {})
            judged[c["oid"]] = {"A": {k: A.get(k) for k in ("label", "entailment", "justification", "error_subtype")},
                                "B": {k: B.get(k) for k in ("label", "entailment", "justification", "error_subtype")},
                                "numeric_A": numeric_status(c, A, ev), "numeric_B": numeric_status(c, B, ev),
                                "calls": [ca, cb]}
            if A.get("label") != B.get("label"):
                disputes.append({"claim_id": c["claim_id"], "item_id": c["claim_id"], "text": c["span"], "A": A,
                                 "B": B, "oid": c["oid"]})
        if disputes:
            dec = adjudicate(case_id, pkg, disputes, tag)
            for d in disputes:
                judged[d["oid"]]["adjudicated"] = dec.get(d["item_id"])
        for c in claims:
            j = judged[c["oid"]]
            lab = j["A"]["label"] if j["A"]["label"] == j["B"]["label"] else (j.get("adjudicated") or {}).get("label")
            na, nb = j["numeric_A"], j["numeric_B"]
            num = ("error" if any(x == "error" and y == "error" for x, y in zip(na, nb)) else
                   "uncertain" if any("error" in (x, y) for x, y in zip(na, nb)) else "ok")
            j.update(final_label=lab or "UNRESOLVED", numeric=num)
    out = Path(a.out) if a.out else ROOT / "v2" / "results" / "phase4" / tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "judged.json").write_text(json.dumps(judged, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / f"judge_registry_{tag}.json").write_text(json.dumps(registry, ensure_ascii=False, indent=1),
                                                        encoding="utf-8", newline="\n")
    print(f"judged {len(judged)} distinct revised sentences over {len(by_case)} packages; "
          f"p4_judge spent ${or_judge.spent('p4_judge'):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
