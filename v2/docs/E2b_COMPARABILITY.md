# E2b: one minimal comparability addition to D1 (DEV only, exploratory)

**Status: design fixed before the run.** Follows [`E1_E2_RESULTS.md`](E1_E2_RESULTS.md) section 4.

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
