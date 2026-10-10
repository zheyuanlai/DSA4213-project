# Supplementary H2 Failure Diagnostic (EXPLORATORY)

**Status:** the design below was committed before any diagnostic call. The diagnostic is run **once** (run tag `h2diag_v1`).
It is exploratory and is not part of the pre-registered primary analysis. Primary TEST results, prompts, configurations and annotation
packets are unchanged. DEV cases only: nothing from the TEST split is read, and no private label or system mapping is involved.

## Why
In the primary run, no verifier ever chose STRENGTHEN: 0 of the **406** claims verified by C3–C6 on the 32 TEST cases (C3 103, C4 103, C5 103, C6 97). This was also 0 in every other run: DEV pilots, real-paper runs and the long-package diagnostic. So H2 could not be tested as designed.
This diagnostic asks *where* strengthening fails: whether the decisive evidence is never retrieved, whether understatement is noticed
but ACCEPTed anyway, or whether the verifier simply does not treat understatement as an error.

## Materials: 12 counterfactual drafts (`data/diagnostic/h2_counterfactual_drafts.json`)
No such drafts existed before this step. They were written for this diagnostic by the coordinating AI agent under one rule, fixed in advance.
The DEV split has exactly six ℓ=2 cases, one per ordinal category, each with a matched pair partner of gold ℓ=1 or ℓ=0.
Both members of a pair receive the **identical one-sentence draft**, built only from evidence the two cases share:

| Pair | Probe type (post-hoc label, see Revision) | Understated draft (gold 2) | Matched control (identical text) | Decisive evidence only in the gold-2 case |
|---|---|---|---|---|
| SIG | claim strengthening | SIG-p1a | SIG-p1b (gold 1) | paired t-test `S2` for Tessaline vs Varrow-NMT |
| CON | claim strengthening | CON-p1a | CON-p1b (gold 1) | Ivel-Fraud cells `T1.r3.*` (a win: 6/6 vs 5/6) |
| EFF | claim strengthening | EFF-p1a | EFF-p1b (gold 1) | same-hardware latency `T1.r{1,2}.lat`, `T1.r2.src` |
| ROB | omitted-finding recovery | ROB-p1a | ROB-p1b (gold 0) | label-noise table `T2` |
| GEN | omitted-finding recovery | GEN-p1a | GEN-p1b (gold 0) | held-out-domain rows `T1.r3–r5` |
| CIT | omitted-finding recovery | CIT-p1b | CIT-p1a (gold 0) | passage `P1` stating the 31% reduction |

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
| 2. False strengthening (STRENGTHEN on 6 matched controls) | 0 / 6 (see caveat below) | 0 / 6 |
| 3. At least one listed decisive evidence ID returned (understated drafts) | 3 / 6 | 4 / 6 |
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

### Revision after external review (documentation-only; no re-run, no prompt or code change to the agent)

**Two kinds of probe.** The six understated drafts test two different abilities, and they are reported separately here. This grouping is a
post-hoc label added after the run; the drafts and the run are unchanged.
* **Claim strengthening (SIG, CON, EFF):** the draft states the focal comparison, but more weakly than the evidence allows
  ("higher mean BLEU" when a significant test exists; "most of the six datasets" when all six are wins; fewer decoder passes when same-hardware
  latency also shows a speedup). This is what the per-sentence STRENGTHEN action is meant to fix. CON ("most" → "all six") is the purest case.
* **Omitted-finding recovery (ROB, GEN, CIT):** the draft reports a different accurate fact (seed stability, in-distribution scores,
  the procedure's citation) and omits the focal finding. Recovering it requires *adding* a conclusion, not rewording one, so these probes
  test more than STRENGTHEN was designed for.

| Probe type | Condition | STRENGTHEN | ≥ 1 listed decisive ID returned | all listed decisive IDs returned (post-hoc) | rationale states the stronger fact (post-hoc reading) |
|---|---|---|---|---|---|
| claim strengthening (n=3) | C4 | 0 / 3 | 3 / 3 | 3 / 3 | 2 / 3 (SIG, CON) |
| claim strengthening (n=3) | C5 | 0 / 3 | 3 / 3 | 3 / 3 | 2 / 3 (SIG, CON) |
| omitted-finding recovery (n=3) | C4 | 0 / 3 | 0 / 3 | 0 / 3 | 0 / 3 |
| omitted-finding recovery (n=3) | C5 | 0 / 3 | 1 / 3 (GEN) | 1 / 3 (GEN) | 0 / 3 |

**How retrieval was measured.** The pre-registered measure counts a run as "retrieved" if **at least one** listed decisive evidence ID was returned.
That says nothing about whether *all* the decisive evidence was obtained. A stricter post-hoc check gives the same counts here: in every run
with at least one hit, all listed IDs were returned. The list is our own definition of decisive evidence (for EFF: both latency cells and the
timing-source cell; the table note stating that all latencies were measured on the same hardware comes with the same lookup).

**False strengthening.** 0/6 on the controls does **not** show that strengthening is safe. C4 never chose STRENGTHEN on any draft, so it never had
the chance to strengthen wrongly. This result must not be presented as a safety advantage.

**Interpretation (exploratory; DEV only, one backbone, n = 3 per probe type).**
* The clearest evidence comes from **SIG and CON**. In both conditions the verifier retrieved the decisive evidence and wrote the stronger fact into
  its rationale ("a significant paired t-test (p=0.017) is also reported"; "indeed all six"), yet ACCEPTed the weaker sentence because
  "the claim does not overstate". EFF also retrieved its decisive cells, but the rationale never mentioned latency. Recognizing that EFF supports a
  speed claim also requires seeing that the timings come from the same hardware.
* The mechanism this suggests: **the verifier treats a claim as acceptable whenever the evidence supports it, even when the evidence warrants a
  stronger statement.** In practice it behaves as an overstatement checker, not a bidirectional calibration agent. It did not follow the verifier
  prompt's instruction to STRENGTHEN when its rationale identifies an understated part.
* In the omitted-finding probes, the failure happened earlier, at **retrieval**: the verifier checked only the evidence the sentence itself cites
  (table T1 and the cited rows or numbers), so the label-noise table, the held-out rows (C4) and the passage reporting the 31% reduction were never seen.
* Two separate obstacles are therefore visible: incomplete retrieval of evidence that would support stronger conclusions, and acceptance of supported
  but unnecessarily weak claims. With identical C4 and C5 outputs, the STRENGTHEN-vs-no-STRENGTHEN contrast of H2 is empty for this backbone and verifier design.

**Suggested wording for the report** (hedged: one backbone, a handful of DEV cases):
> In the primary experiments, enabling strengthening did not lead to any STRENGTHEN actions. A supplementary DEV-only diagnostic with
> deliberately weaker drafts showed the same pattern: the full verifier accepted all six probes without revision. Trace analysis identified two
> failure modes: incomplete retrieval of evidence supporting stronger conclusions, and acceptance of supported but unnecessarily weak claims.
> These findings suggest that allowing strengthening as an action is insufficient to induce bidirectional claim calibration.

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
