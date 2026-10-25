# V2 research summary and technical handoff

*For group members who know V1 (PaperPilot) but have not followed V2. Written 2026-10-25. Branch `v2-calibration`
(pushed to `origin`; not yet merged into `main`). V1 files and results are unchanged.*

**One-sentence summary.** V1's verifier issued no STRENGTHEN decisions on naturally generated drafts. Diagnostic
experiments identified decision framing—not evidence retrieval—as a major bottleneck when explicit understatements
were supplied. A small prompt-and-schema change (D1) improved correct strengthening from 12/36 to 28/36 runs on
new held-out, explicit-hedge items, with no false strengthening observed there. How often the original writing
workflow offers *all forms* of strengthening opportunities, and whether this improves end-to-end quality, remain open.

**Evidence tiers used throughout.**

* **[DEV]**: our own 39 diagnostic probes, used for development (E1–E5).
* **[TEST]**: the independent, frozen Phase 4 held-out benchmark.
* **[V1-retro]**: observations from V1's existing frozen records and AI labels; no new runs.

## 1. Motivation

* **[V1-retro]** V1's hypothesis H2 was that a verifier that can STRENGTHEN as well as WEAKEN calibrates claims in both
  directions. **No STRENGTHEN decision occurred** in its original evaluations:
  * **0/303** synthetic TEST claims in conditions where STRENGTHEN was enabled (C3: 103, C4: 103, C6: 97); the often-cited **0/406** counts another 103 C5 claims, but C5 *forbids* STRENGTHEN;
  * 0 of 86 real-paper claims;
  * 0 of 64 long-package claims.
  These denominators count verified claims, **not** independently established understatement opportunities.
* **[V1-retro]** V1's own H2 diagnostic also produced 0 STRENGTHEN on 6 deliberately understated DEV drafts. H2 therefore
  could not be tested.
* **V2's question:** why did STRENGTHEN never happen, and can a targeted fix make it happen correctly?

## 2. Failure diagnosis (E1/E2, [DEV])

Three explanations were considered:

* **A. Evidence acquisition:** the verifier never retrieves the evidence for a stronger claim.
* **B. Decision framework:** it sees the evidence but still accepts a weak claim.
* **C. Opportunity scarcity (not necessarily a system failure):** the original writer may already produce calibrated claims, so its drafts supply few *explicit, same-proposition* understatements for the verifier to fix. The prevalence of broader under-reporting was not established.

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

**Mechanism in one sentence:** V1 tends to ask whether the existing claim is *defensible*; D1 additionally asks whether
stronger wording of that **same proposition** is defensible. This is not a new retrieval model, an extra evidence tool,
or a coverage/completeness checker.

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
  * Disputes went back to the author once; 10 of 50 candidate items were still disputed and were dropped **before any TEST inference**. The retained set is therefore a validated *subset*, not comprehensive coverage of all proposed strengthening types.
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
  * A strengthening counts only if the action is STRENGTHEN **and** the resulting sentence is judged SUPPORTED with no numeric error. This matters because an action count alone does not establish better output quality.

| [TEST] `p4_test_v1` | V1 C4 | **V2 C4** | V2 C5 |
|---|---|---|---|
| Correct strengthening (12 items × 3 runs) | 12/36 | **28/36** | 0/36 |
| False strengthening (28 items × 3) | 0/84 | **0/84** | 0/84 |
| Overstatement corrected (10 × 3) | 21/30 | 22/30 | 27/30 |
| Calibrated controls preserved / harmful edits (18 × 3) | 54/54 / 0 | 54/54 / 0 | 54/54 / 0 |
| Overall gold decision correct (all 40 items) | 0.70 | **0.85** | 0.57 |
| Cost (120 runs) | $0.040 | $0.041 | $0.036 |
| Model latency per run | 11.1 s | 13.9 s | 13.8 s |

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

1. **What V2 improves [TEST].** On independently authored, held-out **explicit-hedge** items, D1 increases correct
   strengthening from 12/36 (V1) to 28/36 (V2), with no false strengthening or harmful edits *observed on this test*
   and nearly unchanged inference cost (**but 13.9 vs 11.1 seconds of model latency per run**). The numerator requires a **supported final revision**, not just a STRENGTHEN
   action. This demonstrates better *conditional verifier capability*, not better complete PaperPilot passages.
2. **What C5 actually establishes.** V2 C5 retains the structured judgement but is **not allowed to issue
   STRENGTHEN** (STRONGER_SUPPORTED → ACCEPT). Its 0/36 on a metric requiring that action is **true by design**, not
   independent evidence of greater revision quality. The meaningful evidence is the verified correctness of V2 C4's
   actual stronger wording, paired with the original and no-strengthening controls. C5 is an action-removal ablation.
