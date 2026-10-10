# Evidence-Calibration Benchmark — Design Specification and Gold Rules

This is the public specification of the 48-case synthetic benchmark. It records the
**rules** used to assign gold labels. The TEST-split gold labels are kept private to the
project coordinator until blind human annotation is finished; their SHA-256 is frozen
in `benchmarks/freeze_manifest.json`. All method, dataset, author and paper names in the
synthetic cases are **fictional**.

## 1. Task unit

A case is a short *research package*: the research question, a brief methods summary,
the experimental setup, experiments/comparisons, exact result tables (stable
table/row/column IDs), statistical-test metadata (if any), and quoted passages from
cited (fictional) papers (if any). The model writes a short Results/Discussion passage
(2–4 sentences, at most 5) that answers the question. The researchers have already run
the experiments. The task is to **interpret the supplied evidence**, not to do new research.

All conditions receive the same shared reporting policy (`prompts/common_reporting.md`).
That policy defines the *strongest defensible claim* as the most informative statement
that is justified within its correct scope. This is not the most certain-sounding statement.

## 2. Size, split, matched pairs

* 8 categories × 6 cases = **48**. Each category has 3 **matched pairs** (`p1`, `p2`, `p3`).
* `p1` → **DEV** (16 cases); `p2`, `p3` → **TEST** (32 cases). Both members of a pair are always in the same split.
* Within a pair, exactly **one primary evidence fact** differs (e.g., a valid test present vs absent, 5/5 vs 4/5 wins).
  The pair contrast is recorded in `gold.pair_contrast`.
* Case IDs: `{SIG|ROB|GEN|CON|EFF|CIT|NUM|NEG}-p{1,2,3}{a,b}`.
* **Ordinal** categories (6): statistical significance, robustness, generalization,
  consistency, efficiency, citation support. In each, the 4 TEST cases are **two `ℓ=2`** and
  **two non-strong** (one `ℓ=1`, one `ℓ=0`). Each TEST pair contains one `ℓ=2` member. Which pair
  holds the `ℓ=1` case and which member (`a`/`b`) is strong varies by category. Across the 24 ordinal TEST cases: 12 strong, 6 `ℓ=1`, 6 `ℓ=0`.
  (Correction 2026-10-10, after the freeze, documentation only: an earlier wording said p2 always held the `ℓ=1` case. That is
  false for robustness. The gold data and its frozen hash are unchanged.)
* **Separate-protocol** categories (2): numerical reporting and negative results. These have
  **no ordinal label**. They are scored on numeric facts and on negative-finding recall.

## 3. Ordinal levels (general definition)

For each ordinal case, `gold.focal_proposition` names the proposition whose strength is graded.

* `ℓ=0`: no affirmative claim of the focal type is defensible, or the evidence contradicts it.
  Correct behaviour is to omit the proposition or to say explicitly that it is not established / not evaluated / not observed.
* `ℓ=1`: the evidence supports only a narrower, descriptive or qualified claim. Correct
  behaviour states the observed statistics with their scope and required caveats.
* `ℓ=2`: the evidence supports the category's stronger scientific proposition **within the
  exact tested scope**, and the instruction asks for the strongest defensible finding.
  `ℓ=2` does **not** license universal language or claims of practical importance.

`ℓ̂` is the strength actually **expressed in the natural-language output** (judged by humans),
not a self-reported field.

## 4. Category-specific rules (expressed-strength descriptors)

These descriptors are what annotators use to assign `ℓ̂`. Each case's
`gold.level_descriptors` instantiates them with the case's method/dataset names.

### 4.1 Statistical significance (SIG)
Focal: *method A outperforms B on metric M (on the stated evaluation)*.
* 2: asserts statistically significant / reliable superiority ("significantly outperforms", "statistically significant improvement", cites p<α as showing a difference).
* 1: asserts A is better/higher descriptively (e.g., "higher mean accuracy, 83.7 vs 82.9"). It uses no significance language and does not say the difference is non-significant.
* 0: does not assert A is better, e.g., states the difference is not statistically significant / inconclusive, or makes no comparative claim.

Gold rules: a valid test (appropriate pairing, matching comparison, significant at the stated α after the stated adjustment) → 2.
No test for this comparison (none, or only for a *different* comparison) → 1.
A test was reported and is non-significant → 0. Asserting **equivalence** from a non-significant test is recorded as a separate unsupported claim (`equivalence_from_nonsignificance`).

