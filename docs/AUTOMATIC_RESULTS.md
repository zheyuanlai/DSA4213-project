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
  A supplementary **exploratory** DEV diagnostic with 12 injected counterfactual drafts (`docs/H2_DIAGNOSTIC.md`) found no STRENGTHEN at all: 0/6 on deliberately understated drafts. C4 and C5 outputs were identical (12/12). On the 3 pure claim-strengthening probes (SIG, CON, EFF), the decisive evidence was retrieved in every run, and in SIG and CON the rationale stated the stronger fact, yet the verifier ACCEPTed. On the 3 omitted-finding probes (ROB, GEN, CIT), the decisive evidence was mostly never retrieved (C4 0/3, C5 1/3). The 0/6 false strengthening on controls is not a safety result, because the verifier never strengthened anything.
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

Tables: `results/automatic/real_papers_v2/TABLES.md`. There is no gold, so there are no PROXY levels. Claim support and readability are **human-only and PENDING**.

* **`real_v1` (frozen protocol, kept and reported):** 35/48 runs completed: C1 12/12, C2 11/12, C3 6/12, C4 6/12. On 6 papers the 700-token
  outline JSON was truncated twice, so C3/C4 failed there. On 1 paper the C2 reviser was truncated. The frozen limits had been tuned on short synthetic packages
  and did not transfer to real papers. Real-paper passages are ~150 words vs ~90 on the synthetic cases.
* **`real_v2` (amended token limits, `configs/amended_secondary.yaml`, all papers and all conditions re-run):** **46/48 completed**. C1 and C2 12/12;
  C3 and C4 11/12. RP-02's outline was still truncated at 1500 tokens, and the limits were not raised again, to avoid rerunning until success.
  The real-paper **annotation packet is built from `real_v2`**: 39 distinct texts, 151 sentence rows.
* Verifier decisions on real papers: C3 4 WEAKEN / 39 ACCEPT, C4 2 / 41, with no STRENGTHEN, REMOVE or FLAG. Passages changed: C3 33%, C4 17%.
  Numbers not derivable from the package: 0.
* **Adaptive vs scripted (11 papers where both completed):** C4 − C3 = −3.27 tool calls per paper (95% CI [−4.55, −2.00]), −$0.0005 (CI [−0.0006, −0.0003]).
  The adaptive verifier used 3.16 tools per claim; the scripted one used the fixed 4 on all 43 claims.

## 4. Long-package diagnostic (exploratory; 8 cases × C7/C3/C4; design frozen in `docs/DIAGNOSTIC_LONG_PACKAGES.md`)

Tables: `results/automatic/diagnostic_long/TABLES.md`. Run `diag_v2` under the amended config. **24/24 completed.**

* **Tool use:** the adaptive verifier used **2.34 tools per claim** (19 of 32 claims stopped after 2 checks, 3 after 1). The scripted verifier used 4 on all 32 claims.
  Per case: C4 − C3 = **−6.63 tool calls** (95% CI [−8.00, −5.25]), −$0.0007 (CI [−0.0008, −0.0005]), −11.3 s summed latency (CI [−17.2, −5.3]).
  The saving relative to the fixed checklist is larger than on the short synthetic packages (−3.66 per case), which is the direction the proposal anticipated.
* **Edits:** both verifiers made exactly 1 WEAKEN on 32 claims, and the remaining decisions were ACCEPT. Passages changed: 12.5% in both.
* **PROXY (UNVALIDATED; n = 7, CIT excluded):** identical for C7, C3 and C4 (0.43 match, 0.14 above gold, 0.43 below gold). With n = 7 and an unvalidated proxy,
  nothing can be concluded about correctness. Taken at face value, the many "below gold" cases would suggest understated drafts that no verifier strengthened.
  That can be checked only by human annotation of these outputs, which is optional and not in the primary packet.

## 5. Spend and provider reconciliation

From `outputs/ledger_summary.json` (generated by `python scripts/summarize_ledger.py --reconcile`):

| stage | USD |
|---|---|
| preflight (probes) | 0.0003 |
| dev (3 DEV pilots) | 0.2636 |
| main (primary TEST run) | 0.2334 |
| real (`real_v1` 0.0615 + `real_v2` 0.0929) | 0.1544 |
| buffer (`diag_v2`) | 0.0461 |
| **total new spend** | **0.6978** |

`GET /api/v1/key` at 13:42 UTC reported usage **$0.6978** (limit $15, remaining $14.30), against $0 at the start.
**The ledger and OpenRouter's own counter differ by $0.000002.** The 16 error entries (HTTP 404/429 routing and rate-limit errors, logged at $0) therefore carried no hidden charges.
All but $0.000008 is provider-reported `usage.cost` (the remainder is back-filled manual probes). The hard cap was $12, and the $3 reserve is intact.
Serving providers for successful calls: StreamLake 4,551, Parasail 324, DeepInfra 8, Together 1 (manual probe), Alibaba 3 (Qwen probes).
