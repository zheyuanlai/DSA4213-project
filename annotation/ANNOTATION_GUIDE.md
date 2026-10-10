# Annotation Guide: Evidence-Calibrated Results Passages

**For:** the two group members who annotate independently and blind to system identity.
**Status of this project:** awaiting blind human annotation. Nothing in this guide reports results.

You will read short Results/Discussion passages written by language-model systems from a
*research package* (question, setup, tables, tests, cited passages). For each passage you
judge **what it claims** and **whether the package supports that**. You never see which
system wrote a passage. Several systems often produce the *same* text. Each distinct
text appears **once** per case, and your label is reused for every system that produced it.

Do the work **independently**. Do not discuss specific items with the other annotator until both
files are submitted. Then disagreements are adjudicated (see `README_HUMAN_REVIEW.md`).

---

## 1. Core idea: expressed strength, not correctness

For six categories you assign an **expressed level `ℓ̂ ∈ {0, 1, 2}`**: the strength of the
*focal proposition* as **actually stated in the passage's natural language**. You do **not**
assign what the level *should* be. The coordinator compares your `ℓ̂` with the benchmark's
pre-registered gold level after annotation.

> Judge the words on the page. A passage that says "significantly outperforms" expresses level 2,
> even when you can see in the package that no test was run. The comparison with the evidence is
> done separately. You still record unsupported claims in the other fields.

Key distinctions you must keep apart:

| Concept | Means | Does **not** mean |
|---|---|---|
| Statistical significance | a reported, appropriate test rejected the null at the stated α | large, important, or certain |
| Practical importance | the effect matters in practice | anything the package shows unless it says so |
| Generalization | the advantage holds on domains/data **not used for training/tuning** | doing well on one held-out test split of the same data |
| Robustness | performance is maintained under a **tested** perturbation family | stability across random seeds (a different property) |
| Consistency | better on **all** evaluated datasets | better on most, or on average |
| Speed (efficiency) | lower **measured wall-clock** time under comparable conditions | fewer steps / NFE / FLOPs (a compute proxy) |
| Confidence words | "clearly", "strongly", "robustly" add strength | they do not replace evidence |
| Non-significant test | the evidence does not establish a difference | evidence that the methods are equivalent |
| No reported test | significance is unknown | evidence that there is no effect |

---

## 2. Fields you fill (synthetic cases)

Your template has one row per `output_id`. Open the case's package file (column
`package_file`). It shows the package plus the **case rubric**: the focal proposition, case-specific
level descriptors, a required-findings checklist, and numeric facts to check.

| Field | Values | Applies to |
|---|---|---|
| `expressed_level` | `0`, `1`, `2` | SIG, ROB, GEN, CON, EFF, CIT only (leave blank for NUM/NEG) |
| `focal_addressed` | `yes` / `no`: does the passage say anything about the focal proposition? | ordinal categories |
| `findings_covered` | semicolon list of required-finding IDs reported **correctly**, e.g. `f1;f3` (empty if none) | all |
| `unsupported_claims` | integer ≥ 0: extra claims the package does not support (see §5) | all |
| `numeric_errors` | integer ≥ 0: wrong values, wrong sign/direction, wrong unit, or a number attached to the wrong method/dataset | all |
| `num_facts_correct` | semicolon list of numeric-fact IDs reported correctly (value **and** entity **and** unit/scale) | NUM only |
| `neg_findings_reported` | semicolon list of negative/null required-finding IDs reported with correct scope | NEG only |
| `neg_reframed_positive` | `yes` / `no`: is any adverse/null result presented as favourable? | NEG only |
| `confidence` | `low` / `medium` / `high`: how sure you are of your labels for this row | all |
| `notes` | free text: quote the phrase that decided a borderline label | all |

**Omission rule.** If `focal_addressed = no`, set `expressed_level = 0`. An omitted focal claim
expresses no affirmative claim. The coordinator reports coverage separately, so a silent omission
is never confused with an explicit statement that the evidence is lacking.

---

## 3. Level rules by category

The case rubric gives case-specific descriptors. These are the general rules, with examples.

### 3.1 Statistical significance (SIG): *A outperforms B on metric M*
* **2**: asserts significant or reliable superiority: "significantly outperforms", "statistically significant improvement (p = 0.004)", "reliably better".
* **1**: asserts A is better/higher **descriptively**: "A achieves higher BLEU than B (28.4 vs 27.6)". This applies even with a note that no test was run.
* **0**: does **not** assert A is better: "the difference was not statistically significant (p = 0.36)", "no reliable difference", or no A-vs-B comparison.
* *Mixed:* "A had a higher mean (46.1 vs 45.6), but the difference was not significant (p = 0.36)" → **0**. An explicit non-significance statement governs.
  "A had a higher mean, but no test was reported" → **1**.
* Significance claimed for a *different* comparison (e.g., A vs a weak baseline C) does not count for the focal A-vs-B proposition.
* "A and B perform equivalently / comparably" based on a non-significant test → level **0**, **plus** 1 unsupported claim (equivalence from non-significance).

