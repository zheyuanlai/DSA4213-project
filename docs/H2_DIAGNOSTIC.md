# Supplementary H2 Failure Diagnostic (EXPLORATORY)

**Status:** the design below was committed before any diagnostic call. The diagnostic is run **once** (run tag `h2diag_v1`).
It is exploratory and is not part of the pre-registered primary analysis. Primary TEST results, prompts, configurations and annotation
packets are unchanged. DEV cases only: nothing from the TEST split is read, and no private label or system mapping is involved.

## Why
In the primary run, no verifier ever chose STRENGTHEN (0 of 488 verified claims across C3–C6), so H2 could not be tested as designed.
This diagnostic asks *where* strengthening fails: whether the decisive evidence is never retrieved, whether understatement is noticed
but ACCEPTed anyway, or whether the verifier simply does not treat understatement as an error.

## Materials: 12 counterfactual drafts (`data/diagnostic/h2_counterfactual_drafts.json`)
No such drafts existed before this step. They were written for this diagnostic by the coordinating AI agent under one rule, fixed in advance.
The DEV split has exactly six ℓ=2 cases, one per ordinal category, each with a matched pair partner of gold ℓ=1 or ℓ=0.
Both members of a pair receive the **identical one-sentence draft**, built only from evidence the two cases share:

| Pair | Understated draft (gold 2) | Matched control (identical text) | Decisive evidence only in the gold-2 case |
|---|---|---|---|
| SIG | SIG-p1a | SIG-p1b (gold 1) | paired t-test `S2` for Tessaline vs Varrow-NMT |
| CON | CON-p1a | CON-p1b (gold 1) | Ivel-Fraud cells `T1.r3.*` (a win: 6/6 vs 5/6) |
| EFF | EFF-p1a | EFF-p1b (gold 1) | same-hardware latency `T1.r{1,2}.lat`, `T1.r2.src` |
| ROB | ROB-p1a | ROB-p1b (gold 0) | label-noise table `T2` |
| GEN | GEN-p1a | GEN-p1b (gold 0) | held-out-domain rows `T1.r3–r5` |
| CIT | CIT-p1b | CIT-p1a (gold 0) | passage `P1` stating the 31% reduction |

So each draft is exactly calibrated on the control, where the correct action is ACCEPT (or any non-strengthening decision),
and understated on the gold-2 case, where the correct action is STRENGTHEN.

## Procedure
* Conditions: **C4** (adaptive verifier, STRENGTHEN allowed) and **C5** (adaptive verifier, STRENGTHEN not allowed), both starting from
  the identical injected draft. 12 drafts × 2 conditions = 24 verifications, one claim each.
* Backbone, decoding, routing: `configs/frozen_primary.yaml` (DeepSeek V4 Flash 0731, temperature 0, reasoning off). Tools and the
  4-call evidence budget are the originals. Prompts are the frozen verifier prompts. The verifier code is the frozen logic plus the
  post-run repair-path reply fix (`docs/FINAL_AUDIT.md`), which affects only turns where a decision is invalid.
* Script: `scripts/run_h2_diagnostic.py` (it refuses a second run under the same tag). Cost stage `buffer`.

## Pre-registered measures (`scripts/analyze_h2_diagnostic.py`)
1. **Correct strengthening recovery:** STRENGTHEN decisions on the 6 understated drafts (C4; C5 cannot strengthen).
2. **False strengthening:** STRENGTHEN decisions on the 6 matched controls.
3. **Decisive evidence retrieved:** whether any decisive evidence ID (above) appears among the IDs returned by the verifier's tool calls for that claim.
4. **Recognized understatement but ACCEPT:** ACCEPT decisions whose rationale matches a fixed recognition phrase list
   (`RECOGNITION` regex in the script). All rationales are also reported verbatim, so readers can judge for themselves.
5. **C4 vs C5 final expressed strength:** whether the final texts differ, plus the lexical PROXY level of each final text
   (UNVALIDATED; not available for CIT). All 24 final texts are listed so a human can read them.

No prompt, model, tool or budget will be changed in response to the results, and the diagnostic will not be re-run.

## Results
Run tag `h2diag_v1`, run once on 2026-10-10. **24/24 verifications completed**, with 0 invalid decisions.
Cost: C4 $0.0060 + C5 $0.0053 = **$0.0113** (stage `buffer`).
Per-run table: `results/h2_diagnostic/TABLES.md` and `per_run.csv`. Traces: `outputs/h2_diagnostic/`.

### Pre-registered measures

| Measure | C4 (STRENGTHEN allowed) | C5 (STRENGTHEN disabled) |
|---|---|---|
| 1. Correct strengthening recovery (STRENGTHEN on 6 understated drafts) | **0 / 6** | 0 / 6 (not allowed) |
| 2. False strengthening (STRENGTHEN on 6 matched controls) | **0 / 6** | 0 / 6 |
| 3. Decisive evidence retrieved (understated drafts) | 3 / 6 | 4 / 6 |
| 4. ACCEPT on understated drafts / ACCEPT with a pre-registered recognition phrase | 6 / 6 / **1** | 6 / 6 / **0** |
| 5. Final texts identical between C4 and C5 | **12 / 12** (every draft left unchanged in both) | |
| PROXY final strength differs C4 vs C5 (UNVALIDATED) | 0 drafts | |

