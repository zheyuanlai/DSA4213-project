### diagnostic_long: per-condition summary

| metric | C7 | C3 | C4 |
|---|---|---|---|
| completed runs | 8 | 8 | 8 |
| failed runs | 0 | 0 | 0 |
| mean cost / case (USD) | 0.00110 | 0.00376 | 0.00310 |
| model calls / case | 2.00 | 22.00 | 15.38 |
| evidence-tool calls / case | 0.00 | 16.00 | 9.38 |
| summed call latency / case (s) | 8.3 | 53.5 | 42.2 |
| words in final passage | 145.6 | 144.6 | 145.6 |
| share of passages changed from starting draft | 0.000 | 0.125 | 0.125 |
| WEAKEN decisions | 0 | 1 | 1 |
| STRENGTHEN decisions | 0 | 0 | 0 |
| REMOVE decisions | 0 | 0 | 0 |
| FLAG decisions | 0 | 0 | 0 |
| ACCEPT decisions | 0 | 31 | 31 |
| invalid decisions (fallback) | 0 | 0 | 0 |
| protocol errors | 0 | 0 | 0 |
| parallel tool calls not executed | 0 | 0 | 23 |
| numbers in final passages | 221 | 221 | 221 |
| numbers not derivable from package (rule) | 0 | 0 | 0 |
| PROXY lexical level = gold (UNVALIDATED) | 0.429 | 0.429 | 0.429 |
| PROXY lexical level > gold (UNVALIDATED) | 0.143 | 0.143 | 0.143 |
| PROXY lexical level < gold (UNVALIDATED) | 0.429 | 0.429 | 0.429 |

### diagnostic_long: paired differences (first minus second condition), case-level bootstrap 95% CI [matched-pair bootstrap CI]

| comparison | metric | n | diff | 95% CI | pair-level CI |
|---|---|---|---|---|---|
| H3_C4_vs_C3 | cost_usd | 8 | -0.0007 | [-0.0008, -0.0005] | [-0.0008, -0.0005] |
| H3_C4_vs_C3 | n_tool_calls | 8 | -6.6250 | [-8.0000, -5.2500] | [-8.0000, -5.2500] |
| H3_C4_vs_C3 | n_model_calls | 8 | -6.6250 | [-8.0000, -5.2500] | [-8.0000, -5.2500] |
| H3_C4_vs_C3 | latency_s | 8 | -11.2614 | [-17.1781, -5.2658] | [-17.1781, -5.2658] |
| H3_C4_vs_C3 | changed_from_start | 8 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_correct_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_over_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_under_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | cost_usd | 8 | +0.0020 | [+0.0019, +0.0022] | [+0.0019, +0.0022] |
| verification_C4_vs_C7 | n_tool_calls | 8 | +9.3750 | [+8.0000, +10.7500] | [+8.0000, +10.7500] |
| verification_C4_vs_C7 | n_model_calls | 8 | +13.3750 | [+12.0000, +14.7500] | [+12.0000, +14.7500] |
| verification_C4_vs_C7 | latency_s | 8 | +33.8789 | [+30.2966, +38.0651] | [+30.2966, +38.0651] |
| verification_C4_vs_C7 | changed_from_start | 8 | +0.1250 | [+0.0000, +0.3750] | [+0.0000, +0.3750] |
| verification_C4_vs_C7 | proxy_correct_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | proxy_over_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | proxy_under_UNVALIDATED | 7 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |

### diagnostic_long: verifier tool trajectories

| condition | claims | tools / claim | tools-per-claim distribution | first tool | most common sequences |
|---|---|---|---|---|---|
| C3 | 32 | 4.00 | {'4': 32} | {'lookup_table': 32} | lookup_table > compare_numbers > get_test_metadata > retrieve_passage (32) |
| C4 | 32 | 2.34 | {'2': 19, '3': 6, '4': 4, '1': 3} | {'lookup_table': 31, 'get_test_metadata': 1} | lookup_table > get_test_metadata (18); lookup_table (3); lookup_table > get_test_metadata > compare_numbers (2) |