3. **What we learned about V1 [TEST].** V1 *can* strengthen when a draft is overtly hedged and a significance result
   exists to cite (12/36 [TEST]); it almost never does so for claims needing no significance test (1/18). Thus the
   original 0/303 eligible decisions is **not evidence of zero underlying ability**. The observed zero is consistent
   with a combination of an overly permissive ACCEPT criterion [DEV] and few explicit opportunities in V1 natural
   drafts [V1-retro], but their relative contributions have not been causally quantified.
4. **What opportunity scarcity does—and does not—mean [V1-retro].** V1's frozen AI claim labels found very few
   *explicit same-proposition* understatements:
   * synthetic TEST outputs: 0–1 claims labelled UNDERSTATED per condition;
   * real-paper outline drafts: about 1.5% of 202 atomic claims;
   * no focal-claim understatement under the original focal annotations.

   The shared scientific-reporting policy (`prompts/common_reporting.md`) explicitly instructs the writer to state
   the **"strongest defensible claim"**; the claim planner (`prompts/claim_outline.md`) pre-specifies finding strength,
   scope and caveats, and the writer follows that plan. Upstream calibration may therefore already prevent obvious
   understatement. **This would be a desirable writer behaviour, not failure mode C in the sense of a defect.**
   However, no writer-prompt/outline ablation established the cause. Nor does the low label rate prove that the
   writer fully reported all supported findings: missing a statistically supported qualification, a number, or an
   entire finding may show up as *implicit under-reporting / coverage loss*, rather than an explicitly hedged
   atomic claim. V1's finding-coverage and numeric-recall limitations remain relevant.
5. **The evaluation-definition gap.** V1's focal gold-level scheme can distinguish more-informative reporting (for
   instance, a supported significance qualification) from a weaker description, whereas its later atomic-claim rubric
   emphasizes the claims *actually stated* and generally does **not** label an omitted stronger conclusion as
   UNDERSTATED. Phase 4 adopted the latter rubric and excluded disputed omission/proxy/attribution-magnitude
   strengthening items. Consequently, **the true natural rate of all potentially useful strengthening edits is
   unknown**; Phase 4 supports only the narrower explicit-hedge claim.

### 6.1 A held-out example: V1 accepts, V2 strengthens [TEST]

**Case `T4-P2-U2-strong`** (frozen Phase 4 item; package `T4-P2-strong` in `v2/benchmarks/test_v2/cases.jsonl`). The
same package and starting sentence were given to every condition.

* **Starting sentence (explicit hedge):** "NacreFuse appears to improve exact-match accuracy on Kersey-QA from 73.9% to
  74.8% relative to VellumRerank."
* **Decisive evidence:**
  * Table T1 gives Kersey-QA exact match "74.8 ± 1.2" (NacreFuse) and "73.9 ± 1.1" (VellumRerank), mean ± SD over 12
    seeds.
  * Test S1 is a paired t-test, n = 12, t = 3.2, df = 11, "raw p = 0.0084", alpha 0.05, with "Holm correction across
    four pre-specified dataset comparisons; adjusted p = 0.0336".
* **V1 C4** (`v2/outputs/phase4/p4_test_v1/D0-tools-800/T4-P2-U2-strong__r{1,2,3}.json`): **ACCEPT in 3/3 runs**. V1
  retrieved and cited the decisive test, then judged the hedge appropriate. Run 1: *"A paired t-test (n=12, t=3.2, raw
  p=0.0084, Holm-adjusted p=0.0336) supports the improvement. "Appears to improve" is appropriately hedged and scoped to
  Kersey-QA."*
* **V2 C4** (`v2/outputs/phase4/p4_test_v1/D1-tools/T4-P2-U2-strong__r{1,2,3}.json`): **STRENGTHEN in 3/3 runs**, with
  `support_relation` = STRONGER_SUPPORTED. Run 1's rationale: *"The sentence's hedge "appears to improve" understates the
  reported significant result."* Revised sentence (runs 1 and 3; run 2 is equivalent but shorter):
  > "NacreFuse significantly improves exact-match accuracy on Kersey-QA from 73.9% to 74.8% relative to VellumRerank
  > (paired t-test, n=12, raw p=0.0084; Holm-adjusted p=0.0336)."
* **AI judge verdict** (blinded; `v2/results/phase4/p4_test_v1/judged.json`, item `x7fd3f944d1`): **SUPPORTED** by both
  judges, numbers checked by code with no error.
  * Judge A (GPT-5.6): *"T1 shows the stated Kersey-QA improvement; S1 confirms 12 paired seeds and significance after
    Holm correction."*
  * Judge B (Claude Haiku 5.5): *"Kersey-QA means rise from 73.9 to 74.8 (T1); S1 has n=12, raw p=0.0084, Holm-adjusted
    p=0.0336 below alpha."*
* **Matched control** (`T4-P2-U2-partner`). The identical sentence on the partner package, where raw p = 0.0323 but
  Holm-adjusted p = 0.1292, was **never strengthened** by V2 C4 (WEAKEN, WEAKEN, ACCEPT). The strengthening therefore
  tracks the evidence, not the wording.

