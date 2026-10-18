# Evaluation Extension Protocol (post-freeze, exploratory, AI-judged)

**Status.** Written and committed on 2026-10-18, **before** any annotation call of the extension. It is a
**post-freeze exploratory analysis**. It was designed after the original TEST evaluation, after the
multi-agent AI annotation in `docs/AI_ANNOTATION_RESULTS.md`, and in response to the tutor's feedback that the
main metric "only checks the strength label of one or two sentences on short synthetic cases". It was **not**
pre-registered before the original TEST evaluation and must not be described as such. The pre-registered H1–H3
analysis in `docs/PROTOCOL_FREEZE.md` is unchanged.

All new labels are produced by AI models. They are not human judgements, agreement between them is not human
inter-annotator reliability, and no human validated them.

## 0. What does not change

* No new backbone inference. The frozen DeepSeek V4 Flash outputs are scored as they are. (No OpenRouter key is
  configured in this environment, and the extension does not need new generations.)
* Frozen files are not edited: prompts, `src/`, configs, TEST gold, `benchmarks/freeze_manifest.json`,
  `evaluation/{auto_metrics,score_human,paired_bootstrap}.py`, the annotation guide.
* Existing AI annotations (`annotation/ai/`) and scores (`results/ai_scored/`) are read, never rewritten.
* Condition mappings stay in `private/` (gitignored). New opaque IDs for texts that had none (long-diagnostic
  outputs, real-paper outline drafts) are written to `private/extended/` only.
* The original metrics stay primary for H1–H3. Every new metric is reported next to them, never in place of them,
  and no composite score is formed.

## 1. Data in scope

| Set | Texts | Conditions | Unit of pairing |
|---|---|---|---|
| Synthetic TEST (`primary_v1`) | 122 distinct texts from 224 runs (all completed) | C1–C7 | case (32); matched pair (16) for sensitivity |
| Real papers (`real_v2`) | 39 distinct final texts from 46/48 completed runs, plus the 11 outline drafts that start C3/C4 | C1–C4 | paper (12; 11 where C3/C4 completed) |
| Long diagnostic (`diag_v2`) | 10 distinct texts from 24 runs | C7, C3, C4 | case (8) |

Shared-draft lineage (from the run records, `drafts[*]`): C7 = outline draft = starting draft of C3/C4/C5;
C1 = direct draft = starting draft of C2/C6. On real papers C3/C4 start from an outline draft that is not itself
a condition; it is annotated as a draft only. RP-02 has no outline draft (C3/C4 failed on truncation).

## 2. Annotation units and blinding

* **Sentence units.** Every distinct sentence (`final_sentences` or `drafts[*].sentences` of the run records) is
  one unit per case, with an opaque ID `U-<sha256(case, text)[:10]>`. Identical sentences in different texts are
  the same unit, so they get identical claims and labels by construction. This is what makes before/after
  comparisons of verifier edits exact for unchanged sentences.
* **What a judge sees.** The rendered research package (`src.render.render_package`, i.e. exactly what the writers
  saw), the distinct texts of the case under opaque labels in a seeded random order, and the sentence units.
  Synthetic cases use their existing aliases (`K01`…), diagnostic cases new aliases (`L01`…), real papers `RP-xx`.
* **What a judge never sees.** Condition identities or names (C1–C7, "verifier", "draft", "baseline"), run IDs,
  file paths, gold levels, gold decisions or justifications, focal propositions, level descriptors, the private
  mappings, other judges' labels (except the adjudicator, who sees anonymised readings), automatic results, or
  the original AI annotations. A leakage check (`evaluation/judges.py`) scans every prompt for these strings and
  refuses to send one that matches. Unit tests cover it.
* **Coverage judging** additionally shows a findings checklist (§6). For the long diagnostic it shows the
  descriptions of the private `required_findings` only (as the original pass-2 annotators saw for synthetic
  cases); never the gold level, gold decision or justification.
* **Isolation.** Judges run as separate processes in an empty scratch directory, with the whole input in the
  prompt. Judge B has every tool disabled. Judge A's event log is checked for shell commands; a judgment whose
  log shows any command execution is discarded and re-run once, and the count is reported.

## 3. Judges and provenance

