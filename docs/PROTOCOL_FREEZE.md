# Protocol Freeze (pre-registered before any TEST-split call)

The machine-readable record is `benchmarks/freeze_manifest.json`. It holds sha256 values for the frozen config, every prompt,
every `src/*.py`, the public benchmark files, the annotation guide and the evaluation scripts, plus the private
TEST-gold hash, the git commit, and an audit showing that no ledger entry or output file referenced a TEST case before the freeze.
`python scripts/freeze_protocol.py --check` verifies that none of these files has changed since.

## Frozen elements
* **Data:** 48 cases. The DEV split (16) was used for all tuning. The TEST split (32) was never sent to any model before the freeze.
  Pairs never cross splits. TEST gold levels: per ordinal category, two ℓ=2 and two non-strong (overall 12 strong, 6 ℓ=1, 6 ℓ=0).
* **Backbone and decoding:** `configs/frozen_primary.yaml` (DeepSeek V4 Flash 0731, temperature 0, reasoning off,
  fp8 endpoint routing with `require_parameters`). The same file is used for the real-paper study (conditions C1–C4).
* **Conditions:** `src/conditions.py` / `configs/conditions.yaml` (C1–C7, shared-upstream design).
* **Verifier:** 4 evidence-tool calls per claim, max 6 claims per passage, 1 verification pass. Scripted order:
  `lookup_table → compare_numbers → get_test_metadata → retrieve_passage`.
* **Prompts:** `prompts/*.md` (hashes in the manifest and in every run record).
* **Gold protocol and annotation guide:** `docs/BENCHMARK_SPEC.md`, `annotation/ANNOTATION_GUIDE.md`.
* **Evaluation plan:** `evaluation/score_human.py` (primary human-scored metrics), `evaluation/auto_metrics.py`
  (automatic and PROXY metrics), `evaluation/paired_bootstrap.py`.

## Changes made on DEV before the freeze (complete list)
1. Provider routing changed from DeepInfra-only to three fp8 endpoints (rate limits). `parallel_tool_calls` was dropped.
2. One tool call executed per turn (DEV showed many parallel calls).
3. Decision validator accepts `evidence_ids` sent as a JSON-encoded string (a DEV bug that produced one invalid decision).
4. Both verifier prompts gained the same check-list and the rule "decision must agree with rationale". This was motivated by one DEV case.
   The change was re-checked on DEV with identical cached drafts (run tag `dev_pilot3`).
5. PROXY lexical heuristics in `evaluation/auto_metrics.py` were debugged on DEV outputs. They are unvalidated and not primary.

## Pre-registered analysis (unchanged from the proposal)
* **H1:** C4 vs C2 (and C1): overstatement, calibration accuracy, coverage, cost. C6 vs C2 is reported as the same-draft contrast.
* **H2:** C4 vs C5 (identical starting drafts): understatement among strong-support cases (N=12), corrected vs introduced edits, overstatement trade-off.
* **H3:** C4 vs C3: calibration and coverage; actual tool calls, latency and cost; adaptive tool choices.
* Case-level paired bootstrap 95% CIs (10,000 resamples), with matched-pair-level bootstrap as a sensitivity analysis.
  With 24 ordinal TEST cases, only large differences (~20 percentage points) are detectable. Per-category results (n=4) are descriptive only.
* Primary calibration metrics come from **two blind human annotators** after adjudication. Automatic metrics are reported
  separately. PROXY metrics are never presented as calibration accuracy.
