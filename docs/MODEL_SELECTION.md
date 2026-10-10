# Backbone Model Selection (DEV only)

**Selected and pinned:** `deepseek/deepseek-v4-flash-0731` on OpenRouter, the same model for all seven conditions and for the real-paper study.

| Setting | Value | Reason |
|---|---|---|
| Provider routing | `order/only = [streamlake/fp8, parasail/fp8, deepinfra/fp8]`, `allow_fallbacks=true`, `require_parameters=true` | All three are fp8 endpoints that list `tools`, `tool_choice` and `response_format`. DeepInfra (cheapest) returned HTTP 429 "rate-limited upstream" throughout 2026-10-10. The serving provider is logged on every call. |
| `temperature` | 0 | Smallest valid setting. We do **not** assume determinism; shared drafts remove draft-sampling noise from the ablations. |
| `reasoning` | `{enabled: false}` | Equal across conditions. It avoids passing reasoning blocks through multi-turn tool loops and keeps cost and latency low. DEV quality was adequate without it, so reasoning-on was not explored (a documented limitation). |
| Structured output | `response_format: json_schema (strict)` for writer/outline/reviser; validated locally | |
| Tool calling | named `tool_choice` (scripted C3, forced `submit_decision`) and `"required"` (adaptive) | `parallel_tool_calls` is **not** sent because `require_parameters` would drop DeepInfra. Only the first tool call per turn is executed; extras are answered `NOT_EXECUTED`. |
| Per-call `max_tokens` | writer/outline/reviser 700, reviewer 450, verifier turn 450 | |

## Candidate probes (stage `preflight`, logged in `outputs/cost_ledger.jsonl`, outputs in `outputs/preflight/`)

| Candidate | Health | JSON schema | Forced named tool | `required` + multi-turn tool results | Forced `submit_decision` | Verdict |
|---|---|---|---|---|---|---|
| `deepseek/deepseek-v4-flash-0731` | ✓ | ✓ | ✓ | ✓ | ✓ | **selected** (first choice; full protocol works) |
| `qwen/qwen3.5-flash-02-23` (Alibaba only) | ✓ | ✓ | ✗ HTTP 404 "No endpoints found that support the provided 'tool_choice' value" | not reached | not reached | rejected: cannot run the scripted verifier (C3) natively |
| `deepseek/deepseek-v3.2`, `z-ai/glm-4.7` | not probed | | | | | not needed: the first choice worked |

Prices observed on 2026-10-10 differed from the indicative table in the brief. For V4 Flash 0731, the fp8 endpoints used
cost $0.088–0.14 per M input and $0.18–0.28 per M output tokens. All costs reported in this project are the
**provider-reported `usage.cost`**, not list prices.

## DEV pilot evidence (16 DEV cases × 7 conditions, run tag `dev_pilot2`)

* 112/112 jobs completed. There were no API errors, no failed drafts, and one invalid verifier decision. It came from a parsing bug in
  `evidence_ids` sent as a JSON-encoded string, which was fixed before freeze.
* Total DEV-pilot cost $0.155: about $0.0002 per case for C1, $0.0007 for C2, and $0.0015–0.0024 for the verifier conditions.
* Qualitative reading against the public DEV gold: the backbone's drafts were already scoped well on most DEV traps. Verifiers
  mostly ACCEPTed (~93% of claims) and made correct numeric corrections (e.g., a wrong margin range 3.6–4.4 corrected
  to the true 3.3–4.6). One clear miss was a misattributed citation (CIT-p1a): the scripted verifier's rationale noticed the
  passage did not state the figure but still ACCEPTed. This motivated the only verifier-prompt change before freeze
  (see `docs/PROTOCOL_FREEZE.md`).
* No STRENGTHEN decision occurred on DEV: the drafts showed little understatement for the verifier to correct.

The backbone is a Chinese-origin model chosen as low-cost experimental infrastructure. Comparing model origins is **not** a hypothesis of this project.
