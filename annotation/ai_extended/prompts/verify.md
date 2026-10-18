# Task: verify atomic claims against the research package (prompt ext-verify)

Below is a research package, the passages written from it (for context), and atomic claims extracted from their sentences. For **every claim ID**, judge the claim against the package only.

## Two separate judgements
Both judgements **ignore whether exact numeric values are correct**: every number is checked separately by a program using your mapping (below). If a claim's only problem is a wrong number, judge it as if the number were right (the program will flag it). Do judge everything else: direction, which method is better, scope, significance, attribution, hedges.
1. `entailment`: apart from exact numeric values, is the proposition as stated true according to the package?
   `ENTAILED` (everything it asserts is supported), `NOT_ENTAILED` (the package does not establish some part of it), `CONTRADICTED` (the package shows it is false), `NA` (not a factual claim).
2. `label` (calibration-aware):
   * `SUPPORTED`: entailed, and its certainty, scope and strength match the evidence.
   * `OVERSTATED`: the package supports a weaker statement in the same direction, but the claim's certainty, scope, generality, significance or magnitude wording goes beyond it. Examples: "significantly/reliably/statistically better" without a valid test of that exact comparison at the stated alpha (after any stated adjustment); "consistently / on all datasets" when one or more is a loss or tie; "robust" beyond the tested range or criterion; "generalizes" from in-distribution or single-domain evidence; "faster" from proxies (FLOPs, steps) or timings on different hardware; "large/substantial" for a difference the package gives no basis to call large.
   * `UNDERSTATED`: weaker than the package establishes: unwarranted hedging of a result the package directly establishes ("may be faster" when same-hardware wall-clock shows it is), narrower scope or fewer wins than shown ("most" when all), describing a significant tested difference as possibly due to chance, or denying a conclusion the package does establish. Not mentioning a stronger conclusion elsewhere is not an understatement of this claim.
   * `UNSUPPORTED`: no basis in the package, or wrong in direction or attribution: a fabricated finding; a result attributed to a cited work whose supplied passage does not report it; equivalence or "no difference" asserted from a non-significant test; a causal or mechanistic explanation presented as a finding.
   * `NOT_VERIFIABLE`: not a factual claim about the package (recommendation, opinion, a mechanism explicitly framed as speculation, restatement of the question).
   * Consistency: SUPPORTED requires ENTAILED; OVERSTATED and UNSUPPORTED require NOT_ENTAILED or CONTRADICTED; UNDERSTATED requires ENTAILED or CONTRADICTED; NOT_VERIFIABLE requires NA.
   * Hedged wording that stays within the evidence ("suggests", "is consistent with") is SUPPORTED. A correct statement that no test, variance or held-out evaluation was reported is SUPPORTED when the package indeed reports none.

## Other fields
* `evidence_ids`: the package IDs that decide the judgement (cells `T1.r3.avg`, rows `T1.r3`, tables `T1`, tests `S1`, passages `P1`, comparisons `exp1/cmp1`). Empty only if nothing in the package bears on it.
* `justification`: at most 25 words, citing the evidence.
* `confidence`: `low`, `medium` or `high`. `error_subtype`: short snake_case reason when the label is not SUPPORTED (e.g. `unsupported_significance`, `wrong_direction`, `overgeneralized_scope`, `misattributed_citation`, `unwarranted_hedge`), else null.
* `extraction_flag`: `OK`; `NOT_IN_TEXT` (the claim is not expressed by its sentence); `NOT_ATOMIC` (it bundles independently checkable claims); `DISTORTED` (its proposition changes the sentence's meaning).

## Numeric mapping (one entry for every listed number ID)
Map each number to the evidence that **the text refers to** (its method, dataset, metric, comparison and direction), not to wherever that number happens to appear. A program evaluates your mapping and compares it with the asserted value; do not do the arithmetic yourself.
* `source_type`: `cell` or `test` with an `expression`; `text` with a verbatim `quote` (copied exactly from the package) for numbers that exist only in prose (setup text, cited passages, test notes); `none` if the referenced quantity does not exist in the package (e.g. a p-value for a comparison that was never tested, a number with no source).
* `expression`: arithmetic over package IDs. Values: cells `T1.r3.avg`; a cell's ± value `T1.r3.avg.spread`; tests `S1.p_value`, `S1.statistic`, `S1.df`, `S1.n`, `S1.ci_low`, `S1.ci_high`, `S1.alpha`. Operators `+ - * /`, parentheses, numbers, and `abs()`, `min()`, `max()`, `mean()`, `sum()`, `count(a > b, c > d, ...)` (number of true comparisons). Write the expression in the direction the text states: "A is 2.1 points lower than B" → `T1.rB.m - T1.rA.m`; "a 13% relative gain of A over B" → `(T1.rA.m - T1.rB.m) / T1.rB.m * 100`; "gains from 2.9 to 5.9" → each end is the `min(...)`/`max(...)` of the per-dataset differences; "wins on 4 of 5 datasets" → `count(...)`.
* `scale`: text value = package value × scale. Use 1 normally; 100 or 0.01 for %↔fraction; 1000 or 0.001 for ms↔s and similar unit changes. Never use a scale to make a wrong number fit.
* `quote`: required for `text`, else null. `expression`: required for `cell`/`test`, else null.

## Research package
{{PACKAGE}}

## Passages (context; sentence IDs in brackets)
{{PASSAGES}}

## Claims to verify
{{CLAIMS}}