The mechanism is the one first seen on DEV, where V1 noted "indeed all six" yet accepted "most of the six"
(`docs/H2_DIAGNOSTIC.md`). The held-out case shows it on independently authored material. This is one illustrative item
and does not stand in for the aggregate result. Note also that "appears to" is a hedge pattern that also occurs in DEV.
For a no-test-needed example on a phrasing new relative to DEV, see `T4-P3-U2-strong`. There V1 accepted "comparable to
or better than … on at least four of the five" in 3/3 runs, and V2 revised it to "higher macro-F1 than Copperfin on all
five tasks" in 3/3 runs, judged SUPPORTED.

### 6.2 How V2 contributes to the overall PaperPilot study

| V1 question / finding | What V2 contributes—and what it does not |
|---|---|
| **H1: Full PaperPilot vs direct generation / writer–reviewer** | V1 found benefits over direct generation on some synthetic measures but no established overall advantage over the generic writer–reviewer; numeric recall was lower than C2. V2 **did not rerun the complete writer pipeline** and does not overturn H1. |
| **H2: Does bidirectional verification help?** | V1 could not assess H2 through natural drafts because no strengthening occurred. V2 separates *availability of opportunities* from *ability to act*, identifies a DEV decision-framing bottleneck, and demonstrates improved conditional strengthening on a new controlled TEST. It does **not** establish gains on natural end-to-end writing. |
| **H3: Adaptive vs scripted evidence tools** | V1's adaptive checker matched scripted checking with fewer tool calls (about **3.66 fewer per synthetic TEST case**). V2's oracle-vs-tools comparison suggests decision framing, not retrieval, was the main bottleneck **on the DEV probes**; this does not negate the H3 efficiency result. |
| **Finding coverage and numeric fidelity** | Sentence-level strength calibration and *reporting all important findings* are different objectives. D1 does not add a coverage planner and cannot be assumed to fix V1's omissions or numeric-recall gap. |
| **General research contribution** | A zero-frequency agent action is ambiguous: diagnose **opportunity prevalence**, **evidence availability**, **decision correctness given an opportunity**, and **final revision quality** separately before claiming that an architecture has failed. |

### 6.3 The debugging and validation logic as a research contribution

This was **not merely prompt trial-and-error**. The sequence was: zero STRENGTHEN in V1 → controlled DEV probes →
complete-evidence (oracle) intervention to isolate the decision stage → separation of same-proposition strength from
scope-expansion/omission cases → comparison of D1, D2 and D1c under inference variability → D1 tested in the real
tool loop at equal token limits (E5) → independent held-out TEST with matched controls, output judging and a
STRENGTHEN-disabled ablation. The inference reproducibility audit also showed why temperature 0 is insufficient to
justify interpreting isolated 1–2-case flips; interleaved repeats were used instead.

Together these experiments turn an initially ambiguous **0-action observation** into a narrower, evidence-backed
account of when the verifier can strengthen, which decision framing improves it, and which system-level benefits
remain unproven.

## 7. Limitations

* **Restricted TEST coverage.**
  * Only explicit-hedge understatement is tested.
  * Omission-type, proxy-metric (P4) and citation-magnitude (P8) strengthening items were dropped at validation.
  * Single sentences only; paragraph effects were deferred.
  * Scope-anchoring and omitted-finding cases are out of scope.
* **Small, selected samples.** 12 STRENGTHEN items in 8 matched-pair clusters [TEST]; 39 probes [DEV]. The intervals
  are wide. The 0/84 false-strengthening observations are **28 controls × 3 repeated runs**, not 84 independent cases.
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

1. **A zero-use action needs diagnosis, not an assumption of incapacity.** V1 issued 0/303 STRENGTHEN decisions where
   the action was enabled on synthetic TEST drafts; DEV oracle probes revealed a major decision-framing bottleneck,
   but TEST later showed V1 *can* strengthen when an overt hedge and supporting evidence are supplied.
2. **Explicit strength comparison improves conditional calibration.** On held-out explicit-hedge understatements,
   correct, AI-validated strengthening increased from 12/36 to 28/36 runs, with no false strengthening or damage to
   calibrated controls observed in this small TEST. The action-removed C5 is a useful control, not independent proof
   of improved output quality.
3. **Practical value remains conditional.** Existing V1 AI labels suggest explicit understatements are rare in its
   natural drafts; this may partly reflect successful upstream planning. Implicit under-reporting and whole-passage
   coverage are different problems. The new benchmark does not establish end-to-end V2 superiority over C2.
4. **Method takeaway:** Separate evidence retrieval, strength decision, the frequency of genuine opportunities, and
   final-text correctness; use paired, interleaved repeats when nominal temperature-0 inference is variable.
