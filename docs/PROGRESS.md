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
- `dev_pilot3` (verifier conditions only, re-run on identical cached drafts, 64 jobs, $0.109): no invalid decisions and similar edit rates.
  C6 now removes an unsupported citation attribution. One imperfect correction was seen (C5: a wrong range changed to a less-wrong range).
- Backbone pinned: DeepSeek V4 Flash 0731 (`docs/MODEL_SELECTION.md`). Freeze: `docs/PROTOCOL_FREEZE.md`, `benchmarks/freeze_manifest.json`.

## Phase 3: Primary experiment
- `primary_v1` (frozen, 32 TEST × 7 = 224 jobs, 11:29–12:07 UTC): **224/224 completed**, no failures or protocol errors, $0.233.

## Phase 4: Real papers and exploratory diagnostic
- `real_v1` (frozen limits): 35/48 completed. The outline was truncated on 6 papers (C3/C4 failed) and the reviser on 1 (C2). Kept and reported.
- `real_v2` (`configs/amended_secondary.yaml`, all papers and conditions re-run): 46/48. RP-02 C3/C4 failed again at 1500 tokens. The packet uses `real_v2`.
- `diag_v2` (8 long-package cases × C7/C3/C4, design frozen and amended before any call): 24/24.

## Phase 5: Automatic evaluation
- `docs/AUTOMATIC_RESULTS.md` and `results/automatic/{synthetic_test,real_papers_v2,diagnostic_long}/` (TABLES.md, figures).
- Adaptive vs scripted tool calls per case: −3.66 (TEST), −3.27 (real, n=11), −6.63 (diagnostic). STRENGTHEN never occurred.

## Phase 6: Blind handoff
- Independent read-only audit: 4 MAJOR + 5 MINOR findings, all fixed or documented (`docs/FINAL_AUDIT.md`).
- Synthetic packet: 122 distinct texts, two passes (pass 1 without gold-worded checklists), opaque case aliases. Real packet: 39 outputs / 151 sentences.
  Integrity checks pass. Mappings are private.

## Phase 7: Audit and push
- Fresh-clone tests pass; README mock command verified; secret scan of tree and history: 0 findings; private GitHub repo pushed.
- Spend: $0.6978, reconciled with `GET /api/v1/key` to $0.000002.

## Supplementary: exploratory H2 failure diagnostic (after handoff)
- Design and 12 counterfactual DEV drafts committed first (`docs/H2_DIAGNOSTIC.md`); run once as `h2diag_v1` (C4 vs C5, frozen model/tools/budget), $0.011.
- Result: no STRENGTHEN on any draft; C4 = C5 on all 12. Claim-strengthening probes (SIG/CON/EFF): evidence retrieved 3/3 in both conditions, stronger fact acknowledged in SIG/CON, still ACCEPT. Omitted-finding probes (ROB/GEN/CIT): evidence mostly not retrieved.
- Documentation-only revision after external review: corrected the primary-run denominator (406 verified claims, not 488), split the probe types, named the retrieval measure precisely, and removed the claim that 0/6 false strengthening shows safety.

## Phase 8: exploratory multi-agent AI annotation (2026-10-18)

- Four blinded AI roles independently labelled the existing AB/CD packets; agreement was computed
  within pair and every disagreement was adjudicated against the supplied evidence.
- Consensus coverage: 122 synthetic outputs, 39 real-paper outputs, and 151 real-paper sentences.
- Added macro-F1, ordinal MAE, severe-error rate, and paired uncertainty for numeric, negative-result,
  unsupported-claim, and real-paper outcomes. The original outputs and TEST gold were unchanged.
- Results are in `docs/AI_ANNOTATION_RESULTS.md` and `results/ai_scored/`. They are explicitly
  exploratory AI judgements, not the human evaluation promised in the frozen protocol.
