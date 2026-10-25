# Phase 4 design: held-out capability test (Part A) and retrospective natural-draft study (Part B)

**Status: DESIGN for review (2026-10-25). Nothing in this document has been generated, frozen or run.**
The selected V2 verifier is **D1-tools** (`v2/verifier_tools.py`, variant `D1`, 800 tokens per turn). It is not changed
for the primary evaluation.

## 0. Questions and what each part can answer

V1 never strengthened. E1–E5 point to three possible explanations:

* **A. Evidence acquisition:** the verifier cannot find the evidence for a stronger claim. On the DEV probes, the
  decisive evidence was retrieved in 33 of 36 runs, so this is not the main bottleneck there.
* **B. Decision framework:** the verifier sees the evidence but accepts a weak claim. D1 fixes most of this on DEV.
* **C. Opportunity scarcity:** natural drafts rarely understate. The V1 AI labels already suggest this.

| | Part A: held-out capability test | Part B: retrospective natural-draft study |
|---|---|---|
| Question | Does D1's fix of B generalise to new evidence types and phrasings? Does strengthening add value over the same verifier without it (C5)? Are calibrated claims preserved? | How often do natural V1 outline drafts contain same-proposition understatement (C)? On those drafts, does V2 change calibration, and does it introduce harmful edits? |
| Data | New, frozen synthetic items: packages + common starting drafts with gold | Frozen V1 packages and the naturally generated **shared outline drafts** that started V1 C3/C4/C5/C7 |
| Can support | Verifier capability on controlled single-sentence and short-paragraph drafts; correct and false strengthening; overstatement correction; revision quality | The natural prevalence of strengthening opportunities; V1-vs-V2 behaviour and side effects on real writer output |
| Cannot support | How often opportunities arise naturally; end-to-end writer-to-verifier quality; real-paper performance; other backbones | An independent held-out test (these data were examined during V1, and V2 was designed after V1's results); a precise strengthening accuracy (too few opportunities) |

Neither part is a complete pipeline evaluation. Both evaluate the **verifier on fixed starting drafts**.

## 1. Part A: benchmark composition

### 1.1 Matched scenarios

There are **12 new matched scenario pairs (24 packages)**. They are written in the V1 package schema
(`src/package_schema.py`, authored as `benchmarks/schema.AuthoredCase`). Each pair differs in **one declared evidence fact**.
All names, datasets and numbers are new; the reuse of DEV names or values is checked automatically.

| # | Proposition type | Strong member (supported level 2) | Partner | New relative to DEV? |
|---|---|---|---|---|
| 1 | Significance via confidence interval | paired 95% CI for the difference excludes 0 (no p-value) | CI includes 0 → level 0 | yes (CI-only evidence) |
| 2 | Significance after a multiple-comparison correction | adjusted p < α | raw p < α, adjusted p > α → level 1 | yes |
| 3 | Consistency across languages | wins on all 8 languages | 7 of 8 → level 1 | partly (new unit) |
| 4 | Consistency with ties | strictly better on all 5 tasks | one tie → level 1 | yes (ties) |
| 5 | Direct measurement: memory | peak memory measured on a shared setup | only the parameter count is reported → level 1 | yes |
| 6 | Direct measurement: throughput | same hardware and batch size | different batch sizes → level 1 | partly (new trap) |
| 7 | Robustness over severity | criterion met at all 4 corruption severities | fails at the highest → level 1 | partly |
| 8 | Cross-lingual generalisation | better on 3 held-out languages | only 1 held-out language → level 1 | partly (new domain type) |
| 9 | Citation magnitude | the passage states a specific effect size | the passage states the direction only → level 1 | partly |
| 10 | Negative result (the method is worse) | significantly worse (valid test) | worse, no test → level 1 | **yes (strengthening a negative)** |
| 11 | Monotonic trend | gain at every model size tested | non-monotonic → level 0 | yes |
| 12 | Non-inferiority | CI lies within a pre-specified margin | no margin or test → level 0 | yes |

Pairs 1–10 have a level-1 partner and pairs 11–12 a level-0 partner. Two further level-0 partners are chosen at
authoring time, so that 4 pairs have a level-0 partner. The exact allocation is fixed in the case specification before
authoring.

### 1.2 Draft items (single sentence)

Each pair gets **U** and **U2**: two understated drafts of the **same proposition** at level 1, using *different*
linguistic patterns. It also gets **S**, the strong form at level 2. Each draft is placed on both members. A level-0
partner additionally gets **Z**, a correct "not established" statement.

| Draft | Strong member (gold 2) | Partner with gold 1 | Partner with gold 0 |
|---|---|---|---|
| U, U2 (level 1) | **STRENGTHEN** (24) | ACCEPT (16) | REMOVE/WEAKEN (8) |
| S (level 2) | ACCEPT (12) | WEAKEN (8) | REMOVE/WEAKEN (4) |
| Z (level 0) | none | none | ACCEPT (4) |

That gives **76 single-sentence items: 24 STRENGTHEN, 32 ACCEPT and 20 WEAKEN/REMOVE.** Understatement patterns are
balanced across pairs, and at least half are **not used in DEV**:

* "preliminary evidence", "a trend toward", "tentatively";
* litotes ("not worse than");
* "in several settings";
* "comparable or better";
* a double hedge.

Some patterns **need no statistical test**, for example "appears to use less memory" when peak memory was measured.
These target the "no test, so keep the hedge" failure seen in E5.

**Excluded by construction:** scope broadening (a sentence that states only a sub-claim) and omitted findings. The
validator checks that each U/U2 draft states the same proposition as S.

### 1.3 Paragraph items (multi-sentence), descriptive

There are **8 three- or four-sentence paragraphs** on strong members, about 28 sentences in total. Each contains:

* one understated sentence (gold STRENGTHEN);
* one or two calibrated context sentences (gold ACCEPT);
* in 3 of the 8, a sentence that **already states the strong form**. In these, the understated sentence either restates
  it with a hedge (a redundancy trap) or concerns another proposition.

Measured: the per-sentence decisions, and side effects (duplicated strong claims, over-broad claims, contradictions
between sentences). Gold for the redundancy traps needs a rule (risk R4).

### 1.4 Size

That is 76 + about 28 = **about 104 sentence verifications per condition and repeat**. With 3 conditions × 3 repeats,
that gives about 936 runs. With 24 STRENGTHEN items, a 0.80 rate has a 95% interval of about ±0.16. 0 false
strengthenings in 52 non-STRENGTHEN items bounds the rate below about 0.06. This is enough to separate the conditions
by the large margins seen on DEV, not to rank small differences.

## 2. Part B: exact V1 artifacts to reuse

| Set | Starting drafts (withheld unless noted) | Units | Frozen V1 labels reused |
|---|---|---|---|
| B1 synthetic TEST | `outputs/synthetic/deepseek__deepseek-v4-flash-0731/_shared/<32 TEST cases>/outline.json` (the drafts behind V1 C3/C4/C5/C7) | 32 drafts, 103 sentences (V1 C4 verified 103) | Atomic-claim consensus for C7 = outline draft (`annotation/ai_extended/consensus/synthetic_claims.jsonl`); AI focal annotation (`annotation/ai/consensus/`) |
| B2 real papers | `outputs/real_papers_v2/deepseek__deepseek-v4-flash-0731/_shared/RP-xx/outline.json` (11 papers; RP-02 has no outline) | about 43 sentences (V1 C4 verified 43) | `real_claims.jsonl` for the outline draft |
| B3 long packages | `outputs/diagnostic/deepseek__deepseek-v4-flash-0731/_shared/LONG-*/outline.json` (**available locally**) | 8 drafts, 32 sentences | `diagnostic_claims.jsonl` for C7 |
| Packages | `data/synthetic/test.jsonl`, `data/real_papers/`, `data/diagnostic/long.jsonl` (public) | | |
| Linking texts to labels | `private/extended/` registry and `private/condition_mapping*.csv` (coordinator only) | | |

**Needed from the coordinator (Lai Zheyuan):** the withheld `outputs/synthetic/`, `outputs/real_papers_v2/` and `private/`.
On receipt, every file is checked against the SHA-256 in `outputs/WITHHELD_UNTIL_ANNOTATION.json` and
`benchmarks/freeze_manifest.json`. Only the `_shared/*/outline.json` files and the registry are read. Without these
files, Part B reduces to B3 (8 drafts).

DEV drafts (`outputs/dev_pilot*/`) were used for tuning and are **not** used in Part B.

### 2.1 B-prevalence (no new model calls)

* **Unit.** The rate of same-proposition understatement is the share of **outline-draft atomic claims** labelled
  UNDERSTATED in the frozen V1 consensus, per set. The V1 judge definition already excludes "not mentioning a stronger
  conclusion elsewhere", which matches V2's same-proposition notion.
* **Already published V1 figures.** Synthetic: 0–1 understated claims per condition. Real outline drafts: 0.015 of
  202 claims.
* **Focal level.** For B1 it is reported from the V1 focal annotation: C7 had no understatement.
* **Limitation.** These are AI labels (AI–AI κ 0.56–0.65), so the figure is an estimate.

### 2.2 B-verification

V1 C4 and V2 C4 (section 3) run on **identical** natural drafts, with 3 interleaved repeats. A sentence the verifier
leaves unchanged keeps the frozen V1 consensus label of that draft sentence, because the text is identical. **Only edited
sentences are newly judged** (section 5). V2 C5 is not run in Part B. Whether STRENGTHEN matters there can be read
directly from V2 C4's STRENGTHEN edits and their judged quality.

## 3. Conditions and paired comparison

| Condition | Code | Prompt and schema | STRENGTHEN |
|---|---|---|---|
| **V1 C4** | V1 `src.verifier.verify_draft`, unchanged (as `D0-tools-800`) | V1 adaptive prompt and schema | allowed (never used in V1) |
| **V2 C4** | `v2.verifier_tools.verify_draft_tools`, variant D1 (unchanged) | V1 adaptive prompt + D1 addendum; D1 schema | allowed |
| **V2 C5** | same port, D1 with STRENGTHEN disabled | as V2 C4, except the mapping line, which becomes "STRONGER_SUPPORTED → ACCEPT (strengthening is not available)"; V1's existing no-strengthen note is appended automatically | removed from the allowed set |

All three conditions share the same backbone, decoding, routing, 4-call tool budget, 6-claim cap, 800 tokens per turn,
evidence index, starting draft and package. V2 C5 needs **one new prompt file** that differs from the D1 addendum in a
single line (risk R1). Its decision schema is D1's, with STRENGTHEN removed from the enum.

**Batching.** Parts A and B are each run as **one batch**, interleaved by repeat, item and condition, with 3 repeats.

**Primary analysis unit.** The run, clustered by item. Rates are the per-item mean over repeats, averaged over items.
Majorities are secondary. Raw per-run decisions are always shown.

**Paired contrasts.** V2 C4 − V1 C4 (does the decision framework help?) and V2 C4 − V2 C5 (does strengthening add
value?). Both use the paired cluster bootstrap over scenario pairs (`evaluation/paired_bootstrap.cluster_bootstrap`,
10,000 resamples). Raw counts are always reported, and nothing is called "significant".

## 4. Generation, validation and freezing (Part A)

The V1 workflow is reused: author → independent validation → deterministic checks → freeze → inference → blinded AI
annotation → scoring.

| Step | Who / what | Separation |
|---|---|---|
| 1. Case specification | Coordinating agent writes `v2/docs/PHASE4_CASE_SPEC.md`: the scenario table, level descriptors (BENCHMARK_SPEC style), linguistic-pattern quotas and draft rules | It does **not** mention D1, the DEV probes or E1–E5 failure details beyond the categories above |
| 2. Authoring | **GPT-5.6 via Codex CLI** (V1 judge backend, fresh read-only sandbox). Inputs: the spec, the V1 package schema and the non-benchmark example `docs/benchmark_example_case_NOT_IN_BENCHMARK.json`. Outputs: packages + drafts + gold (expected decision, levels, decisive evidence IDs, pattern label) | The author never sees the D1 prompt, the DEV probes or any verifier output |
| 3. Deterministic checks | `benchmarks.validate.check_case` (test statistics, p/CI consistency, evidence IDs, rubric-leak patterns) plus new V2 checks: (a) the two packages of a pair differ only in the declared fields; (b) every number in a draft matches a cell (`evaluation.numeric_fidelity`); (c) decisive IDs resolve; (d) no DEV name or number reuse; (e) pattern and decision quotas | Code only |
| 4. Blind validation | **Claude Sonnet 5.5** via the V1 claude backend (all tools off). It sees only package + draft and outputs: same proposition as the strong form (yes/no), the strongest supported statement, the relation, and the expected decision | It does not see the gold. Disagreements go back to the author once and are then re-validated. Still unresolved → **dropped**, and the number dropped is reported |
| 5. Optional student spot check | 12 random items with their gold | Recorded separately from the AI validation |
| 6. Freeze | Public items in `v2/benchmarks/test_v2/`, gold in `v2/private/` (gitignored); `v2/benchmarks/freeze_manifest.json` hashes the items, the gold, the D1/C5 prompts, `verifier_tools.py`, the runner, the analysis and judge prompts, and this design. Committed **before any TEST inference** | No verifier has seen a TEST item before the freeze |

**Stop rule before freezing:** if more than 25% of items are dropped at validation, the spec is revised and the authoring
repeated. This is never done after inference. **After freezing, no prompt, code, item or scoring rule changes.** Any
deviation is logged with a date, as in V1.

## 5. Metrics and economical AI judging

### 5.1 Metrics

**Part A, primary** (from the frozen gold; no judge needed for decisions):

1. **Correct strengthening rate** on the 24 understated items: STRENGTHEN chosen, and the revision judged SUPPORTED with
   no numeric error.
2. **False strengthening rate** on the 52 non-understated items.
3. **Overstatement correction** on the 20 overstated items: WEAKEN/REMOVE, with a non-overstated result.
4. **Control preservation** on the 32 calibrated items: ACCEPT, or an edit judged SUPPORTED. Edits that make a
   calibrated item wrong count as **harmful edits**.

**Part A, secondary:**

* final-sentence calibration distribution (supported / overstated / understated / unsupported);
* factual and numeric errors introduced by revisions;
* breakdown by pattern (seen vs unseen in DEV) and by proposition type;
* paragraph side effects;
* decisive-evidence retrieval and failure stages F0–F3 (agent coding, indicative);
* tool calls, cost and latency per run.

**Part B:**

* prevalence (2.1);
* per-condition edit rate and decision mix;
* STRENGTHEN edits and their judged quality;
* **harmful edits** (a draft claim judged SUPPORTED becomes an error);
* repairs (a draft error becomes SUPPORTED);
* net support change;
* new numeric errors;
* cost and latency;
* V2 C4 − V1 C4, paired by draft with the bootstrap over cases.

### 5.2 Judging workflow

A simplified version of V1 evaluation-extension sections 3–7, reusing `evaluation/judges.py`, `extended_pipeline.py`,
`numeric_fidelity.py` and `edit_analysis.py`:

* **What is judged.** Only **distinct revised sentences**, deduplicated across conditions and repeats. Unchanged
  sentences take their gold (Part A) or frozen V1 label (Part B).
* **Packets.** Blinded: package plus opaque sentence IDs, with no condition, run tag or gold. V1's `check_leakage` is
  enforced.
* **Extraction.** Atomic claims by Judge A, as in V1, so Part B labels have the same granularity as the frozen ones.
* **Two judge families.** Judge A is GPT-5.6 (Codex) and Judge B is Claude Haiku 5.5, the V1 rule for synthetic text;
  real and long packages use Sonnet 5.5. Both use the **unchanged V1 `verify.md` prompt**, whose labels are exactly
  SUPPORTED / OVERSTATED / UNDERSTATED / UNSUPPORTED.
* **Adjudication.** A separate GPT-5.6 role, blind to which judge said what, resolves disagreements.
* **Numbers.** Checked by deterministic code from the judges' evidence mappings.
* **Not repeated from V1:** checklist coverage, test–retest of the adjudicator, a third-family majority vote, and
  passage-level success metrics.
* **V2-specific separation.** A V2 raw directory and V2 budgets. V1's `CLAUDE_BUDGET_USD` already counts $5.22 of V1
  spend, so V2 must not share it.

## 6. Runtime and cost (from actual logs)

**Experiments on OpenRouter** (V2 ledger, new stage `v2_phase4`, hard cap $2.00; key balance $13.6):

| Run | Units | Basis | Estimate |
|---|---|---|---|
| Part A | 104 × 3 conditions × 3 repeats = 936 runs | E5: $0.368–0.381 per 1,000 runs (D0-tools-800 / D1-tools); about 4.7 s per run with 2 workers | about **$0.40**, about 75 min |
| Part B, B1 | 103 × 2 × 3 = 618 runs | as E5 | about $0.24, about 50 min |
| Part B, B2 | about 43 × 2 × 3 = 258 runs | larger packages, assumed about $0.0006 per claim | about $0.15, about 35 min |
| Part B, B3 | 32 × 2 × 3 = 192 runs | V1 long C4: $0.0005 per claim, 8.5 s per claim | about $0.10, about 25 min |
| **Total** | about 2,000 runs | | **about $0.9, about 3 h** |

**AI judges and authoring** (separate accounting, not on the OpenRouter ledger):

* Codex / GPT-5.6 for authoring, extraction, Judge A and adjudication: subscription, no per-call charge. Expect about
  1–2 h of wall time (V1: 42 s per verify batch of about 28 claims).
* Claude for validation (Sonnet, about 104 items) and Judge B (Haiku/Sonnet, about 250–400 distinct revised sentences):
  by V1's rate (about $0.065 per verify batch of about 28 claims), roughly **$1–2 at list price**. Hard cap $4.

**Implementation, in order:**

1. Case spec and this design committed.
2. V2 C5 prompt line and tests.
3. Authoring and validation wrappers around `evaluation.judges` (V2 prompt dir, raw dir and budget).
4. V2 deterministic checks.
5. Authoring and validation runs, then reconciliation.
6. Freeze.
7. Part B data intake and integrity check, and the prevalence script.
8. Part A and Part B inference.
9. Judging pipeline.
10. Scoring and the report section.

Estimate: about 1–1.5 days of engineering plus the compute times above. Checkpoints with the students come after
step 1, after step 6 (before any TEST inference) and after step 10.

## 7. Risks and ambiguities to resolve before the TEST run

* **R1. V2 C5 policy.** STRONGER_SUPPORTED → ACCEPT is proposed. The alternative is to let C5 keep its judgement fields
  but force ACCEPT in code. The prompt version is simpler and mirrors V1's C5.
* **R2. Separation and leakage.**
  * The coordinating agent designed D1 and writes the case spec. The spec must stay at the level of categories and
    rules.
  * GPT-5.6 is both author and Judge A. This mainly affects the secondary judged metrics, because the primary decision
    metrics use the validated gold. An alternative assignment is author = Claude Sonnet and validator = GPT-5.6. Either
    way the overlap is documented.
  * The validator is a third role, Claude Sonnet, with no V2 context.
* **R3. The operational definition of "same proposition".** Example: is "lower memory" the same proposition as "fewer
  parameters"? The spec gives explicit rules and examples, and the validator applies them.
* **R4. Paragraph gold.** A hedged restatement of a strong claim made earlier in the same paragraph: is ACCEPT, REMOVE or
  a non-duplicating STRENGTHEN correct? Proposed: acceptable = {ACCEPT, REMOVE}. A STRENGTHEN that duplicates the earlier
  claim counts as a side effect, not an error. Paragraph results are descriptive.
* **R5. Part B access.** The coordinator must provide the withheld outputs and `private/` (section 2). Without them, only
  B3 remains.
* **R6. Few natural opportunities.** Prevalence is expected to be about 0–2% of claims, so Part B mainly tests **side
  effects**, not strengthening accuracy. This is stated in advance.
* **R7. Inference variability.** Single interleaved batches with 3 repeats, run-level metrics and no seed or temperature
  changes. If the provider changes mid-batch, the provider is recorded and reported. Five repeats instead of three would
  cost about $0.25 more; three are proposed.
* **R8. AI-only labels.** Gold validity rests on AI authoring plus AI validation plus deterministic checks; output labels
  rest on two AI families plus adjudication. These are not human judgements. The optional student spot check is the
  only human element.
* **R9. Token setting.** Part B's V1 C4 runs at 800 tokens per turn, not V1's frozen 450. The frozen V1 C4 outputs are
  reported only as context. No V1 truncation at 450 was found.
* **R10. Real-paper verification cap.** Unchanged V1 settings: at most 6 claims verified per passage, and at most 5
  sentences written.

## 8. Recommendation

Proceed with Part A as specified (76 single-sentence items + 8 paragraphs; V1 C4 / V2 C4 / V2 C5; 3 interleaved
repeats) and with Part B on B1–B3, provided the coordinator supplies the withheld files.

Decisions requested before implementation:

1. R1 (C5 policy);
2. R2 (author/validator model assignment);
3. R4 (paragraph gold rule);
4. R5 (data access);
5. 3 vs 5 repeats;
6. whether a student spot check of 12 items will be done.