| Role | Model (as reported by the CLI) | Interface and settings |
|---|---|---|
| Judge A: extraction, verification, coverage, alignment, checklist building | OpenAI GPT-5.6 (`gpt-5.6-sol`) | Codex CLI 0.153.4 `codex exec`, ephemeral, read-only sandbox, empty working dir, `model_reasoning_effort=high`, JSON-schema output. Sampling temperature is not user-settable. ChatGPT-subscription auth, so no per-call USD charge; tokens are logged |
| Judge B: independent verification, coverage, alignment, checklist review | Anthropic Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Claude Code CLI `claude -p`, `--tools ""` (no tools), no settings/MCP/session persistence, custom system prompt, JSON-schema output, CLI-default sampling. List-price cost is logged per call |
| Adjudicator | OpenAI GPT-5.6 (`gpt-5.6-sol`) in a separate adjudication role | As Judge A, `model_reasoning_effort=high`; sees the two readings anonymised as "Reading 1/2" in seeded random order |

Two different model families give the two independent readings. The adjudicator shares Judge A's family, so it
may prefer Judge A's readings. To make this visible, the share of adjudications that side with each judge is
reported. The adjudicator may answer `UNRESOLVED`; unresolved items are excluded from denominators and counted,
with best/worst-case bounds where they could change a conclusion. The orchestrating agent (Claude Code) builds
packets, runs code and computes metrics. It does not assign labels.

Every judgment is cached under `annotation/ai_extended/raw/<stage>/<judge>/` keyed by
`sha256(prompt, model, prompt version, settings)`. Each record stores the model ID reported by the CLI, prompt
file and its hash, settings, timestamps, token usage, cost (Judge B), the raw response and the parsed JSON.
Jobs are resumable and never re-run a cached key.

**Budget.** Extension spend on metered calls (Judge B) is capped at **$6.50** at list price, enforced in code
before each call (the task cap is $7). OpenRouter spend: $0 (no call). Codex usage is subscription-based and
reported in tokens.

## 4. Stages

1. **Checklist building** (real papers and long diagnostic; §6), frozen and committed before stage 4.
2. **Atomic claim extraction** (Judge A).
3. **Claim verification**, Judge A and Judge B independently, on the frozen claim set.
4. **Finding-coverage judging** (real + diagnostic), Judge A and Judge B independently.
5. **Edit alignment** (§8), Judge A and Judge B independently.
6. **Disagreement detection** (deterministic) and **adjudication** of every disagreement.
7. **Validation and freeze** of consensus files (`annotation/ai_extended/consensus/`, with sha256 manifest).
8. **Unblinding and scoring.** Condition identities and synthetic gold are read only here.

Labels are never changed after the freeze because a metric looks implausible. A discovered implementation bug is
fixed in code, documented, and the earlier result kept.

## 5. Metric definitions

Notation: for condition *c* and case *i*, a text *T(c,i)*; a missing or failed run has no text.

### 5.A Strict whole-passage success (existing AI labels only; synthetic TEST)

From `annotation/ai/consensus/consensus_synthetic.csv`, the private mapping, gold and rubric. No new judgment.

`complete_correct(c,i) = 1` iff all applicable checks pass:

1. **Focal strength** (24 ordinal cases): `ℓ̂ = ℓ`. As in `score_human.py`, `focal_addressed = no` gives
   `ℓ̂ = 0`, which is correct when `ℓ = 0`. Omitting the focal claim is therefore not penalised when ℓ = 0,
   provided check 2 holds.
2. **Coverage:** every rubric required finding is in `findings_covered`.
3. `unsupported_claims = 0`.
4. `numeric_errors = 0`.
5. NUM cases: every rubric numeric fact is in `num_facts_correct`.
6. NEG cases: every negative/null/mixed-polarity required finding is in `neg_findings_reported`.
7. NEG cases: `neg_reframed_positive = no`.
8. The run completed with a valid output.

Reported per condition over the 32 TEST cases, alongside its components: exact focal accuracy (n = 24),
unsupported-claim-free rate, numeric-error-free rate, complete-coverage rate (all required findings), and the
NUM/NEG checks (n = 4 each). **ITT** (primary): a missing run fails every check. **Completed-only** sensitivity:
missing runs dropped. (All 224 synthetic runs completed, so the two coincide; both are reported.)
A sensitivity variant replaces checks 3–4 with "no atomic error" from §5.B.

### 5.B Atomic claim evaluation (new AI annotation; synthetic, real, diagnostic)

