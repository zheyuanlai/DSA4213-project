# Execution Plan (autonomous engineering run, 2026-10-10)

> **Status note (2026-10-18, final).** This plan covers the engineering run of 2026-10-10. The human annotation it
> anticipates was not carried out; AI-judged evaluations replaced it. See [`docs/README.md`](README.md) and the final report
> [`report/final_report.md`](../report/final_report.md).

This plan records how the technical work for the DSA4213 Group 5 project was organized. The
project title is *Saying What the Evidence Shows: Overstatement and Understatement in
Agent-Written Results Sections*. The engineering run stops **before** human blind annotation,
which two group members will do.

| Phase | Deliverable | Acceptance check |
|---|---|---|
| 0 Preflight | repo skeleton, `.gitignore` first, key-limit check, model probes | `outputs/preflight/*.json`; ledger ≤ $0.50 for stage `preflight` |
| 1 Data + method | 48-case benchmark (16 DEV / 32 TEST), deterministic tools, 7 conditions, guarded client | `python -m benchmarks.validate` OK; `pytest` green |
| 2 DEV pilot + freeze | backbone chosen on DEV only; prompts/settings frozen | `configs/frozen_primary.yaml`, `benchmarks/freeze_manifest.json`, `docs/PROTOCOL_FREEZE.md` |
| 3 Primary run | 7 conditions × 32 TEST cases = 224 outputs | job manifest shows every job completed/failed (no silent drops) |
| 4 Real papers | 10–15 CC-licensed arXiv papers × C1–C4 | manifest + exact achieved counts |
| 5 Automatic evaluation | rule-verifiable metrics, costs, tool behaviour, PROXY labels | `docs/AUTOMATIC_RESULTS.md`, `figures/` |
| 6 Blind handoff | blinded packets, A/B templates, private condition map, merge/κ/scoring scripts | blinding integrity tests pass |
| 7 Audit + push | secret scan (tree + history), private GitHub repo | `scripts/security_check.py` exit 0; `gh repo view` shows PRIVATE |

Budget: a hard cap of $12.00 on new OpenRouter spend, enforced in code by `src/cost_guard.py`, with a $3 reserve kept on the $15 key.
Stage caps: preflight $0.50, dev $1.50, main $6.00, real $2.50, buffer $1.50.

Claude Code (Opus) did the orchestration and coding, with subagents for benchmark authoring,
real-paper package extraction and literature verification. **These AI workers are not
student contributions.** The backbone model evaluated in C1–C7 is a single pinned
OpenRouter model, not Claude.
