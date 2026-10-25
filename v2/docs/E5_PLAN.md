# E5 plan: the selected D1 verifier inside the adaptive tool loop (DEV only, exploratory)

**Status: PROPOSAL for review. Not implemented, not run.** It depends on the outcome of E2b, which decides whether D1 or
D1c is carried forward. "D1" below means whichever is selected.

## Question

Does the decision improvement seen with oracle evidence (E2) survive when the verifier must obtain evidence through V1's
tools? Where it does not, is the loss caused by retrieval (the decisive evidence is never returned) or by the decision
(the evidence is returned, but the judgement fails)?

## Conditions

| ID | Evidence | Decision prompt and schema | Source |
|---|---|---|---|
| D0-tools | V1 tools | V1 adaptive verifier, unchanged | reuse `e1e2_v1` |
| **D1-tools** | V1 tools, same loop and budget | V1 adaptive prompt + D1 addendum (+ D1c paragraph if selected); D1 schema | **new** |
| D1-oracle | full package | D1 | reuse the `e2b_v1` D1 run, from the same period |

The main contrast is **D1-tools vs D1-oracle**, which isolates the effect of having to retrieve evidence. **D1-tools vs
D0-tools** is the effect of the decision change in the realistic tool setting.

## Implementation (minimal; V1 unchanged)

* V1's `src.verifier.verify_claim` builds its `submit_decision` schema internally, so the D1 schema cannot be passed in.
  `v2/verifier_tools.py` will be a faithful port of `verify_claim` and `verify_draft` with two injectable parts: the
  system prompt and the decision schema. Tools, tool execution, budgets, duplicate handling, forced submit and
  validation are V1's own functions, called read-only.
* **Equivalence test:** with the V1 prompt and the V1 schema, the port must produce the same message sequence and
  decision as V1's `verify_draft` on the mock client. This guards against accidental behaviour changes.
* System prompt: V1 `common_reporting.md` + V1 `verifier_adaptive.md` (unchanged, with V1's tool procedure) + the D1
  addendum (+ D1c paragraph). The verifier context is V1's evidence index without values.
* Budget: 4 evidence-tool calls per claim, 1 decision repair, as in V1.
* **Token limit (one known difference).** The D1 judgement fields need more output than V1's 450 tokens per turn. D1-tools
  will use 800 tokens per turn. Before the run I will check V1's records for truncation (`finish_reason = length`) at 450.
  If none occurs, the larger limit is unlikely to matter for D0, and this will be stated.
* The runner and analysis reuse the existing scripts: a new condition `D1-tools`, the same probes, 3 repeats.

## Measures

The E2 measures (correct STRENGTHEN, false STRENGTHEN, ACCEPT and WEAKEN/REMOVE accuracy, stability, relation accuracy),
plus:

* **Retrieval:** decisive evidence returned per run (prefix match, as in the corrected analysis). Tool calls per claim.
  Which tools were called.
* **Survival:** for each probe that D1-oracle gets right, whether D1-tools also gets it right.
* **Attribution of each loss** (a probe right in D1-oracle, wrong in D1-tools):
  * **retrieval loss** if the decisive evidence was not returned in the failing runs;
  * **decision loss** if it was returned. These are coded F1–F3 as before.
* Cost, latency and tool calls compared with D0-tools.
* Reporting: the claim-level STRENGTHEN probes (9) are the main set. The scope-anchoring subgroup (3) and the full set
  of 12 are reported separately.

## Criteria, to be fixed before the run

Proposed; to be confirmed at review.

* **The improvement survives** if D1-tools strengthens at least (D1-oracle claim-level count − 1) of the 9 claim-level
  STRENGTHEN probes, with false STRENGTHEN ≤ 1 of 27 and WEAKEN/REMOVE accuracy not below D0-tools.
* If more than one probe is lost, the losses are attributed (retrieval vs decision) before any change is considered. A
  retrieval change (for example, showing which comparisons have a reported test, or a passage-retrieval hint) would be
  a separate, later step with its own DEV check, not part of E5.

## Cost and size

39 probes × 1 new condition × 3 repeats = 117 tool-loop verifications, about $0.03–0.05 by the D0-tools cost in
`e1e2_v1`. Hard cap $1 on the V2 ledger.