**Extraction.** Each sentence unit is decomposed into atomic claims: the smallest propositions that can be true or
false separately, keeping the attribution, scope and qualifiers they carry in the text, never adding content.
"A significantly outperforms B on three datasets and cuts inference time by 20%" gives four claims (superiority;
significance of that comparison; scope of three datasets; 20% time reduction). Stored per claim: `claim_id`,
`unit_id`, `span` (verbatim substring), canonical `proposition`, `claim_type`, entities, metrics, datasets, units,
qualifiers/scope, and the `numbers` it asserts (each as written, value, unit, approximate flag, role).
Claim types: `result_value`, `comparison`, `statistical_significance`, `consistency_or_generality`, `robustness`,
`generalization`, `efficiency`, `citation_attribution`, `negative_or_null_result`, `trend_or_tradeoff`,
`causal_or_mechanistic`, `scope_or_caveat`, `method_or_setup`, `other`. **Result claims** are all types except
`scope_or_caveat` and `method_or_setup`.

**Verification labels.** Each judge assigns, from the package only, two separate dimensions plus a label:

* `entailment` ∈ {`ENTAILED`, `NOT_ENTAILED`, `CONTRADICTED`, `NA`}: whether the proposition as stated is
  true according to the package (factual entailment).
* `label` (calibration-aware, ignoring exact numeric values, which are checked deterministically):
  * `SUPPORTED`: entailed, and its certainty, scope and strength match the evidence.
  * `OVERSTATED`: the evidence supports a weaker statement in the same direction, but the claim's certainty,
    scope, generality, significance or magnitude wording goes beyond it ("significantly" without a valid test;
    "all datasets" when 4/5; "robust" beyond the tested range).
  * `UNDERSTATED`: weaker than the evidence establishes: unwarranted hedging of an established result, narrower
    scope than shown, or denying an established conclusion. Not reporting a stronger conclusion elsewhere is
    *not* an atomic understatement; that is measured by coverage.
  * `UNSUPPORTED`: no basis in the package, or contradicted in direction or attribution (fabricated finding,
    misattributed citation, causal explanation presented as a finding).
  * `NOT_VERIFIABLE`: not a factual claim about the package (recommendation, opinion, explicitly marked
    speculation, restatement of the question).
  * Allowed combinations: SUPPORTED⇒ENTAILED; OVERSTATED or UNSUPPORTED⇒NOT_ENTAILED or CONTRADICTED;
    UNDERSTATED⇒ENTAILED or CONTRADICTED; NOT_VERIFIABLE⇔NA.
* Also: cited evidence IDs, ≤ 40-word evidence-based justification, confidence (low/medium/high), error subtype,
  an extraction-quality flag (`OK`, `NOT_IN_TEXT`, `NOT_ATOMIC`, `DISTORTED`), and for each number its evidence
  mapping (§5.C).

**Final label** (deterministic): `NUMERIC_ERROR` if any of the claim's numeric assertions is incorrect under §5.C;
otherwise the consensus `label`. Claims whose extraction is confirmed invalid in adjudication are excluded and
counted. `NUMERIC_ERROR` is therefore never decided by a model's arithmetic.

**Metrics** (per condition, pooled over claims, with cases as resampling units):

* `assessable` = claims with final label ≠ `NOT_VERIFIABLE` (and not excluded/unresolved).
* **Atomic Claim Support Rate** = #SUPPORTED / #assessable.
* **Atomic factual error rate** = #(entailment ∈ {NOT_ENTAILED, CONTRADICTED} or NUMERIC_ERROR) / #assessable.
  Understatement alone is a calibration problem, not a factual error, unless it denies an established fact.
* Claim-level **overstatement, understatement, unsupported, numeric-error rates** = #label / #assessable.
* The same rates restricted to **result claims** (so that adding true caveats cannot inflate support).
* **Fully supported passage rate** = share of texts with ≥ 1 assessable claim and every assessable claim
  SUPPORTED. **Factually clean passage rate**: no factual error (understatement allowed).
* A text with zero assessable claims is **not** counted as fully supported: it scores 0 on passage rates, has no
  claim-rate contribution, and is listed. Content coverage is reported separately (§5.A coverage, §5.E recall).
* Also reported: assessable claims per text, NOT_VERIFIABLE share, extraction QC flags, unresolved count.

### 5.C Numerical fidelity (all sets)

**Assertions.** Every number in an extracted claim is a numeric assertion. Roles: `result` (a reported value),
`derived` (difference, ratio, percentage change, range end), `statistical` (p-value, CI, test statistic, df),
`cited` (a magnitude attributed to a cited passage), `count_outcome` (e.g. "4 of 5 datasets"), `setup`
(seeds, dataset sizes, model sizes). **Primary numeric metrics exclude `setup`** (reported separately).
Identifiers that only look numeric (model names such as "Llama3", metric names such as "nDCG@10", years in
citations) are not assertions.

