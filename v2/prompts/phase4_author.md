# Task: author one matched pair of research packages and draft sentences

You are writing test material for a study of how accurately short Results sentences state the strength of the evidence
behind them. You will author **one matched pair** of fictional research packages and a few one-sentence drafts. Output
only one JSON object in the format given at the end.

## What a research package is

A package is everything a writer sees about a finished experiment: the research question, a methods summary, the
experimental setup, experiments and comparisons, results tables, statistical tests and quoted passages from cited works.
The example below shows the format; follow its structure exactly (field names, nesting, ID style).

{{EXAMPLE_PACKAGE}}

Package rules:
* All method, model, dataset, author and paper names are **new and fictional**. Do not use any of these names:
  {{AVOID_NAMES}}
* IDs: tables `T1`, `T2`, …; rows `r1`, `r2`, …; short lowercase column IDs; experiments `exp1`, …; comparisons `cmp1`, …;
  tests `S1`, …; passages `P1`, …. Every statistical test must reference an existing experiment/comparison.
* Each table cell has `text` exactly as shown (e.g. "83.7 ± 1.2"), `value` equal to the first number in `text`, and
  `spread` only if the text shows "±".
* Statistical tests must be internally consistent: the p-value agrees with the statistic and df (two-sided t-test unless
  stated), the confidence interval excludes 0 if and only if p < alpha for unadjusted tests, paired tests have df = n − 1,
  and `p_value_text` agrees with `p_value`. Where a package reports only a confidence interval (no p-value), set
  `p_value` and `p_value_text` to null and give `ci_low`, `ci_high`, `ci_level`, `effect_description`.
* Never use these words anywhere in a package or draft: gold, level 0/1/2, forbidden, overstated, understated,
  calibrated, calibration, required finding.
* Keep each package short (well under 10,000 characters of JSON). `task_instruction` asks for a 2–4 sentence
  Results/Discussion passage answering the question.
* The two packages of the pair must be **identical except for the declared contrast** (and anything that must change to
  keep it consistent, e.g. a table note). Same question, methods summary, setup wording, names and all unrelated
  numbers.

## The pair to author

{{PAIR_SPEC}}

Define a **focal proposition**: the strong scientific claim at issue (e.g. "A outperforms B in BLEU on the X test set").
Give three level descriptors for how strongly a sentence can express it:
* `"2"`: the strong, unqualified form, justified only in the strong member.
* `"1"`: a narrower, descriptive, partial or hedged form.
* `"0"`: no claim of that kind, or a statement that it is not established.

The **strong member supports level 2**. The **partner supports the level given above** (`partner_level`).

## Drafts (one sentence each, at most 40 words, no evidence IDs in the text)

* `U`: states the **same focal proposition** at level 1, using the U pattern above. It must be true and accurate for
  both members, except when the partner is at level 0. It must use only numbers present in both packages.
* `U2`: the same, but using the U2 pattern. The wording must clearly differ from U.
* `S`: the level-2 strong form of the focal proposition, accurate for the strong member.
* `Z` (only if `partner_level` is 0): an accurate statement for the partner that the focal claim is not established, for
  example "the confidence interval includes zero" or "the excerpt reports no result".

Important:
* U and U2 must weaken the **same** proposition. They must **not** describe a different fact, mention only a subset of
  the evaluated conditions, or rely on a proxy quantity instead of the focal quantity.
* For each draft give `expressed_level` (0, 1 or 2), a short `pattern` label, and `writer_evidence_hints` (the package
  IDs the sentence relies on).

## Output format

Return exactly one JSON object:

```
{"pair_id": "...", "focal_proposition": "...",
 "level_descriptors": {"0": "...", "1": "...", "2": "..."},
 "pair_contrast": "<the one evidence fact that differs, in one sentence>",
 "decisive_evidence_ids": ["<IDs in the STRONG package that carry the contrast>"],
 "strong_package": {<research package>},
 "partner_package": {<research package>},
 "drafts": [{"key": "U", "text": "...", "expressed_level": 1, "pattern": "...", "writer_evidence_hints": ["..."]},
            {"key": "U2", ...}, {"key": "S", ...}, {"key": "Z", ...}]}
```
