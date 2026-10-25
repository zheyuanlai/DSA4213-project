# V2 research summary and technical handoff

*For group members who know V1 (PaperPilot) but have not followed V2. Written 2026-10-25. Branch `v2-calibration`
(local; not yet pushed or merged). V1 files and results are unchanged.*

**One-sentence summary.** V1's verifier never strengthened an understated claim. We traced this mainly to how it
**decides**, not to what it **retrieves**. A small prompt-and-schema change (D1) makes it strengthen on new, held-out
items without false strengthening. Natural writer drafts, however, almost never contain such opportunities.

**Evidence tiers used throughout.**

* **[DEV]**: our own 39 diagnostic probes, used for development (E1–E5).
* **[TEST]**: the independent, frozen Phase 4 held-out benchmark.
* **[V1-retro]**: observations from V1's existing frozen records and AI labels; no new runs.

## 1. Motivation

* **[V1-retro]** V1's hypothesis H2 was that a verifier that can STRENGTHEN as well as WEAKEN calibrates claims in both
  directions. In V1, **no verifier ever chose STRENGTHEN**:
  * 0 of 406 verified TEST claims (C3–C6);
  * 0 of 86 real-paper claims;
  * 0 of 64 long-package claims.
* **[V1-retro]** V1's own H2 diagnostic also produced 0 STRENGTHEN on 6 deliberately understated DEV drafts. H2 therefore
  could not be tested.
* **V2's question:** why did STRENGTHEN never happen, and can a targeted fix make it happen correctly?

## 2. Failure diagnosis (E1/E2, [DEV])

Three explanations were considered:

* **A. Evidence acquisition:** the verifier never retrieves the evidence for a stronger claim.
* **B. Decision framework:** it sees the evidence but still accepts a weak claim.
* **C. Opportunity scarcity:** natural drafts rarely understate.

**Design.** 39 single-sentence DEV probes built from DEV matched pairs, with identical draft text on both members of a
pair: 12 should be STRENGTHENed, 15 ACCEPTed and 12 WEAKENed/REMOVEd. To isolate B from A, the verifier was also run
with the **complete evidence in its context** ("oracle"), with no tools. Each probe was run 3 times
(`v2/docs/E1_E2_RESULTS.md`).

| [DEV] `e1e2_v1` | V1 with tools | V1 decision, oracle evidence | **D1, oracle** | D2, oracle |
|---|---|---|---|---|
| Correct STRENGTHEN (of 12) | 0 | 0 | 7 | 9 |
| False STRENGTHEN (of 27) | 0 | 0 | 0 | 1 |

**What we learned.**

* **A is not the main cause on these probes.** Even with perfect evidence, the V1 decision prompt strengthened 0 of 12.
  With tools, V1 had retrieved the decisive evidence in 33 of its 36 failed runs.
* **B is the main cause.** Most V1 failures were "noticed the stronger fact, judged the weak claim acceptable". Typical
  rationales:
  * "'Most' is a correct, if conservative, description";
  * "a significant paired t-test (p=0.017) … the claim does not overstate".

  V1 checks whether a sentence is *supported*, not whether it is *as strong as the evidence allows*.
* **A separate failure type, scope anchoring.** Three probes state only a sub-claim (one domain, one noise rate, a proxy
  metric). Every variant failed them. Fixing them would mean *adding* a finding rather than strengthening the same one.
  They are reported as a separate post-hoc subgroup and excluded from later targets.

**Two methodological lessons**
(`v2/docs/E2b_COMPARABILITY.md`, `v2/docs/REPRODUCIBILITY_AUDIT.md`):

* **Inference variability.** An identical D1 re-run one day later gave 9/12 instead of 7/12. The request bytes, model
  version, provider and settings were all identical. Temperature 0 is not deterministic, so all later comparisons run
  the compared conditions **in one interleaved batch with 3 repeats**. D2's apparent advantage over D1 was within this
  noise. D2 also falsely strengthened a speed claim that rested on non-comparable hardware, so it was dropped.
* **A one-paragraph "comparability" addition (D1c)** showed no clear benefit over D1 in the same batch, and was not
  adopted.

## 3. The V2 modification: D1

Only the decision instructions and the decision schema change. Before deciding, the verifier must fill four fields:

1. `proposition`: what the sentence claims;
2. `expressed_strength`: how strongly it says it, quoting the words that set the strength;
3. `strongest_supported`: the strongest version of the **same** proposition that the evidence supports, written as one
   sentence;
4. `support_relation`: STRONGER_SUPPORTED / MATCHES / WEAKER_SUPPORTED / NOT_SUPPORTED / UNDETERMINED.

The prompt then maps the relation to a decision (STRONGER → STRENGTHEN, MATCHES → ACCEPT, and so on). The mapping is
**not** enforced in code: E1/E2 showed that the model's actions almost always follow its own relation.

