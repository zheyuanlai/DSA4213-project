# Related-Work Verification

Project: *Saying What the Evidence Shows: Overstatement and Understatement in Agent-Written Results Sections*

Verification date: 2026-10-10. Sources checked: arXiv abstract pages and the arXiv export API (for exact titles, authors, dates, versions), the full-text PDFs (downloaded and searched locally), ACL Anthology entry pages and their official `.bib` files, NeurIPS/ICLR proceedings pages and their official `.bib` files, and Crossref DOI metadata. Content summaries come only from text actually read (the abstract plus the sections cited). Verified BibTeX is in `report/references_verified.bib`.

Status legend: **VERIFIED** = the source exists and title, authors, and ID/venue match (or the only difference is a stale or under-specified venue that this report corrects). **PARTIALLY VERIFIED** = title found, but the ID, venue, or authors conflict. **NOT FOUND** = no public source located.

## Summary table

| # | Short name | Status | Verified ID / venue | Discrepancy flag |
|---|---|---|---|---|
| 1 | Provenance Before Prose | VERIFIED | arXiv:2608.25336 (v2, 19 Sep 2026), cs.CL | Minor: the PDF header says "Accepted to EMNLP: August 2026". arXiv has no journal-ref, and no EMNLP 2026 proceedings are on the ACL Anthology yet, so cite it as an arXiv preprint. |
| 2 | CalBrief | VERIFIED | arXiv:2606.27383 (v1, 11 Jun 2026), cs.DL | ID matches. **The 59/61 claim is in the paper (§7.1, p. 10)**, but the proposal's wording should be tightened (see §2). |
| 3 | RIGOURATE | VERIFIED | Findings of ACL 2026, pp. 34022–34043 (arXiv:2601.04350) | **Venue update:** now published in Findings of ACL 2026. Cite the Anthology version. |
| 4 | Can AI Validate Science? (CLAIM-BENCH) | VERIFIED | IJCNLP-AACL 2025 (main/long), pp. 2355–2379. arXiv:2506.08235 | The proposal gives only "2025". The venue is IJCNLP-AACL 2025. The arXiv v1 subtitle differs ("...for Accurate Scientific Claim → Evidence Reasoning"). The proposal's title matches the Anthology version. |
| 5 | The AI Scientist | VERIFIED | arXiv:2408.06292 (v3, 1 Sep 2024), cs.AI | None. Note: a consolidated Nature 2026 paper exists under a different title (see §5). |
| 6 | CLAIMCHECK | VERIFIED | Findings of EMNLP 2025, pp. 21712–21735. arXiv:2503.21717 | None. |
| 7 | Spark-to-Paper | VERIFIED | arXiv:2608.11924 (v1, 12 Aug 2026), cs.CL | Trivial: one author is "Junsheng Zhang" in the arXiv metadata but "Jusheng Zhang" in the PDF. |
| 8 | EviGraph | VERIFIED | arXiv:2608.04738 (v2, 6 Aug 2026), cs.AI | None. **Caution:** a different paper uses the same name, arXiv:2608.24667 ("EviGraph: Towards Verifiable Evidence Construction for Information-Seeking Agents"). Do not mix them up. |
| 9 | Agent Laboratory | VERIFIED | Findings of EMNLP 2025, pp. 5977–6043. arXiv:2501.04227 | None. |
| 10 | SciTrue | VERIFIED | EACL 2026, **Volume 3: System Demonstrations**, pp. 397–406 | Minor: it is a **demo-track** paper, so cite it as such. A different SciTrue paper exists (arXiv:2609.00654, NTCIR SciClaimEval). |
| 11 | ResearchLoop | VERIFIED | arXiv:2605.28282 (v1, 27 May 2026), cs.AI, technical report | None. |
| A1 | Wright & Augenstein 2021 (additional) | VERIFIED | EMNLP 2021, pp. 10824–10836 | n/a |
| A2 | Yu et al. 2020 (additional) | VERIFIED | COLING 2020, pp. 4860–4872 | n/a |
| A3 | Self-Refine (additional) | VERIFIED | NeurIPS 2023 (vol. 36), pp. 46534–46594 | n/a |
| A4 | CRITIC (additional) | VERIFIED | ICLR 2024 | n/a |
| A5 | FActScore (additional) | VERIFIED | EMNLP 2023, pp. 12076–12100 | n/a |

