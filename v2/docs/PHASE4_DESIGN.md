# Phase 4 (reduced): one held-out evaluation of the V2 fix

**Status: reduced design adopted 2026-10-25 for the 29 October presentation.** The full design it replaces is in git
history (commit `9afb3de`). V2 is a small extension of V1, so this phase aims at **one convincing held-out test of the
V2 decision fix**, not a second full-scale study.

## 1. Scope

| Kept | Deferred or dropped |
|---|---|
| Part A: new held-out single-sentence benchmark (8 matched pairs, about 50 items), 3 conditions, 3 interleaved repeats | Paragraph (multi-sentence) items |
| Natural-understatement prevalence from the **frozen V1 AI annotations** (no new calls) | Full Part B inference study on V1 drafts. Optional, only if Zheyuan's withheld files arrive; it never blocks Part A |
| Separate authoring and blind validation, deterministic checks, a pre-inference freeze, identical inputs, blinded judging of revisions | Required student gold annotation (none; reported honestly) |
| Gold-based decision metrics, supported revisions, false strengthening, harmful edits, cost | The V1 extension pipeline beyond verification of revised sentences (checklists, coverage, test–retest, third judge) |

## 2. Part A benchmark

**8 matched scenario pairs (16 packages)**, all new and fictional. The two members of a pair differ in one declared
evidence fact.

| # | Proposition type | Strong member (supported level 2) | Partner |
|---|---|---|---|
| P1 | Significance from a confidence interval only | paired 95% CI of the difference excludes 0 | CI includes 0 → **level 0** |
| P2 | Significance after a multiple-comparison correction | adjusted p < α | raw p < α, adjusted p ≥ α → level 1 |
| P3 | Consistency with ties | strictly better on all tasks | one task tied → level 1 |
| P4 | Directly measured memory | peak memory measured for both on the same setup | only parameter counts → level 1 |
| P5 | Throughput comparability | both measured at the same batch size and hardware | measured at different batch sizes → level 1 |
| P6 | Robustness over severities | criterion met at every severity | fails at the highest → level 1 |
| P7 | Negative result | the method is significantly worse (valid test) | worse, no test → level 1 |
| P8 | Citation magnitude | the cited passage states the effect size | the passage describes only the procedure → **level 0** |

**Drafts per pair.**

* **U** and **U2**: same-proposition understatements at level 1, with different linguistic patterns.
* **S**: the strong form, level 2.
* Each draft is placed on both members.
* **Z**: a correct "not established" statement, on the two level-0 partners only.

| Draft | Strong member | Level-1 partner | Level-0 partner |
|---|---|---|---|
| U, U2 | **STRENGTHEN** (16) | ACCEPT (12) | REMOVE/WEAKEN (4) |
| S | ACCEPT (8) | WEAKEN (6) | REMOVE/WEAKEN (2) |
| Z | none | none | ACCEPT (2) |

That gives **50 items: 16 STRENGTHEN, 22 ACCEPT, 12 WEAKEN/REMOVE.**

