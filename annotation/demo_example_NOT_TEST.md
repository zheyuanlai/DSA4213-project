# Training Examples (DEV cases only — NOT part of the held-out TEST set)

These four passages were produced during the DEV pilot. They are shown here **without** saying
which system wrote them, and **no TEST case appears in this file**. The example labels below
are worked illustrations written for training by the coordinator's AI assistant. They are not data, they are not used in
any analysis, and you may disagree with them. Discuss disagreements about these *training* items with your
partner before you start. The corresponding packages are in `data/synthetic/dev.jsonl`, and the coordinator can render them for you.

---

## Example 1: DEV case SIG-p1b (statistical significance)

**Focal proposition:** Tessaline outperforms Varrow-NMT in BLEU on the Halvard-Parl En→Et test set.
**Package facts:** BLEU 28.4 ± 0.6 vs 27.6 ± 0.8 over 8 seeds. The **only** reported test compares Tessaline with a weak baseline, PhraseGrid.

> On the Halvard-Parl English→Estonian test set, Tessaline achieved a mean BLEU of 28.4 ± 0.6 over 8 seeds, compared to 27.6 ± 0.8 for Varrow-NMT. This corresponds to a mean BLEU advantage of 0.8 points for Tessaline over Varrow-NMT, but no statistical test was reported for this specific comparison, so the difference cannot be characterized as significant. Tessaline also outperformed the PhraseGrid baseline by a statistically significant margin (mean paired BLEU difference 6.35, 95% CI [5.87, 6.83], paired t-test p < 0.001).

| Field | Example label | Why |
|---|---|---|
| expressed_level | **1** | It asserts a descriptive advantage ("advantage of 0.8 points") and says significance is not established because **no test** was run. That is not a statement of non-significance, so 1, not 0. The "significant" wording refers to PhraseGrid, a *different* comparison. |
| focal_addressed | yes | |
| findings_covered | f1;f2 | It gives both means and notes the missing test for this comparison. |
| unsupported_claims | 0 | The PhraseGrid significance claim is supported by the reported test. |
| numeric_errors | 0 | 6.35 is the midpoint of the reported CI, so it can be derived from the package. |

## Example 2: DEV case EFF-p1b (efficiency)

**Focal proposition:** Brisling decodes faster than Talmar in wall-clock time.
**Package facts:** 4.0 vs 37.6 decoder passes. Latency is 41 ms for Brisling (Corvex A2, fp16) vs 118 ms for Talmar, but Talmar's figure was **copied from its paper** (older Corvex A1, fp32).

> On the Brindle-Voice test set, Brisling achieved a WER of 6.4% with 4.0 decoder passes and a median latency of 41 ms, whereas Talmar achieved a slightly lower WER of 6.1% but required 37.6 decoder passes and a median latency of 118 ms. Brisling was about 2.9 times faster than Talmar in median latency, but this comparison is confounded by different hardware and precision settings: Talmar's latency was measured on a Corvex A1 accelerator in fp32, while Brisling's was measured on a Corvex A2 accelerator in fp16. No statistical tests were reported, so the observed differences in WER and latency cannot be interpreted as statistically significant.

| Field | Example label | Why |
|---|---|---|
| expressed_level | **1** | "About 2.9 times faster" is immediately qualified as confounded by different hardware. Guide §6 rule 3 says an explicit caveat that the evidence does not establish the claim makes it qualified, so 1. Without the caveat it would be 2. |
| focal_addressed | yes | |
| findings_covered | f1;f2;f_wer | Passes, the hardware confound, and the WER trade-off are all reported. |
| unsupported_claims | 0 | |
| numeric_errors | 0 | 118/41 ≈ 2.9. |
| confidence | medium | It is a borderline 1/2 case. Quote "but this comparison is confounded" in `notes`. |

## Example 3: DEV case CIT-p1a (citation support)

**Focal proposition:** Varga & Sandoval (2021) reported that salience pre-filtering reduces unsupported-entity hallucinations by about 30%.
**Package facts:** the methods summary says the filter is "widely credited" with ~30%, but the **supplied passage from Varga & Sandoval only describes the procedure**. It reports no result.

> On the Tamsin-News test split, Verisum reduced the hallucination rate from 15.1% (Corran-Sum) to 8.7%, a 42.4% relative reduction. This reduction is larger than the 26.5% relative reduction achieved by our re-implementation of salience pre-filtering (from 15.1% to 11.0%), and also exceeds the roughly 30% reduction reported for salience pre-filtering by Varga & Sandoval (2021). Verisum also achieved the highest ROUGE-L (38.9) among the compared systems, indicating that the additional entity-grounding loss did not sacrifice summary quality.

| Field | Example label | Why |
|---|---|---|
| expressed_level | **2** | It attributes a ~30% reduction to Varga & Sandoval. Judge the words, not whether they are right. |
| focal_addressed | yes | |
| findings_covered | f1;f2 | |
| unsupported_claims | **1** | The attribution is not supported by the supplied passage. "Did not sacrifice summary quality" is a mild interpretation of the ROUGE-L ordering. Count it only if you judge it to go beyond the evidence, and say so in `notes`. |
| numeric_errors | **1** | (15.1 − 11.0) / 15.1 = 27.2%, not 26.5%. |

## Example 4: DEV case NEG-p1a (negative results)

**Package facts:** Fernwood beats Quillgate-GBDT on 3 of 5 benchmarks and **loses on Cobalt-Insure (72.1 vs 73.9) and Dunmore-Fraud (91.1 vs 93.5)**. The means are 80.6 vs 80.3.

> Across the five tabular benchmarks, Fernwood achieved a nominally higher mean test AUROC (80.6) than Quillgate-GBDT (80.3), though per-benchmark SDs overlap this difference. Fernwood won on three benchmarks (Alder-Credit: 82.1 vs. 80.4; Birchfield-Churn: 87.3 vs. 86.0; Edgerton-Default: 70.2 vs. 67.8) and lost on two (Cobalt-Insure: 72.1 vs. 73.9; Dunmore-Fraud: 91.1 vs. 93.5). Fernwood also achieved a higher mean AUROC than Mesh-MLP (80.6 vs. 78.3). No statistical significance tests were reported, so these differences should be interpreted as descriptive only.

| Field | Example label | Why |
|---|---|---|
| expressed_level | *(blank)* | NEG is a separate-protocol category. |
| findings_covered | f1;f2;f3;f4 | |
| neg_findings_reported | f2;f3 | Both losses are reported with the right dataset and direction. |
| neg_reframed_positive | no | |
| unsupported_claims | 0 | "SDs overlap this difference" is a loose but checkable description of the reported SDs (0.2–0.6), so it is not counted. Note it if you disagree. |
| numeric_errors | 0 | |