Counts for the 11 proposal references: **11 VERIFIED, 0 PARTIALLY VERIFIED, 0 NOT FOUND**. All 5 additional items are VERIFIED.

---

## Per-reference details

### 1. Provenance Before Prose (VERIFIED)
- **Exact title:** Provenance Before Prose: Claim-Locked Reporting for Statistical Text Generation
- **Authors:** Xiao Fan, Jingyuan Li, Hongbin Guo, Yubo Han, Yi Zhang (Xidian University)
- **Year / ID:** 2026. arXiv:2608.25336, v1 26 Aug 2026, v2 19 Sep 2026. cs.CL. No journal-ref.
- **URL:** https://arxiv.org/abs/2608.25336 (code: https://github.com/XiuFan719/Claim-Locked-Reporting)
- **Proposal vs. found:** The ID matches. The v2 PDF header reads "Accepted to EMNLP: August 2026", but arXiv records no journal-ref and the ACL Anthology has no EMNLP 2026 event page yet (HTTP 404 on 2026-10-10). Treat the acceptance as self-reported and cite the arXiv version.
- **Content (abstract, §1–3, App. A):** The paper treats statistical claim distortion (drifted numbers, inverted directions, overstated strength) as a control problem. A claim builder turns a structured statistical evidence record into a *claim ledger*. Each claim is bound to its evidence source, numbers, direction, and *allowed language strength*. A risk auditor and a policy controller then decide which claims are admissible. A deterministic renderer emits the numbers, and the LLM writes only connective prose. The policy controller applies a **"monotone strength downgrade: a flagged claim's allowed language strength can only be lowered, never raised"** (§3.2). The evaluation covers fMRI functional-connectivity reports and RCT reports from Evidence Inference 2.0, measuring cross-run reproducibility (+37.4 and +20.5 points over a hybrid template) plus "Strong" (unhedged strong-language) and "Hedge" governance counts.
- **Relation to our study:** This is the closest prior work on locking claim strength to evidence before or while writing. It differs from our study in three ways. Its strength control is one-directional by design (downgrade only). Its governance metrics count over-strong sentences and do not penalise unnecessary hedging. It works from a structured statistical record with LLM-free rendering, not from an agent revising free-form Results prose. Our two-directional (overstatement *and* understatement) evaluation is a clear point of contrast.

