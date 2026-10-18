# Saying What the Evidence Shows: Overstatement and Understatement in Agent-Written Results Sections

*DSA4213 Group 5. WORKING DRAFT. All evaluation labels are AI-generated; no human annotation has been performed.*

> **Status banner:** The planned human blind annotation was **not** carried out. Calibration and claim-level results
> in §5 come from **AI judges** (a multi-agent AI annotation of the focal labels, `docs/AI_ANNOTATION_RESULTS.md`, and a
> post-freeze, exploratory evidence-level evaluation by two AI model families with AI adjudication,
> `docs/EVALUATION_EXTENSION_RESULTS.md`). They must not be reported as human judgements, and AI–AI agreement is not
> human inter-annotator reliability. Sections marked [AUTO] contain automatic, rule-verified measurements; [PROXY]
> marks unvalidated lexical heuristics. Contribution shares in §9 must be filled in and confirmed by all four students.

## 1. Introduction and research question
Researchers increasingly ask LLM agents to draft Results sections from completed experiments. Such text can
**overstate**, for example by calling a mean difference "significant" with no test, claiming robustness that was never
tested, or saying "consistently" when the method won 3 of 5 datasets. It can also **understate**, when a cautious
checker weakens a conclusion the evidence fully supports. We ask: *does claim-by-claim evidence verification
improve calibration, reducing overstatement without creating excessive understatement, compared with direct generation and a generic
writer–reviewer loop, under controlled inference and revision budgets?* (H1–H3: see `docs/PROTOCOL_FREEZE.md`.)

## 2. Related work (verified sources only; see `docs/RELATED_WORK_VERIFICATION.md`)
* Evidence-locked or calibrated scientific reporting: Provenance Before Prose (Fan et al., 2026, arXiv preprint); CalBrief (Fu et al., 2026).
  CalBrief reports that an explicit strength-calibration policy downgraded 59 of the 61 takeaways whose human-verified label was "moderate" (§7.1) in a 16-package pilot.
* Exaggeration measurement: RIGOURATE (Findings of ACL 2026); Wright & Augenstein (EMNLP 2021) label press releases as undersell, accurate or exaggerate.
  **We therefore do not claim to be the first to study understatement.**
* Claim–evidence reasoning and grounded critique: CLAIM-BENCH (IJCNLP-AACL 2025), CLAIMCHECK (Findings of EMNLP 2025), SciTrue (EACL 2026 demo).
* Research agents: The AI Scientist (2024), Agent Laboratory (Findings of EMNLP 2025), Spark-to-Paper, EviGraph and ResearchLoop (2026 preprints; numbers "as reported").
* Self-refinement and tool-based critique: Self-Refine (NeurIPS 2023), CRITIC (ICLR 2024). Atomic factuality: FActScore (EMNLP 2023).
* **Positioning (hedged):** among the agent systems we read, verification either only downgrades or blocks claims, or only scores exaggeration.
  Our contribution is a *controlled bidirectional* study with matched-pair cases and explicit STRENGTHEN/no-STRENGTHEN ablations.

## 3. Benchmark
48 original synthetic cases (8 categories × 6; 16 DEV / 32 TEST; 24 matched pairs, each differing in one evidence fact).
Six ordinal categories have gold ℓ ∈ {0,1,2} (TEST: 12 strong, 6 ℓ=1, 6 ℓ=0). Numerical reporting and negative results use separate protocols.
Gold rules: `docs/BENCHMARK_SPEC.md`. Real-paper study: 12 CC-licensed arXiv papers, with no gold labels.

## 4. System and conditions
Deterministic evidence store; four tools; finite-state verifier; seven conditions with shared upstream drafts (Table in README).
Backbone: `deepseek/deepseek-v4-flash-0731` for every condition (`docs/MODEL_SELECTION.md`).

