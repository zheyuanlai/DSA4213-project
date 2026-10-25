"""Phase 4 blind gold validation with Claude Sonnet 5.5 (design: v2/docs/PHASE4_DESIGN.md section 4).

  python v2/scripts/phase4_validate.py --round r1 --authored v2/private/phase4/authored/r1 [--carry r0.json]

For every member package, the validator sees the package (V1 writer view) and the drafts placed on it, under shuffled
opaque sentence IDs. It never sees the intended levels or the expected decisions. The label definitions are copied at
run time, verbatim, from V1's judge prompt (annotation/ai_extended/prompts/verify.md), and the system prompt is V1's
judge system prompt. Agreement is checked on the decision direction:

* UNDERSTATED → STRENGTHEN
* SUPPORTED → ACCEPT
* OVERSTATED / UNSUPPORTED → WEAKEN/REMOVE

STRENGTHEN items also need same_proposition = true. Output: v2/private/phase4/validation/<round>.json.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.package_schema import ResearchPackage  # noqa: E402
from v2 import or_judge  # noqa: E402
from v2.benchmarks.phase4_checks import PAIR_SPEC  # noqa: E402
from v2.verifier_oracle import oracle_evidence  # noqa: E402

PRIVATE = ROOT / "v2" / "private" / "phase4"
V1_PROMPTS = ROOT / "annotation" / "ai_extended" / "prompts"
DIRECTION = {"UNDERSTATED": "STRENGTHEN", "SUPPORTED": "ACCEPT", "OVERSTATED": "REDUCE", "UNSUPPORTED": "REDUCE"}


def label_definitions() -> str:
    """The `label` block of V1's verify prompt, verbatim."""
    v = (V1_PROMPTS / "verify.md").read_text(encoding="utf-8")
    i = v.index("2. `label` (calibration-aware):")
    j = v.index("## Other fields")
    return v[i:j].split(":", 1)[1].strip()


def expected_decision(draft_level: int, member_level: int) -> str:
    if draft_level < member_level:
        return "STRENGTHEN"
    if draft_level == member_level:
        return "ACCEPT"
    return "REMOVE_OR_WEAKEN" if member_level == 0 else "WEAKEN"


def items_for_pair(pair: dict) -> list[dict]:
    pid = pair["pair_id"]
    plevel = PAIR_SPEC[pid]["partner_level"]
    out = []
    for member, level in (("strong", 2), ("partner", plevel)):
        for d in pair["drafts"]:
            if d["key"] == "Z" and member == "strong":
                continue
            out.append({"item_id": f"{pid}-{d['key']}-{member}", "pair_id": pid, "key": d["key"], "member": member,
                        "member_level": level, "draft_level": d["expressed_level"], "text": d["text"],
                        "expected": expected_decision(d["expressed_level"], level)})
    return out


def validate_member(pair: dict, member: str, items: list[dict], seed: str) -> list[dict]:
    pkg = ResearchPackage.model_validate(pair[f"{member}_package"])
    its = [x for x in items if x["member"] == member]
    rng = random.Random(f"{seed}:{pair['pair_id']}:{member}")
    order = its[:]
    rng.shuffle(order)
    ids = {x["item_id"]: f"d{k + 1}" for k, x in enumerate(order)}
    sentences = "\n".join(f"[{ids[x['item_id']]}] {x['text']}" for x in order)
    tpl = (ROOT / "v2" / "prompts" / "phase4_validate.md").read_text(encoding="utf-8")
    prompt = (tpl.replace("{{LABEL_DEFINITIONS}}", label_definitions()).replace("{{PACKAGE}}", oracle_evidence(pkg))
              .replace("{{SENTENCES}}", sentences))
    system = (V1_PROMPTS / "system.md").read_text(encoding="utf-8").strip()
    call = or_judge.call_json(or_judge.VALIDATOR_MODEL, "p4_validate", f"{pair['pair_id']}-{member}", system, prompt,
                              max_tokens=4000)
    got = {}
    try:
        for j in or_judge.parse_json(call.content).get("judgements", []):
            got[j.get("sentence_id")] = j
    except ValueError:
        pass
    out = []
    for x in its:
        j = got.get(ids[x["item_id"]], {})
        lab = j.get("label")
        direction = DIRECTION.get(lab, "OTHER")
        exp_dir = "REDUCE" if x["expected"] in ("WEAKEN", "REMOVE_OR_WEAKEN") else x["expected"]
        agree = direction == exp_dir and (x["expected"] != "STRENGTHEN" or j.get("same_proposition") is True)
        out.append({**x, "validator_label": lab, "validator_same_proposition": j.get("same_proposition"),
                    "validator_strongest": j.get("strongest_supported"),
                    "validator_justification": j.get("justification"), "validator_confidence": j.get("confidence"),
                    "agree": agree, "raw": call.raw_path, "cost_usd": call.cost_usd})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--authored", required=True, help="directory of authored pair files")
    ap.add_argument("--carry", default="", help="earlier validation JSON: keep its results for pairs not re-authored")
    ap.add_argument("--seed", default="phase4")
    a = ap.parse_args(argv)
    adir = Path(a.authored)
    results = []
    done_pairs = set()
    for f in sorted(adir.glob("P*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec["errors"] or rec["pair"] is None:
            print(f"{rec['pair_id']}: skipped (deterministic errors remain)")
            continue
        items = items_for_pair(rec["pair"])
        for member in ("strong", "partner"):
            results += validate_member(rec["pair"], member, items, a.seed)
        done_pairs.add(rec["pair_id"])
    carried = []
    if a.carry:
        old = json.loads(Path(a.carry).read_text(encoding="utf-8"))
        carried = [r for r in old["items"] if r["pair_id"] not in done_pairs]
        results += carried
    disputes = [r for r in results if not r["agree"]]
    summary = {"round": a.round, "authored_dir": str(adir), "n_items": len(results), "n_agree": len(results) - len(disputes),
               "n_disputes": len(disputes), "carried_from": a.carry or None, "items": results,
               "disputes": [{**d, "intended": f"{d['expected']} (draft level {d['draft_level']}, member level "
                                              f"{d['member_level']})"} for d in disputes]}
    out = PRIVATE / "validation" / f"{a.round}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{summary['n_agree']}/{summary['n_items']} agree; {summary['n_disputes']} disputes -> {out}")
    for d in disputes:
        print(f"  {d['item_id']}: expected {d['expected']}, validator {d['validator_label']} "
              f"(same_prop={d['validator_same_proposition']})")
    print(f"p4_validate spent so far: ${or_judge.spent('p4_validate'):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