### 2. CalBrief (VERIFIED, 59/61 claim found)
- **Exact title:** CalBrief: A Pilot Diagnostic Benchmark for Evidence-Calibrated Scientific Briefing with Large Language Models
- **Authors:** Yu Fu, Yongqi Kang, Yong Zhao (Sichuan University)
- **Year / ID:** 2026. arXiv:2606.27383, v1 only, 11 Jun 2026. Primary category cs.DL (also cs.AI, cs.CL).
- **URL:** https://arxiv.org/abs/2606.27383
- **Proposal vs. found:** The ID and title match.
- **Content (abstract, §1–7):** The pilot benchmark has 16 scientific evidence packages and 96 human-verified package-level takeaways. Gold strength labels are binary: 61 moderate, 35 weak (Table 1). CalBrief is an auditable role/gap/strength probe. Its final calibration step is a deterministic policy that maps support, gaps, and mismatch signals to {moderate, weak, uncertain, insufficient_evidence} (§4). The structured pipeline improves role and gap reasoning, but its explicit strength calibration is "systematically over-conservative": strict macro-F1 is 0.0406, against 0.3867 for always-moderate and up to 0.6250 for direct LLM prompting (Table 3). A closed-model diagnostic (GPT-4o, Claude Sonnet, Gemini Flash) attributes about 63% of the conservatism gap to expanding the label space from binary to 4-way, about 1% to gap/scope signal injection (not significant), and about 36% to the pipeline policy itself (Table 5).
- **59/61 verification result: FOUND.** Section 7.1, "Systematic Conservatism in Explicit Calibration" (p. 10), says:
  > "The dominant strength error is directional conservatism. Of the 61 gold-moderate takeaways, only 2 are predicted moderate; the remaining 59 are downgraded (22 to weak, 16 to uncertain, 21 to insufficient evidence). No gold-weak takeaway is upgraded to moderate, and within the weak class 33 of 35 are pushed to insufficient evidence."

  The paper also describes the mechanism: "the policy treats missing higher-level evidence as a reason to weaken even properly bounded takeaways" (§7.1).
  **Wording caveats for the proposal's sentence** ("a pilot calibration mechanism weakened 59 of 61 conclusions that deserved a stronger label"):
  1. The units are *package-level takeaways* in a briefing task, not Results-section claims.
  2. "Deserved a stronger label" means the human-verified gold label was **moderate**, the stronger of the two binary gold labels. There is no "strong" label.
  3. "Weakened" here means the predicted strength label was downgraded, including to the abstention-like labels uncertain and insufficient_evidence. The paper attributes most of the overall conservatism gap to adding those labels.
  4. The figure comes from a small pilot (16 packages).

  Suggested wording: *"In the CalBrief pilot benchmark, an explicit strength-calibration policy downgraded 59 of the 61 takeaways whose human-verified strength label was 'moderate' (Fu et al., 2026, §7.1)."*
- **Relation to our study:** This is the most direct evidence that calibration mechanisms can **cause understatement**, the failure mode our study guards against. It differs from our study in task (multi-paper briefing versus claim-by-claim Results verification), in that it diagnoses the problem without proposing a fix, and in using binary gold labels.

### 3. RIGOURATE (VERIFIED; now published)
- **Exact title:** RIGOURATE: Quantifying Scientific Exaggeration with Evidence-Aligned Claim Evaluation
- **Authors:** Joseph James, Chenghao Xiao, Yucheng Li, Nafise Sadat Moosavi, Chenghua Lin
- **Year / venue:** 2026. *Findings of the Association for Computational Linguistics: ACL 2026*, San Diego, July 2026, pp. 34022–34043, DOI 10.18653/v1/2026.findings-acl.1699. arXiv:2601.04350 (v2, 12 Jan 2026).
- **URL:** https://aclanthology.org/2026.findings-acl.1699/ (arXiv: https://arxiv.org/abs/2601.04350)
- **Proposal vs. found:** The arXiv ID is correct. **Current status: published in Findings of ACL 2026.** Cite the Anthology version.
- **Content (abstract, §1–3, App. prompt):** The paper defines *intra-paper overstatement detection*: claims in the abstract and introduction are scored against evidence (text, figures, tables) elsewhere in the same paper. The dataset has over 10K claim–evidence sets from ICLR and NeurIPS papers, annotated by eight LLMs, with scores calibrated using OpenReview comments and validated by human evaluation. The system is a fine-tuned reranker for evidence retrieval plus a fine-tuned multimodal model that predicts a continuous overstatement score in [0, 1] with a justification. The annotation scale runs from "0.0: no exaggeration" to "1.0: major exaggeration", and the paper explicitly focuses on exaggeration. It cites understatement as a separate fact-checking dimension that it does not model (§2.1).
- **Relation to our study:** This is a strong detector-side precedent for evidence-proportional claim strength in ML papers. It differs from our study because its scale is one-sided (understatement is not scored), it targets human-written abstracts and introductions rather than agent-written Results sections, and it detects problems without revising text.

