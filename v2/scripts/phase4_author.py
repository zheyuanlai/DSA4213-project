"""Phase 4 case authoring with GPT-5.6 (design: v2/docs/PHASE4_DESIGN.md section 4).

  python v2/scripts/phase4_author.py --round r1 [--pairs P1,P2]          # author pairs from the spec
  python v2/scripts/phase4_author.py --round r2 --revise v2/private/phase4/validation/r1.json

The author sees only the authoring prompt (v2/prompts/phase4_author.md), its pair's row of
v2/benchmarks/phase4_pairs_spec.json, V1's non-benchmark example package and a list of names to avoid. It never sees
a verifier prompt, the DEV probes or any verifier output. Each reply is checked deterministically
(v2/benchmarks/phase4_checks.py). On errors there is one repair turn. Results go to v2/private/phase4/authored/<round>/
(gitignored until the freeze). Paid calls go on the V2 judge ledger, stage p4_author.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v2 import or_judge  # noqa: E402
from v2.benchmarks.phase4_checks import PAIR_SPEC, check_pair, known_names  # noqa: E402

PRIVATE = ROOT / "v2" / "private" / "phase4"
SYSTEM = ("You author fictional research materials for a methods study. Follow the instructions exactly and reply "
          "with one JSON object only.")
MAX_TOKENS = 20000


def author_prompt(pid: str, avoid: list[str]) -> str:
    tpl = (ROOT / "v2" / "prompts" / "phase4_author.md").read_text(encoding="utf-8")
    example = json.loads((ROOT / "docs" / "benchmark_example_case_NOT_IN_BENCHMARK.json").read_text(encoding="utf-8"))
    spec = {k: v for k, v in PAIR_SPEC[pid].items()}
    return (tpl.replace("{{EXAMPLE_PACKAGE}}", json.dumps(example["package"], ensure_ascii=False, indent=1))
            .replace("{{AVOID_NAMES}}", ", ".join(avoid))
            .replace("{{PAIR_SPEC}}", json.dumps(spec, ensure_ascii=False, indent=1)))


def revise_prompt(pid: str, avoid: list[str], previous: dict, disputes: list[dict]) -> str:
    lines = [author_prompt(pid, avoid), "", "## Revision request",
             "Here is your previous JSON for this pair:", json.dumps(previous, ensure_ascii=False),
             "", "An independent reader, who did not see the intended strengths, judged some drafts differently:"]
    for d in disputes:
        lines.append(f"* draft {d['key']} on the {d['member']} member (intended: {d['intended']}): reader label "
                     f"{d['validator_label']}, same_proposition={d['validator_same_proposition']}; reason: "
                     f"{d['validator_justification']}")
    lines += ["", "Revise only what is needed (draft wording, or the package if the evidence was ambiguous) so that "
              "each draft clearly has its intended strength on each member, keeping every rule above. If you think the "
              "reader is wrong, make the evidence or the wording unambiguous. Return the full corrected JSON object."]
    return "\n".join(lines)


def author_one(pid: str, prompt: str, avoid: set[str]) -> dict:
    call = or_judge.call_json(or_judge.AUTHOR_MODEL, "p4_author", pid, SYSTEM, prompt, max_tokens=MAX_TOKENS)
    calls = [{"raw": call.raw_path, "cost_usd": call.cost_usd, "cached": call.cached}]
    try:
        obj = or_judge.parse_json(call.content)
        errs, warns = check_pair(obj, avoid)
    except ValueError as e:
        obj, errs, warns = None, [f"parse: {e}"], []
    if errs:
        history = [{"role": "user", "content": prompt}, {"role": "assistant", "content": call.content}]
        fix = ("Your JSON has these problems:\n- " + "\n- ".join(errs[:25]) +
               "\nReturn the full corrected JSON object only.")
        call2 = or_judge.call_json(or_judge.AUTHOR_MODEL, "p4_author", pid + ":repair", SYSTEM, fix,
                                   max_tokens=MAX_TOKENS, history=history)
        calls.append({"raw": call2.raw_path, "cost_usd": call2.cost_usd, "cached": call2.cached})
        try:
            obj = or_judge.parse_json(call2.content)
            errs, warns = check_pair(obj, avoid)
        except ValueError as e:
            obj, errs, warns = None, [f"parse after repair: {e}"], []
    return {"pair_id": pid, "pair": obj, "errors": errs, "warnings": warns, "calls": calls}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--pairs", default=",".join(PAIR_SPEC))
    ap.add_argument("--revise", default="", help="validation JSON whose disputes are sent back to the author")
    a = ap.parse_args(argv)
    avoid_set = known_names()
    avoid = sorted(avoid_set)
    out_dir = PRIVATE / "authored" / a.round
    out_dir.mkdir(parents=True, exist_ok=True)
    pids = [p for p in a.pairs.split(",") if p]
    disputes_by_pair: dict[str, list] = {}
    prev_dir = None
    if a.revise:
        val = json.loads(Path(a.revise).read_text(encoding="utf-8"))
        prev_dir = Path(val["authored_dir"])
        for d in val["disputes"]:
            disputes_by_pair.setdefault(d["pair_id"], []).append(d)
        pids = [p for p in pids if p in disputes_by_pair]
    for pid in pids:
        if a.revise:
            prev = json.loads((prev_dir / f"{pid}.json").read_text(encoding="utf-8"))["pair"]
            prompt = revise_prompt(pid, avoid, prev, disputes_by_pair[pid])
        else:
            prompt = author_prompt(pid, avoid)
        rec = author_one(pid, prompt, avoid_set)
        rec["round"] = a.round
        (out_dir / f"{pid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8",
                                             newline="\n")
        print(f"{pid}: {'OK' if not rec['errors'] else 'ERRORS ' + str(len(rec['errors']))}"
              f" warnings={len(rec['warnings'])} cost=${sum(c['cost_usd'] for c in rec['calls']):.4f}")
        for e in rec["errors"][:6]:
            print("   E:", e)
    print(f"p4_author spent so far: ${or_judge.spent('p4_author'):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