* **Patterns.** At least 8 of the 16 U/U2 drafts use patterns not used in DEV (for example "preliminary evidence", "a
  trend toward", litotes, "in several settings", "comparable or better", a double hedge).
* **Targeted failure.** At least 4 understate a claim that **needs no statistical test** (memory, throughput,
  robustness, consistency), aimed at E5's "no test, so keep the hedge" failure.
* **Excluded by construction.** Scope broadening and omitted findings.

**Expected decisions are computed by code** from (draft level, member level): lower → STRENGTHEN, equal → ACCEPT,
higher → WEAKEN (or REMOVE/WEAKEN when the member is at level 0). The author does not assign them.

## 3. Conditions (identical inputs; one interleaved batch; 3 repeats)

| Condition | Code | Policy |
|---|---|---|
| V1 C4 | V1 `src.verifier.verify_draft`, unchanged, 800 tokens per turn (`D0-tools-800`) | V1 prompt and schema |
| V2 C4 | `v2.verifier_tools`, variant D1, unchanged (`D1-tools`) | D1 addendum and schema |
| V2 C5 | same port, STRENGTHEN removed from the allowed set (`D1-tools-C5`) | D1 addendum with the single mapping line changed to **STRONGER_SUPPORTED → ACCEPT**, plus V1's existing no-strengthen note. **Frozen before TEST** |

All conditions share the same backbone, decoding, routing, 4-call tool budget, package, starting draft and evidence
index. The analysis unit is the run, clustered by item. Contrasts are V2 C4 − V1 C4 and V2 C4 − V2 C5, with the paired
cluster bootstrap over pairs (`evaluation/paired_bootstrap.cluster_bootstrap`). Raw counts are always shown, and nothing
is called "significant".

## 4. Authoring, validation, freeze

| Step | Model / tool | Separation |
|---|---|---|
| Case spec (`v2/docs/PHASE4_CASE_SPEC.md`) | coordinating agent | Categories, levels and draft rules only. No D1 prompt, DEV probes or E-results |
| Authoring | **GPT-5.6 (`openai/gpt-5.6-sol`)** | Sees the spec, the V1 package schema and the non-benchmark example; never sees D1, the DEV probes or verifier outputs |
| Deterministic checks | code (reusing `benchmarks/validate.py` pieces) | test statistics and p/CI consistency, cell text/value, evidence IDs, rubric-leak words, pair-difference check, draft numbers in the package, no DEV name reuse, quotas |
| Blind validation | **Claude Sonnet 5.5 (`anthropic/claude-sonnet-5.5`)** | Sees package + draft only. Returns the same-proposition flag, strongest supported statement, levels and relation. A disagreement goes back to the author once; still unresolved → dropped |
| Freeze | `v2/benchmarks/freeze_manifest.json` | Hashes of the public items, the gold (in `v2/private/`, gitignored), the D1/C5 prompts, `verifier_tools.py`, the runner, analysis and judge prompts. Committed before any TEST inference |

**Backend.** The Codex and Claude CLIs used in V1 are not installed on this machine, so authoring and validation call the
**same model families through OpenRouter**. Spend goes on a separate V2 judge ledger (`v2/outputs/judge_ledger.jsonl`),
kept apart from experiment spend.

**Overlap with the output judges** (documented): GPT-5.6 authors the cases and is also Judge A for revisions. The primary
metrics use the validated gold, not the judges.

## 5. Metrics and judging

* **Primary (gold-based).**
  * Correct strengthening: STRENGTHEN chosen on the 16 understated items, and the revision judged SUPPORTED with no
    numeric error.
  * False strengthening: on the 34 other items.
  * Overstatement correction: the 12 overstated items.
  * Control preservation: the 22 calibrated items.
  * **Harmful edits:** a calibrated item that ends up as an error.
* **Secondary.**
  * seen vs unseen patterns;
  * the no-test-needed subgroup;
  * per-pair breakdown;
  * decisive-evidence retrieval;
  * cost, latency and tool calls.
* **Judging.**
  * Only **distinct revised sentences** are judged; unchanged sentences keep their gold.
  * Judges see blinded items: package + sentence, with no condition and no gold.
  * Judge A is GPT-5.6 and Judge B is Claude Haiku 5.5, both with the **unchanged V1 `verify.md` prompt**, applied to
    the revised sentence as one claim.
  * Disagreements go to a GPT-5.6 adjudication call.
  * Numbers are checked by `evaluation/numeric_fidelity`.

## 6. Prevalence of natural understatement (frozen V1 labels, no new calls)

From `docs/EVALUATION_EXTENSION_RESULTS.md` and `results/ai_extended/`:

* atomic claims labelled UNDERSTATED: synthetic TEST outputs 0–1 per condition; real-paper outline drafts 0.015 of 202;
* AI focal annotation: no understatement in any condition on the 24 ordinal TEST cases.

Reported as AI-labelled estimates (AI–AI κ 0.56–0.65). A Part B inference study on V1 drafts is optional (section 1).

## 7. Cost and time (from actual logs)

* **TEST inference (OpenRouter, V2 ledger, stage cap $1).** 50 items × 3 conditions × 3 repeats = 450 runs. E5 cost
  $0.37–0.38 per 1,000 runs and took about 4.7 s per run with 2 workers, so about **$0.17 and about 35 min**.
* **Authoring and validation (OpenRouter, judge ledger, cap $4).**
  * 8 authoring calls to GPT-5.6-sol ($4/$20 per M tokens; with reasoning, about $0.2–0.35 per pair);
  * about 16 validation calls to Sonnet 5.5 ($2/$10 per M);
  * together about **$2–3.5**.
* **Revision judging (judge ledger).** About 80–150 distinct revisions, each judged by Judge A and Judge B, plus
  adjudication: about $0.5–1.
* **Engineering.** About half a day for authoring/validation/checks/freeze, plus about 2–3 h for inference, judging and
  scoring.

## 8. Remaining risks

* **The AI-only gold.** No student validation.
* **Author/judge family overlap.**
* **A single backbone.**
* **"Same proposition" judgements.** The validator applies the spec's rules.
* **Inference variability.** Mitigated by 3 interleaved repeats and run-level metrics.
* **Small n.** 16 STRENGTHEN items: a 0.8 rate has a 95% interval of about ±0.2, so this detects only the large effect
  seen on DEV.