**Mapping (AI, semantic).** Each judge maps every assertion to the evidence **that the text refers to** (its
entity, dataset, metric, comparison and direction), not to wherever the number happens to occur:
`source_type` ∈ {`cell`, `test`, `text`, `none`}; an arithmetic `expression` over evidence IDs (cells
`T1.r3.avg`, spreads `T1.r3.avg.spread`, tests `S1` / `S1.p_value` / `.statistic` / `.df` / `.n` / `.ci_low` /
`.ci_high` / `.alpha`), using `+ − × ÷`, `abs`, `min`, `max`, `mean`, `sum`, `count(…)` of comparisons; or a
verbatim `quote` from the package for numbers that only exist in prose; a unit `scale` from {1, 100, 0.01,
1000, 0.001}; and a `comparator` for bounds (`=`, `<`, `≤`, `>`, `≥`).

**Checking (deterministic, `evaluation/numeric_fidelity.py`).** The expression is evaluated on the package
values; the asserted value is compared after scaling. Tolerance = half a unit in the last displayed digit of the
asserted number plus half a unit in the last digit of the package value(s) involved (summed over operands for
derived values), plus 5% relative for numbers marked approximate ("about", "~", "roughly", "nearly").
A scale ≠ 1 is accepted only for a genuine unit change (%↔fraction, ms↔s, ×100 metric scales).
Verdicts: `CORRECT`; or an error typed as `VALUE_MISMATCH`, `MISATTRIBUTED` (the value matches a different cell,
test or derived quantity in the package but not the referenced one), `SIGN_OR_DIRECTION` (magnitude right, sign or
direction wrong), `UNIT_OR_SCALE`, `ARITHMETIC` (operands right, derived value wrong), `STAT_MISASSOCIATION`
(a statistic attached to a comparison it was not computed for), `FABRICATED` (no source anywhere); `INVALID_MAPPING`
(the mapping itself is unusable) goes to adjudication. `text` sources pass only if the quote occurs verbatim in the
rendered package and contains the value.

**Metrics.**

* **Numerical Precision** = #CORRECT numeric assertions / #numeric assertions (non-setup), pooled per condition;
  error types reported separately.
* **Numerical Recall** = #required numeric facts correctly reported / #required numeric facts. A required fact is
  correctly reported iff the text contains a CORRECT assertion whose expression uses the same evidence operands
  as the fact and whose value matches it within tolerance (absolute value for signed differences, after scale).
  Reference facts: synthetic TEST gold `numeric_facts` (64 facts in 16 cases; private, used only at scoring);
  real papers and long diagnostic: the numeric facts of the frozen package-only checklist (§6).
* Numerical F1 is a secondary diagnostic only; precision and recall are always shown separately, so a system that
  drops numbers cannot look ideal (recall falls).
* Also: numeric assertions per text, and numeric-error-free passage rate.

### 5.D Verifier repair effectiveness (edit analysis)

**Pairs.** Each final text is compared with its own starting draft: C3/C4/C5 vs C7 (synthetic); C2/C6 vs C1
(synthetic); C3/C4 vs the outline draft and C2 vs C1 (real); C3/C4 vs C7 (diagnostic). Texts from different
lineages are never matched.

**Alignment (AI).** Unchanged sentences share units, so their claims align trivially. For changed sentences
(verifier conditions) and for the whole text (C2, which rewrites everything), each judge aligns the draft's
claims to the final's claims, shown as "Version X / Version Y" without lineage or condition: each draft claim
is `UNCHANGED`, `REWORDED` (same meaning), `MODIFIED` (with direction `WEAKENED`, `STRENGTHENED`,
`NUMBER_CHANGED`, `SCOPE_CHANGED` or `OTHER`) or `DELETED`; unmatched final claims are `ADDED`.

**Outcome classes** (deterministic, from aligned final labels; error = OVERSTATED, UNDERSTATED, UNSUPPORTED,
NUMERIC_ERROR):

* An initial error is **corrected** if every aligned final claim is SUPPORTED, **removed** if the claim was
  DELETED, **retained** otherwise.
* A substantive edit (MODIFIED, DELETED, ADDED) is **beneficial** if it corrects or removes an error and
  introduces none; **harmful** if it introduces an error (correct→error, added erroneous claim) or deletes a
  correct claim that carried a required finding; **neutral** otherwise.

**Metrics** (pooled per condition; undefined, not 0 or 1, when the denominator is 0):

