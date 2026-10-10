### synthetic_test: per-condition summary

| metric | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| completed runs | 32 | 32 | 32 | 32 | 32 | 32 | 32 |
| failed runs | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mean cost / case (USD) | 0.00023 | 0.00068 | 0.00241 | 0.00209 | 0.00191 | 0.00163 | 0.00060 |
| model calls / case | 1.00 | 3.00 | 18.09 | 14.44 | 14.72 | 12.91 | 2.00 |
| evidence-tool calls / case | 0.00 | 0.00 | 12.88 | 9.22 | 9.50 | 8.88 | 0.00 |
| summed call latency / case (s) | 2.0 | 9.2 | 38.7 | 34.7 | 34.6 | 31.1 | 5.5 |
| words in final passage | 86.8 | 97.6 | 89.9 | 90.3 | 89.7 | 88.0 | 89.7 |
| share of passages changed from starting draft | 0.000 | 1.000 | 0.156 | 0.250 | 0.219 | 0.250 | 0.000 |
| WEAKEN decisions | 0 | 0 | 5 | 9 | 7 | 9 | 0 |
| STRENGTHEN decisions | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REMOVE decisions | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| FLAG decisions | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ACCEPT decisions | 0 | 0 | 98 | 94 | 96 | 88 | 0 |
| invalid decisions (fallback) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| protocol errors | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| parallel tool calls not executed | 0 | 0 | 0 | 168 | 164 | 164 | 0 |
| numbers in final passages | 375 | 412 | 457 | 459 | 457 | 380 | 459 |
| numbers not derivable from package (rule) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NUM cases: share of gold numeric values present (rule) | 0.866 | 0.866 | 0.723 | 0.723 | 0.723 | 0.866 | 0.723 |
| PROXY lexical level = gold (UNVALIDATED) | 0.700 | 0.800 | 0.750 | 0.750 | 0.700 | 0.700 | 0.750 |
| PROXY lexical level > gold (UNVALIDATED) | 0.200 | 0.100 | 0.100 | 0.100 | 0.100 | 0.200 | 0.100 |
| PROXY lexical level < gold (UNVALIDATED) | 0.100 | 0.100 | 0.150 | 0.150 | 0.200 | 0.100 | 0.150 |
| PROXY NEG-finding mention rate (UNVALIDATED) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

### synthetic_test: paired differences (first minus second condition), case-level bootstrap 95% CI [matched-pair bootstrap CI]

