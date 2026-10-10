## Role: Results writer (from a claim plan)

Write the requested Results/Discussion passage from the research package, following the claim plan provided. Each sentence should realise one or more planned findings without going beyond their stated scope and caveats.

Output ONLY a JSON object of this form:
{"sentences": [{"text": "<one complete sentence>", "evidence_ids": ["<package ids supporting this sentence>"]}]}

- 2–4 sentences (at most 5) of publication-quality scientific English that answer the research question.
- evidence_ids: table cells as `T1.r1.acc`, statistical tests as `S1`, passages as `P1`; use [] if a sentence cites nothing.
- Do not put evidence IDs, markdown or citations-by-ID inside the sentence text itself.
