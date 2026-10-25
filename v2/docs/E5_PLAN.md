# E5 plan: the selected D1 verifier inside the adaptive tool loop (DEV only, exploratory)

**Status: run `e5_v1` done (2026-10-25); results in [`E5_RESULTS.md`](E5_RESULTS.md).** It follows E2b, which kept **D1**
(D1c showed no clear benefit).
All three conditions run in **one interleaved batch**, because E2b found large batch-to-batch variation.

## Question

Does the decision improvement seen with oracle evidence (E2) survive when the verifier must obtain evidence through V1's
tools? Where it does not, is the loss caused by retrieval (the decisive evidence is never returned) or by the decision
(the evidence is returned, but the judgement fails)?

## Conditions

| ID | Evidence | Decision prompt and schema | Source |
|---|---|---|---|
| D0-tools-800 | V1 tools | V1 adaptive verifier, **V1's own code unchanged**, 800 tokens per turn | re-run in the same batch |
| **D1-tools** | V1 tools, same loop and budget | V1 adaptive prompt + D1 addendum; D1 schema; 800 tokens per turn | **new** |
| D1-oracle | full package | D1 (800 tokens, as in E2) | re-run in the same batch |

The main contrast is **D1-tools vs D1-oracle**, which isolates the effect of having to retrieve evidence. **D1-tools vs
D0-tools-800** is the effect of the decision framework in the realistic tool setting, at equal token limits.
`D0-tools` from `e1e2_v1` (450 tokens, V1's setting) is reported only as cross-batch context.

## Implementation (minimal; V1 unchanged)

* V1's `src.verifier.verify_claim` builds its `submit_decision` schema internally, so the D1 schema cannot be passed in.
  `v2/verifier_tools.py` is a faithful port of `verify_claim` and `verify_draft` with two injectable parts: the
  system prompt and the decision schema. Tools, tool execution, budgets, duplicate handling, forced submit and
  validation are V1's own functions, called read-only.
* **Equivalence test** (`v2/tests/test_v2_e5.py`): with the V1 prompt and the V1 schema, the port sends the same message
  sequence (roles, tools, tool choices, messages) and returns the same traces and final draft as V1's `verify_draft` on
  the mock client, at both 450 and 800 tokens. A source diff of `verify_claim` against the port shows only the two
  injected parameters, the capture of the submitted arguments, and one removed comment.
* System prompt: V1 `common_reporting.md` + V1 `verifier_adaptive.md` (unchanged, with V1's tool procedure) + the D1
  addendum, verbatim. The verifier context is V1's evidence index without values.
* Budget: 4 evidence-tool calls per claim, 1 decision repair, as in V1.
* **Token limit.** Both tool conditions use 800 tokens per turn (decided 2026-10-25), so the decision frameworks are
  compared at equal limits. D0-tools-800 differs from V1 only in this setting. V1's verifier records show no `length`
  truncation at 450 (see `REPRODUCIBILITY_AUDIT.md`).
* The runner and analysis reuse the existing scripts (new conditions `D0-tools-800` and `D1-tools`), with the same probes and
  3 repeats. Jobs are interleaved by repeat, probe and condition. Each run's raw decision is stored, and the analysis
  writes an E5 attribution list.

## Measures

The E2 measures (correct STRENGTHEN, false STRENGTHEN, ACCEPT and WEAKEN/REMOVE accuracy, stability, relation accuracy),
plus:

* **Retrieval:** decisive evidence returned per run (prefix match, as in the corrected analysis). Tool calls per claim.
  Which tools were called.
* **Survival:** for each probe that D1-oracle gets right, whether D1-tools also gets it right.
* **Attribution of each loss** (a probe right in D1-oracle, wrong in D1-tools):
  * **retrieval loss** if the decisive evidence was not returned in the failing runs;
  * **decision loss** if it was returned. These are coded F1–F3 as before.
* Cost, latency and tool calls compared with D0-tools-800.
* Reporting: the claim-level STRENGTHEN probes (9) are the main set. The scope-anchoring subgroup (3) and the full set
  of 12 are reported separately.

## Reference criteria (guidance, not mechanical pass/fail)

Agreed 2026-10-25: the figures below are reference points. The conclusion is reached by reading the specific errors, the
raw per-run decisions, and the quality of the revised text.

* **Reference for "the improvement survives":** D1-tools strengthens at least (D1-oracle claim-level count − 1) of the 9 claim-level
  STRENGTHEN probes, with false STRENGTHEN ≤ 1 of 27 and WEAKEN/REMOVE accuracy not below D0-tools-800.
* If more than one probe is lost, the losses are attributed (retrieval vs decision) before any change is considered. A
  retrieval change (for example, showing which comparisons have a reported test, or a passage-retrieval hint) would be
  a separate, later step with its own DEV check, not part of E5.

## Cost and size

39 probes × 3 conditions (D0-tools-800, D1-tools, D1-oracle) × 3 repeats = 351 runs, about $0.07–0.09 (from the per-run
costs in `e1e2_v1`/`e2b_v1`). Hard cap $1 on the V2 ledger (spent so far: $0.10).
