### real_papers_v2: per-condition summary

| metric | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| completed runs | 12 | 12 | 11 | 11 |
| failed runs | 0 | 0 | 1 | 1 |
| mean cost / case (USD) | 0.00041 | 0.00115 | 0.00406 | 0.00364 |
| model calls / case | 1.00 | 3.00 | 19.92 | 16.92 |
| evidence-tool calls / case | 0.00 | 0.00 | 14.33 | 11.33 |
| summed call latency / case (s) | 8.2 | 18.6 | 54.7 | 51.4 |
| words in final passage | 151.8 | 162.4 | 159.7 | 156.7 |
| share of passages changed from starting draft | 0.000 | 1.000 | 0.333 | 0.167 |
| WEAKEN decisions | 0 | 0 | 4 | 2 |
| STRENGTHEN decisions | 0 | 0 | 0 | 0 |
| REMOVE decisions | 0 | 0 | 0 | 0 |
| FLAG decisions | 0 | 0 | 0 | 0 |
| ACCEPT decisions | 0 | 0 | 39 | 41 |
| invalid decisions (fallback) | 0 | 0 | 0 | 0 |
| protocol errors | 0 | 0 | 0 | 0 |
| parallel tool calls not executed | 0 | 0 | 0 | 74 |
| numbers in final passages | 193 | 224 | 275 | 275 |
| numbers not derivable from package (rule) | 0 | 0 | 0 | 0 |
| PROXY lexical level = gold (UNVALIDATED) | — | — | — | — |
| PROXY lexical level > gold (UNVALIDATED) | — | — | — | — |
| PROXY lexical level < gold (UNVALIDATED) | — | — | — | — |

### real_papers_v2: paired differences (first minus second condition), case-level bootstrap 95% CI [matched-pair bootstrap CI]

| comparison | metric | n | diff | 95% CI | pair-level CI |
|---|---|---|---|---|---|
| H1_C4_vs_C2 | cost_usd | 11 | +0.0027 | [+0.0024, +0.0030] | [+0.0024, +0.0030] |
| H1_C4_vs_C2 | n_tool_calls | 11 | +12.3636 | [+11.1818, +13.4545] | [+11.1818, +13.4545] |
| H1_C4_vs_C2 | n_model_calls | 11 | +15.2727 | [+14.0909, +16.4545] | [+14.0909, +16.4545] |
| H1_C4_vs_C2 | latency_s | 11 | +35.1744 | [+26.6667, +43.4593] | [+26.6667, +43.4593] |
| H1_C4_vs_C2 | changed_from_start | 11 | -0.8182 | [-1.0000, -0.5455] | [-1.0000, -0.5455] |
| H1_C4_vs_C1 | cost_usd | 11 | +0.0035 | [+0.0032, +0.0037] | [+0.0032, +0.0037] |
| H1_C4_vs_C1 | n_tool_calls | 11 | +12.3636 | [+11.1818, +13.4545] | [+11.1818, +13.4545] |
| H1_C4_vs_C1 | n_model_calls | 11 | +17.2727 | [+16.0909, +18.4545] | [+16.0909, +18.4545] |
| H1_C4_vs_C1 | latency_s | 11 | +45.6630 | [+36.9427, +53.6592] | [+36.9427, +53.6592] |
| H1_C4_vs_C1 | changed_from_start | 11 | +0.1818 | [+0.0000, +0.4545] | [+0.0000, +0.4545] |
| H3_C4_vs_C3 | cost_usd | 11 | -0.0005 | [-0.0006, -0.0003] | [-0.0006, -0.0003] |
| H3_C4_vs_C3 | n_tool_calls | 11 | -3.2727 | [-4.5455, -2.0000] | [-4.5455, -2.0000] |
| H3_C4_vs_C3 | n_model_calls | 11 | -3.2727 | [-4.5455, -2.0000] | [-4.5455, -2.0000] |
| H3_C4_vs_C3 | latency_s | 11 | -3.6207 | [-7.6864, -0.0599] | [-7.6864, -0.0599] |
| H3_C4_vs_C3 | changed_from_start | 11 | -0.1818 | [-0.4545, +0.0000] | [-0.4545, +0.0000] |

### real_papers_v2: verifier tool trajectories

| condition | claims | tools / claim | tools-per-claim distribution | first tool | most common sequences |
|---|---|---|---|---|---|
| C3 | 43 | 4.00 | {'4': 43} | {'lookup_table': 43} | lookup_table > compare_numbers > get_test_metadata > retrieve_passage (43) |
| C4 | 43 | 3.16 | {'2': 14, '3': 8, '4': 21} | {'lookup_table': 39, 'get_test_metadata': 4} | lookup_table > get_test_metadata (12); lookup_table > lookup_table > get_test_metadata (5); lookup_table > compare_numbers > compare_numbers > compare_numbers (4) |