* Error repair recall = (corrected + removed) / initial errors; also the corrected-only version.
* Edit precision = beneficial / substantive edits. Harmful edit rate = harmful / substantive edits.
* Unnecessary weakening rate = WEAKENED edits of draft claims that were SUPPORTED / all WEAKENED edits.
* New errors introduced; new unsupported claims introduced; numeric errors fixed; numeric errors introduced;
  initial errors left unchanged (retained in sentences the system did not edit vs edited).
* Required findings lost after editing (covered in the draft, not in the final), from the coverage labels
  (existing AI labels on synthetic; §5.E on real and diagnostic).
* Verifier decisions (ACCEPT/WEAKEN/STRENGTHEN/REMOVE/FLAG) are counted from the traces. STRENGTHEN has never
  been observed; if this remains true it is reported, and zero strengthening is not read as evidence of
  bidirectional calibration (see `docs/H2_DIAGNOSTIC.md`).

### 5.E Real-paper (and long-diagnostic) finding completeness

**Checklist (§6)**, per output and item, each judge assigns `CORRECT` (the finding is stated with correct
direction, entity and scope; exact numbers are scored separately in §5.C, but a stated number must not change the
finding), `INCORRECT` (mentioned but misreported or mis-scoped) or `ABSENT`.

* **Real-Paper Finding Recall** = #CORRECT items / #items, pooled per condition, papers as resampling units.
* Negative-finding recall: items with polarity negative/null/mixed.
* Core-finding recall and **paragraph-level completeness** = share of texts covering every core item.
* Numerical-fact recall (§5.C), and unsupported-finding rate = UNSUPPORTED result claims / assessable result
  claims (§5.B).
* **Completeness versus readability:** per-text finding recall against the existing AI readability score
  (`annotation/ai/consensus/consensus_real_outputs.csv`), Spearman ρ (descriptive) and per-condition means.

The long diagnostic is scored against its private gold `required_findings` (primary, frozen before outputs
existed) and against the package-only checklist (secondary, which also supplies its numeric facts).

### 5.F Evidence-use efficiency (existing logs)

From the run records' `totals` and `claim_traces`: evidence-tool calls per verified claim and per text; model
calls; cost per text (USD, provider-reported, including the shared upstream draft); latency per text; **cost per
completely correct passage** = mean cost / complete_correct rate (undefined if the rate is 0); error repairs per
100 tool calls; **decisive-evidence retrieval** = share of verified draft claims with an error (verification
opportunities) for which the verifier's returned evidence IDs include every evidence ID the consensus judgment
cited (a cell counts as retrieved if it, its row or its table was returned); evidence precision = share of
returned table/test/passage items the consensus cited for that claim. Quality–cost comparisons (support rate,
complete-correct rate, numeric precision and recall vs cost and tool calls) with a Pareto plot.
Fewer tool calls is reported as an efficiency result only, never as evidence of better factual correctness.

## 6. Reference checklists (real papers and long diagnostic)

Built **from the package only**, before any output is judged against it:

1. Judge A receives one rendered package and returns 4–8 findings (main positive results, negative/null results,
   key comparisons, critical scope limitations where the package makes them central), each with a stable ID
   (`F1`…), description, polarity, kind, importance (`core`/`supporting`) and source evidence IDs; and 3–8 required
   numeric facts (headline numbers, not every cell), each with an expression over evidence IDs, value and unit.
2. Judge B reviews each item against the package (`VALID`, `UNSUPPORTED`, `TRIVIAL`) and may propose up to two
   missing core findings.
3. Deterministic merge: items Judge B marks `UNSUPPORTED` are dropped; proposed missing core findings with valid
   evidence IDs are added; numeric facts whose expression does not evaluate to the stated value are dropped.
   Every change is logged.
4. The authors' own Results sections (`private/real_papers/author_claims.jsonl`) and outside sources are not used.
5. The checklists and their sha256 are committed before stage 4.

## 7. Agreement and adjudication