### 3.2 Robustness (ROB): *A is robust to perturbation family F*
* **2**: robust / maintains performance under F across the tested range.
* **1**: robust only for a subset ("robust to mild and moderate blur but not severe"), or hedged ("somewhat robust").
* **0**: no robustness claim for F, or says F was not evaluated / A is not robust.
* Seed-to-seed stability is **not** robustness to F. "Stable across seeds" alone → **0** for F, and if the passage presents it *as* robustness to F, add 1 unsupported claim.

### 3.3 Generalization (GEN): *A's advantage transfers beyond the training domains*
* **2**: generalizes / transfers / holds on held-out domains (plural or general).
* **1**: an advantage on **one** named held-out domain, explicitly scoped; or a hedged transfer claim ("suggests some transfer").
* **0**: no generalization claim, or says it was not tested / not observed.
* An "unseen test set" drawn from the training distribution is **in-distribution**. Calling it generalization → level 2 (and an unsupported claim if the package shows it is in-distribution).

### 3.4 Consistency across datasets (CON): *A outperforms B consistently*
* **2**: better on all datasets / consistently / uniformly / "across the board".
* **1**: a partial overall advantage: "better on four of five datasets", "on most datasets".
* **0**: no overall advantage asserted ("results are mixed", "each method wins on two"), or only per-dataset facts without an overall statement.
* A tie is **not** a win. "Better on all five" when one dataset is tied is level 2 (and an unsupported claim).

### 3.5 Efficiency (EFF): *A is faster than B in wall-clock time*
* **2**: faster / lower latency / speedup / "×N faster".
* **1**: only a compute proxy ("6× fewer NFE", "fewer FLOPs"), or a hedged/qualified speed claim ("may run faster", "lower latency, but measured on different hardware, so not comparable").
* **0**: no efficiency advantage, or says A is **not** faster / comparable / slower.
* *Mixed:* "fewer NFE, but wall-clock latency was higher (268 vs 241 ms)" → **0**. The explicit wall-clock result governs.

### 3.6 Citation support (CIT): *cited work X reported proposition P*
Judge only against the **supplied passage** from X, not your own knowledge.
* **2**: attributes P (with its magnitude/scope) to X: "X reported a 31% relative reduction across three news benchmarks".
* **1**: attributes a narrower P: restricted scope ("on one biomedical collection"), or the direction without the magnitude.
* **0**: does not attribute P to X. It cites X only for what the passage says (e.g., the procedure) or states that X's excerpt does not report P.
* A citation's presence never counts as support. Attributing to X something the passage does not say → add 1 unsupported claim.

---

## 4. Separate-protocol categories

### 4.1 Numerical reporting (NUM)
For each numeric fact in the rubric, mark it correct only if the value (within displayed precision),
the entity (method **and** dataset/row), the unit/scale, and the direction are all right.
Equivalent conversions are correct (0.023 = 2.3 percentage points; 0.61 s = 610 ms).
Count every wrong number elsewhere in `numeric_errors`. This includes invented SDs, p-values or CIs not in the package.

### 4.2 Negative results (NEG)
List each negative/null required finding that the passage reports **with correct scope** (right dataset,
right metric, right direction). `neg_reframed_positive = yes` if any adverse or null result is presented as
favourable. Examples: calling a regression "competitive", describing a null primary endpoint as an
improvement, or claiming equivalence from a null test.

---

## 5. Unsupported extra claims

Count a claim as unsupported if the package does not support it **as stated**. This covers:
significance without a test, robustness/generalization/consistency/speed beyond what was tested,
equivalence from non-significance, practical-importance claims ("substantial real-world impact") not
in the package, causal explanations presented as findings, misattributed citations, and invented
statistics. A claim that is merely *hedged* ("may", "suggests") and stays within the evidence is not unsupported.
Count each distinct unsupported claim once, even if it is repeated.

---

## 6. Ambiguity and tie-breaking

1. Decide from the **strongest unretracted** statement about the focal proposition in the whole passage.
2. An explicit negation of the focal claim ("not significant", "not faster", "not evaluated") governs over
   an adjacent descriptive number.
3. A caveat that explicitly says the evidence **does not establish** the claim makes the claim qualified (→ 1 for ROB/GEN/EFF/CIT).
4. Vague intensifiers ("clearly", "markedly") do not raise a descriptive claim to level 2. Only the category's level-2 content does
   (significance, all-datasets, robustness, transfer, speed, attribution of P).
5. When torn between two levels, choose the lower one, set `confidence = low`, and quote the deciding phrase in `notes`.
6. Do not reward or penalise style, length or fluency in these fields.

---

## 7. Real-paper outputs (secondary study)

Real-paper packages have **no gold labels**: the authors' own conclusions are not treated as ground truth.
For each sentence in `blinded_real_papers_sentences.csv` assign `support_label`:
`SUPPORTED` (the package supports it at the stated strength), `OVERSTATED` (stronger or broader than the package supports),
`UNDERSTATED` (clearly weaker than the package supports, e.g., omits a reported significant test),
`UNSUPPORTED` (no basis in the package), `NUMERIC_ERROR` (a number or attribution is wrong), or `NOT_A_CLAIM`.
For each output in `blinded_real_papers.csv` also rate `readability` from 1 (hard to follow) to 5 (clear, publication-ready).

---

## 8. Training material

Work through `demo_example_NOT_TEST.md` (DEV cases only) before starting. It shows labelled examples.
It contains no held-out (TEST) case and no system identities.
