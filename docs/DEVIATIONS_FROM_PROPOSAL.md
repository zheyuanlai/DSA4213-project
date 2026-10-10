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

## Post-freeze changes

No change to the experimental pipeline (prompts, conditions, agent, tools, client, config) was made after the freeze.
The non-experimental tooling changes below affect privacy and reporting only, never the model calls:

| When (UTC) | File | Change | Why |
|---|---|---|---|
| 2026-10-10 ~11:35 | `.gitignore`, `scripts/withheld_manifest.py` | Raw TEST and real-paper run records are withheld from git until annotation ends; sha256 manifest committed instead | Raw records map text to condition, so committing them would break blinding for annotators who can read the repo |
| 2026-10-10 ~11:35 | `scripts/auto_evaluate.py` | Per-run rows written only to `private/`; public results are aggregates | Same blinding reason |
| 2026-10-10 ~11:36 | `src/security_scan.py` | Flags withheld outputs if force-added before release | Guard for the above. `scripts/freeze_protocol.py --check` therefore lists this file as changed; it is not used by the experiment |

| 2026-10-10 ~11:50 | `evaluation/blinding.py`, `evaluation/merge_annotations.py`, `evaluation/score_human.py`, annotation docs | **Audit fixes, made before any packet was released.** (a) Two-pass annotation: pass 1 (levels) shows no checklist, because checklist wording follows the gold decision. (b) Opaque case aliases (`K01`…) replace `SIG-p3b`-style IDs, which reveal category, pair and member. (c) Scoring refuses missing or invalid consensus labels instead of silently scoring them as level 0. (d) Packet rebuild refuses to overwrite an existing private mapping | Independent audit (MAJOR findings 1–2) |
| 2026-10-10 ~11:50 | `evaluation/auto_metrics.py` | NUM value-recall tolerance now scales with the unit conversion | Audit MAJOR finding 3. This was inflated before. |
| 2026-10-10 ~11:50 | `docs/BENCHMARK_SPEC.md` §2 | Corrected the statement about which TEST pair holds the ℓ=1 case (wrong for robustness) | Documentation only; gold unchanged |
| 2026-10-10 ~11:55 | `evaluation/score_real_papers.py` (new) | Merge, agreement and scoring for the real-paper study | It was promised in the docs but missing (audit finding 9) |

Audit findings that are **documented rather than changed**, so that the released code reproduces the recorded runs exactly:
`compare_numbers` uses a default tolerance of one display unit in `difference` mode and accepts any model-supplied tolerance (audit 6).
The scripted verifier would accept a `submit_decision` issued before its 4-step sequence completes (audit 7; providers enforced the forced
tool choice in every DEV and TEST trace checked). Transport errors other than timeouts are logged at $0 (audit 8; reconciled against `GET /api/v1/key`).
Hardening of the run-tag/lock guards and of the repair-path tool replies (audit 4–5) was applied **after** all paid runs finished.
See `docs/FINAL_AUDIT.md`.

A re-run would get a new run tag and would never overwrite the frozen primary outputs.