Agreement (Judge A vs Judge B, before adjudication), always with raw agreement next to Cohen's κ: claim `label`
(6-way), `entailment`, numeric verdict (after deterministic checking of each judge's mapping), coverage status,
alignment relation. These measure AI–AI consistency only, not correctness. Every item where the judges differ
(or a mapping is invalid, or a judge flags an extraction problem) is adjudicated from the package alone. The
adjudicator returns a decision, a rationale citing evidence IDs, and may return `UNRESOLVED`.

## 8. Statistical analysis

* **Synthetic:** cases are the paired units (n = 32, or the applicable subset: 24 ordinal, 16 with numeric facts,
  4 NUM, 4 NEG). Paired case bootstrap, 10,000 resamples, seed 4213, 95% percentile intervals. Matched-pair
  cluster bootstrap as sensitivity. Claim-pooled rates are bootstrapped as ratios of sums over resampled cases.
* **Real papers:** papers are the units; sentences or claims within a paper are never treated as independent.
  Completed-only paired contrasts use the common completed set (11 papers when C3 or C4 is involved, 12 otherwise).
  Failure-inclusive (ITT) results are reported separately: a failed run counts as recall 0 and passage success 0
  and contributes no claims.
* **Long diagnostic:** 8 cases, descriptive with case-bootstrap intervals.
* **Planned comparisons** (first minus second): C4−C2, C4−C1, C4−C3, C4−C5, C4−C7; plus the draft-lineage
  contrasts C3−C7, C5−C7, C2−C1, C6−C1. On real papers: C4−C2, C4−C1, C4−C3, C3−draft, C4−draft, C2−C1.
* For each metric: definition, denominator, n, per-condition value, paired difference, 95% CI, missing-data
  policy, and the number of discordant cases (a−better / b−better / tied). An interval of [0, 0] produced by
  identical labels is flagged as *degenerate* and is not read as evidence of equivalence.
* No multiplicity correction is applied and nothing is called significant: every comparison is reported, all
  results are exploratory and descriptive, and intervals are interpreted as uncertainty ranges. The original
  pre-registered H1–H3 outcomes stay as reported in `docs/AI_ANNOTATION_RESULTS.md`.

## 9. Experiments

1. Strict complete-and-correct rates for C1–C7 (§5.A).
2. Atomic claim support on synthetic, real and diagnostic texts (§5.B).
3. Numerical precision and recall with deterministic checks (§5.C).
4. Verifier repairs and damage (§5.D).
5. Real-paper completeness and its relation to factual correctness and readability (§5.E).
6. Long-package stress test on the existing diagnostic outputs (§5.B–5.F). It is exploratory and is not held-out
   validation: the cases were designed after the DEV pilots.
7. Efficiency and quality–cost trade-offs (§5.F).

## 10. Limitations fixed in advance

AI judges may share errors, and the adjudicator belongs to Judge A's family. There is no human validation.
The focal-label metric has a ceiling effect, which is why these metrics were added, and the new metrics were
chosen after seeing the first results. Samples are small (32/24/16/4/4 synthetic cases, 11–12 papers, 8 long
cases). One backbone. Judge B is not deterministic. Extraction is single-source (Judge A), so its granularity
affects claim counts; result-claim and passage-level metrics are reported to limit that effect.

## 11. Amendments made before any annotation call

1. **Numeric tolerance (§5.C).** Package values are treated as exact as displayed, because they are the evidence
   the writer saw; a derived value is checked against the arithmetic on displayed values. The tolerance is half a
   unit in the last digit of the *asserted* number, plus 5% relative when the text marks the number as approximate.
   The earlier wording also added the package values' rounding, which would accept arithmetic slips (for example
   "4.8" for 40.7 − 36.0 = 4.7). Synthetic gold facts keep their own stated tolerances for recall matching.
2. **Comparator (§5.C).** Whether a number is a bound ("p < 0.05", "more than 20%") is recorded once at
   extraction, as a property of the text, instead of separately in each judge's mapping.
3. **Error subtype of agreed numeric errors.** When both judges' mappings give an error, the claim is a numeric
   error either way; the error *type* reported is the one from Judge A's mapping.
4. **Synthetic case IDs in prompts.** Synthetic packets use the existing `K` aliases; diagnostic packets use `L`
   aliases from a seeded shuffle. Real papers keep `RP-xx`.
