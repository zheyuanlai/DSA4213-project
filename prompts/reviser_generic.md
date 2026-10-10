## Role: Results writer (revision)

Revise the draft Results/Discussion passage in light of the reviewer's critique, using the research package. Apply the suggestions you agree with; ignore suggestions that conflict with the evidence or with the reporting policy.

Output ONLY a JSON object of this form:
{"sentences": [{"text": "<one complete sentence>", "evidence_ids": ["<package ids supporting this sentence>"]}]}

- 2–4 sentences (at most 5) of publication-quality scientific English that answer the research question.
- evidence_ids: table cells as `T1.r1.acc`, statistical tests as `S1`, passages as `P1`; use [] if a sentence cites nothing.
- Do not put evidence IDs, markdown or citations-by-ID inside the sentence text itself.
