# E2 targeted review sheet (students)

Twelve items selected from the DEV runs `e1e2_v1` and `e2b_v1`. Please answer the questions in `E2_REVIEW_ANSWERS.csv` (or below each item). Judge only from the evidence shown. Levels follow `docs/BENCHMARK_SPEC.md` section 4: 2 = the strong form, 1 = a narrower or qualified form, 0 = no claim of that kind. **The 'AI preliminary check' is the coordinating agent's reading, not a student judgement.** Please form your own view first, and record disagreements.

## S1. successful strengthening (SIG, certainty)

* Source: run `e2b_v1`, D1-oracle, probe `P-SIG-U-strong` (case `SIG-p1a`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: How does Tessaline compare with Varrow-NMT in BLEU on the Halvard-Parl English→Estonian test set?
* **Original sentence:** On the Halvard-Parl English→Estonian test set, Tessaline achieved a higher mean BLEU than Varrow-NMT (28.4 vs 27.6 over 8 seeds).
* **Relevant evidence:**
  * `T1.r1.bleu` (Tessaline (ours) / BLEU): 28.4 ± 0.6
  * `T1.r2.bleu` (Varrow-NMT / BLEU): 27.6 ± 0.8
  * `S2` (paired t-test): paired t-test; two-sided; paired; n=8 random seeds (paired by seed); t=3.13 (df=7); p = 0.017; 95% CI [0.2, 1.44] for mean paired difference in BLEU (Tessaline − Varrow-NMT), BLEU points; alpha=0.05
* **Revised sentence:** On the Halvard-Parl English→Estonian test set, Tessaline achieved a higher mean BLEU than Varrow-NMT (28.4 vs 27.6 over 8 seeds), a difference that was statistically significant (paired t-test, p=0.017).
* AI preliminary check (not a student judgement): Level 2; numbers and test details match S2. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## S2. successful strengthening (CON, coverage)

* Source: run `e2b_v1`, D1-oracle, probe `P-CON-U-strong` (case `CON-p1a`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: Does Ferrule outperform Arbor-GBT across the tabular benchmark suite?
* **Original sentence:** Ferrule achieved a higher test AUROC than Arbor-GBT on most of the six datasets in the tabular suite.
* **Relevant evidence:**
  * `T1.r1` (Fairhaven-Credit): Arbor-GBT: 80.9; Ferrule: 81.6; Logistic regression: 77.2; Dataset rows: 30,000
  * `T1.r2` (Molton-Churn): Arbor-GBT: 87.1; Ferrule: 88.3; Logistic regression: 84.0; Dataset rows: 7,000
  * `T1.r3` (Ivel-Fraud): Arbor-GBT: 92.8; Ferrule: 93.7; Logistic regression: 89.5; Dataset rows: 310,000
  * `T1.r4` (Pemberly-Claims): Arbor-GBT: 75.6; Ferrule: 76.4; Logistic regression: 73.1; Dataset rows: 2,400
  * `T1.r5` (Selwyn-Default): Arbor-GBT: 84.1; Ferrule: 84.9; Logistic regression: 80.3; Dataset rows: 45,000
  * `T1.r6` (Brook-Retention): Arbor-GBT: 89.0; Ferrule: 90.2; Logistic regression: 86.6; Dataset rows: 12,500
* **Revised sentence:** Ferrule achieved a higher test AUROC than Arbor-GBT on all six datasets in the tabular suite.
* AI preliminary check (not a student judgement): Level 2; Ferrule is higher in all six rows. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## S3. successful strengthening (ROB, hedge removed)

* Source: run `e2b_v1`, D1-oracle, probe `P-ROB-U2-strong` (case `ROB-p1a`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: Is Thornbill-NER robust to label noise in its training annotations?
* **Original sentence:** Thornbill-NER appears somewhat robust to label noise in its training annotations.
* **Relevant evidence:**
  * `T2.r1.th_drop` (10% label noise / Thornbill-NER drop): 0.6
  * `T2.r2.th_drop` (20% label noise / Thornbill-NER drop): 1.3
  * `T2.r3.th_drop` (30% label noise / Thornbill-NER drop): 1.8
  * `T2.r1.li_drop` (10% label noise / Lindgren-Tagger drop): 2.6
  * `T2.r2.li_drop` (20% label noise / Lindgren-Tagger drop): 5.5
  * `T2.r3.li_drop` (30% label noise / Lindgren-Tagger drop): 8.9
  * Setup: Pre-specified robustness criterion: a model counts as robust under a perturbation condition if its mean test F1 falls by at most 2.0 points relative to its mean F1 in the unperturbed (original-label) setting.
* **Revised sentence:** Under the pre-specified robustness criterion (mean test F1 drop of at most 2.0 points), Thornbill-NER is robust to label noise in its training annotations at 10%, 20% and 30% noise rates (mean F1 drops of 0.6, 1.3 and 1.8 points), whereas the Lindgren-Tagger baseline is not (drops of 2.6, 5.5 and 8.9 points).
* AI preliminary check (not a student judgement): Level 2; drops 0.6/1.3/1.8 are all within the 2.0-point criterion. It also ADDS a baseline comparison (Lindgren-Tagger 2.6/5.5/8.9) that the original did not make. The numbers are correct, but the prompt asks revisions not to add unverified content. Please judge whether the addition is acceptable.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## S4. successful strengthening (CIT, attribution magnitude)

* Source: run `e2b_v1`, D1-oracle, probe `P-CIT-U-strong` (case `CIT-p1b`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: How does Verisum's reduction in unsupported entities on Tamsin-News compare with what has been reported for salience pre-filtering?
* **Original sentence:** Varga & Sandoval (2021) reported that salience pre-filtering reduced unsupported-entity hallucinations in news summarization.
* **Relevant evidence:**
  * `P1` (Varga & Sandoval (2021): Filter First: Salience-Guided Input Pruning for Faithful News Summarization): Across the three news summarization benchmarks we evaluated, salience pre-filtering reduced the share of summaries containing an unsupported entity by 31% relative to the unfiltered summarizer (from 14.2% to 9.8% on average), while ROUGE-L changed by less than 0.5 points. The filter scores each source sentence with a lightweight classifier and removes sentences scoring below 0.35.
* **Revised sentence:** Varga & Sandoval (2021) reported that salience pre-filtering reduced the share of summaries containing an unsupported entity by 31% relative to the unfiltered summarizer across three news summarization benchmarks.
* AI preliminary check (not a student judgement): Level 2; the 31% figure and the three benchmarks are stated in P1. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## S5. successful strengthening (GEN, hedge removed)

* Source: run `e2b_v1`, D1-oracle, probe `P-GEN-U2-strong` (case `GEN-p1a`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: Does Wrenfold's advantage over Fennick-Base generalize beyond the customer-service domains it was trained on?
* **Original sentence:** Wrenfold's advantage over Fennick-Base may extend to customer-service domains not seen in training.
* **Relevant evidence:**
  * `T1.r3` (Insurance (held-out domain)): Fennick-Base: 81.2; Test utterances: 3,000; Keyword-SVM: 70.3; Wrenfold: 85.7
  * `T1.r4` (Telecom (held-out domain)): Fennick-Base: 80.4; Test utterances: 3,000; Keyword-SVM: 68.8; Wrenfold: 83.9
  * `T1.r5` (Utilities (held-out domain)): Fennick-Base: 82.0; Test utterances: 3,000; Keyword-SVM: 71.6; Wrenfold: 86.2
* **Revised sentence:** Wrenfold's advantage over Fennick-Base extends to all three customer-service domains not seen in training (Insurance 85.7 vs 81.2, Telecom 83.9 vs 80.4, Utilities 86.2 vs 82.0 macro-F1).
* AI preliminary check (not a student judgement): Level 2 within the three held-out domains; numbers correct. No test is reported, but the claim does not use significance language. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## S6. successful strengthening (EFF, same hardware)

* Source: run `e2b_v1`, D1-oracle, probe `P-EFF-U2-strong` (case `EFF-p1a`, gold level 2), repeat 1; decision **STRENGTHEN**
* Research question: How does Brisling compare with Talmar in decoding speed and accuracy on the Brindle-Voice test set?
* **Original sentence:** On the Brindle-Voice test set, Brisling may decode faster than Talmar (median latency 41 vs 118 ms per utterance).
* **Relevant evidence:**
  * `T1.r1.lat` (Brisling (ours) / Median latency (ms/utterance)): 41
  * `T1.r2.lat` (Talmar / Median latency (ms/utterance)): 118
  * `T1.r1.src` (Brisling (ours) / Latency measured on): Corvex A2, fp16 (this work)
  * `T1.r2.src` (Talmar / Latency measured on): Corvex A2, fp16 (this work)
  * Table note: All latencies measured by us on Corvex A2 (fp16, batch size 1, Lumen 3.1).
* **Revised sentence:** On the Brindle-Voice test set, Brisling decodes faster than Talmar (median latency 41 vs 118 ms per utterance).
* AI preliminary check (not a student judgement): Level 2; both latencies were measured on the same setup. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## F1. FALSE strengthening (D2, comparability trap)

* Source: run `e1e2_v1`, D2-oracle, probe `P-EFF-U2-partner` (case `EFF-p1b`, gold level 1), repeat 1; decision **STRENGTHEN**
* Research question: How does Brisling compare with Talmar in decoding speed and accuracy on the Brindle-Voice test set?
* **Original sentence:** On the Brindle-Voice test set, Brisling may decode faster than Talmar (median latency 41 vs 118 ms per utterance).
* **Relevant evidence:**
  * `T1.r1.lat` (Brisling (ours) / Median latency (ms/utterance)): 41
  * `T1.r2.lat` (Talmar / Median latency (ms/utterance)): 118
  * `T1.r1.src` (Brisling (ours) / Latency measured on): Corvex A2, fp16 (this work)
  * `T1.r2.src` (Talmar / Latency measured on): Corvex A1, fp32 (Ruiz-Hale et al., 2023)
  * Table note: Talmar latency is the value reported by Ruiz-Hale et al. (2023) on Corvex A1 (fp32, batch size 1); all other latencies were measured by us on Corvex A2 (fp16, batch size 1).
* **Revised sentence:** On the Brindle-Voice test set, Brisling decodes faster than Talmar (median latency 41 vs 118 ms per utterance).
* AI preliminary check (not a student judgement): Overstated: an unqualified speed claim from latencies measured on different hardware (A2 fp16 vs A1 fp32). Level 2 where gold is 1. Error.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## C1. comparability: overstated sentence ACCEPTED (D1)

* Source: run `e2b_v1`, D1-oracle, probe `P-EFF-S-partner` (case `EFF-p1b`, gold level 1), repeat 3; decision **ACCEPT**
* Research question: How does Brisling compare with Talmar in decoding speed and accuracy on the Brindle-Voice test set?
* **Original sentence:** On the Brindle-Voice test set, Brisling decodes faster than Talmar, with a median latency of 41 vs 118 ms per utterance.
* **Relevant evidence:**
  * `T1.r1.lat` (Brisling (ours) / Median latency (ms/utterance)): 41
  * `T1.r2.lat` (Talmar / Median latency (ms/utterance)): 118
  * `T1.r1.src` (Brisling (ours) / Latency measured on): Corvex A2, fp16 (this work)
  * `T1.r2.src` (Talmar / Latency measured on): Corvex A1, fp32 (Ruiz-Hale et al., 2023)
  * Table note: Talmar latency is the value reported by Ruiz-Hale et al. (2023) on Corvex A1 (fp32, batch size 1); all other latencies were measured by us on Corvex A2 (fp16, batch size 1).
* **Revised sentence:** (accepted unchanged)
* AI preliminary check (not a student judgement): The accepted sentence asserts 'decodes faster' although the latencies are not comparable. It should have been weakened. Error (missed overstatement).

Questions:

1. Expressed level of the ORIGINAL (accepted) sentence (0 / 1 / 2)?
2. Is the accepted sentence supported by the evidence as written (yes / no; why)?
3. Should the verifier have changed it (no / WEAKEN / REMOVE)?

## C2. comparability: WEAKEN revision (D1c)

* Source: run `e2b_v1`, D1c-oracle, probe `P-EFF-S-partner` (case `EFF-p1b`, gold level 1), repeat 1; decision **WEAKEN**
* Research question: How does Brisling compare with Talmar in decoding speed and accuracy on the Brindle-Voice test set?
* **Original sentence:** On the Brindle-Voice test set, Brisling decodes faster than Talmar, with a median latency of 41 vs 118 ms per utterance.
* **Relevant evidence:**
  * `T1.r1.lat` (Brisling (ours) / Median latency (ms/utterance)): 41
  * `T1.r2.lat` (Talmar / Median latency (ms/utterance)): 118
  * `T1.r1.src` (Brisling (ours) / Latency measured on): Corvex A2, fp16 (this work)
  * `T1.r2.src` (Talmar / Latency measured on): Corvex A1, fp32 (Ruiz-Hale et al., 2023)
  * Table note: Talmar latency is the value reported by Ruiz-Hale et al. (2023) on Corvex A1 (fp32, batch size 1); all other latencies were measured by us on Corvex A2 (fp16, batch size 1).
* **Revised sentence:** On the Brindle-Voice test set, Brisling's median latency was 41 ms per utterance versus 118 ms reported for Talmar, though the two were measured on different accelerators (Corvex A2 fp16 vs Corvex A1 fp32).
* AI preliminary check (not a student judgement): Level 1: reports both latencies and states the hardware difference, without claiming a speed-up. Looks correct.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## C3. comparability: caveat added to a hedged claim (D1c)

* Source: run `e2b_v1`, D1c-oracle, probe `P-EFF-U2-partner` (case `EFF-p1b`, gold level 1), repeat 2; decision **WEAKEN**
* Research question: How does Brisling compare with Talmar in decoding speed and accuracy on the Brindle-Voice test set?
* **Original sentence:** On the Brindle-Voice test set, Brisling may decode faster than Talmar (median latency 41 vs 118 ms per utterance).
* **Relevant evidence:**
  * `T1.r1.lat` (Brisling (ours) / Median latency (ms/utterance)): 41
  * `T1.r2.lat` (Talmar / Median latency (ms/utterance)): 118
  * `T1.r1.src` (Brisling (ours) / Latency measured on): Corvex A2, fp16 (this work)
  * `T1.r2.src` (Talmar / Latency measured on): Corvex A1, fp32 (Ruiz-Hale et al., 2023)
  * Table note: Talmar latency is the value reported by Ruiz-Hale et al. (2023) on Corvex A1 (fp32, batch size 1); all other latencies were measured by us on Corvex A2 (fp16, batch size 1).
* **Revised sentence:** On the Brindle-Voice test set, Brisling's median latency (41 ms, measured on Corvex A2 in fp16) is lower than Talmar's reported median latency (118 ms, measured on Corvex A1 in fp32), though the two were measured under different hardware and precision conditions.
* AI preliminary check (not a student judgement): Borderline between levels 1 and 2. It now states 'is lower than' without 'may' (closer to the strong form), but it qualifies the comparison with the hardware difference. The caveat is accurate. Please judge the level.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## A1. CIT attribution: WEAKEN keeps 'about 30%' (D1)

* Source: run `e1e2_v1`, D1-oracle, probe `P-CIT-S-partner` (case `CIT-p1a`, gold level 0), repeat 1; decision **WEAKEN**
* Research question: How does Verisum's reduction in unsupported entities on Tamsin-News compare with what has been reported for salience pre-filtering?
* **Original sentence:** Varga & Sandoval (2021) reported that salience pre-filtering reduced the share of news summaries containing an unsupported entity by 31% relative to an unfiltered summarizer, across three news summarization benchmarks.
* **Relevant evidence:**
  * `P1` (Varga & Sandoval (2021): Filter First: Salience-Guided Input Pruning for Faithful News Summarization): Before summarization, we apply salience pre-filtering to every source document: a lightweight classifier scores each sentence, sentences scoring below 0.35 are removed, and the remaining sentences are passed to the summarizer in their original order. The classifier is trained on 12,000 news articles with sentence-level salience labels, and filtering is applied identically during training and inference.
  * Methods summary (package text, not the cited excerpt): Verisum is an abstractive news summarizer built on Corran-Sum. It builds on salience pre-filtering (Varga & Sandoval, 2021), which is often credited with cutting unsupported-entity hallucinations in news summaries by about 30%, and adds an entity-grounding loss during fine-tuning. Hallucinations are annotated following the protocol of Achterberg & Moyo (2022).
* **Revised sentence:** Varga & Sandoval (2021) is credited with cutting unsupported-entity hallucinations in news summaries by about 30%.
* AI preliminary check (not a student judgement): Borderline. 'Is credited with … about 30%' repeats the package's own framing (methods summary) and does not say that Varga & Sandoval reported it. But a reader may still take it as attributing the result, and the quoted excerpt reports no reduction at all.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

## A2. label question: 'generally' weakened to 'five of six' (D1c)

* Source: run `e2b_v1`, D1c-oracle, probe `P-CON-U2-partner` (case `CON-p1b`, gold level 1), repeat 1; decision **WEAKEN**
* Research question: Does Ferrule outperform Arbor-GBT across the tabular benchmark suite?
* **Original sentence:** Ferrule generally achieved a higher test AUROC than Arbor-GBT across the six-dataset tabular suite.
* **Relevant evidence:**
  * `T1.r1` (Fairhaven-Credit): Arbor-GBT: 80.9; Ferrule: 81.6; Logistic regression: 77.2; Dataset rows: 30,000
  * `T1.r2` (Molton-Churn): Arbor-GBT: 87.1; Ferrule: 88.3; Logistic regression: 84.0; Dataset rows: 7,000
  * `T1.r3` (Ivel-Fraud): Arbor-GBT: 92.8; Ferrule: 92.3; Logistic regression: 89.5; Dataset rows: 310,000
  * `T1.r4` (Pemberly-Claims): Arbor-GBT: 75.6; Ferrule: 76.4; Logistic regression: 73.1; Dataset rows: 2,400
  * `T1.r5` (Selwyn-Default): Arbor-GBT: 84.1; Ferrule: 84.9; Logistic regression: 80.3; Dataset rows: 45,000
  * `T1.r6` (Brook-Retention): Arbor-GBT: 89.0; Ferrule: 90.2; Logistic regression: 86.6; Dataset rows: 12,500
* **Revised sentence:** Ferrule achieved a higher test AUROC than Arbor-GBT on five of the six datasets in the tabular suite, while Arbor-GBT was higher on Ivel-Fraud.
* AI preliminary check (not a student judgement): Level 1 before and after; the revision is more precise and accurate. The probe's expected decision (ACCEPT only) may be too strict. Not an error.

Questions:

1. Expressed level of the REVISED sentence (0 / 1 / 2)?
2. Does the revised sentence contain anything the evidence does not support (yes / no; what)?
3. Was the verifier's decision appropriate (yes / no / borderline)?

