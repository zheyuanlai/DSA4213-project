# Task: judge each draft sentence against the research package (independent check)

Below is a research package and several candidate one-sentence drafts, each written as if it were the whole Results
statement on the package's question. Judge **each sentence independently** against the package only.

For each sentence ID give:

1. `label`, using exactly these definitions (from the study's evaluation protocol):

{{LABEL_DEFINITIONS}}

2. `strongest_supported`: one sentence giving the strongest statement of the **same proposition** that the package
   supports within the evaluated scope. It may be stronger than, equal to or weaker than the draft.
3. `same_proposition`: `true` if a correct revision of the draft only needs to change how strongly or how broadly the
   draft's own proposition is stated. `false` if the draft is about a different fact than the package's main finding on
   the question, mentions only a subset of what was evaluated, or relies on a proxy quantity, so that a correct
   statement would have to **add a different finding**.
4. `justification`: at most 30 words, citing package IDs (cells `T1.r2.acc`, tests `S1`, passages `P1`).
5. `confidence`: `low`, `medium` or `high`.

## Research package
{{PACKAGE}}

## Draft sentences
{{SENTENCES}}

## Output format
Return exactly one JSON object:
{"judgements": [{"sentence_id": "...", "label": "SUPPORTED|OVERSTATED|UNDERSTATED|UNSUPPORTED|NOT_VERIFIABLE",
"strongest_supported": "...", "same_proposition": true, "justification": "...", "confidence": "high"}]}
