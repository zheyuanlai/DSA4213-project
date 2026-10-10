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

## Phase 1: Data + method (in progress)
- Schemas: `src/package_schema.py` (model-visible), `benchmarks/schema.py` (gold, evaluator-only), `src/schemas.py` (run records).
- Deterministic evidence store and four tools: `src/evidence_store.py`, `src/tools.py`.
- Agent finite-state machine, adaptive and scripted (`src/verifier.py`). Seven conditions run through one pipeline with shared upstream artifacts (`src/conditions.py`, `src/agent.py`). Resumable runner (`src/runner.py`).
- Guarded OpenRouter client with offline mock (`src/openrouter_client.py`, `src/cost_guard.py`).
- Offline test suite: 53 tests passing (mock client only; no paid calls).
- Benchmark cases: being authored in two halves (SIG/ROB/GEN/CON and EFF/CIT/NUM/NEG). The source with gold is in the gitignored `private/benchmark_source/`.
- Related-work verification: `docs/RELATED_WORK_VERIFICATION.md` (all 11 proposal references verified against public sources; see the discrepancies noted there).