| comparison | metric | n | diff | 95% CI | pair-level CI |
|---|---|---|---|---|---|
| H1_C4_vs_C2 | cost_usd | 32 | +0.0014 | [+0.0013, +0.0015] | [+0.0013, +0.0016] |
| H1_C4_vs_C2 | n_tool_calls | 32 | +9.2188 | [+8.4688, +10.0000] | [+8.3750, +10.1562] |
| H1_C4_vs_C2 | n_model_calls | 32 | +11.4375 | [+10.5625, +12.3438] | [+10.4375, +12.5000] |
| H1_C4_vs_C2 | latency_s | 32 | +25.5029 | [+22.5151, +28.6774] | [+22.1385, +29.5533] |
| H1_C4_vs_C2 | changed_from_start | 32 | -0.7500 | [-0.9062, -0.5938] | [-0.9062, -0.5938] |
| H1_C4_vs_C2 | num_value_recall | 4 | -0.1429 | [-0.2857, +0.0000] | [-0.2857, +0.0000] |
| H1_C4_vs_C2 | proxy_correct_UNVALIDATED | 20 | -0.0500 | [-0.2500, +0.1500] | [-0.2500, +0.1500] |
| H1_C4_vs_C2 | proxy_over_UNVALIDATED | 20 | +0.0000 | [-0.1500, +0.1500] | [-0.1500, +0.1500] |
| H1_C4_vs_C2 | proxy_under_UNVALIDATED | 20 | +0.0500 | [-0.1000, +0.2000] | [-0.1000, +0.2000] |
| H1_C4_vs_C1 | cost_usd | 32 | +0.0019 | [+0.0017, +0.0020] | [+0.0017, +0.0020] |
| H1_C4_vs_C1 | n_tool_calls | 32 | +9.2188 | [+8.4688, +10.0000] | [+8.3750, +10.1562] |
| H1_C4_vs_C1 | n_model_calls | 32 | +13.4375 | [+12.5625, +14.3438] | [+12.4375, +14.5000] |
| H1_C4_vs_C1 | latency_s | 32 | +32.6877 | [+29.6163, +35.8923] | [+29.2172, +36.6617] |
| H1_C4_vs_C1 | changed_from_start | 32 | +0.2500 | [+0.0938, +0.4062] | [+0.0938, +0.4062] |
| H1_C4_vs_C1 | num_value_recall | 4 | -0.1429 | [-0.2857, +0.0000] | [-0.2857, +0.0000] |
| H1_C4_vs_C1 | proxy_correct_UNVALIDATED | 20 | +0.0500 | [-0.2000, +0.3000] | [-0.2000, +0.3500] |
| H1_C4_vs_C1 | proxy_over_UNVALIDATED | 20 | -0.1000 | [-0.3000, +0.1000] | [-0.3000, +0.1000] |
| H1_C4_vs_C1 | proxy_under_UNVALIDATED | 20 | +0.0500 | [-0.1000, +0.2000] | [-0.1000, +0.2000] |
| C6_vs_C2_same_draft | cost_usd | 32 | +0.0010 | [+0.0009, +0.0011] | [+0.0009, +0.0011] |
| C6_vs_C2_same_draft | n_tool_calls | 32 | +8.8750 | [+8.2812, +9.5312] | [+8.2812, +9.4375] |
| C6_vs_C2_same_draft | n_model_calls | 32 | +9.9062 | [+9.2812, +10.6250] | [+9.3125, +10.5000] |
| C6_vs_C2_same_draft | latency_s | 32 | +21.8527 | [+19.5812, +24.2066] | [+19.6040, +24.0731] |
| C6_vs_C2_same_draft | changed_from_start | 32 | -0.7500 | [-0.9062, -0.5938] | [-0.8750, -0.5938] |
| C6_vs_C2_same_draft | num_value_recall | 4 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| C6_vs_C2_same_draft | proxy_correct_UNVALIDATED | 20 | -0.1000 | [-0.3000, +0.1000] | [-0.3000, +0.1000] |
| C6_vs_C2_same_draft | proxy_over_UNVALIDATED | 20 | +0.1000 | [+0.0000, +0.2500] | [+0.0000, +0.2500] |
| C6_vs_C2_same_draft | proxy_under_UNVALIDATED | 20 | +0.0000 | [-0.1500, +0.1500] | [-0.1500, +0.1500] |
| H2_C4_vs_C5 | cost_usd | 32 | +0.0002 | [+0.0001, +0.0002] | [+0.0001, +0.0002] |
| H2_C4_vs_C5 | n_tool_calls | 32 | -0.2812 | [-0.6562, +0.0625] | [-0.5938, +0.0000] |
| H2_C4_vs_C5 | n_model_calls | 32 | -0.2812 | [-0.6562, +0.0625] | [-0.5938, +0.0000] |
| H2_C4_vs_C5 | latency_s | 32 | +0.1150 | [-1.7209, +1.9573] | [-1.9373, +2.0298] |
| H2_C4_vs_C5 | changed_from_start | 32 | +0.0312 | [-0.0625, +0.1562] | [-0.0625, +0.1250] |
| H2_C4_vs_C5 | num_value_recall | 4 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H2_C4_vs_C5 | proxy_correct_UNVALIDATED | 20 | +0.0500 | [+0.0000, +0.1500] | [+0.0000, +0.1500] |
| H2_C4_vs_C5 | proxy_over_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H2_C4_vs_C5 | proxy_under_UNVALIDATED | 20 | -0.0500 | [-0.1500, +0.0000] | [-0.1500, +0.0000] |
| H3_C4_vs_C3 | cost_usd | 32 | -0.0003 | [-0.0004, -0.0003] | [-0.0004, -0.0003] |
| H3_C4_vs_C3 | n_tool_calls | 32 | -3.6562 | [-4.1875, -3.1562] | [-4.1875, -3.0938] |
| H3_C4_vs_C3 | n_model_calls | 32 | -3.6562 | [-4.1875, -3.1562] | [-4.1875, -3.0938] |
| H3_C4_vs_C3 | latency_s | 32 | -3.9635 | [-6.1782, -1.5598] | [-6.2953, -1.3288] |
| H3_C4_vs_C3 | changed_from_start | 32 | +0.0938 | [+0.0000, +0.2188] | [+0.0000, +0.1875] |
| H3_C4_vs_C3 | num_value_recall | 4 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_correct_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_over_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| H3_C4_vs_C3 | proxy_under_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | cost_usd | 32 | +0.0015 | [+0.0014, +0.0016] | [+0.0013, +0.0016] |
| verification_C4_vs_C7 | n_tool_calls | 32 | +9.2188 | [+8.4688, +10.0000] | [+8.3750, +10.1562] |
| verification_C4_vs_C7 | n_model_calls | 32 | +12.4375 | [+11.5625, +13.3438] | [+11.4375, +13.5000] |
| verification_C4_vs_C7 | latency_s | 32 | +29.2498 | [+26.4452, +32.1180] | [+26.1392, +32.8270] |
| verification_C4_vs_C7 | changed_from_start | 32 | +0.2500 | [+0.0938, +0.4062] | [+0.0938, +0.4062] |
| verification_C4_vs_C7 | num_value_recall | 4 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | proxy_correct_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | proxy_over_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| verification_C4_vs_C7 | proxy_under_UNVALIDATED | 20 | +0.0000 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| outline_C4_vs_C6 | cost_usd | 32 | +0.0005 | [+0.0003, +0.0006] | [+0.0003, +0.0006] |
| outline_C4_vs_C6 | n_tool_calls | 32 | +0.3438 | [-0.5312, +1.1875] | [-0.5625, +1.2188] |
| outline_C4_vs_C6 | n_model_calls | 32 | +1.5312 | [+0.5312, +2.5312] | [+0.5000, +2.5312] |
| outline_C4_vs_C6 | latency_s | 32 | +3.6502 | [+0.2861, +7.0676] | [+0.0715, +7.4976] |
| outline_C4_vs_C6 | changed_from_start | 32 | +0.0000 | [-0.1875, +0.1875] | [-0.1562, +0.1562] |
| outline_C4_vs_C6 | num_value_recall | 4 | -0.1429 | [-0.2857, +0.0000] | [-0.2857, +0.0000] |
| outline_C4_vs_C6 | proxy_correct_UNVALIDATED | 20 | +0.0500 | [-0.2000, +0.3000] | [-0.2000, +0.3500] |
| outline_C4_vs_C6 | proxy_over_UNVALIDATED | 20 | -0.1000 | [-0.3000, +0.1000] | [-0.3000, +0.1000] |
| outline_C4_vs_C6 | proxy_under_UNVALIDATED | 20 | +0.0500 | [-0.1000, +0.2000] | [-0.1000, +0.2000] |

