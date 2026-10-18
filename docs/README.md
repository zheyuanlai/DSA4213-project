# Documentation Index

Start with the final report, [`../report/final_report.md`](../report/final_report.md). The documents below hold the
detail behind it. Every quality label in this project is an AI judgement; no human annotation was carried out.

## Results (read in this order)

| Document | What it contains | Status |
|---|---|---|
| [`EVALUATION_EXTENSION_RESULTS.md`](EVALUATION_EXTENSION_RESULTS.md) | Main results: whole-passage, atomic-claim, numeric, finding-coverage and verifier-edit metrics for all conditions. Supplementary sections cover judge sensitivity, adjudicator test–retest and the third judge family | Final; AI-judged, exploratory |
| [`AI_ANNOTATION_RESULTS.md`](AI_ANNOTATION_RESULTS.md) | Multi-agent AI annotation of the pre-registered focal labels and secondary metrics; shows the ceiling effect | Final; AI-judged |
| [`AUTOMATIC_RESULTS.md`](AUTOMATIC_RESULTS.md) | Rule-verified automatic measurements (completion, cost, latency, tool trajectories, numeric grounding) and unvalidated `[PROXY]` heuristics | Final for automatic metrics; its "PENDING" lines predate the AI evaluation |
| [`H2_DIAGNOSTIC.md`](H2_DIAGNOSTIC.md) | DEV-only diagnostic of why STRENGTHEN never fires | Final; exploratory |

## Protocols and decisions

| Document | What it contains |
|---|---|
| [`PROTOCOL_FREEZE.md`](PROTOCOL_FREEZE.md) | Pre-registered conditions, hypotheses H1–H3 and analysis plan |
| [`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md) | Gold rules for the 48 synthetic cases (frozen) |
| [`EVALUATION_EXTENSION_PROTOCOL.md`](EVALUATION_EXTENSION_PROTOCOL.md) | Evidence-level evaluation protocol with dated amendments 1–12 |
| [`DEVIATIONS_FROM_PROPOSAL.md`](DEVIATIONS_FROM_PROPOSAL.md) | Every deviation from the proposal and every post-freeze change, with timestamps |
| [`MODEL_SELECTION.md`](MODEL_SELECTION.md) | Choice of the backbone model |
| [`DIAGNOSTIC_LONG_PACKAGES.md`](DIAGNOSTIC_LONG_PACKAGES.md) | Design of the long-package stress test |
| [`RELATED_WORK_VERIFICATION.md`](RELATED_WORK_VERIFICATION.md) | Source-by-source verification of every reference (BibTeX in `report/references_verified.bib`) |

## Reproduction and audit

| Document | What it contains |
|---|---|
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | How to verify, re-derive and re-run results; what is frozen and where |
| [`FINAL_AUDIT.md`](FINAL_AUDIT.md) | Engineering audit at handoff (2026-10-10), quality gates and security review |
| [`COMMIT_SHA_MAPPING.md`](COMMIT_SHA_MAPPING.md) | Mapping from the original commit SHAs to the rewritten ones (message-only rewrite) |

## Historical planning records

These documents describe plans that were not carried out or a phase that has ended. Each has a dated status note at the top.

| Document | What it was |
|---|---|
| [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md) | Original execution plan |
| [`PROGRESS.md`](PROGRESS.md) | Engineering log of 2026-10-10 |
| [`HUMAN_REVIEW_HANDOFF.md`](HUMAN_REVIEW_HANDOFF.md) | Handoff for the planned blind human annotation |
| [`AMENDMENT_FOUR_PERSON_ANNOTATION.md`](AMENDMENT_FOUR_PERSON_ANNOTATION.md) | Four-annotator workflow, prepared but not carried out |
| [`benchmark_example_case_NOT_IN_BENCHMARK.json`](benchmark_example_case_NOT_IN_BENCHMARK.json) | Illustrative case that is not part of the benchmark |
