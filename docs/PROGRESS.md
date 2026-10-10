# Progress Log

Times are UTC+8 local session times on 2026-10-10. Each entry is factual. Nothing here
claims an experiment that was not run.

## Phase 0: Preflight
- Tooling: Python 3.13.13, git 2.43, gh 2.94. GitHub was already authenticated (account `zheyuanlai`, scope `repo`). Internet access to OpenRouter and arXiv worked.
- Key check (`GET /api/v1/key`, free): limit $15, limit_remaining $15, usage $0, not free tier.
  `GET /api/v1/credits` returned 403 (it needs a management key). The hard cap was set to min($12, $15 − $3) = **$12.00**.
- Model metadata snapshot: `outputs/preflight/model_metadata_snapshot.json`. Endpoint prices for
  `deepseek/deepseek-v4-flash-0731` range from $0.0085/$0.27 to $0.44/$1.32 per M tokens depending on provider.
- Paid probes (stage `preflight`), all logged in `outputs/cost_ledger.jsonl`:
  - DeepSeek V4 Flash 0731: health, JSON-schema output, forced named tool choice, `required` tool choice, multi-turn tool results and forced `submit_decision` **all passed**.
    DeepInfra was rate-limited upstream (HTTP 429) throughout. Routing was therefore restricted to fp8 endpoints (StreamLake → Parasail → DeepInfra) with `require_parameters=true`.
    `parallel_tool_calls` is not sent because DeepInfra does not support it and `require_parameters` would filter that provider out.
  - Qwen3.5 Flash 02-23 (Alibaba only): health and JSON passed. A forced named `tool_choice` was **rejected (HTTP 404, no endpoint supports it)**. The scripted verifier (C3) needs this, so Qwen cannot run the protocol natively.
  - 7 manual routing health checks were made with direct `httpx` calls outside the CostGuard. Their provider-reported costs were back-filled into the ledger (total $0.0000082).
- Ledger total after preflight: about $0.00033.

## Phase 1: Data + method (done)
- Schemas: `src/package_schema.py` (model-visible), `benchmarks/schema.py` (gold, evaluator-only), `src/schemas.py` (run records).
- Deterministic evidence store and four tools: `src/evidence_store.py`, `src/tools.py`.
- Agent finite-state machine, adaptive and scripted (`src/verifier.py`). Seven conditions run through one pipeline with shared upstream artifacts (`src/conditions.py`, `src/agent.py`). Resumable runner (`src/runner.py`).
- Guarded OpenRouter client with offline mock (`src/openrouter_client.py`, `src/cost_guard.py`).
- Offline test suite: all tests passing (mock client only; no paid calls).
- Benchmark: 48 cases written by two authoring subagents (SIG/ROB/GEN/CON and EFF/CIT/NUM/NEG) to the spec in `docs/BENCHMARK_SPEC.md`, then reviewed by the lead. All 48 pass `benchmarks.validate` (counts, splits, pairs, gold-evidence resolution, t/p/CI consistency, no rubric leakage). Built with `benchmarks.build`. TEST gold is private (`private/gold/test_gold.jsonl`), and its hash is in `benchmarks/build_hashes.json`.
- Real-paper packages: 12 packages (RP-01…RP-12) from CC BY 4.0 / CC BY-SA 4.0 arXiv papers. The lead independently re-checked every licence against arXiv OAI metadata (12/12 match).
- Related-work verification: `docs/RELATED_WORK_VERIFICATION.md` (all 11 proposal references verified against public sources; see the discrepancies noted there).

## Phase 2: DEV pilot and freeze
- `dev_pilot1` (4 DEV cases × 7 conditions, $0.029): found many parallel tool calls, so only the first call per turn is now executed.
- `dev_pilot2` (16 DEV × 7 = 112 jobs, $0.155): 112/112 completed with no API errors. Verifiers mostly ACCEPT (~93% of claims), make correct numeric fixes, and made no STRENGTHEN decisions.
  One parsing bug (`evidence_ids` as a JSON string) was found and fixed. One rationale/decision inconsistency (CIT-p1a) led to a shared verifier check-list.
- `dev_pilot3` (verifier conditions only, re-run on identical cached drafts, 64 jobs, ~$0.05): no invalid decisions and similar edit rates.
  C6 now removes an unsupported citation attribution. One imperfect correction was seen (C5: a wrong range changed to a less-wrong range).
- Backbone pinned: DeepSeek V4 Flash 0731 (`docs/MODEL_SELECTION.md`). Freeze: `docs/PROTOCOL_FREEZE.md`, `benchmarks/freeze_manifest.json`.