### synthetic_test: verifier tool trajectories

| condition | claims | tools / claim | tools-per-claim distribution | first tool | most common sequences |
|---|---|---|---|---|---|
| C3 | 103 | 4.00 | {'4': 103} | {'lookup_table': 103} | lookup_table > compare_numbers > get_test_metadata > retrieve_passage (103) |
| C4 | 103 | 2.86 | {'4': 31, '2': 43, '1': 1, '3': 28} | {'lookup_table': 91, 'get_test_metadata': 12} | lookup_table > get_test_metadata (31); lookup_table > compare_numbers > compare_numbers > compare_numbers (23); get_test_metadata > get_test_metadata (10) |
| C5 | 103 | 2.95 | {'4': 35, '3': 29, '1': 1, '2': 38} | {'lookup_table': 91, 'get_test_metadata': 12} | lookup_table > get_test_metadata (27); lookup_table > compare_numbers > compare_numbers > compare_numbers (26); lookup_table > get_test_metadata > get_test_metadata (11) |
| C6 | 97 | 2.93 | {'4': 32, '2': 39, '3': 26} | {'lookup_table': 82, 'get_test_metadata': 13, 'retrieve_passage': 2} | lookup_table > get_test_metadata (24); lookup_table > compare_numbers > compare_numbers > compare_numbers (22); lookup_table > get_test_metadata > get_test_metadata (11) |
