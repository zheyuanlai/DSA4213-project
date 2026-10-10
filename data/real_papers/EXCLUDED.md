# Real-paper candidates considered and not included

Retrieved 2026-10-10. This file lists the papers that were screened for the real-paper set and why each was left out.

## 1. Screening by license (automatic)

Candidates came from the arXiv OAI-PMH `arXivRaw` listings (`set=cs:cs:CL`) for three
date windows: 2024-10-15..16, 2025-06-10..11 and 2025-11-12..13. Datestamps there mark the
last metadata change, so these windows also contain older papers that were recently updated.
Only papers with arXiv IDs from 2024–2026 were kept. The windows gave these license counts
(records with 24xx/25xx IDs):

| License | Records | Eligible? |
|---|---|---|
| CC BY 4.0 | 403 | yes |
| arXiv non-exclusive distribution license 1.0 (default) | 291 | **no**: redistribution of excerpts not permitted |
| CC BY-NC-SA 4.0 | 61 | **no**: not on the allowed list (NC) |
| CC BY-NC-ND 4.0 | 35 | **no**: NC and no-derivatives |
| CC BY-SA 4.0 | 28 | yes (share-alike applies to derived packages) |
| CC0 1.0 | 8 | yes |

Some examples that matched the topic but were **rejected for license**:

| arXiv ID | Title (abridged) | License |
|---|---|---|
| 2404.09480 | Mitigating Hallucination in Abstractive Summarization with Domain-Conditional Mutual Information | arXiv non-exclusive |
| 2410.08102 | Efficient Pretraining Data Selection for Language Models via Multi-Actor Collaboration | arXiv non-exclusive |
| 2501.08248 | Eliciting In-context Retrieval and Reasoning for Long-context Large Language Models | CC BY-NC-ND 4.0 |
| 2503.04827 | Preserving Cultural Identity with Context-Aware Translation Through Multi-Agent AI Systems | CC BY-NC-ND 4.0 |
| 2506.06929 | Hybrid Extractive Abstractive Summarization for Multilingual Sentiment Analysis | CC BY-NC-SA 4.0 |
| 2506.07645 | Evaluating LLMs Robustness in Less Resourced Languages with Proxy Models | arXiv non-exclusive |
| 2506.08436 | Olica: Efficient Structured Pruning of Large Language Models without Retraining | arXiv non-exclusive |

## 2. Eligible license, source downloaded, not included

All papers below have a CC BY 4.0 license, confirmed from their `arXivRaw` record. Their
e-prints sit in the gitignored `raw/` directory and are not redistributed. They were left out
for content reasons, or because the 12-paper target had already been reached with a more
diverse set.

| arXiv ID | Title (abridged) | Reason not included |
|---|---|---|
| 2502.12082 | AdaSplash: Adaptive Sparse Flash Attention | Usable efficiency tables (runtime/memory). Not needed after RP-10/RP-12 covered efficiency-style evidence. Good reserve candidate. |
| 2503.08542 | CLEV: LLM-Based Evaluation Through Lightweight Efficient Voting for Free-Form QA | Main results are wide agreement tables (many judges × tasks × candidate models with Kappa and F1 in each cell). Cutting them to ≤7 columns would hide the comparison. Reserve candidate for LLM-as-judge. |
| 2407.09014 | CompAct: Compressing Retrieved Documents Actively for Question Answering | Same topic as RP-07 (RAG). Not selected, for diversity. |
| 2410.10141 | Temperature-Centric Investigation of Speculative Decoding with Knowledge Distillation | Main evidence is in figures; only small tables. |
| 2410.06173 | Manual Verbalizer Enrichment for Few-Shot Text Classification | Same topic as RP-08 (low-resource classification); wide shots × datasets table. |
| 2410.10042 | LoRE: Logit-Ranked Retriever Ensemble for Open-Domain QA | Unusual table layout and a narrow evaluation; retrieval already covered by RP-04/RP-07. |
| 2511.08128 | Sentence-Anchored Gist Compression for Long-Context LLMs | Not selected (topic budget); results spread across many small stage-wise tables. |
| 2410.10849 | Continuous Approximations for Improving QAT of LLMs | Only two small tables (single setting); too little evidence. |
| 2410.10876 | FreqMark: Frequency-Based Watermark for Sentence-Level Detection of LLM-Generated Text | Only two small tables; too little evidence. |
| 2506.04760 | Exp4Fuse: Rank Fusion Framework for Sparse Retrieval | Retrieval already covered by RP-04 and RP-07. |
| 2511.07461 | It Takes Two: A Dual Stage Approach for Terminology-Aware Translation | One small table; MT already covered by RP-06. |
| 2511.08821 | BayesQ: Uncertainty-Guided Bayesian Quantization | Mostly ImageNet/ResNet-50 vision results with a BERT/GLUE part. Every seed standard deviation is printed as 0.1. NLP-centric papers were preferred. |

## 3. Notes

- No paper was accepted on the basis of a license read from anywhere other than arXiv's own metadata
  (the `<license>` field of the OAI-PMH `arXivRaw` record, retrieved 2026-10-10).
- The arXiv license applies to the version distributed by arXiv. Every included package records the
  sha256 of the exact e-print archive downloaded (see `manifest.csv`).