| Unchanged from V1 | Changed |
|---|---|
| Backbone (DeepSeek V4 Flash, temperature 0, reasoning off), provider routing, the V1 adaptive prompt and tool procedure, the 4 evidence tools and 4-call budget, validation, the 6-claim cap | + D1 addendum (`v2/prompts/verifier_oracle_d1_addendum.md`); + four judgement fields in `submit_decision`; per-turn token limit 450 → 800 (the comparison conditions use 800 too) |

Implementation: `v2/verifier_tools.py`, a faithful port of V1's tool loop with an injectable prompt and schema. An
equivalence test against V1 shows identical behaviour when given V1's prompt and schema.

## 4. E5: D1 inside the real tool loop ([DEV])

E5 asked whether the improvement survives when the verifier must fetch evidence through V1's tools
(`v2/docs/E5_RESULTS.md`; one batch, 3 repeats).

| [DEV] `e5_v1` | V1 code (800 tokens) | **D1-tools** | D1-oracle |
|---|---|---|---|
| Correct STRENGTHEN, claim-level probes (of 9) | 0 | **8** | 9 |
| False STRENGTHEN (of 27) | 0 | 0 | 0 |
| WEAKEN/REMOVE correct (of 12) | 10 | 12 | 11 |
| Decisive evidence retrieved, STRENGTHEN-probe runs (of 36) | 33 | 33 | n/a |

* **Survival.** Only one probe was lost relative to oracle evidence, and it was a decision loss: the evidence was
  retrieved.
* **Head-to-head.** Against V1 at equal token limits, 10 probes improved and none regressed, for about 3% more cost per
  run.
* **A recurring residual failure.** The verifier sometimes keeps a hedge "because no statistical test was reported",
  even for claims that need no test (speed, robustness, transfer).

## 5. Phase 4: independent held-out evaluation ([TEST])

**How it differs from V1's original TEST.** V1's TEST measured natural end-to-end passages, which turned out to contain
almost no understatement. Phase 4 is a **controlled verifier test**: every condition gets the same package and the same
starting sentence, and the evidence makes the correct decision known. It is **not** an end-to-end pipeline evaluation.
Design: `v2/docs/PHASE4_DESIGN.md`; construction: `v2/docs/PHASE4_BENCHMARK.md`; results: `v2/docs/PHASE4_RESULTS.md`.

* **Benchmark.**
  * 8 new matched pairs (16 fictional packages) covering: significance from a confidence interval only; significance
    after a multiple-comparison correction; consistency with ties; memory; throughput comparability; robustness over
    severities; a negative result; and citation magnitude.
  * Items were authored by GPT-5.6. Each was **blind-validated** by Claude Sonnet 5.5 with V1's judge label definitions,
    then checked deterministically.
  * Disputes went back to the author once; 10 of 50 items were still disputed and were dropped.
  * The result, **40 items**, was frozen (with hashes) before any inference.
* **Item mix.** 12 STRENGTHEN, 18 ACCEPT, 6 WEAKEN, 4 REMOVE. Of the 12 STRENGTHEN items, 8 use phrasings not seen in
  DEV, and 6 are claims that need no statistical test.
* **Conditions** (one interleaved batch, 3 repeats):
  * **V1 C4**: V1 verifier, unchanged code;
  * **V2 C4**: D1-tools;
  * **V2 C5**: D1-tools with STRENGTHEN removed (STRONGER → ACCEPT).
* **Scoring.**
  * Decisions are scored against the frozen gold.
  * Every distinct revised sentence was judged blind by two AI families, GPT-5.6 and Claude Haiku 5.5, using V1's judge
    prompt unchanged; disagreements were adjudicated, and numbers were checked by code.
  * A strengthening counts only if the revision is judged SUPPORTED and has no numeric error.

| [TEST] `p4_test_v1` | V1 C4 | **V2 C4** | V2 C5 |
|---|---|---|---|
| Correct strengthening (12 items × 3 runs) | 12/36 | **28/36** | 0/36 |
| False strengthening (28 items × 3) | 0/84 | **0/84** | 0/84 |
| Overstatement corrected (10 × 3) | 21/30 | 22/30 | 27/30 |
| Calibrated controls preserved / harmful edits (18 × 3) | 54/54 / 0 | 54/54 / 0 | 54/54 / 0 |
| Cost (120 runs) | $0.040 | $0.041 | $0.036 |

Paired cluster bootstrap over the 8 pairs, 95%:

* correct strengthening, V2 C4 − V1 C4: **+0.44 [+0.14, +0.78]**;
* correct strengthening, V2 C4 − V2 C5: +0.78 [+0.44, +1.00];
* overstatement corrected, V2 C4 − V2 C5: −0.17 [−0.30, −0.04].