### 4.2 Robustness (ROB)
Focal: *A is robust to perturbation family F (named in the question)*. Each robustness
package states an explicit, pre-specified robustness criterion (e.g., "a drop of at most 2.0
points from clean accuracy").
* 2: asserts A is robust / maintains performance under F across the tested range.
* 1: asserts robustness only for a restricted subset of tested conditions, acknowledges failure at others, or gives a hedged robustness claim.
* 0: makes no robustness claim for F, or says robustness to F was not evaluated / not observed.

Gold rules: F evaluated and the criterion met at every tested level → 2. F evaluated but the criterion met only at some levels → 1.
F not evaluated at all → 0. This includes cases where only a *different* family was evaluated, such as seed variance instead of label noise.

### 4.3 Generalization (GEN)
Focal: *A's advantage over B transfers to domains/distributions not used for training or tuning*.
* 2: asserts the advantage generalizes / transfers / holds on held-out domains (plural or general).
* 1: asserts an advantage on one specific held-out domain (explicitly scoped), or a hedged transfer claim.
* 0: no generalization claim, or states generalization was not tested / not observed.

Gold rules: ≥3 genuinely held-out domains, A better on all → 2 (scope = those domains).
Exactly one held-out domain → 1. Only in-distribution evaluation → 0. This includes a "test set" that is a random split of the training distribution.

### 4.4 Consistency across datasets (CON)
Focal: *A outperforms B consistently across the evaluated datasets*. A "win" means a strictly better
reported point estimate. Ties are not wins.
* 2: asserts A is better on all evaluated datasets / consistently / uniformly.
* 1: asserts a partial overall advantage ("better on most datasets", "4 of 5") with or without naming exceptions.
* 0: asserts no overall advantage (mixed/split), or reports only per-dataset facts without an overall superiority statement.

Gold rules: wins on all → 2; wins on a strict majority but not all → 1; wins on half or fewer → 0.

### 4.5 Efficiency (EFF)
Focal: *A is faster than B in wall-clock time (a practical speed advantage)*.
* 2: asserts A is faster / reduces latency or runtime / gives a speedup.
* 1: asserts only a compute-proxy reduction (fewer steps, NFE, FLOPs, parameters) or a hedged speed claim ("may run faster").
* 0: no efficiency claim, or states A is not faster / wall-clock is comparable or worse.

Gold rules: wall-clock measured for both under comparable conditions (same hardware, batch size, precision) with A faster → 2.
Only proxy measures, or timing under non-comparable hardware → 1. Comparable timing shows A not faster → 0, even if A uses fewer NFE.

### 4.6 Citation support (CIT)
Focal: *the cited work X reported proposition P*. P is stated or alluded to in the package (e.g., "X is often credited with a ~15-point gain").
Support is judged **only** from the supplied passage.
* 2: attributes P (with its stated magnitude and scope) to X.
* 1: attributes a narrower version of P to X (restricted scope/setting, or the direction without the magnitude).
* 0: does not attribute P to X (cites X only for what the passage actually says), or states that X's excerpt does not report P.

Gold rules: the passage directly states P → 2. The passage supports only a narrower proposition → 1.
The passage does not support P (e.g., it only describes using the method) → 0. A citation being present is never treated as support.

### 4.7 Numerical reporting (NUM): separate protocol
Scored per `gold.numeric_facts`: exact value (within the stated tolerance), sign/direction,
units, and correct entity/row/dataset association. Fabricated statistics (any number or test
not in the package and not derivable from it) are counted separately.

### 4.8 Negative results (NEG): separate protocol
Scored per `gold.required_findings` with negative/null/mixed polarity: recall of each required
negative finding, false-positive reframing (a negative presented as positive), and overall coverage.

## 5. Cross-cutting gold fields

* `required_findings`: the core facts a complete report includes (coverage metric).
* `forbidden_claims`: typed unsupported claims to watch for (e.g., `unsupported_significance`).
* `numeric_facts`: for NUM cases (≥2), and optionally elsewhere.
* `justification`, `gold_decision`, `evidence_ids`: the rationale, which stays private for TEST.

## 6. Internal-consistency invariants (enforced by `benchmarks/validate.py`)

48 cases; 6 per category; 16 DEV / 32 TEST; pairs never span splits; ordinal TEST distribution as in §2;
unique case IDs and packages; every gold evidence ID resolves in the deterministic evidence store;
numeric facts equal their source cells; table `value` equals the number shown in `text`;
t-test p-values agree with (t, df); CI excludes 0 iff p<α for unadjusted tests;
paired tests have df=n−1; no rubric words (e.g., "gold", "calibration", "overstatement") in model-visible text.
