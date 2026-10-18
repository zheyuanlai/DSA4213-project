# Task: reference checklist for a Results section (prompt ext-checklist-build)

Below is a research package from which a short Results/Discussion passage (about 150 words) will be written. Build, **from the package alone**, the checklist of findings that a complete and accurate passage should report. Do not use outside knowledge about the paper or its authors.

## Findings (4 to 8)
* Include the main positive results that answer the research question, important negative, null or mixed results, key comparisons, and critical scope limitations only where the package makes them central to interpreting the results (e.g. no significance test for the headline comparison; results for only one setting).
* Each finding: `finding_id` (`F1`, `F2`, ...), a one-sentence `description` that states the finding precisely (direction, entities, dataset/metric, scope), `polarity` (`positive`, `negative`, `null`, `mixed`, `neutral`), `kind` (`main_result`, `comparison`, `negative_or_null`, `scope_limitation`, `other`), `importance` (`core` for findings a passage must report to answer the question, `supporting` otherwise; at least two core findings), and `evidence_ids` (package IDs: cells `T1.r3.avg`, rows, tables, tests `S1`, passages `P1`).
* Every finding must be directly supported by the package. Do not include a finding only because papers usually claim it.

## Required numeric facts (3 to 8)
* The headline numbers a complete passage should state (not every table cell): key scores, key differences or ratios, key test results.
* Each fact: `fact_id` (`N1`, ...), `description`, `expression` over package values (cells `T1.r3.avg`, `T1.r3.avg.spread`, tests `S1.p_value`, `S1.statistic`, `S1.ci_low`, `S1.ci_high`; operators `+ - * /`, parentheses, `abs`, `min`, `max`, `mean`), the resulting `value` in package units, its `unit` (or null), and the `finding_id` it supports (or null). The expression must evaluate exactly to the value from the package numbers.

## Research package
{{PACKAGE}}
