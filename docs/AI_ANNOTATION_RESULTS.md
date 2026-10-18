# Expanded Metrics and Multi-Agent AI Annotation

## Status and reporting rule

This is an **AI-assisted exploratory evaluation**, not a human-annotation study. Four independent
AI annotator roles labelled blinded packets, two roles per disjoint half (AB and CD), followed by
evidence-based adjudication. The labels must never be called “human judgements,” and the agreement
statistics must not be interpreted as agreement among independent human raters.

The protocol was added after the proposal in response to the TA's concern that the main metric only
measured the strength label of one or two sentences in short synthetic examples. The experimental
outputs and frozen TEST gold were not changed.

## Recommended metric set

No single composite score should be used. Report a compact metric panel so that a system cannot look
good merely by omitting difficult findings or numeric details.

| Family | Metric | Definition and purpose | Status |
|---|---|---|---|
| Focal calibration | Exact accuracy; macro-F1 | Correct 0/1/2 evidence-strength label; macro-F1 prevents the most frequent level from dominating | Scored |
| Error severity | Ordinal MAE; severe-error rate | Mean absolute distance from gold and fraction with distance 2 | Added and scored |
| Error direction | Overstatement; understatement | Separates risky exaggeration from excessive weakening | Scored |
| Content retention | Required-finding coverage; omission | Detects systems that improve apparent calibration by deleting evidence | Scored |
| Grounding | Unsupported claims per output; outputs with any unsupported claim | Measures newly introduced claims not licensed by the package | Scored |
| Numerical fidelity | Numeric errors per output; required numeric-fact accuracy | Separates fewer wrong numbers from retention of the required numeric evidence | Scored |
| Negative findings | Negative/null finding recall; positive reframing rate | Checks whether inconvenient results disappear or are spun positively | Scored |
| External validity | Real-paper sentence support labels; overall calibration | Tests longer, naturally occurring evidence packages rather than only short synthetic cases | Scored on 12 papers |
| Presentation | Readability, 1–5 | Captures whether verification degrades clarity | Scored on real papers |
| Efficiency | Model calls, tool calls, latency, prompt/completion tokens, USD cost | Quantifies the price of any quality gain | Already logged |
| Diagnostics | Confusion matrix, per-level precision/recall/F1, edit transitions | Shows which levels and edits produce errors | Scored |

For planned contrasts, report the paired mean difference with a case-bootstrap 95% confidence
interval. The matched-pair bootstrap remains a sensitivity analysis for the synthetic benchmark.
The numerical-reporting and negative-result subsets contain only four TEST cases each, so their
intervals are exploratory and should not support strong claims.

## Annotation protocol

- The 122 deduplicated synthetic outputs were split by intact matched pairs; AB labelled 61 and CD
  labelled 61. Each role completed strength labels before receiving the detailed checklist pass.
- The 39 real-paper outputs (151 sentences) were split 19/20 across the same teams.
- Annotators saw blinded packets only. They did not see condition identities, TEST gold, private
  mappings, automatic results, or one another's labels before submission.
- Disagreements were adjudicated against the supplied evidence: 14 synthetic fields and 36
  real-paper fields.
- Unblinding and scoring occurred only after consensus labels were fixed.

### Agreement before adjudication

| Measure | Team AB | Team CD |
|---|---:|---:|
| Synthetic expressed-level kappa | 1.000 | 1.000 |
| Synthetic numeric-error “any” kappa | 0.938 | 0.932 |
| Synthetic finding-coverage kappa | 0.000* | 0.881 |
| Real sentence support-label kappa | 0.827 | 0.760 |
| Real readability quadratic kappa | 0.491 | 0.239 |
| Real overall-calibration kappa | 0.390 | 0.638 |

\* AB agreed on 99.3% of coverage decisions, but almost all decisions were positive; kappa collapses
under this prevalence imbalance. Report both agreement and kappa. The modest readability and overall-
calibration agreement shows that these subjective metrics need cautious interpretation.

## Results

### Synthetic TEST

The original focal-strength task is saturated. C2–C6 all obtain 1.000 exact accuracy and macro-F1;
C1 and C7 obtain 0.958 exact accuracy and 0.956 macro-F1. This is direct evidence that focal strength
alone is not sufficiently discriminative for this dataset.

The secondary metrics reveal trade-offs hidden by that ceiling:

- C4 versus C2 has no focal-calibration, coverage, or unsupported-claim difference. C4 has fewer
  numeric errors per output (difference -0.156, 95% CI [-0.375, 0.031]) but lower required numeric-fact
  accuracy on the four numeric cases (-0.174, [-0.286, -0.062]). This pattern is consistent with a
  retention–error trade-off; neither metric should be reported alone.
- C4 versus C1 improves exact focal accuracy by 0.042 [0.000, 0.125] and reduces outputs containing
  unsupported claims by 0.125 [-0.250, -0.031], while required-finding coverage is unchanged.
- C4 and C5 are indistinguishable on focal calibration, coverage, unsupported claims, numeric-fact
  accuracy, and negative-result metrics. The annotation therefore gives no evidence that allowing
  STRENGTHEN helps H2.
- C4 and C3 are identical on focal calibration, coverage, unsupported claims, and numeric-fact
  accuracy. C4 averages 0.062 fewer numeric errors per output [-0.156, 0.000], while the automatic
  logs show fewer evidence-tool calls (9.22 versus 12.88), lower latency (34.7 versus 38.7 seconds),
  and lower cost ($0.00209 versus $0.00241 per case). This supports an efficiency result, not a broad
  quality-superiority claim.
- Relative to the shared unverified outline draft C7, C4 fixes one focal overstatement, improves
  pooled finding coverage by 0.016 [0.000, 0.047], and has 0.094 fewer numeric errors per output
  [-0.219, 0.000]. Most uncertainty intervals still touch zero.

### Real-paper packages

Across the 11 real papers completed by C4, its mean per-paper sentence-label rates are 0.773 supported, 0.000
overstated, 0.045 understated, 0.000 unsupported, and 0.182 numeric error; mean readability is 4.455/5.
The C4–C2 paired intervals include zero for support, understatement, numeric error, and readability.
C4 and C3 have identical support and readability, but C4 has a 0.023 higher numeric-error rate
[0.000, 0.068]. Thus the real-paper evaluation does not establish a general quality advantage for C4.

The contrast between near-perfect synthetic focal calibration and 15.7–18.2% real-paper numeric-error
rates is the strongest reason to retain both synthetic and real-paper evaluation.

Full values and all planned comparisons are in `results/ai_scored/TABLES_AI.md`.

## Report-ready conclusion

> The original ordinal calibration metric exhibited a ceiling effect: five of seven conditions
> achieved perfect exact accuracy and macro-F1 on the synthetic TEST set. We therefore report a
> multidimensional evaluation covering error severity and direction, finding coverage, unsupported
> claims, numeric fidelity, negative-result retention, real-paper sentence support, readability, and
> efficiency. Under multi-agent AI annotation, verification corrected one focal overstatement and
> reduced unsupported claims relative to direct generation, but the full adaptive agent did not
> outperform the writer–reviewer baseline on focal calibration or real-paper support. Numeric
> fidelity showed a retention–error trade-off, and most paired confidence intervals included zero.
> These AI-labelled results are exploratory and should not be presented as human evaluation.

## Limitation and minimum human check

Four AI roles reduce single-pass randomness but do not create four independent human perspectives;
their errors may be correlated because the roles use the same model family and rubric. If workload
permits, the highest-value human check is a small stratified audit rather than relabelling everything:
sample all agent disagreements, all rare over/understatement cases, all real-paper numeric errors, and
a random set of agreements. Report the audit size and AI–human agreement, and correct audited labels
before making human-facing claims.

## Reproduction

```bash
python scripts/ai_annotation_pipeline.py validate
python scripts/ai_annotation_pipeline.py agreement
python scripts/ai_annotation_pipeline.py combine
python scripts/ai_annotation_pipeline.py score
```

The AI track is isolated under `annotation/ai/` and `results/ai_*`; it does not populate or impersonate
the human-annotation folders.

## Material passport

- **Primary materials:** frozen synthetic TEST evidence/gold, private condition mappings, 12 licensed
  real-paper evidence packages, 122 synthetic outputs, and 39 real-paper outputs.
- **Generated materials:** four independent AI label sets, four adjudication sheets, three consensus
  files, pairwise agreement JSON, and scored JSON/Markdown tables.
- **Role of AI:** AI performed all annotations and adjudication in this track. Humans did not validate
  these labels during this run.
- **Scope:** supports exploratory course-project analysis and metric design; does not support a claim
  of human preference, human reliability, or independent human validation.
