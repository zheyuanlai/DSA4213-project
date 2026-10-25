# E2b: one minimal comparability addition to D1 (DEV only, exploratory)

**Status: design fixed before the run (commit 701e123); results added below.** Follows [`E1_E2_RESULTS.md`](E1_E2_RESULTS.md) section 4.

## Why

In `e1e2_v1`, every condition mostly ACCEPTed "Brisling decodes faster than Talmar (41 vs 118 ms)" on EFF-S-partner,
where Talmar's latency was copied from another paper and measured on different hardware. Several rationales mentioned the
difference and still accepted. On EFF-U2-partner, D2 strengthened the hedged version of the same comparison in 3 of 3
runs. D1 is the main V2 candidate (decided 2026-10-25). This step asks whether **one general sentence about the
comparability of compared results** fixes these cases without regressions.

## The change (D1c = D1 + one paragraph)

`v2/prompts/verifier_oracle_d1c_comparability.md` is appended to the D1 system prompt. Nothing else changes: same
evidence block, user message, schema, token limit, backbone and decoding.

> ## Comparisons
>
> When the sentence compares results (for example, that one method is better, faster or more robust than another), the
> comparison is only as strong as the comparability of those results. If the package indicates that the compared results
> were obtained under different conditions (for example a different dataset, metric or measurement setup), the
> strongest supported statement must reflect that limitation; do not treat such a comparison as established. Do not
> assume that conditions differ when the package does not say so.

Design choices:

* **General principle, not a benchmark rule.** Results compared under different conditions do not establish a
  difference. The examples name datasets, metrics and the measurement setup. "Hardware" is deliberately not named, so
  the paragraph does not point at the EFF cases.
* **Triggered only by positive evidence.** The last sentence is there to prevent the D2-style failure in reverse:
  weakening comparisons merely because comparability is not explicitly confirmed.
* **No checklist and no decision change.** The structured judgement and the relation-to-decision mapping of D1 are kept
  as they are.

## Procedure

Run `e2b_v1`: **D1-oracle and D1c-oracle**, all 39 DEV probes, 3 repeats each (234 runs). D1 is re-run in the same batch
because D1 was only 31/39 stable in `e1e2_v1`. Comparing D1c with the old D1 run would mix the prompt effect with
run-to-run variation. The `e1e2_v1` D1 results are reported alongside for reference. Estimated cost about $0.03; hard cap
as before.

## Criteria, fixed before the run

D1c replaces D1 only if **all** of the following hold. Probe level means the majority over 3 repeats; D1 means the D1 run
in the same batch.

1. **Target improves.** EFF-S-partner is no longer ACCEPTed: the majority is WEAKEN, with revisions that qualify or drop
   the speed claim. EFF-U2-partner is not STRENGTHENed.
2. **No regressions.** No probe that D1 gets right becomes wrong in D1c. A probe whose correctness depends on a borderline
   acceptable set (EFF-U2-partner, CON-U2-partner) is reported, but does not by itself decide the outcome.
3. **No new over-caution.** No new unnecessary WEAKEN on the 15 ACCEPT probes, especially the same-condition comparisons
   SIG-S-strong, CON-S-strong, EFF-S-strong and GEN-S-strong. False STRENGTHEN stays at 0 of 27 probes.
4. **Revisions are evidence-supported.** Every D1c revision on the EFF probes and on any probe whose decision changed is
   read by the agent, and the representative ones go on the student review sheet. Revisions that add caveats which the
   package does not support count as regressions.

If criterion 1 fails, or criterion 2, 3 or 4 shows a meaningful regression, **D1 is kept** and the result is reported
as a negative finding. The scope-anchoring subgroup (GEN-U, ROB-U, EFF-U) is reported separately and is not a target.

## Results (run `e2b_v1`, 2026-10-25; 234 runs, $0.030, 0 invalid decisions)

Tables: `v2/results/e1e2/e2b_v1/` (`TABLES.md`, `COMPARE_D1_vs_D1c.md`, `COMPARE_D1_run1_vs_run2.md`).

| Measure (probe level, majority of 3) | D1 (same batch) | D1c |
|---|---|---|
| Correct STRENGTHEN, all (of 12) | 9 | 9 |
| …claim-level (of 9) / scope-anchoring subgroup (of 3), post hoc | 9 / 0 | 9 / 0 |
| ACCEPT correct (of 15) | 14 | 14 |
| WEAKEN/REMOVE correct (of 12) | 12 | 12 |
| False STRENGTHEN (of 27 probes / of 81 runs) | 0 / 1 | 0 / 1 |
| Probes whose correctness changed D1 → D1c | | 0 improved, **0 regressed** |
| Stable probes (of 39) | 35 | 34 |

Target probes, run level:

| Probe | D1 | D1c |
|---|---|---|
| EFF-S-partner ("decodes faster", different hardware; should WEAKEN) | WEAKEN 2/3, ACCEPT 1/3 | **WEAKEN 3/3** |
| EFF-U2-partner ("may decode faster", different hardware; ACCEPT, or WEAKEN that only adds the caveat) | ACCEPT 3/3 | ACCEPT 1/3, WEAKEN with caveat 2/3 |
| EFF-S-strong (same hardware; should ACCEPT) | ACCEPT 3/3 | ACCEPT 3/3 |
| EFF-U2-strong (same hardware; should STRENGTHEN) | STRENGTHEN 3/3 | STRENGTHEN 3/3 |

All D1c WEAKEN revisions on the EFF partner case state both latencies and the different accelerators, and none keeps an
unqualified speed claim (agent reading; student check items C2/C3). No same-condition comparison (SIG-S, CON-S, GEN-S,
EFF-S on the strong cases) received a new caveat.

**Criteria.** Criteria 1–3 are met by D1c. Criterion 4 is met on the agent's reading, with the student check pending.
However, the **same-batch D1 also meets criterion 1**: its majority on EFF-S-partner is already WEAKEN in this batch.
The difference between D1 and D1c is one run of three on EFF-S-partner and two caveat-only runs on EFF-U2-partner. That
is smaller than the run-to-run variation documented below. **D1c therefore shows no clear benefit, and D1 is kept**
(decision rule of 2026-10-25). D1c is recorded as harmless but not adopted.

### Run-to-run variation of D1 (important for every comparison)

The D1 prompt, schema, code path, model, routing and decoding are byte-identical between `e1e2_v1` (2026-10-24) and
`e2b_v1` (2026-10-25). Both batches were served by the same provider (StreamLake). Yet:

* claim-level STRENGTHEN runs went from 18/27 to 26/27;
* at probe level, 3 probes improved (SIG-U-strong, CIT-U-strong, EFF-S-partner) and none regressed.

Temperature 0 is therefore far from deterministic across batches or days. Consequences:

1. The E1/E2 difference between D1 (7/12) and D2 (9/12) in `e1e2_v1` is no larger than D1's own batch-to-batch shift
   (7/12 → 9/12). **D2's apparent recall advantage cannot be attributed to its prompt.** Its false-strengthening pattern
   on the comparability trap remains a real reason not to use it.
2. Every comparison must be made **within one batch**, with all compared conditions run together and interleaved, and
   with repeats. Results from different batches are reported only as context.
3. For E5, D1-oracle has to be re-run in the same batch as D1-tools rather than reused.
