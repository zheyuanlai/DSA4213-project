# Real-paper secondary dataset (`split = "real"`)

This folder holds 12 research packages built from recent (2024–2025) NLP/ML arXiv papers whose
licenses allow derived excerpts to be redistributed. It is the **secondary** dataset of the
DSA4213 project. It checks whether the claim-calibration behaviour seen on the synthetic
benchmark also appears with real evidence. Each package gives the model the evidence an author
had (question, method and setup summaries, a subset of results tables, any reported statistical
tests, and short attributed excerpts). The model then writes a short Results/Discussion passage.

**There are no gold labels.** These cases carry no `category`, no focal proposition, and no
correct claim level. Human reviewers judge each output for claim support (is every claim backed
by the package evidence, and is its strength calibrated?) and for readability. The authors' own
headline claims are recorded separately, for qualitative comparison only, in the gitignored
`private/real_papers/author_claims.jsonl`. They are **not** gold labels: some author claims are
themselves stronger than the evidence supports.

## Contents

| Path | What it is |
|---|---|
| `packages/RP-01.json` … `RP-12.json` | One `CaseRecord` per paper (`src/package_schema.py`). `case_id` RP-XX, `category: null`, `split: "real"`, `pair_id: null`. |
| `manifest.csv` | One row per package: arXiv ID, title, authors, year, URL, exact license URL, retrieval date, sha256 of the downloaded e-print, tables used, method alias, status, notes. |
| `EXCLUDED.md` | Candidates screened and rejected, with reasons (license or content). |
| `raw/` | **Gitignored, not redistributed.** Original arXiv e-print archives (`raw/<arXiv-ID>/eprint.bin`) and their extracted LaTeX, kept only so the transcriptions can be re-checked locally. |

## How the packages were built

1. **Selection.** Candidates came from arXiv OAI-PMH `arXivRaw` listings for `cs.CL`. Only papers
   whose `<license>` field is CC BY 4.0, CC BY-SA 4.0 or CC0 1.0 were eligible. The default arXiv
   license and all NC/ND licenses were excluded. Papers were preferred if they had a quantitative
   method-vs-baseline table, variance or significance reporting, and ablation, robustness,
   generalization or efficiency results. Topics were diversified.
2. **Source.** For each paper the LaTeX e-print was downloaded from `https://arxiv.org/e-print/<ID>`
   into a new empty directory, and its sha256 was recorded. It was treated as untrusted data and
   only read as text (nothing in it was compiled or executed).
3. **Transcription.** One or two key results tables were transcribed by hand from the LaTeX, with
   values copied verbatim. Rows and columns were dropped to keep at most 8 rows × 7 columns. Some
   tables were restructured (for example transposed, or one column taken from each dataset block);
   every package notes this in the table `notes` and in `source_manifest.notes`. Values were
   checked automatically against the raw LaTeX: every cell number appears in the source, rows
   appear in order on one source line, and 181 restructured cells were checked one by one.
4. **What was withheld.** The paper's abstract, its Results/Discussion/Conclusion prose and its
   claim sentences are **not** in the packages. Neither is the title, which appears only in
   `source_manifest`, and `source_manifest` is never rendered to the model (`src/render.py`
   renders only `ResearchPackage` fields). `methods_summary` and `experimental_setup` are short
   paraphrases written for this dataset.
5. **Method renaming.** Each paper's own proposed method or system is replaced by a neutral alias
   ("Method M", "Model M-110M", "Method M-static", …) to reduce memorization effects. Baselines,
   models and datasets keep their real names. The one exception is RP-05, whose dataset shares
   the method's name and was renamed to "Dataset D". Renaming is **not** anonymization: a model
   may still recognize a paper from its numbers or setup.
6. **Statistical tests** are encoded in `statistical_tests` only when the paper reports them
   (RP-04: paired t-test markers; RP-08: one-tailed paired t-tests). Unreported fields are left
   null. Significance stars, standard errors and standard deviations that appear inside tables
   are kept as cell text.
7. **Excerpts** (`source_passages`) are 0–2 short (at most 60 words) verbatim sentences from the
   paper's setup or related-work text. They are attributed to "Source paper" because the title is
   withheld from the model. Full attribution is in `source_manifest` and below. Typographic
   rendering was the only change: LaTeX citation commands became bracketed references and inline
   math became plain text. Each case's manifest notes record these changes.
8. **Validation.** Every file passes
   `CaseRecord.model_validate(...)` and `EvidenceStore.from_package(...)` (run from the project root):

   ```bash
   for f in data/real_papers/packages/RP-*.json; do
     python -c "import json,sys; from src.package_schema import CaseRecord; from src.evidence_store import EvidenceStore; c=CaseRecord.model_validate(json.load(open(sys.argv[1]))); EvidenceStore.from_package(c.package); print('ok')" "$f"
   done
   ```

## Licensing and attribution

The papers below are the sources of the packages. Each package contains a derived, partial and
modified version of its source: a table subset (sometimes restructured), paraphrased summaries,
short excerpts, and the proposed method renamed. These changes are made under the paper's license.
Original raw sources are **not** redistributed. Nothing in this dataset implies endorsement by the
original authors.

