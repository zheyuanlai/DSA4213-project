# Task: atomic claim extraction (prompt ext-extract)

Below is a research package and the distinct passages that were written from it. Each passage is split into sentences; each distinct sentence has an ID (`U-...`). Decompose **every listed sentence ID** into atomic claims.

## What an atomic claim is
* The smallest proposition in the sentence that could be true or false on its own. Keep the attribution (who reported it), scope (which dataset, metric, setting, subset) and any hedge or qualifier ("may", "suggests", "on average", "in this setting") inside the claim it modifies. Never add content that the sentence does not express, and never merge content from other sentences.
* Split when a sentence states several findings that could be wrong independently: results on different datasets/metrics/methods stated as separate findings; a comparison plus a separate claim that it is statistically significant; generality ("on all datasets", "consistently"); robustness, transfer, speed, causal or practical-importance content; a scope or caveat statement.
* Keep together a comparison and the numbers that instantiate it ("A reached 83.7 vs B's 82.9" is one comparison claim with two numbers); numbers are checked separately.
* Example: "Method A significantly outperforms B on three datasets and reduces inference time by 20%." gives (1) A outperforms B on the three datasets; (2) the A-vs-B difference is statistically significant; (3) the comparison covers three datasets; (4) A reduces inference time relative to B by 20%.
* Do not duplicate: emit a separate scope or generality claim only when it asserts something checkable that no other claim from the same sentence already asserts (in the example, the number of datasets). "A outperformed B on every collection" is **one** claim; do not add "the comparison covers every collection" next to it.
* Caveats and limitations about the evidence ("no significance test was reported", "results come from a single run", "only four collections were evaluated") are claims too (type `scope_or_caveat`). Pure transitions or restatements of the question with no content are not claims; a sentence can have zero claims.

## Fields for each claim
* `span`: a verbatim, contiguous substring of the sentence (copy characters exactly) that expresses the claim; the shortest span that covers it. Spans of different claims may overlap.
* `proposition`: one self-contained sentence stating the claim with pronouns resolved (e.g. "Corbel's average nDCG@10 (40.7) is higher than Dovetail-DR's (36.0) across the four collections").
* `claim_type`: one of `result_value`, `comparison`, `statistical_significance`, `consistency_or_generality`, `robustness`, `generalization`, `efficiency`, `citation_attribution`, `negative_or_null_result`, `trend_or_tradeoff`, `causal_or_mechanistic`, `scope_or_caveat`, `method_or_setup`, `other`.
* `entities` (methods/systems), `metrics`, `datasets`: names as they appear; `qualifiers`: hedges, scope restrictions, quantifiers ("all", "most", "on average").
* `numbers`: every number in the span that expresses a quantity, each with
  * `as_written`: the token as it appears, including sign and symbol (e.g. "−0.5", "41.2%", "5.7×", "p < 0.05");
  * `value`: the numeric value as asserted, in the text's own units ("41.2%" → 41.2; "2.3 percentage points" → 2.3; "5.7×" → 5.7; "halved" → 0.5; "doubled" → 2; "four of five" → 4);
  * `comparator`: `=` for a stated value, or `<`, `<=`, `>`, `>=` for bounds ("p < 0.05" → `<` 0.05; "more than 20%" → `>` 20);
  * `approximate`: true only if the text marks it approximate ("about", "~", "roughly", "nearly", "around");
  * `role`: `result` (a reported value), `derived` (difference, ratio, percentage change, range end computed from results), `statistical` (p-value, CI bound, test statistic, df), `cited` (a magnitude attributed to a cited work), `count_outcome` (a count of outcomes, e.g. wins on 4 of 5 datasets), `setup` (seeds, sample sizes, dataset sizes, model sizes, hyperparameters);
  * `unit`: the unit as written or null.
  Do not list digits that are part of names (model names such as "Llama3", metric names such as "nDCG@10" or "F1", dataset names), citation years, or table/section numbers.

## Research package
{{PACKAGE}}

## Passages (context; sentence IDs in brackets)
{{PASSAGES}}

## Sentences to decompose (every ID must appear exactly once in your answer)
{{UNITS}}