5. **Pilot-based changes (2026-10-18, before the main verification, coverage and alignment runs).** A pilot on
   one synthetic case (K05) and one real paper (RP-08) led to these changes; pilot judgments made with superseded
   prompts are kept for spend accounting only and are not used.
   * Extraction: a separate scope claim is emitted only when it asserts something no other claim from the same
     sentence asserts (the pilot produced duplicates such as "the comparison covers every collection" next to
     "A outperformed B on every collection", which would double-count generality errors).
   * Verification: both `entailment` and `label` explicitly ignore exact numeric values, which are checked by code
     (in the pilot one judge penalised a wrong number in the label, creating avoidable disputes). Justifications are
     limited to 25 words. Claims of one case with the same proposition and the same numbers are verified once and
     the reading is copied (`copied_from` is recorded). Prompts use short local IDs (`c1`, `c1.n1`), mapped back in code.
   * Judge B model: the metered cap does not cover Sonnet 5.5 everywhere (pilot cost per synthetic case: Sonnet
     $0.12, Haiku 5.5 $0.012; both agreed with Judge A on 43/43 and 42/43 pilot labels, with 0/62 numeric disputes).
     Judge B is therefore **Claude Sonnet 5.5 for real-paper and long-diagnostic verification and coverage**, and
     **Claude Haiku 5.5 for synthetic verification and for all alignment**. Agreement is reported per family with
     the model named. Judge B returns plain JSON that is validated locally against the same schema (the CLI's
     structured-output mode made the model emit the object twice).
   * Label/entailment disputes on a claim that is already a numeric error under agreed numeric verdicts are not
     adjudicated, because they cannot change any metric; Judge A's value is kept and the claim is marked.
6. **Checklist merge outcome.** The deterministic merge (§6) dropped numeric facts whose expression did not resolve
   to package values (for example an invented key `T1.r1.jga.avg`, or a parenthetical gain misread as a spread);
   L06 keeps 2 numeric facts and RP-09 keeps 5. Reviewer-proposed core findings were added for 15 of 20 packages and
   reviewer-rejected findings were dropped for 3 diagnostic packages. Every change is in each checklist's `merge_log`.
