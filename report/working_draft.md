# Saying What the Evidence Shows: Overstatement and Understatement in Agent-Written Results Sections

*DSA4213 Group 5. WORKING DRAFT, written before human annotation.*

> **Status banner (remove only when true):** Human blind annotation has **not** been done yet. Every
> calibration result in §5 is **PENDING**. Sections marked [AUTO] contain only automatic, rule-verified
> measurements. Sections marked [PROXY] contain unvalidated lexical heuristics and must not be cited as calibration accuracy.
> Contribution shares in §9 must be filled in and confirmed by all four students.

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
### 5.1 Primary human-scored calibration (H1–H3): **PENDING human annotation**
| Condition | Calibration acc. (N=24) | Overstatement | Understatement | Strong-stratum under. (N=12) | Coverage |
|---|---|---|---|---|---|
| C1–C7 | PENDING | PENDING | PENDING | PENDING | PENDING |

Produced by `python -m evaluation.score_human ...` after adjudication. Includes paired bootstrap CIs and edit transitions.

### 5.2 Automatic results [AUTO]
See `docs/AUTOMATIC_RESULTS.md`: completion, cost per case, model and tool calls, latency, verifier decision distribution, tool
trajectories, numeric grounding, and NUM value recall.

### 5.3 Proxy diagnostics [PROXY]
See `docs/AUTOMATIC_RESULTS.md` §PROXY. These are lexical heuristics only. Their agreement with the human labels will be reported once those exist.

### 5.4 Real-paper study: **PENDING human annotation** (claim support and readability)

## 6. Failure analysis
Examples with source IDs from the traces are in `docs/AUTOMATIC_RESULTS.md`, including numeric corrections, a misattribution miss on DEV, and parallel-call behaviour.
To be extended with human-identified failures.

## 7. Costs and risks
Actual OpenRouter spend comes from `outputs/cost_ledger.jsonl` (see `docs/FINAL_AUDIT.md`). Risks: over-trusting automatic
verification; proxy metrics mistaken for calibration; benchmark traps being learnable; the single-backbone limitation.

## 8. Limitations
32 TEST cases give power only for large effects. One backbone model with reasoning off. Synthetic cases are author-designed.
Real papers have no gold. Lexical proxies are unvalidated. Shared drafts make the conditions dependent by design, which the paired analysis handles.

## 9. Contributions and AI use
**Student contribution shares: TO BE CONFIRMED BY ALL FOUR STUDENTS (must sum to 100%).**
AI use: Claude Code (Anthropic) implemented the code, drafted the synthetic cases and documentation, and extracted the real-paper packages
under the coordinator's direction. The evaluated backbone is DeepSeek V4 Flash via OpenRouter. AI assistants are not group members.