## 5. Results
### 5.1 Focal calibration (H1–H3), AI-judged [AI]
Multi-agent AI annotation of the 24 ordinal TEST cases (`docs/AI_ANNOTATION_RESULTS.md`): focal exact accuracy is 1.000
for C2–C6 and 0.958 for C1 and C7; overstatement 0.042 for C1/C7 and 0 elsewhere; no understatement in any condition.
This metric is at ceiling: five of seven systems are perfect, so it cannot rank them. That is the reason for §5.2.

### 5.2 Whole-passage, evidence-level evaluation (post-freeze, exploratory) [AI + deterministic]
Following tutor feedback, every generated passage was decomposed into atomic claims (1,591 claims, 2,618 numbers),
each claim verified against its package by two AI judge families with blind AI adjudication, numbers checked by
deterministic code, real-paper and long-package findings scored against package-only checklists, and verifier edits
compared claim by claim with their own drafts. Full results and intervals: `docs/EVALUATION_EXTENSION_RESULTS.md`.

| Synthetic TEST (32 cases) | C1 | C2 | C6 | C7 | C3 | C4 | C5 |
|---|---|---|---|---|---|---|---|
| Strict complete & correct passage | 0.594 | 0.719 | 0.719 | 0.625 | 0.688 | 0.750 | 0.750 |
| Atomic support rate | 0.926 | 0.943 | 0.951 | 0.948 | 0.963 | 0.970 | 0.970 |
| Fully supported passage | 0.656 | 0.594 | 0.750 | 0.719 | 0.781 | 0.812 | 0.812 |
| Numeric precision / recall | .98/.83 | .98/.83 | 1.00/.83 | .99/.72 | .99/.72 | .99/.72 | .99/.72 |

| Real papers (completed runs) | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| Atomic support rate | 0.894 | 0.885 | 0.873 | 0.874 |
| Finding recall | 0.376 | 0.412 | 0.487 | 0.474 |
| Negative/null-finding recall | 0.179 | 0.256 | 0.417 | 0.417 |
| Fully supported passage | 0.250 | 0.250 | 0.091 | 0.091 |

* **H1.** C4 beats direct generation on strict passage success (C4 − C1 +0.156, 95% CI [0.000, +0.312]) but does **not**
  outperform the writer–reviewer loop: C4 − C2 is +0.031 [−0.094, +0.156] on strict success and +0.027 [−0.009, +0.063]
  on atomic support, and C4 is worse on numeric recall (−0.109 [−0.185, −0.033]). On real papers C4 is not better than
  C1 or C2 in support; its higher negative-finding recall comes from the shared outline draft, not from verification.
* **Verification effect (C4 vs its own draft C7).** Small and harmless on synthetic cases (support +0.022 [+0.004,
  +0.050]; no new errors); +0.018 [0.000, +0.057] on real papers; none on the long packages. Verifiers repaired 29–43%
  of synthetic draft errors but only 7–10% of real-paper draft errors, mostly because they ACCEPTed erroneous sentences
  after retrieving relevant evidence. The generic reviser repaired more but introduced 9 (synthetic) and 12 (real) new errors.
* **H3.** Adaptive verification (C4) matches or slightly exceeds scripted verification (C3) at lower cost
  (−3.66 tool calls and −$0.0003 per synthetic case). This is an efficiency result.
* Contrasts in this section keep their direction when recomputed from either AI judge alone, except real-paper C4 vs C2
  differences in support and overall finding recall, which change sign and are inconclusive.

### 5.3 Automatic results [AUTO] and proxy diagnostics [PROXY]
See `docs/AUTOMATIC_RESULTS.md`: completion, cost per case, model and tool calls, latency, verifier decision distribution,
tool trajectories, numeric grounding, NUM value recall, and lexical PROXY levels (unvalidated; never cite as calibration accuracy).

