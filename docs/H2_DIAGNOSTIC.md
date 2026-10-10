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
RESULTS_PLACEHOLDER
