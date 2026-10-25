# Reproducibility audit of the two D1-oracle batches (2026-10-25)

**Question.** D1-oracle strengthened 7/12 probes in `e1e2_v1` (2026-10-24) and 9/12 in `e2b_v1` (2026-10-25). Is anything
other than inference variability different between the two batches?

## Checks and results

| Check | How | Result |
|---|---|---|
| Full request body (messages, tools, tool_choice, max_tokens, decoding, provider routing) | Rebuilt the first-call body of all 39 probes from each batch's commit (`8b83f97` and `701e123`, both clean), in separate git worktrees, through V1's `OpenRouterClient.build_body`; compared SHA-256 | **39/39 identical** |
| Prompt files, V1 code, model, config | `run_meta.json` hashes | identical |
| Tokens seen by the backend | API `prompt_tokens` per probe | identical for 38/39 probes; the 39th differs only because one `e1e2_v1` run needed a repair turn (below) |
| Provider and backend model | OpenRouter generation metadata for 18 calls (the 3 probes that flipped, 3 repeats × 2 batches) | every call: model `deepseek/deepseek-v4-flash-20260731`, provider StreamLake, identical `native_tokens_prompt`, `native_finish_reason = tool_calls`, not BYOK |
| Provider over all D1 calls | run records | StreamLake 118/118 (`e1e2_v1`) and 117/117 (`e2b_v1`) |
| Truncation | `finish_reason` of every D1 call | all `tool_calls`; none `length` (max 800 tokens; observed completions about 300–450) |
| Repairs and protocol differences | `model_calls`, `protocol_errors` | `e1e2_v1`: 1 repair (P-ROB-U2-partner r3: REMOVE first cited no package ID; the final decision is REMOVE in both batches); `e2b_v1`: none |
| Raw decisions kept | per-run JSON records | yes: every repeat is stored, and majorities are computed only in analysis |

## Within-batch variation as well

Repeats in the same batch, minutes apart, also differ. In `e1e2_v1`, SIG-U-strong was STRENGTHEN, ACCEPT, ACCEPT. In
`e2b_v1`, CIT-U-strong was STRENGTHEN, STRENGTHEN, ACCEPT. The completion lengths of these calls differ, while their
inputs are identical.

## Conclusion

Nothing differs between the batches except the sampled outputs. The observed differences are best described as
**inference variability under nominally identical settings** (temperature 0, same model version, same provider, same
request bytes). Following the agreed approach, the backbone, temperature and seed are **not** changed to suppress it.
Instead:

* compared conditions are run in the same batch, interleaved, with repeats;
* raw per-run decisions are reported next to the majorities;
* differences of one or two probes are not interpreted as effects.

## Side note on V1's 450-token verifier turns

Across V1's DEV pilots and the long-package diagnostic, 25 verifier turns used exactly 450 completion tokens, the V1
per-turn limit. All of them still reported `finish_reason = tool_calls`, and they occur mainly in early pilot turns where
the model issued many parallel tool calls. In `e1e2_v1`, D0-tools used at most 373. E5 runs both tool conditions at 800
tokens per turn, so the limit does not differ between the compared decision frameworks.
