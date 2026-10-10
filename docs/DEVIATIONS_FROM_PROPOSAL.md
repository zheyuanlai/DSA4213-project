# Deviations from the Proposal and Implementation Decisions

All deviations were decided **before** any TEST-split call. The only exception would be listed in the "post-freeze" section, which is currently empty.

| # | Proposal / brief | What was done | Why |
|---|---|---|---|
| 1 | "begin with max 3 evidence tool calls per claim" | **4** evidence-tool calls per claim for both C3 and the adaptive verifiers | The scripted verifier (C3) must run each of the 4 shared tools once in a fixed order. An equal budget of 4 keeps H3 fair. |
| 2 | Separate claim-segmentation step | Writers output a JSON list of sentences, and each sentence is one claim (max 6 verified per passage) | Deterministic, free and identical across C3–C6, and every condition has the same output format. |
| 3 | C1–C7 run as independent systems | **Shared upstream artifacts**: C7 = outline + draft, which is also the starting draft of C3/C4/C5. C1 = direct draft, which is also the starting draft of C2/C6 | Exact counterfactuals: C4 vs C5 differs only in STRENGTHEN, C4 vs C3 only in tool policy, C4 vs C7 only in verification. Per-condition costs include the shared upstream cost. |
| 4 | Verifier sees the package | The verifier sees question/method/setup/comparisons plus an evidence **index** (table schemas, passage list) **without values**, and obtains evidence only through tools | Every decision is grounded in returned observations, which makes tool selection meaningful (H3). |
| 5 | — | `category` and `case_id` are never shown to the model | Avoids cueing the trap type. |
| 6 | One pinned provider | Routing restricted to three fp8 endpoints (StreamLake → Parasail → DeepInfra) for the single pinned model | DeepInfra was rate-limited. The provider is logged per call and its distribution is reported. |
| 7 | — | Reasoning disabled for all conditions | Cost, latency and protocol simplicity. Not explored with reasoning on (limitation). |
| 8 | — | FLAG keeps the sentence unchanged, flagged only in metadata. REMOVE drops it; WEAKEN/STRENGTHEN replace it | Missing evidence is not proof of the opposite claim. |
| 9 | — | Only the first tool call per turn is executed; extras get `NOT_EXECUTED` | `parallel_tool_calls=false` cannot be sent (it would filter out providers). Sequential selection keeps "choose the next check after each observation" meaningful. |
| 10 | — | TEST gold is coordinator-private until annotation ends, and its hash is frozen | Keeps annotators blind to gold. Rules are public in `docs/BENCHMARK_SPEC.md`. |
| 11 | One annotation row per condition-case | One row per **distinct text per case**, with labels expanded to all conditions via the private mapping | Many verifier runs accept everything, so their texts are identical. This saves annotator time and guarantees identical texts get identical labels. |
| 12 | 10–15 real papers with public LaTeX | **12** papers, restricted to CC BY 4.0 / CC BY-SA 4.0 licences (verified via arXiv metadata). Proposed method renamed; 1–2 tables transcribed; author Results/Discussion withheld; no gold | Redistribution rights and memorization control. Real-paper metrics are human-only and PENDING. |
| 13 | — | Lexical PROXY strength heuristics developed and debugged on DEV only | Pipeline sanity checks only. Not validated, not a substitute for human labels. |
| 14 | — | One verifier-prompt change made after the DEV pilot (identical check-list and rationale-consistency rule added to both adaptive and scripted verifier prompts) | DEV showed a rationale/decision inconsistency (CIT-p1a). It was applied symmetrically to C3–C6 before freeze. |

## Post-freeze deviations

None so far. Any later change will be listed here with a timestamp. A re-run would get a new run tag and would never overwrite the frozen primary outputs.