### 4. Can AI Validate Science? / CLAIM-BENCH (VERIFIED)
- **Exact title (published):** Can AI Validate Science? Benchmarking LLMs on Claim → Evidence Reasoning in AI Papers. The arXiv v1 title is "Can AI Validate Science? Benchmarking LLMs for Accurate Scientific Claim → Evidence Reasoning".
- **Authors:** Shashidhar Reddy Javaji, Yupeng Cao, Haohang Li, Yangyang Yu, Nikhil Muralidhar, Zining Zhu (Stevens Institute of Technology)
- **Year / venue:** 2025. *Proceedings of IJCNLP-AACL 2025* (14th IJCNLP and 4th AACL), Mumbai, December 2025, pp. 2355–2379, DOI 10.18653/v1/2025.ijcnlp-long.127. arXiv:2506.08235 (v1, 9 Jun 2025).
- **URL:** https://aclanthology.org/2025.ijcnlp-long.127/
- **Proposal vs. found:** The proposal gives only "2025" with no venue. The venue is IJCNLP-AACL 2025. The proposal's title matches the Anthology title.
- **Content (abstract, §1):** CLAIM-BENCH jointly evaluates claim extraction, evidence extraction, and claim–evidence link validation, using more than 300 manually annotated claim–evidence pairs from AI papers. Six LLMs are tested with three prompting strategies. Closed models outperform open ones, but the best model reaches only about 0.59 F1 on claim identification. Iterative, decomposed prompting (three-pass and one-by-one) increases retrieved pairs by more than 4x at higher computational cost. The authors attribute the difficulty to long-range dependencies between claims and dispersed evidence.
- **Relation to our study:** This supports the motivation that claim-to-evidence linking is hard for LLMs and that decomposed, claim-by-claim processing helps recall. It benchmarks extraction and linking only. It does not assess claim *strength* calibration and does not revise text.

