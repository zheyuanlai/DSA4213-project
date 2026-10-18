# Final Audit (engineering handoff, 2026-10-10)

> **Status note (2026-10-18, final).** This audit records the engineering handoff of 2026-10-10. Blind human
> annotation was not carried out; AI-judged evaluations followed ([`AI_ANNOTATION_RESULTS.md`](AI_ANNOTATION_RESULTS.md),
> [`EVALUATION_EXTENSION_RESULTS.md`](EVALUATION_EXTENSION_RESULTS.md)). The current integrity checks are
> `python scripts/verify_artifacts.py` and the CI workflow; see [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

**Overall status: synthetic study and real-paper study are READY FOR BLIND HUMAN ANNOTATION.** No human labels exist, so no
human-scored result or inter-annotator κ has been computed. H1–H3 calibration outcomes are pending.

## 1. Quality gates

| # | Gate | Status | Evidence |
|---|---|---|---|
| 1 | README, environment, CLI, tests | ✅ | `python -m pytest`: all tests pass. A fresh clone without `private/` passes, skipping 2 tests that need coordinator-private gold. README mock command verified in the fresh clone. |
| 2 | 48 validated cases, 16 DEV / 32 TEST, no gold leaks, pair invariants | ✅ | `benchmarks/validate.py` OK, `tests/test_benchmark_integrity.py`, `tests/test_gold_leakage.py` (AST check that inference code never reads gold) |
| 3 | Seven conditions implemented and unit-tested | ✅ | `src/conditions.py`, `tests/test_agent_conditions.py` (C5 cannot strengthen, C3 forced order, C6 no outline, C7 no verifier, C1/C2 no tools, identical C3/C4/C5/C7 drafts) |
| 4 | Live model actually called; no mock outputs in analyses | ✅ | 224/224 primary outputs with provider generation IDs. `auto_evaluate.py` and the packet builder refuse `is_mock` outputs. |
| 5 | Spend within $12 and $3 reserve kept | ✅ | $0.6978 total, reconciled to $0.000002 with `GET /api/v1/key` (`outputs/ledger_summary.json`) |
| 6 | Per-case outputs, traces, status and failure manifest | ✅ | `outputs/*/…/job_manifest.json`, `outputs/run_manifest.jsonl`, run records with every draft and trace (TEST/real withheld from git until annotation; sha256 in `outputs/WITHHELD_UNTIL_ANNOTATION.json`) |
| 7 | Automatic/proxy metrics with limitations documented | ✅ | `docs/AUTOMATIC_RESULTS.md`, `results/automatic/*/TABLES.md`. Every PROXY column is labelled UNVALIDATED. |
| 8 | Blind packets, two empty templates, stable IDs, mapping private | ✅ | Synthetic: 122 rows (from 224 runs), two passes, A/B independent orders. Real: 39 outputs / 151 sentences. Both pass `verify_packet`. Mappings in gitignored `private/`. |
| 9 | Merge/κ/scoring pipeline runnable on dummy fixtures | ✅ | `tests/test_human_scoring_scripts.py` (κ matches hand calculations, adjudication, strict scoring, real-paper merge/score) |
| 10 | Secret/privacy scan; private repo push | ✅ | `scripts/security_check.py`: 0 findings over the tree, index, full history and commit messages, including a live-key and fragment check. Repo `zheyuanlai/DSA4213-project` is PRIVATE. |

## 2. Independent audit (subagent, read-only) and resolution

| Finding | Severity | Resolution |
|---|---|---|
| Annotator rubric (gold-worded checklists) and pair-revealing case IDs could reveal gold | MAJOR | **Fixed before any packet release:** two-pass annotation (pass 1 without checklists), opaque case aliases, extended do-not-open list, spec wording corrected |
| `score_human` silently scored missing labels as level 0; mapping could be overwritten | MAJOR | **Fixed:** refuses missing or invalid labels; packet rebuild refuses to overwrite a mapping (force keeps a backup) |
| NUM value-recall tolerance inflated for ÷100/÷1000 conversions | MAJOR | **Fixed** + regression test |
| New run tag could reuse or overwrite another run's family; no cross-process lock; shared drafts reused across prompt/config changes | MAJOR | **Fixed after all paid runs:** run-tag guard, `.run.lock`, provenance check on shared artifacts (legacy artifacts without provenance are still reusable) |
| Repair path could leave a tool call unanswered | MINOR | **Fixed after all paid runs**. Never observed in any recorded run: 0 protocol errors in the primary run. |
| `compare_numbers` difference tolerance = 1 display unit; model-supplied tolerance uncapped | MINOR | **Documented, not changed**, so the released tool matches the recorded runs |
| Scripted mode would accept an early decision | MINOR | **Documented.** Never occurred: all 103 primary, 43 real-paper and 32 diagnostic scripted claims ran the full fixed 4-tool order |
| Non-timeout transport errors logged at $0; per-process reservations | MINOR | **Documented.** Final reconciliation shows ledger = key usage (Δ $0.000002) |
| Docs promised a missing real-paper scorer; freeze doc overstated which files were hashed | MINOR | **Fixed:** `evaluation/score_real_papers.py` added; freeze doc corrected |

Post-freeze changes are listed with timestamps in `docs/DEVIATIONS_FROM_PROPOSAL.md`. None of them changed a model call in the primary run.
`scripts/freeze_protocol.py --check` lists exactly these changed files: `annotation/ANNOTATION_GUIDE.md` (two-pass), `docs/BENCHMARK_SPEC.md` (wording correction), `evaluation/auto_metrics.py` (NUM tolerance), `evaluation/score_human.py` (strictness), `src/security_scan.py`, `src/runner.py` (max_tokens override, added before `real_v2`/`diag_v2`, plus later guards), and `src/agent.py` / `src/verifier.py` (hardening after all paid runs). **No prompt, `configs/frozen_primary.yaml`, `src/tools.py`, `src/writer.py`, `src/openrouter_client.py` or `src/evidence_store.py` changed.**
The primary run itself was produced at frozen commit `04bc5e5` (now `a32d2b5` after the message rewrite; identical tree, see `docs/COMMIT_SHA_MAPPING.md`). Its code hash is stored in every run record.

## 3. Security and privacy
* The OpenRouter key was read only from the environment. It was kept in a mode-600 file in the session scratchpad, outside the repository, and was never
  written to a tracked or untracked project file, a command line, a log or the ledger. The scanner checks the full key and 16-character fragments
  of it across all files and all git history: 0 findings.
* **Recommended:** rotate the key (it appeared in the chat that started this run) and delete the scratchpad copy. Only the key owner can rotate it.
* Coordinator-only files that are **not** in GitHub and must be backed up: `private/` (condition mappings, case aliases, TEST and diagnostic gold,
  authored sources, packet seeds, per-run automatic rows, TEST edit examples), `outputs/synthetic/`, `outputs/real_papers/`, `outputs/real_papers_v2/`.
* No student numbers or personal data are in the repository (scanner pattern for NUS student numbers: 0 findings). Git commits use the account owner's configured identity.
* Real-paper excerpts are from CC BY 4.0 / CC BY-SA 4.0 papers only (re-verified via arXiv OAI). Raw LaTeX sources are not committed.

## 4. Known limitations (to carry into the report)
One backbone model with reasoning off. 32 TEST cases give power only for large effects. STRENGTHEN never fired, so H2 cannot be tested as designed.
The frozen token limits truncated on long real papers (`real_v1`); `real_v2` with amended limits still failed on RP-02.
Lexical proxies are unvalidated. Numeric grounding is a lower bound. Synthetic cases were written by AI subagents under the coordinator's direction and reviewed by the lead agent.
They still need student review before the report. Shared drafts make conditions dependent by design (the analysis is paired).