- Packages derived from **CC BY 4.0** papers are shared under **CC BY 4.0**
  (https://creativecommons.org/licenses/by/4.0/).
- Packages derived from **CC BY-SA 4.0** papers (RP-03, RP-12) are shared under **CC BY-SA 4.0**
  (https://creativecommons.org/licenses/by-sa/4.0/), as share-alike requires.

| Case | Attribution (authors, year, title, arXiv) | License |
|---|---|---|
| RP-01 | Saksham Rastogi, Pratyush Maini, Danish Pruthi (2025). *STAMP Your Content: Proving Dataset Membership via Watermarked Rephrasings.* arXiv:2504.13416, https://arxiv.org/abs/2504.13416 | CC BY 4.0 |
| RP-02 | Paulius Rauba, Qiyao Wei, Mihaela van der Schaar (2025). *Statistical Hypothesis Testing for Auditing Robustness in Language Models.* arXiv:2506.07947, https://arxiv.org/abs/2506.07947 | CC BY 4.0 |
| RP-03 | Jiangnan Li, Thuy-Trang Vu, Christian Herold, Amirhossein Tebbifakhr, Shahram Khadivi, Gholamreza Haffari (2025). *CONGRAD:Conflicting Gradient Filtering for Multilingual Preference Alignment.* arXiv:2503.23777, https://arxiv.org/abs/2503.23777 | CC BY-SA 4.0 |
| RP-04 | Kidist Amde Mekonnen, Yosef Worku Alemneh, Maarten de Rijke (2025). *Optimized Text Embedding Models and Benchmarks for Amharic Passage Retrieval.* arXiv:2505.19356, https://arxiv.org/abs/2505.19356 | CC BY 4.0 |
| RP-05 | Alexander Spangher, Tenghao Huang, Jialiang Gu, Jiatong Shi, Muhao Chen (2025). *DiscoSum: Discourse-aware News Summarization.* arXiv:2506.06930, https://arxiv.org/abs/2506.06930 | CC BY 4.0 |
| RP-06 | Gahyun Yoo, Jay Yoon Lee (2024). *QE-EBM: Using Quality Estimators as Energy Loss for Machine Translation.* arXiv:2410.10228, https://arxiv.org/abs/2410.10228 | CC BY 4.0 |
| RP-07 | Siyuan Huang, Zhiyuan Ma, Jintao Du, Changhua Meng, Weiqiang Wang, Jingwen Leng, Minyi Guo, Zhouhan Lin (2025). *Gumbel Reranking: Differentiable End-to-End Reranker Optimization.* arXiv:2502.11116, https://arxiv.org/abs/2502.11116 | CC BY 4.0 |
| RP-08 | I-Fan Lin, Faegheh Hasibi, Suzan Verberne (2024). *Generate then Refine: Data Augmentation for Zero-shot Intent Detection.* arXiv:2410.01953, https://arxiv.org/abs/2410.01953 | CC BY 4.0 |
| RP-09 | Lingyuan Liu, Mengxiang Zhang (2025). *Being Strong Progressively! Enhancing Knowledge Distillation of Large Language Models through a Curriculum Learning Framework.* arXiv:2506.05695, https://arxiv.org/abs/2506.05695 | CC BY 4.0 |
| RP-10 | Tergel Munkhbat, Namgyu Ho, Seo Hyun Kim, Yongjin Yang, Yujin Kim, Se-Young Yun (2025). *Self-Training Elicits Concise Reasoning in Large Language Models.* arXiv:2502.20122, https://arxiv.org/abs/2502.20122 | CC BY 4.0 |
| RP-11 | Zhuoqun Huang, Neil G. Marchant, Olga Ohrimenko, Benjamin I. P. Rubinstein (2025). *AdaptDel: Adaptable Deletion Rate Randomized Smoothing for Certified Robustness.* arXiv:2511.09316, https://arxiv.org/abs/2511.09316 | CC BY 4.0 |
| RP-12 | Charles Goddard, Fernando Fernandes Neto (2025). *Training-Free Tokenizer Transplantation via Orthogonal Matching Pursuit.* arXiv:2506.06607, https://arxiv.org/abs/2506.06607 | CC BY-SA 4.0 |

License URLs, as recorded in each package's `source_manifest.license`, are the exact values of
arXiv's `<license>` metadata field, retrieved 2026-10-10.

## Topic coverage

LLM evaluation and contamination detection (RP-01), robustness auditing with hypothesis tests
(RP-02), multilingual preference alignment (RP-03), low-resource retrieval (RP-04),
structure-controlled summarization (RP-05), machine translation (RP-06), RAG reranker training
(RP-07), zero-shot intent detection through data augmentation (RP-08), knowledge distillation
(RP-09), efficient (concise) reasoning (RP-10), certified robustness (RP-11), and tokenizer transfer
(RP-12).

## Known limitations

- Each package is a subset of its paper. Evidence outside the transcribed tables (figures, other
  tables, text) is missing, and any judgement of claim support is relative to the package only.
- Several papers report no variance or significance tests. That is part of what the dataset is
  meant to probe, not a transcription gap.
- Some packages note inconsistencies or ambiguities found in the sources, for example a duplicated
  dataset label in RP-11 and a baseline value that differs slightly between two tables in RP-09.