By subgroup (correct strengthening, runs):

| Subgroup | V1 C4 | V2 C4 |
|---|---|---|
| Claims needing no statistical test | 1/18 | 12/18 |
| Phrasings not used in DEV | 6/24 | 19/24 |

## 6. Interpretation

1. **What V2 fixes.** On independently written held-out items, the D1 decision framework turns "supported but too weak"
   into correct strengthening, with no false strengthening, no harmful edits and essentially unchanged cost. Removing
   STRENGTHEN (C5) removes the effect. So the *action* matters, given the explicit comparison.
2. **What we learned about V1.** V1 *can* strengthen when a draft is overtly hedged and a significance result exists to
   cite (12/36 [TEST]). It almost never strengthens claims that need no test (1/18). Its 0/406 in V1 therefore reflects
   two things: (B) its decision standard, and (C) natural drafts that rarely contain overt hedges.
3. **Why opportunities stay rare in natural drafts [V1-retro].** V1's frozen AI labels found almost no understatement:
   * synthetic TEST outputs: 0–1 claims labelled UNDERSTATED per condition;
   * real-paper outline drafts: about 1.5% of 202 claims;
   * no focal-claim understatement at all.

   V1's writer is prompted to state the "strongest defensible claim" and can see all the evidence. In PaperPilot as it
   stands, V2 would rarely edit upward. Its value is that of a safeguard, and it does **not** change V1's main finding
   that C4 does not outperform the writer–reviewer loop.
4. **A rubric subtlety worth one sentence in the report.** V1's judge rubric counts an *explicit hedge* as
   understatement. It does not count an *omission*, such as a descriptive comparison that leaves out a significant test,
   or an attribution without its magnitude. V1's benchmark level scale counts both. The held-out validation followed the
   judge rubric, so Phase 4 tests explicit-hedge understatement only.

## 7. Limitations

* **Restricted TEST coverage.**
  * Only explicit-hedge understatement is tested.
  * Omission-type, proxy-metric (P4) and citation-magnitude (P8) strengthening items were dropped at validation.
  * Single sentences only; paragraph effects were deferred.
  * Scope-anchoring and omitted-finding cases are out of scope.
* **Small samples.** 12 STRENGTHEN items in 8 clusters [TEST]; 39 probes [DEV]. The intervals are wide.
* **AI-only labels.** The gold rests on AI authoring, AI validation and deterministic checks; outputs were judged by AI.
  No student validation was done. GPT-5.6 both authored the items and served as Judge A, and Claude was both validator
  and Judge B.
* **A possible trade-off.** V2 C4 corrected overstatement slightly less often than C5 (22/30 vs 27/30), driven by two
  items. This should be reported as a signal, not an effect.
* **Residual failure.** The "no test → keep hedge" pattern persists: both throughput items [TEST], and 3 runs in E5 [DEV].
* **One backbone,** and inference variability under nominally identical settings (handled with batched repeats).
* **Protocol deviations** (`v2/docs/PHASE4_DEVIATIONS.md`):
  * **D1–D2:** after inference but before any scoring, the judge harness got two format and parameter fixes: the output
    schema was appended to the prompt, the token limit was raised, truncated replies are no longer reused, and the judge
    budget was raised.
  * **D0:** the raw authoring replies, which contain the intended levels, were committed to git before inference. No
    model in the pipeline can read the repository, so the results are unaffected.
* **Post hoc by construction.** All of V2 was designed after V1's results were known. It is an exploratory follow-up,
  not part of V1's pre-registered study.
* **Engineering notes.**
  * Running on Windows needs `v2/compat_win/` and `core.autocrlf=false` (`v2/README.md`).
  * V2 spend is $3.31 in total: experiments $0.33, AI judges/authoring $2.99. It reconciles with the OpenRouter key.

## 8. Suggested takeaways for the final report and presentation

V1 stays the main story. V2 fits as roughly **one slide or about 1 minute**, placed after V1's H2 negative result.

1. **V1's "never strengthens" was a decision problem, not a retrieval problem.** With all evidence in view, the original
   verifier still accepted claims it knew were too weak [DEV].
2. **A minimal explicit strength comparison fixes it on held-out items.** Correct strengthening rises from 12/36 to
   28/36, with 0 false strengthening, 0 harmful edits and the same cost [TEST]. It needs the STRENGTHEN action (C5: 0/36).
3. **But natural drafts offer almost no strengthening opportunities** [V1-retro]. The fix is a safeguard. It does not
   overturn V1's headline result that C4 does not beat the writer–reviewer loop.
4. **(If time allows) Two method lessons.**
   * Temperature-0 inference varies across batches, so compare within one interleaved batch.
   * Whether omissions count as "understatement" depends on the rubric. Our held-out test covers only explicit hedges.