### 5.4 H2 as a negative finding [AUTO + exploratory diagnostic + AI]
In the primary experiments, enabling strengthening did not lead to any STRENGTHEN actions (0 of 406 verified TEST claims across C3–C6;
0 on real papers and long packages). C4 and C5 are indistinguishable on every AI-judged metric. A supplementary DEV-only diagnostic
with deliberately weaker drafts showed the same pattern: the full verifier accepted all six probes without revision
(`docs/H2_DIAGNOSTIC.md`). Trace analysis identified two failure modes: incomplete retrieval of evidence supporting stronger
conclusions, and acceptance of supported but unnecessarily weak claims. Allowing strengthening as an action was insufficient
to induce bidirectional claim calibration; zero strengthening must not be read as successful bidirectional calibration.

### 5.5 Real-paper study [AI]
46/48 runs completed (RP-02 failed for C3/C4 on outline truncation). Real-paper passages carry two to three times the synthetic
claim-level error rate (0.10–0.13 vs 0.03–0.07) and only 9–25% of them are fully supported; see §5.2.

## 6. Failure analysis
Concrete before/after verifier edits with their AI labels are in `docs/EVALUATION_EXTENSION_RESULTS.md` §4.4: correct numeric
repairs (a 2.9-point gain corrected to 3.8 on the right dataset), correct removal of unsupported inference, an edit that replaced
one wrong number with another misattributed one, range endpoints left wrong after attribution fixes, and an overstated summary
replaced by four overstated per-benchmark claims. DEV examples and parallel-call behaviour are in `docs/AUTOMATIC_RESULTS.md`.

## 7. Costs and risks
Actual OpenRouter spend comes from `outputs/cost_ledger.jsonl` (see `docs/FINAL_AUDIT.md`). Risks: over-trusting automatic
verification; proxy metrics mistaken for calibration; benchmark traps being learnable; the single-backbone limitation.

## 8. Limitations
* **AI-generated annotations.** All calibration, claim, coverage and edit labels come from AI models. Judges from two model
  families were used, but their errors (and the extractor's and adjudicator's) may be correlated; the adjudicator shares one
  judge's model family. **There is no independent human validation.**
* **Ceiling effect.** The pre-registered focal-label metric is saturated on the synthetic TEST set.
* **Post-freeze metrics.** The evidence-level metrics in §5.2 were designed after the frozen evaluation and the first AI
  results; they are exploratory, and several checker and scoring refinements are documented in the protocol's amendment log.
* **Adjudicator instability.** Re-asking the AI adjudicator the identical prompts changed 19% of synthetic and 10% of
  real-paper disputed label decisions and 31% of real-paper coverage decisions; no planned contrast changed sign, but
  per-system repair rates and real-paper finding recall moved (`docs/EVALUATION_EXTENSION_RESULTS.md` §10).
* **Small samples.** 32 TEST cases (24 ordinal, 4 NUM, 4 NEG), 11–12 real papers, 8 long cases; most intervals include zero.
* **No STRENGTHEN actions**, so H2 could not be tested as designed.
* **Mixed and negative findings.** The full agent does not outperform the writer–reviewer baseline; verification gains are
  small and nearly absent on real and long packages; numeric recall is lower in the outline-based lineage.
* One backbone model with reasoning off. Synthetic cases are author-designed. Real papers have no gold; their checklists were
  built by AI from the packages. Lexical proxies are unvalidated. Shared drafts make conditions dependent by design, which the
  paired analysis handles.

## 9. Contributions and AI use
**Student contribution shares: TO BE CONFIRMED BY ALL FOUR STUDENTS (must sum to 100%).**
AI use: Claude Code (Anthropic) implemented the code, drafted the synthetic cases and documentation, and extracted the real-paper packages
under the coordinator's direction. The evaluated backbone is DeepSeek V4 Flash via OpenRouter. All evaluation labels were produced by
AI: Codex agents for the multi-agent focal annotation; GPT-5.6 (Codex CLI) and Claude Sonnet 5.5 / Haiku 5.5 (Claude CLI) as judges,
and GPT-5.6 as adjudicator, for the evidence-level evaluation. AI assistants are not group members and their labels are not human judgements.
