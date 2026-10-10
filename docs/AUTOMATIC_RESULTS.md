# Automatic Results (pre-human; NOT calibration results)

> **Read this first.** Everything here is either **rule-verified** (deterministic and checkable against the package or the
> billing records) or a **PROXY** (a lexical heuristic, explicitly labelled UNVALIDATED). The pre-registered primary outcomes are calibration
> accuracy, overstatement and understatement for H1–H3. They require the **two blind human annotators** and are **PENDING**.
> Annotators must not read this file before submitting their labels.

Exact tables (generated from the result files, not hand-copied): `results/automatic/synthetic_test/TABLES.md`.
Figures: `results/automatic/synthetic_test/figures/`. Per-run rows are kept in `private/auto_eval/` until annotation ends,
because they would let a reader link texts to conditions.

## 1. Primary held-out run (32 TEST cases × 7 conditions)

* **Completion: 224/224 runs completed**, 0 failed. Zero protocol errors, zero invalid verifier decisions. Zero truncated or format-repaired
  generations in the shared drafts and in the C2 revisions. Run tag `primary_v1` under the frozen protocol (`benchmarks/freeze_manifest.json`).
* **Cost (provider-reported `usage.cost`):** $0.233 for the whole primary run. Mean per case: C1 $0.00023, C2 $0.00068, C7 $0.00060, C6 $0.00163,
  C5 $0.00191, C4 $0.00209, C3 $0.00241. Per-condition costs include the shared upstream draft (`docs/DEVIATIONS_FROM_PROPOSAL.md` #3).
* **Calls:** model calls per case: C1 1, C2 3, C7 2, C6 12.9, C4 14.4, C5 14.7, C3 18.1. Evidence-tool calls per case: C3 12.9, C4 9.2, C5 9.5, C6 8.9.
* **Verifier decisions (claims):** C3 5 WEAKEN / 98 ACCEPT; C4 9 / 94; C5 7 / 96; C6 9 / 88.
  **No STRENGTHEN, REMOVE or FLAG decision occurred in any condition**, and none occurred on DEV either.
  Passages changed from their starting draft: C3 15.6%, C4 25.0%, C5 21.9%, C6 25.0% (C2's generic revision rewrote 100%).
* **Numeric grounding (rule):** 0 of 375–459 numbers per condition were non-derivable from the package. This metric is a *lower bound* on numeric errors:
  a wrong number can coincide with a derivable one. For example, DEV showed wrong margin ranges whose endpoints were each some real margin.
* **NUM cases, value presence (rule; entity association needs humans):** 0.866 of the gold numeric values appear in C1/C2/C6 passages
  vs 0.723 in the outline-based C3/C4/C5/C7 passages (n = 4 cases, so this is descriptive). Verification did not change this metric, because no verifier adds content.

### 1.1 H3-relevant automatic contrast (adaptive C4 vs scripted C3; identical starting drafts)
| metric (per case) | C4 − C3 | case-bootstrap 95% CI | matched-pair CI |
|---|---|---|---|
| evidence-tool calls | −3.66 | [−4.19, −3.16] | [−4.19, −3.09] |
| model calls | −3.66 | [−4.19, −3.16] | [−4.19, −3.09] |
| cost (USD) | −0.0003 | [−0.0004, −0.0003] | [−0.0004, −0.0003] |
| summed latency (s) | −4.0 | [−6.2, −1.6] | [−6.3, −1.3] |

The adaptive verifier stopped after 2 checks for 42% of claims and used 2.86 tools per claim on average. The scripted verifier always used 4.
Its most frequent trajectories were `lookup_table → get_test_metadata` (31 claims) and `lookup_table → compare_numbers ×3` (23 claims).
In all 103 scripted claims, the provider enforced the fixed four-tool order, with no early decisions.
**Whether this reduction costs or gains correctness can be decided only with the human labels.** The PROXY shows identical outcomes for C3 and C4.

### 1.2 Other automatic contrasts (see TABLES.md for all CIs)
* C4 vs C5 (H2; identical drafts, STRENGTHEN allowed vs not): since STRENGTHEN never fired, the two differ only by sampling in the
  verification calls (passages changed: 25.0% vs 21.9%). **H2 cannot be tested as intended on this backbone and benchmark**, because there was no strengthening behaviour to compare.
  This is a substantive (negative) automatic finding. Human labels will still show whether the C5/C4 edits introduced understatement.
* C4 vs C2 (H1): C4 costs +$0.0014/case and is slower. C2 changes every passage, while C4 changes 25%. Calibration effects are PENDING.
* The adaptive verifier often tried to issue several tool calls per turn (164–168 extra calls per condition, answered `NOT_EXECUTED`; `docs/DEVIATIONS_FROM_PROPOSAL.md` #9).

### 1.3 PROXY (lexical, UNVALIDATED; 20 cases per condition from SIG/ROB/GEN/CON/EFF; CIT is not proxied)
Share where the lexical level equals gold: C1 0.70, C2 0.80, C3 0.75, C4 0.75, C5 0.70, C6 0.70, C7 0.75. All paired differences have CIs including 0.
The heuristics were tuned on DEV only, and their agreement with human labels is unknown. **Do not cite these as calibration accuracy.**

## 2. Edit examples (DEV only; TEST examples are released after annotation)

The demo traces below are DEV cases. Every TEST verifier edit (30 in total), with its tools, rationale and before/after text, is in
`private/auto_eval/TEST_edit_examples.md`, to be released after annotation. Reading those TEST edits as the coordinator
(not as an annotator) showed several correct numeric repairs, removals of significance language where no test was reported, and at least
one apparently harmful over-weakening. In that case a supported generalization claim on a gold-ℓ=2 case was replaced by a caveat about
missing significance tests, conflating generalization with significance. That is exactly the H2 risk. Its human label is pending.

**(a) Numeric repair (DEV CON-p1a, adaptive verifier).** Trajectory: `lookup_table(T1)` → `compare_numbers(3.6, T1.r1.fer − T1.r1.lr)` → actual 4.4,
no match → two more `compare_numbers` → WEAKEN, citing the 12 cells.
Before: "…with larger margins of 3.6–4.4 percentage points." After: "…with margins of 3.3–4.6 percentage points." (Correct: the true margins are 4.4, 4.3, 4.2, 3.3, 4.6, 3.6.)

**(b) Removal of a misattributed citation (DEV CIT-p1a, no-outline verifier).** Trajectory: `lookup_table(T1)` → `retrieve_passage(P1)` →
two `compare_numbers` → WEAKEN, citing T1 cells and P1. Rationale: "the retrieved P1 passage describes the filtering method but reports no reduction figure".
The clause "…and also exceeds the roughly 30% reduction reported … by Varga & Sandoval (2021)" was removed.
The verifier left the arithmetic slip "26.5%" (the true value is 27.2%) in place, even though its own `compare_numbers` call returned 27.15.

**(c) Imperfect correction (DEV CON-p1b, no-strengthen verifier).** The verifier replaced a wrong range "3.6 to 7.1" with "3.3 to 4.6". The true range is 2.8–4.6:
on Ivel-Fraud the margin is 92.3 − 89.5 = 2.8. Its four tool calls never checked that row.

**(d) STRENGTHEN:** no example exists. The decision never occurred on DEV or TEST.

## 3. Real-paper study (12 CC-licensed papers × C1–C4)
PENDING write-up. real_v1 (frozen protocol): C1 12/12, C2 11/12, C3 6/12, C4 6/12 completed (outline/reviser truncation). real_v2 (amended token limits): 45/48 jobs completed at the last check, RP-02 C3/C4 failed (outline truncated even at 1500 tokens). The real-paper annotation packet has NOT been built yet.

## 4. Long-package diagnostic (exploratory; 8 cases × C7/C3/C4)
PENDING: diag_v2 was queued to run after real_v2. Check outputs/diagnostic/ and the ledger for its status.

## 5. Spend and provider reconciliation
See outputs/ledger_summary.json (run `python scripts/summarize_ledger.py --reconcile`). At 11:49 UTC the ledger showed $0.395 vs key usage $0.389. Total spend stays far below the $12 cap.
