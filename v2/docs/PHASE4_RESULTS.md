# Phase 4 results: held-out test of the V2 fix

* **Run.** `p4_test_v1`, 2026-10-25: 40 frozen items × 3 conditions × 3 interleaved repeats = 360 runs. All completed.
* **Judging.** 119 distinct revised sentences, judged blind by GPT-5.6 (A) and Claude Haiku 5.5 (B). They agreed on 117;
  2 were adjudicated.
* **Scoring.** Frozen `phase4_score.py` rules.
* **Deviations.** Two format-only fixes to the judging harness, recorded before scoring: [`PHASE4_DEVIATIONS.md`](PHASE4_DEVIATIONS.md).
  `phase4_freeze.py --check` reports exactly those two files as changed.
* **Tables.** `v2/results/phase4/p4_test_v1/` (`SUMMARY.md`, `summary.json`, `judged.json`).

## 1. Main results

Rates are per-item means over 3 repeats; raw run counts in brackets.

| Metric | V1 C4 (original verifier) | **V2 C4 (D1-tools)** | V2 C5 (D1-tools, no STRENGTHEN) |
|---|---|---|---|
| Correct strengthening, 12 understated items: STRENGTHEN + revision SUPPORTED, no numeric error | 0.33 (12/36) | **0.78 (28/36)** | 0.00 (0/36) |
| False strengthening, 28 other items | 0.00 (0/84) | **0.00 (0/84)** | 0.00 (0/84) |
| Overstatement corrected, 10 overstated items | 0.70 (21/30) | 0.73 (22/30) | **0.90 (27/30)** |
| Calibrated controls preserved, 18 items | 1.00 (54/54) | 1.00 (54/54) | 1.00 (54/54) |
| Harmful edits on calibrated controls | 0/54 | 0/54 | 0/54 |
| Decision in the gold set (all 40) | 0.70 | **0.85** | 0.57 |
| Cost (USD, 120 runs) / model latency per run / tool calls per run | 0.040 / 11.1 s / 2.8 | 0.041 / 13.9 s / 3.0 | 0.036 / 13.8 s / 2.7 |

**Paired contrasts** (cluster bootstrap over the 8 pairs, 95%):

| Contrast | Correct strengthening | Overstatement corrected | Decision correct |
|---|---|---|---|
| V2 C4 − V1 C4 | +0.44 [+0.14, +0.78] | +0.03 [−0.06, +0.17] | +0.15 [+0.01, +0.31] |
| V2 C4 − V2 C5 | +0.78 [+0.44, +1.00] | −0.17 [−0.30, −0.04] | +0.28 [+0.14, +0.42] |

No contrast in false strengthening, control preservation or harmful edits; all three are 0 in every condition.

**Subgroups (correct strengthening, runs):**

| Subgroup | V1 C4 | V2 C4 | V2 C5 |
|---|---|---|---|
| Weakening patterns not used in DEV | 6/24 | 19/24 | 0/24 |
| Claims needing no statistical test | 1/18 | 12/18 | 0/18 |

## 2. What the records show

1. **The fix generalises to new items without false strengthening.** On held-out items written and validated by other
   models, V2 C4 strengthens 28 of 36 understated runs, and every revision is judged SUPPORTED. It never strengthens a
   calibrated or overstated item (0/84), and it never damages a calibrated control (0/54).
2. **V1 can strengthen when the draft is overtly hedged and a significance result exists.** V1 strengthened 12/36 runs.
   The cases are the CI-based trend draft P1-U2 (3/3), the negative-result drafts P7-U and P7-U2 (3/3 each) and P2-U
   (2/3). Its revisions add the test, for example "Nacre performs significantly worse … (paired t-test, p = 0.0067)".
   V1 almost never strengthens claims that **need no test**: 1/18, against 12/18 for V2.

   This refines the V1 diagnosis. V1's 0/406 on its own drafts reflected a lack of overt hedges in natural drafts
   (opportunity scarcity, see section 4) as well as its decision framing.
3. **The remaining V2 failure is the one seen in E5, now replicated on held-out data.** Both P5 throughput drafts
   (same hardware and batch size) were accepted in 6/6 runs. The rationale reads: "The sentence is appropriately hedged
   ('seems', 'tentative') … No test was reported." The verifier treats "no significance test" as a reason to keep a
   hedge on a claim that needs no test.
4. **A possible trade-off in the weakening direction (small n).** V2 C5 corrected overstatement more often than V2 C4
   (27/30 vs 22/30), and V1 C4 was at 21/30. The difference comes from:
   * **P1-S-partner** ("outperforms" when the CI includes 0): V2 C4 corrected it in 1 of 3 runs, V2 C5 in 3/3, V1 in 0/3.
   * **P8-U2-partner** (a "preliminary evidence" attribution the excerpt does not support): V2 C4 accepted it in 2 of 3
     runs, reading a passage phrase as support.
   * **P8-S-partner:** revisions in all conditions sometimes kept unsupported content or had numeric errors.

   With 10 items in 4 pairs, this is a signal to report, not an established effect.
5. **STRENGTHEN is what produces the strengthening.** With the same D1 judgement but no STRENGTHEN action, V2 C5
   accepted every understated item (0/36). Its "decision correct" is lowest, because ACCEPT is wrong for understated
   items.

## 3. What this evaluation can and cannot support

* **Can:** the V2 decision fix generalises to held-out, independently authored and validated, **explicit-hedge**
  understatements across 6 evidence types, with no false strengthening and no harmful edits, at about the same cost as
  V1. Strengthening needs the STRENGTHEN action.
* **Cannot:**
  * omission-type understatement (removed at validation: [`PHASE4_BENCHMARK.md`](PHASE4_BENCHMARK.md) §3) and the proxy
    and attribution-magnitude types (P4 and P8 STRENGTHEN items dropped);
  * natural frequency of opportunities;
  * end-to-end passage quality;
  * real papers;
  * other backbones.

  Further limits:
  * n is small (12 STRENGTHEN items, 8 clusters; intervals are wide);
  * all labels come from AI models, with no human validation;
  * GPT-5.6 both authored the items and served as Judge A.

## 4. Natural opportunities (frozen V1 AI labels; no new calls)

* **Synthetic TEST outputs.** Atomic claims labelled UNDERSTATED: 0–1 per condition.
* **Real-paper outline drafts.** 0.015 of 202 claims, about 3.
* **Synthetic focal annotation.** No understatement in any condition.

Under the same rubric the Phase 4 validator used, natural V1 drafts therefore offer almost no strengthening
opportunities. V2's ability to strengthen is real, but it would rarely be exercised on PaperPilot's natural drafts. Its
practical value there is mainly as a safeguard, not as a source of frequent edits.

## 5. Spend

| Item | Cost |
|---|---|
| TEST inference (V2 experiment ledger, stage `v2_phase4`) | $0.117 |
| Revision judging (V2 judge ledger, `p4_judge`) | $1.382 |
| Authoring and validation (judge ledger) | $1.605 |
| **Phase 4 total** | **$3.10** |
| V2 overall | experiments $0.33, judge ledger $2.99 |

The OpenRouter key's total use of $4.53 reconciles with V1 $1.22 + V2 $3.31.
