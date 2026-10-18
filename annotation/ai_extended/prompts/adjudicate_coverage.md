# Task: adjudicate disagreements about finding coverage (prompt ext-adjudicate-coverage)

Two independent readings disagree on whether a passage reports a checklist finding. Decide from the research package and the passage alone. The readings are anonymous and in random order.
* `CORRECT`: the passage states the finding with correct direction, entities, dataset/metric and scope (exact numbers not required, but a stated number or qualifier must not change the finding).
* `INCORRECT`: the passage addresses the finding but misreports it (wrong direction/entity/scope, or over/understated so the finding as communicated is wrong).
* `ABSENT`: not reported.
Answer `UNRESOLVED` only if the package genuinely does not allow a decision. Rationale: at most 30 words.

## Research package
{{PACKAGE}}

## Disputed items
{{ITEMS}}