### 5. The AI Scientist (VERIFIED)
- **Exact title:** The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery
- **Authors:** Chris Lu, Cong Lu, Robert Tjarko Lange, Jakob Foerster, Jeff Clune, David Ha
- **Year / ID:** 2024. arXiv:2408.06292 (v1 12 Aug 2024, v3 1 Sep 2024), cs.AI.
- **URL:** https://arxiv.org/abs/2408.06292
- **Proposal vs. found:** Matches. **Related:** a consolidated journal paper with a *different title* exists: C. Lu, C. Lu, R. T. Lange, Y. Yamada, S. Hu, J. Foerster, D. Ha, J. Clune, "Towards end-to-end automation of AI research", *Nature* 651(8107):914–919, 2026, DOI 10.1038/s41586-026-10265-5 (metadata from Crossref; Sakana AI's announcement calls 2408.06292 the "initial preprint"). I read only metadata for the Nature paper, not its text. Keep citing the arXiv paper for the v1 system details below.
- **Content (abstract, §3, §5):** An end-to-end pipeline covers idea generation, experiment iteration, LaTeX paper write-up (section by section with self-reflection, prompted to "only use real experimental results"), and an LLM automated reviewer reported to reach near-human performance. The in-depth case study (§5) lists pathologies including **"Positive Interpretation of Results. The paper tends to take a positive spin even on its negative results"**: a KL increase from 0.090 to 0.093 was reported as a "3.3% improvement". It also lists hallucinated experimental details (e.g., the GPU type).
- **Relation to our study:** This is the canonical agent-written-paper system, and its own case study documents overstatement in Results reporting, which motivates our work. It has no claim-level evidence verification or strength calibration, only generic self-reflection and a holistic reviewer.

### 6. CLAIMCHECK (VERIFIED)
- **Exact title:** CLAIMCHECK: How Grounded are LLM Critiques of Scientific Papers?
- **Authors (16):** Jiefu Ou, William Walden, Kate Sanders, Zhengping Jiang, Kaiser Sun, Jeffrey Cheng, William Jurayj, Miriam Wanner, Shaobo Liang, Candice Morgan, Seunghoon Han, Weiqi Wang, Chandler May, Hannah Recknor, Daniel Khashabi, Benjamin Van Durme (JHU)
- **Year / venue:** 2025. *Findings of the ACL: EMNLP 2025*, Suzhou, November 2025, pp. 21712–21735, DOI 10.18653/v1/2025.findings-emnlp.1185. Also arXiv:2503.21717.
- **URL:** https://aclanthology.org/2025.findings-emnlp.1185/
- **Proposal vs. found:** Matches.
- **Content (abstract, §1–3):** The dataset pairs rejected NeurIPS 2023/2024 submissions with OpenReview reviews. Experts annotated claim-related weaknesses, linked them to the paper claims they dispute, and labelled validity, objectivity, and type (Insufficient evidence, Contradictory, Novelty, Related Work, Clarity, Other). Three tasks: associate weaknesses with claims; label and rewrite weaknesses; verify claims with grounded reasoning. LLMs predict weakness labels reasonably well but underperform human experts on the other tasks. The authors argue that binary factuality labels miss the common case of claims that are "flawed but not entirely false".
- **Relation to our study:** It supports the reviewer/critic side: LLM critiques of claims are often weakly grounded. That motivates our evidence-locked, claim-by-claim verifier over a free-form reviewer. It evaluates critiques of human papers, not calibration of agent-written text, and has no strength scale.

### 7. Spark-to-Paper (VERIFIED)
- **Exact title:** Spark-to-Paper: End-to-End Research Paper Generation as a Composable Skill
- **Authors:** Zhuoyang Qian, Biao Wu, Yiran Wang, Chris D Yan, Desan Dai, Liangwei Zheng, Jin Jiang, Junsheng Zhang (arXiv metadata; "Jusheng" in the PDF), Wenhao Wang (Vast Intelligence Lab; UTS)
- **Year / ID:** 2026. arXiv:2608.11924 (v1, 12 Aug 2026), cs.CL.
- **URL:** https://arxiv.org/abs/2608.11924 (code: https://github.com/Spark-To-Paper-Skills/spark-to-paper-skills)
- **Proposal vs. found:** The ID matches. Trivial author-spelling difference (above).
- **Content (abstract, §1, App. C):** Thirteen composable skills run inside a coding assistant (implemented in Claude Code). Experiment planning is separated from reporting so that required evidence is fixed before results are seen. Claims are revised according to measured outcomes, and deterministic integrity checks are combined with self-critique. The claim-admission protocol (App. C, Table 5) assigns each major claim one of five labels: supported, partially-supported, unsupported, contradicted, needs-confirmation. The mapped actions are retain with evidence-matched wording, narrow, weaken/remove, remove or report as a limitation, and return for confirmation. Reported results: 99.5% citation validity; fabrication detection rises from 14% (single-pass) to 92% (full stack) on injected unsupported claims.
- **Relation to our study:** This is a close system-level analogue: claim-level evidence admission inside an agent writing pipeline. Its revision actions only narrow, weaken, or remove claims, and its evaluation measures detection of injected *unsupported* claims. I found no measurement of understated (over-weakened) claims. Our bidirectional metric fills that gap.

### 8. EviGraph (VERIFIED)
- **Exact title:** EviGraph: Evidence-Guided Autonomous Research Agents
- **Authors:** Zhenjiang Ren, Ruiji Li, Xujing Zhang, Ziliang Pang, Shuo Ren, Jiajun Zhang (CASIA / UCAS / HKBU / Wuhan AI Research)
- **Year / ID:** 2026. arXiv:2608.04738 (v1 5 Aug 2026, v2 6 Aug 2026), cs.AI. Comment: 23 pages.
- **URL:** https://arxiv.org/abs/2608.04738
- **Proposal vs. found:** Matches. Do not confuse it with the unrelated arXiv:2608.24667, which shares the "EviGraph" name.
- **Content (abstract, §1):** The research state is a typed evidence graph (Problem, Gap, Hypothesis, Experiment, Finding, Claim). The agent inspects chains for missing dependencies, semantic misalignment, and result–claim inconsistency, finds the earliest weak node, and regenerates its downstream subgraph, with checkpointing to reject harmful repairs. A manuscript is generated only when every retained claim is grounded in a validated chain. On ARC-Bench-ML and NanoResearch-20 it reports an 86.45% Overall score and a Claim Support Rate of 37.85% versus 27% for the strongest baseline (the "40.19%" figure is a relative gain), with 87.73% Experimental Data Consistency.
- **Relation to our study:** It shares the goal of claim–evidence consistency in agent-written papers. It works at the level of research-process architecture and measures claim *support* only, not under-claiming. Our study is narrower, focusing on calibrating claim strength in Results prose in both directions.

### 9. Agent Laboratory (VERIFIED)
- **Exact title:** Agent Laboratory: Using LLM Agents as Research Assistants
- **Authors:** Samuel Schmidgall, Yusheng Su, Ze Wang, Ximeng Sun, Jialian Wu, Xiaodong Yu, Jiang Liu, Michael Moor, Zicheng Liu, Emad Barsoum
- **Year / venue:** 2025. *Findings of the ACL: EMNLP 2025*, Suzhou, November 2025, pp. 5977–6043, DOI 10.18653/v1/2025.findings-emnlp.320. arXiv:2501.04227.
- **URL:** https://aclanthology.org/2025.findings-emnlp.320/
- **Proposal vs. found:** Matches.
- **Content (§3.3, §4; checked in both arXiv v2 and the Anthology PDF):** The framework moves from literature review to experimentation (mle-solver) to report writing (paper-solver). paper-solver builds a scaffold, then iteratively edits the LaTeX and scores drafts with an adapted version of the AI Scientist automated reviewer. Human evaluation found that automated reviewer scores "significantly overestimate" quality: 6.1/10 versus 3.8/10 overall from human reviewers.
- **Relation to our study:** It shows that holistic LLM reviewers inside writing loops are miscalibrated optimists. That supports replacing or augmenting them with claim-level evidence checks. It does not verify individual claims or calibrate their strength.

### 10. SciTrue (VERIFIED; demo track)
- **Exact title:** SciTrue: Evidence-Grounded Claim Verification in Science
- **Authors:** Neset Tan, Minghao Li, Mark Gahegan (University of Auckland). The PDF spells the first author "Neşet Özkan Tan".
- **Year / venue:** 2026. *Proceedings of the 19th Conference of the European Chapter of the ACL (Volume 3: System Demonstrations)*, Rabat, March 2026, pp. 397–406, DOI 10.18653/v1/2026.eacl-demo.27.
- **URL:** https://aclanthology.org/2026.eacl-demo.27/
- **Proposal vs. found:** "EACL 2026" is correct but incomplete. It is a **system demonstration** paper, so cite the demo volume. A separate SciTrue paper by an overlapping group exists (arXiv:2609.00654, NTCIR SciClaimEval shared task); do not mix them up.
- **Content (abstract, §3–4):** The system retrieves literature through the Semantic Scholar API (up to 15 articles, GPT-4o backbone) and decomposes a claim into subclaims. Each subclaim is linked to a specific supporting or refuting passage, with an evidence label (fully or conditionally supports or refutes), key assumptions, rhetorical role, and claim–article relationship strength (strong/medium/weak). The verdict is fully, mostly, partially, or not supported. In a human evaluation of 300 attributions it outperforms GPT-4o-search-preview and Perplexity Sonar Pro on traceability, attribution accuracy, and context alignment.
- **Relation to our study:** A precedent for tool-augmented, decomposed, graded verification of scientific claims against *external literature*. Our verifier instead checks claims against the paper's *own* experimental evidence and edits the wording. SciTrue issues verdicts and does not rewrite claims.

### 11. ResearchLoop (VERIFIED)
- **Exact title:** ResearchLoop: An Evidence-Gated Control Plane for AI-Assisted Research
- **Authors:** Yihan Xia, Taotao Wang (Shenzhen University)
- **Year / ID:** 2026. arXiv:2605.28282 (v1, 27 May 2026), cs.AI. Comment: "32 pages, 4 figures, 6 tables; technical report".
- **URL:** https://arxiv.org/abs/2605.28282
- **Proposal vs. found:** Matches.
- **Content (abstract, §1, §3, §5, §7.2):** Research questions, task contracts, evidence objects, claim ledgers, closeouts, and paper bindings are kept as durable repository-backed state. Claims are admitted only at the scope their evidence gate approves ("evidence first, admitted scope second, paper language last"). In a controlled study (16 SE-research tasks, 3 seeds, deterministic claim-extraction audit, no human adjudication), the full protocol lowers the unsupported-claim rate by 8.43 percentage points against an ad-hoc prompt (63.3% relative). Per-task significance is only borderline (Mann-Whitney p = 0.081, n = 16 tasks).
- **Relation to our study:** Another evidence-gating, claim-ledger design. It is one-directional (admission versus blocking), measures unsupported claims only, and its audit counts evidence-trace presence rather than whether claim strength matches the evidence.

---

## Additional verified works (optional, marked "additional")

### A1. Semi-Supervised Exaggeration Detection of Health Science Press Releases (additional, VERIFIED)
- Dustin Wright, Isabelle Augenstein. *Proceedings of EMNLP 2021*, pp. 10824–10836, DOI 10.18653/v1/2021.emnlp-main.845. arXiv:2108.13493. https://aclanthology.org/2021.emnlp-main.845/
- **Content (abstract, §2):** The task is formalised as a **three-way** label over (press release, abstract) pairs: "0 implies the target document undersells source document, 1 ... accurately reflects ..., and 2 ... exaggerates" (§2). The authors curate 563 expert-labelled pairs and propose MT-PET, a multi-task Pattern-Exploiting Training method with an auxiliary claim-strength task (correlational / conditional causal / direct causal).
- **Relation:** This is important prior art showing that *bidirectional* (undersell versus exaggerate) claim-strength labelling exists in science-communication NLP. Our contribution should therefore not claim to be the first to consider understatement. The difference is setting: we study agent-written Results sections checked against experimental evidence, with agentic revision.

### A2. Measuring Correlation-to-Causation Exaggeration in Press Releases (additional, VERIFIED)
- Bei Yu, Jun Wang, Lu Guo, Yingya Li. *Proceedings of COLING 2020*, pp. 4860–4872, DOI 10.18653/v1/2020.coling-main.427. https://aclanthology.org/2020.coling-main.427/
- **Content (abstract):** Claim-strength classifiers (correlational / conditional causal / direct causal / not claim) are applied to health press releases about observational studies. 22% of press releases turned correlational findings into causal claims, and universities exaggerated more often than journals (1.5:1).
- **Relation:** A precedent for an ordinal claim-strength taxonomy used to detect overclaiming relative to a source. It is detection-only and human-written.

### A3. Self-Refine: Iterative Refinement with Self-Feedback (additional, VERIFIED)
- Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, Peter Clark. *NeurIPS 2023* (Advances in NeurIPS 36), pp. 46534–46594, DOI 10.52202/075280-2019. https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html
- **Content (abstract only):** One LLM generates, critiques, and refines its own output iteratively, without training. It is evaluated on 7 tasks with GPT-3.5, ChatGPT, and GPT-4, with about 20% absolute average improvement over one-step generation.
- **Relation:** The canonical writer–self-critic loop, and a natural baseline for a "self-review" condition. It has no external evidence grounding.

### A4. CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing (additional, VERIFIED)
- Zhibin Gou, Zhihong Shao, Yeyun Gong, Yelong Shen, Yujiu Yang, Nan Duan, Weizhu Chen. *ICLR 2024*. arXiv:2305.11738. https://proceedings.iclr.cc/paper_files/paper/2024/hash/fef126561bbf9d4467dbb8d27334b8fe-Abstract-Conference.html
- **Content (abstract, §1):** The LLM verifies and revises its output through external tools (search, code interpreter, toxicity API) on QA, math program synthesis, and toxicity reduction. Key finding: "exclusive reliance on self-correction without external feedback may yield modest improvements or even deteriorate performance" (§1).
- **Relation:** This supports our design choice of tool- and evidence-grounded verification over pure self-critique. It does not address claim strength.

### A5. FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation (additional, VERIFIED)
- Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi. *Proceedings of EMNLP 2023*, pp. 12076–12100, DOI 10.18653/v1/2023.emnlp-main.741. https://aclanthology.org/2023.emnlp-main.741/
- **Content (abstract):** Generated text is decomposed into atomic facts, and FActScore is the fraction supported by a knowledge source. A retrieval-plus-LM estimator achieves under 2% error against human FActScore.
- **Relation:** The standard claim-decomposition verification paradigm. It measures support (binary per atomic fact) and is blind to strength miscalibration. Provenance Before Prose (#1) makes the same critique of output-level factuality metrics.

---

## Safe claims for the report

**Supported (citable as written):**
- LLM/agent research systems that write full papers exist and produce overstated or "positive-spin" results reporting. Cite The AI Scientist (§5 case study, "Positive Interpretation of Results") and Agent Laboratory (automated reviewers overestimate quality, 6.1 vs 3.8/10).
- Claim-to-evidence reasoning and grounded critique remain hard for LLMs (CLAIM-BENCH; CLAIMCHECK), and self-correction without external feedback is unreliable (CRITIC).
- Recent systems gate, lock, or downgrade claims against evidence: Provenance Before Prose (monotone, downgrade-only strength locking), Spark-to-Paper (claim-admission labels with narrow/weaken/remove actions), EviGraph (evidence-graph gating), and ResearchLoop (evidence-gated claim admission). Overstatement detection in papers exists (RIGOURATE; one-sided 0–1 exaggeration score).
- Calibration mechanisms can over-correct into understatement: CalBrief §7.1 reports that 59 of 61 gold-moderate takeaways were downgraded by an explicit calibration policy. Use the suggested wording in §2 and frame it as a pilot finding on briefing takeaways.
- Bidirectional (undersell/exaggerate) labelling has precedent in science-communication NLP (Wright & Augenstein 2021).

**Must be avoided or hedged:**
- Do **not** claim to be "the first" to study understatement or bidirectional claim-strength calibration (contradicted by Wright & Augenstein 2021's three-way label and by CalBrief's analysis of over-conservatism). A defensible, hedged version: *"to our knowledge, the agentic evidence-gating systems we reviewed (Provenance Before Prose, Spark-to-Paper, EviGraph, ResearchLoop) evaluate or enforce only the overstatement direction; we jointly measure over- and understatement in agent-written Results sections."* This rests on the sections read, not an exhaustive survey, so keep "to our knowledge".
- Do not describe the CalBrief statistic as "conclusions in Results sections" or imply a "strong" label existed. It concerns briefing takeaways with binary gold labels {moderate, weak}.
- Do not cite Provenance Before Prose as "EMNLP 2026" unless it appears in the ACL Anthology. The acceptance is self-reported in the PDF header only. Use the arXiv citation (optionally "to appear, EMNLP 2026 (per authors)").
- Cite RIGOURATE as Findings of ACL 2026, not arXiv-only. Cite SciTrue as an EACL 2026 *system demonstration*. Cite CLAIM-BENCH as IJCNLP-AACL 2025.
- Several key comparators (Provenance Before Prose, CalBrief, Spark-to-Paper, EviGraph, ResearchLoop) are **non-peer-reviewed 2026 arXiv preprints**. Describe their numbers as "reported" and avoid treating them as established results.
- Keep EviGraph (2608.04738) and SciTrue (EACL demo) distinct from their same-name namesakes (2608.24667; arXiv:2609.00654).