Every one of the 24 decisions was ACCEPT, and no text was edited. **C4 and C5 did not differ at all in final expressed claim strength.**

### Where it failed (trace analysis)

**Stage 1: the decisive evidence was often never looked at.** The verifier checks the evidence a sentence *refers to*, not evidence that would support a stronger answer to the question.
* ROB (both conditions): only `T1` (the seed table the sentence cites) was looked up. The label-noise table `T2` was never requested.
* CIT (both): the verifier checked the three numbers and never called `retrieve_passage`, so it never saw that P1 states the 31% reduction.
* GEN (C4 only): `lookup_table` was called only on rows r1 and r2 (the rows the sentence cites), so the held-out-domain rows r3–r5 were never returned.
  C5 happened to request the whole table and did receive them.

**Stage 2: even when the decisive evidence was retrieved, the verifier accepted the weaker claim.** Of the 7 understated runs with decisive evidence
retrieved, the rationale *explicitly stated the stronger fact* in 4 (post-hoc reading by the coordinating AI agent; the pre-registered phrase
list caught only 1, because it missed phrasings such as "indeed all six"):
* SIG, C4: "…a significant paired t-test (p=0.017) is also reported but the claim does not overstate." → ACCEPT
* SIG, C5: "A paired t-test (S2) reports p=0.017, significant at alpha=0.05, supporting the higher-mean claim." → ACCEPT
* CON, C4: "Ferrule exceeds Arbor-GBT on all six datasets … 'Most of the six' is supported." → ACCEPT
* CON, C5: "'Most of the six' is supported (indeed all six)." → ACCEPT
In the other 3 (EFF in both conditions: the same-hardware latency cells were returned; GEN in C5: the held-out rows were returned), the rationale did not mention the decisive evidence.

**Interpretation (exploratory; n = 6 per role, DEV only, one model):** the primary-run absence of STRENGTHEN is not explained only by drafts lacking understatement.
With deliberately understated drafts and STRENGTHEN available, the frozen verifier still never strengthened. It (i) anchors retrieval on the claim's
own references, and (ii) uses an acceptance criterion of "supported and not overstated". It treats understatement as acceptable even when it
writes down the stronger evidence, despite the verifier prompt's instruction to STRENGTHEN when the rationale identifies an understated part.
The verifier is conservative rather than miscalibrated upward (0/6 false strengthening). With identical outputs in C4 and C5, H2's
STRENGTHEN-vs-no-STRENGTHEN contrast is empty for this backbone and verifier design. Two structural caveats: three drafts (ROB, GEN, CIT)
report a *different* accurate fact rather than a weak version of the focal claim, so recovering them needs the verifier to add the focal
finding. That is closer to an "add" action than to rewording one sentence. The SIG, CON and EFF drafts do state the focal comparison at weaker strength.

### All 24 decisions
| draft | condition | decision | final text |
|---|---|---|---|
| H2-SIG-U | C4 | ACCEPT | unchanged |
| H2-SIG-C | C4 | ACCEPT | unchanged |
| H2-CON-U | C4 | ACCEPT | unchanged |
| H2-CON-C | C4 | ACCEPT | unchanged |
| H2-EFF-U | C4 | ACCEPT | unchanged |
| H2-EFF-C | C4 | ACCEPT | unchanged |
| H2-ROB-U | C4 | ACCEPT | unchanged |
| H2-ROB-C | C4 | ACCEPT | unchanged |
| H2-GEN-U | C4 | ACCEPT | unchanged |
| H2-GEN-C | C4 | ACCEPT | unchanged |
| H2-CIT-U | C4 | ACCEPT | unchanged |
| H2-CIT-C | C4 | ACCEPT | unchanged |
| H2-SIG-U | C5 | ACCEPT | unchanged |
| H2-SIG-C | C5 | ACCEPT | unchanged |
| H2-CON-U | C5 | ACCEPT | unchanged |
| H2-CON-C | C5 | ACCEPT | unchanged |
| H2-EFF-U | C5 | ACCEPT | unchanged |
| H2-EFF-C | C5 | ACCEPT | unchanged |
| H2-ROB-U | C5 | ACCEPT | unchanged |
| H2-ROB-C | C5 | ACCEPT | unchanged |
| H2-GEN-U | C5 | ACCEPT | unchanged |
| H2-GEN-C | C5 | ACCEPT | unchanged |
| H2-CIT-U | C5 | ACCEPT | unchanged |
| H2-CIT-C | C5 | ACCEPT | unchanged |

As pre-registered, the diagnostic was not re-run and no prompt, model, tool or budget was changed in response to these results.