7. **Checker fixes found while inspecting disputes (2026-10-18, before any consensus was frozen or scored).**
   Inspection of the first disputed and agreed numeric errors showed three implementation defects in
   `evaluation/numeric_fidelity.py`, fixed in code with unit tests; no label was edited by hand.
   * Numbers written as words in quoted prose ("four held-out collections", "a single training run") were not
     recognised, so correct counts were reported as value mismatches. Number words are now parsed.
   * A count written only as a word whose quoted prose states no count at all ("a single dataset", where the package
     just names one dataset) cannot be checked deterministically; it is now marked not checkable (excluded from
     numeric metrics; the judges' qualitative label still covers the claim). Digit-written numbers, and word counts
     whose quote does state a count, are still checked strictly.
   * Quotes copied from the rendered package without its markdown backticks did not match verbatim; quote matching
     now ignores backticks and bold markers. A "± x" shown in a cell's text without a structured spread field now
     resolves as that cell's `.spread`.
   Adjudication was re-run for the cases whose dispute sets changed; earlier adjudication records are kept under
   `annotation/ai_extended/raw/_superseded/`.
8. **Judge B cost reservation.** The budget guard reserved $0.75 per in-flight Judge B call, which refused real-paper
   coverage calls at $4.33 actual spend. Reservations (and the CLI's own per-call cap) are now $0.75 for verification
   and $0.25 for coverage, alignment and checklist review; the $6.50 total cap is unchanged.
9. **Scoring refinements made after first scoring (2026-10-18; post hoc, applied identically to every condition).**
   * *Required-fact matching.* Some checklist numeric facts are aggregates (e.g. the best score as `max` over rows).
     A passage that states the attaining cell's value was not credited because its evidence set differed from the
     fact's. A correct assertion now reports a fact when its evidence is a subset of the fact's evidence and its value
     matches. This changed real-paper numeric recall from 0.18–0.19 to 0.21–0.24 for all conditions alike.
   * *Harmful deletions.* The first implementation marked every deleted correct claim as harmful whenever its run lost
     any required finding (30 harmful deletions against 4 lost findings for real-paper C2). Each lost required finding is
     now attributed to at most one deleted correct claim; the rest count as neutral. This affects only C2, whose
     real-paper harmful-edit rate fell from 0.31 to 0.15.
   No label, checklist or claim was changed. Both rules have unit tests.
10. **Fixes from an independent code review (2026-10-18, after the first consensus commit `dba147b`).** A read-only
    review of the extension code found implementation defects; all are fixed in code with unit tests, and no AI
    judge reading was edited. The earlier consensus remains in git history.
    * A derived quantity the package itself prints (e.g. a gain shown as "22.51 (2.33 ↑)") was scored as an
      arithmetic error when the writer quoted it; it is now accepted when it equals the derived quantity up to the
      package's own display rounding. Parenthetical numbers that a caption declares to be standard deviations now
      resolve as `.spread`.
    * A number mapped to "no source" that is an implicit word count or a bound is now not checkable (as in amendment 7)
      instead of being searched against all evidence, which had matched "single" to any value near 1.
    * Scientific notation now gets its true display precision. Stated bounds are compared without rounding slack
      (equality is accepted, since texts restate thresholds such as "p < 0.05"), and years in quoted prose cannot
      satisfy a bound.
    * Smaller fixes: the unit-scale error window; gold facts whose written derivation cannot be tied to unique cells are
      matched on value; the degenerate-interval flag now requires a zero difference and a collapsed interval; unresolved
      edit outcomes leave the repair denominator; no failure-inclusive value is reported for the misreported share; F1 is
      0 (not undefined) when precision or recall is 0; the leakage check now applies its strict patterns to model-written
      text as well (only the package is exempt).
    * Effect on the frozen consensus: 2 synthetic and 15 real-paper claims changed from NUMERIC_ERROR to SUPPORTED;
      2 real-paper claims changed from SUPPORTED to NUMERIC_ERROR (re-adjudicated number mappings). Four real-paper cases
      had to be re-adjudicated because their disputes changed; in those cases the adjudicator
      reproduced 4 of 9 earlier label decisions and 24 of 27 number-mapping choices, which changed 5 further labels.
      All results and documents were regenerated from the corrected consensus.
11. **Adjudicator test–retest (specified 2026-10-18, before the replicate run; exploratory).** Re-adjudication of four
    real-paper cases after amendment 10 suggested that the adjudicator's label decisions are unstable. To measure this
    on the full set, every claim, coverage and alignment adjudication prompt is re-asked once, **verbatim**, to the same
    adjudicator (GPT-5.6 via Codex CLI, reasoning effort high); only the cache key carries a salt (`replicate=r1`), so
    no cached answer is reused. No Claude call is made. The replicate writes only under
    `annotation/ai_extended/replicates/r1/`; the primary adjudication, consensus and results are not changed.
    Reported (`evaluation/adjudicator_stability.py`, `results/ai_extended/adjudicator_stability.json`):
    * per-field agreement between the two adjudications of the same disputed items (label, entailment, extraction
      validity, number-mapping choice, coverage status, alignment relation), as raw agreement and Cohen's κ, with
      the changed decisions listed;
    * the number of final consensus labels, numeric verdicts and coverage statuses that differ when the replicate
      adjudication is used;
    * every planned contrast re-scored from the replicate consensus with the same bootstrap (10,000 resamples, seed
      4213), and whether its sign or its exclusion of zero changes.
    The primary results remain the reported ones; the replicate is a sensitivity analysis. Agreement here is AI–AI
    test–retest of one model, not human reliability.
12. **Third judge family and 2-of-3 majority (specified 2026-10-18, before any Judge C call; exploratory).** An
    OpenRouter key became available after the main analysis. A third judge, **Judge C = Qwen 3.7 Plus**
    (`qwen/qwen3.7-plus`, Alibaba, served first-party), re-verifies every claim with the identical verification
    prompt and schema used by Judges A and B (same blinded packets, same de-duplication and local IDs), through the
    project's own OpenRouter client and cost guard: temperature 0, seed 4213, reasoning disabled (the project
    convention), JSON-schema output, `require_parameters` routing. Spend is logged in `outputs/cost_ledger.jsonl` under
    a new stage `eval_ext` whose cap is **$1.78** (the room left under the extension's $7 limit after $5.22 of metered
    Claude calls). DeepSeek models are not used as judges because a DeepSeek model is the system being evaluated.
    One synthetic case (K05) is run first to confirm valid output and cost; its prompt is identical to the main run, so
    the pilot call is reused, and the settings above are not changed afterwards unless the output is invalid.
    Analysis (`evaluation/majority_vote.py`, `results/ai_extended/majority_vote.json`), unchanged primary results:
    * agreement of Judge C with Judges A and B (raw, Cohen's κ) and Fleiss' κ over the three judges;
    * on items the A–B adjudication decided, how often Judge C agrees with the adjudicator's decision, split by
      whether the adjudicator sided with Judge A (its own model family) or Judge B;
    * a **2-of-3 majority consensus** with no adjudicator: label and entailment by majority of A, B, C; each number by
      majority of the three deterministic verdicts (correct vs error) among usable mappings; where no majority exists,
      the primary adjudicated decision is kept and the count reported;
    * every planned contrast re-scored from the majority consensus and from Judge C alone, with the same bootstrap,
      reporting sign and zero-exclusion changes. Finding coverage and alignment are not re-judged.
