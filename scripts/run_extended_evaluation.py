"""Run the post-freeze, AI-judged evaluation extension (docs/EVALUATION_EXTENSION_PROTOCOL.md).

Stages (each is resumable; judge calls are cached by input hash and never repeated):

    python scripts/run_extended_evaluation.py packets
    python scripts/run_extended_evaluation.py checklists            # real + diagnostic; commit before coverage
    python scripts/run_extended_evaluation.py extract
    python scripts/run_extended_evaluation.py verify --judge A      # and --judge B
    python scripts/run_extended_evaluation.py coverage --judge A    # and --judge B (needs frozen checklists)
    python scripts/run_extended_evaluation.py align --judge A       # and --judge B
    python scripts/run_extended_evaluation.py adjudicate
    python scripts/run_extended_evaluation.py consensus
    python scripts/run_extended_evaluation.py score                 # unblinds; writes results/ai_extended/

``--families`` restricts to some of synthetic, real, diagnostic; ``--only`` to some case aliases (pilots).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import extended_pipeline as P  # noqa: E402
from evaluation.extended_data import load_family, write_private_registry  # noqa: E402
from evaluation.judges import JUDGE_A, claude_spent, judge_b_for, write_used  # noqa: E402

FAMS = ("synthetic", "real", "diagnostic")


def _packets(fam: str, only: list[str] | None):
    data = load_family(fam)
    write_private_registry(data)
    packets = P.build_packets(data)
    if only:
        packets = {a: p for a, p in packets.items() if a in only}
    return data, packets


def _claims(fam: str, only: list[str] | None):
    claims = P.load_jsonl(P.EXT / "claims" / f"{fam}.jsonl")
    return [c for c in claims if not only or c["alias"] in only]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("packets", "checklists", "extract", "verify", "coverage", "align", "adjudicate",
                                      "consensus", "score", "report", "stability"))
    ap.add_argument("--families", default=",".join(FAMS))
    ap.add_argument("--judge", choices=("A", "B"), default="A")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--replicate", default="", help="adjudicate/consensus/stability: name of an adjudication replicate "
                    "(re-asks identical prompts with a new cache salt; writes under annotation/ai_extended/replicates/)")
    a = ap.parse_args(argv)
    fams = [f for f in a.families.split(",") if f]
    only = [x for x in a.only.split(",") if x] or None
    if a.stage == "stability":
        from evaluation import adjudicator_stability as S
        if not a.replicate:
            ap.error("stability needs --replicate")
        S.run(a.replicate)
        print(f"written results/ai_extended/adjudicator_stability.json for replicate {a.replicate}")
        return 0
    if a.stage == "report":
        import json
        from evaluation import extended_consensus as C
        from evaluation import extended_report as R
        out = ROOT / "results" / "ai_extended"
        for fam in fams:
            (out / fam).mkdir(parents=True, exist_ok=True)
            (out / fam / "agreement.json").write_text(json.dumps(C.agreement_stats(load_family(fam)), indent=1))
        (out / "provenance.json").write_text(json.dumps(C.provenance(), indent=1))
        R.main()
        print(f"report written to {out.relative_to(ROOT)}; Judge B spend ${claude_spent():.4f}")
        return 0
    for fam in fams:
        judge = JUDGE_A if a.judge == "A" else judge_b_for(fam, a.stage)
        print(f"== {a.stage} [{fam}] judge {judge.name} ({judge.model})" if a.stage in ("verify", "coverage", "align")
              else f"== {a.stage} [{fam}]", flush=True)
        if a.stage in ("adjudicate", "consensus"):
            from evaluation import extended_consensus as C
            data, packets = _packets(fam, only)
            (C.run_adjudication if a.stage == "adjudicate" else C.build_consensus)(
                data, packets, workers=a.workers, replicate=a.replicate or None)
            continue
        if a.stage == "score":
            from evaluation import extended_metrics as M
            M.score_family(fam)
            continue
        data, packets = _packets(fam, only)
        if a.stage == "packets":
            print(f"  {len(packets)} packets, {len(data.texts)} texts, "
                  f"{sum(len(p['units']) for p in packets.values())} sentence units")
        elif a.stage == "checklists":
            if fam == "synthetic":
                print("  synthetic cases use the frozen rubric/gold; no checklist")
                continue
            P.run_checklists(data, packets, workers=a.workers)
        elif a.stage == "extract":
            P.run_extraction(data, packets, workers=a.workers)
        elif a.stage == "verify":
            P.run_verification(data, packets, _claims(fam, only), judge, workers=a.workers)
        elif a.stage == "coverage":
            if fam == "synthetic":
                print("  synthetic coverage comes from the existing AI consensus; skipped")
                continue
            import json
            cl = json.loads((P.EXT / "checklists" / f"{fam}.json").read_text())
            P.run_coverage(data, packets, cl, judge, workers=a.workers)
        elif a.stage == "align":
            P.run_alignment(data, packets, _claims(fam, only), judge, workers=a.workers)
    if not a.replicate:  # replicate records live outside raw/ and are not part of the primary used-lists
        write_used(f"{a.stage}_{'-'.join(fams)}_{a.judge}" + (f"_only-{'-'.join(only)}" if only else ""))
    print(f"Judge B spend so far: ${claude_spent():.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
