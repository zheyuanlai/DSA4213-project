# E5 results: D1 inside the V1 tool loop (DEV only, exploratory)

**Status: automatic results and agent coding complete; student checks pending.** Plan: [`E5_PLAN.md`](E5_PLAN.md).

* Run `e5_v1`, 2026-10-25: 39 probes × 3 conditions × 3 repeats = 351 runs, in one interleaved batch. All completed, with
  0 invalid decisions. Cost $0.110; V2 total so far $0.210.
* Tables: `v2/results/e1e2/e5_v1/` (`TABLES.md`, `COMPARE_D1-oracle_vs_D1-tools.md`,
  `COMPARE_D0-tools-800_vs_D1-tools.md`, `failure_coding.csv`, `revision_review.csv`).
* Probe-level figures use the majority of 3 repeats. Raw per-run decisions are in the tables and records.

## 1. Main table

| Measure | D0-tools-800 (V1 code) | D1-tools | D1-oracle |
|---|---|---|---|
| Correct STRENGTHEN, claim-level (of 9) | 0 | **8** | 9 |
| …scope-anchoring subgroup, post hoc (of 3) | 0 | 0 | 0 |
| STRENGTHEN runs on all 12 STRENGTHEN probes (of 36) | 0 | 23 | 25 |
| ACCEPT correct (of 15) | 15 | 15 | 14 |
| WEAKEN/REMOVE correct (of 12) | 10 | 12 | 11 |
| False STRENGTHEN, probes (of 27) / runs (of 81) | 0 / 0 | 0 / 0 | 0 / 0 |
| Stable probes (of 39) | 37 | 35 | 34 |
| Decisive evidence returned, STRENGTHEN-probe runs (of 36) | 33 | 33 | n/a |
| Evidence-tool calls per claim | 2.21 | 2.46 | 0 |
| Model latency per run (s) | 9.1 | 12.2 | 6.1 |
| Cost (USD, 117 runs) | 0.0431 | 0.0446 | 0.0221 |

## 2. Does the oracle improvement survive the tool loop?

**Largely, yes.**

* **Strengthening.** D1-tools strengthens 8 of the 9 claim-level probes, against 9 for D1-oracle in the same batch.
* **No losses elsewhere.** False strengthening stays at zero, and WEAKEN/REMOVE accuracy is 12/12.
* **Reference criteria.** All are met: at most one probe lost, false STRENGTHEN ≤ 1, WEAKEN/REMOVE not below D0-tools-800.
  As agreed, the reading below also looks at the specific errors.

**Probe-level differences between D1-oracle and D1-tools** (same batch):

| Change | Probe | D1-oracle | D1-tools |
|---|---|---|---|
| Lost | EFF-U2-strong | ST, ST, ST | ST, AC, AC |
| Gained | EFF-S-partner | AC, AC, AC | AC, WE, WE |
| Gained | CON-U2-partner | AC, WE, WE | AC, AC, AC |

The two gains are on probes that already flipped between batches in E2/E2b, so they are not read as effects of the tool
loop.

**Attribution of the one loss: a decision loss, not a retrieval loss.**

* In all three EFF-U2-strong runs, the latency column (including the same-hardware source cells) was returned.
* In the two failed runs, `strongest_supported` even states "Brisling had lower median latency", but the relation is
  MATCHES. The rationale reads: "The hedge 'may' is appropriate since no statistical test was reported for this
  comparison."

## 3. Retrieval

* **Retrieval rarely fails on these probes.** In both tool conditions, the decisive evidence was returned in 33 of the 36
  runs on STRENGTHEN probes.
* **The 3 misses are all EFF-U**, a scope-anchoring probe whose sentence is about decoder passes. The verifier looked up
  the passes column only.
* **D1 checks slightly more.** It makes 2.46 instead of 2.21 tool calls per claim, mostly extra `lookup_table` and
  `retrieve_passage` calls.

## 4. Effect of the decision framework in the realistic tool setting (D0-tools-800 vs D1-tools)

* **Large and one-directional.** At equal token limits, **10 probes improve and none regresses**: 8 STRENGTHEN probes,
  plus CON-S-partner and EFF-S-partner, which D1 now weakens correctly.
* **The token limit was not V1's problem.** D0-tools-800 strengthens 0 of 12, exactly like V1 at 450 tokens in `e1e2_v1`.
* **Cost.** The improvement costs about 3% more per run ($0.0446 vs $0.0431) and about 3 s more model latency per claim.

## 5. Remaining failures and a recurring pattern

Agent coding; student check pending.

| D1-tools failures on STRENGTHEN probes (runs) | Count |
|---|---|
| Scope-anchoring subgroup (EFF-U: F0 3; GEN-U, ROB-U: F1 6) | 9 |
| F2: claim-level probes (EFF-U2-strong r2, r3; GEN-U2-strong r3; ROB-U2-strong r3) | 4 |
| F3 | 0 |

**A recurring F2 pattern.** Three of the four F2 rationales justify keeping a hedge by the absence of a statistical test,
even though the claim (faster, transfers, robust) does not need one under the reporting policy:

* "consistent with the absence of a reported significance test";
* "No statistical test reported, but the claim does not assert significance";
* "The hedge 'may' is appropriate since no statistical test was reported".

The verifier treats "no test" as a reason to keep any qualifier.

**Hypothesis, not tested.** In the tool loop the verifier often calls `get_test_metadata` (94 calls in 117 runs). When no
test exists, the tool returns "statistical significance is NOT established", which may prime hedging. This would also
explain why D1-tools has slightly more F2 than D1-oracle. Testing it would require a change to the tool message, which
is outside E5's scope.

## 6. Interpretation (provisional)

1. The decision-framework change is what produces bidirectional calibration. It transfers to the real tool loop with
   little loss, and there was no false strengthening on these DEV probes.
2. On these probes, retrieval is not the main bottleneck for claim-level strengthening. It matters mostly for the
   scope-anchoring cases, which are out of scope for STRENGTHEN.
3. The main remaining weakness is a decision-standard confusion between "no significance test" and "the claim must stay
   hedged".
4. All of this is DEV evidence on 39 single-sentence probes written by the coordinating agent. It does not show that the
   improvement generalises; that is what the held-out evaluation is for.

## 7. Implications for the held-out evaluation (to be designed next)

* **Selected verifier:** D1-tools (V1 loop, D1 addendum and schema, 800 tokens per turn).
* **Comparison:** V1 C4 (D0-tools-800) vs V2 C4 (D1-tools) vs **V2 C5** (D1-tools without STRENGTHEN). V2 C5 needs one
  design decision. The D1 addendum maps STRONGER_SUPPORTED to STRENGTHEN, which C5 does not allow, so C5 needs a stated
  mapping (for example STRONGER_SUPPORTED → ACCEPT, as V1's no-strengthen note says). This must be fixed before the
  held-out run.
* **Batches:** all conditions in one interleaved batch, with at least 3 repeats.
* **Cases:** new held-out cases written and gold-checked by students. They should include:
  * understatement forms not used in the DEV probes;
  * same-condition and different-condition comparisons;
  * hedged claims that do not need a statistical test;
  * a few multi-sentence drafts, to check for redundant or over-broad strengthening.
