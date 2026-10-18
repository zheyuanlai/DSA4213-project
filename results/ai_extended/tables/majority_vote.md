# Third judge (Qwen 3.7 Plus) and 2-of-3 majority

Judge C = qwen/qwen3.7-plus via OpenRouter (Alibaba; temperature 0, seed 4213, reasoning off), same verification prompt as Judges A (GPT-5.6) and B (Claude). Majority = 2 of 3 AI judges, no adjudicator; numbers checked by code. AI-only, exploratory.

## Agreement before adjudication (representative claims)

| Set | Field | A–B | A–C | B–C | Fleiss κ (A,B,C) | all three agree |
|---|---|---|---|---|---|---|
| synthetic | label | 0.941 (κ 0.562) | 0.945 (κ 0.652) | 0.910 (κ 0.341) | 0.524 | 0.899 |
| synthetic | entailment | 0.943 (κ 0.571) | 0.948 (κ 0.647) | 0.920 (κ 0.362) | 0.533 | 0.906 |
| synthetic | numeric verdict | 0.825 | 0.940 | 0.818 | — | C unusable mappings: 62 |
| real | label | 0.918 (κ 0.653) | 0.873 (κ 0.305) | 0.873 (κ 0.240) | 0.424 | 0.840 |
| real | entailment | 0.933 (κ 0.689) | 0.875 (κ 0.246) | 0.885 (κ 0.211) | 0.414 | 0.847 |
| real | numeric verdict | 0.971 | 0.956 | 0.948 | — | C unusable mappings: 19 |
| diagnostic | label | 0.970 (κ -0.015) | 0.985 (κ 0.000) | 0.985 (κ 0.000) | -0.010 | 0.970 |
| diagnostic | entailment | 0.970 (κ -0.011) | 0.985 (κ 0.000) | 0.985 (κ 0.000) | -0.008 | 0.970 |
| diagnostic | numeric verdict | 1.000 | 0.960 | 0.960 | — | C unusable mappings: 9 |

## Does the independent third judge agree with the adjudicator?

| Set | Field | Adjudicated items | Judge C agrees | By adjudicator side (sided_A / sided_B / neither) |
|---|---|---|---|---|
| synthetic | label | 42 | 12 | sided_A/C_agrees 11, sided_A/C_differs 7, sided_B/C_agrees 1, sided_B/C_differs 23 |
| synthetic | entailment | 42 | 14 | sided_A/C_agrees 10, sided_A/C_differs 7, sided_B/C_agrees 4, sided_B/C_differs 21 |
| real | label | 40 | 6 | sided_A/C_agrees 4, sided_A/C_differs 21, sided_B/C_agrees 2, sided_B/C_differs 13 |
| real | entailment | 34 | 11 | neither/C_differs 1, sided_A/C_agrees 5, sided_A/C_differs 15, sided_B/C_agrees 6, sided_B/C_differs 7 |
| diagnostic | label | 4 | 2 | sided_A/C_agrees 2, sided_A/C_differs 2 |
| diagnostic | entailment | 4 | 2 | sided_A/C_agrees 2, sided_A/C_differs 2 |

## Headline rates: primary (adjudicated) vs 2-of-3 majority vs Judge C alone

| Set | Condition | Support (prim / maj / C) | Factual error (prim / maj / C) | Fully supported (prim / maj / C) |
|---|---|---|---|---|
| synthetic | C1 | 0.926 / 0.897 / 0.859 | 0.074 / 0.099 / 0.129 | 0.656 / 0.562 / 0.469 |
| synthetic | C2 | 0.943 / 0.956 / 0.932 | 0.057 / 0.041 / 0.065 | 0.594 / 0.688 / 0.594 |
| synthetic | C3 | 0.963 / 0.944 / 0.907 | 0.037 / 0.048 / 0.078 | 0.781 / 0.719 / 0.562 |
| synthetic | C4 | 0.970 / 0.952 / 0.918 | 0.030 / 0.041 / 0.067 | 0.812 / 0.750 / 0.656 |
| synthetic | C5 | 0.970 / 0.952 / 0.922 | 0.030 / 0.041 / 0.070 | 0.812 / 0.781 / 0.656 |
| synthetic | C6 | 0.951 / 0.931 / 0.889 | 0.049 / 0.065 / 0.099 | 0.750 / 0.688 / 0.562 |
| synthetic | C7 | 0.948 / 0.926 / 0.888 | 0.052 / 0.067 / 0.097 | 0.719 / 0.625 / 0.500 |
| real | C1 | 0.894 / 0.923 / 0.957 | 0.096 / 0.072 / 0.038 | 0.250 / 0.250 / 0.417 |
| real | C2 | 0.885 / 0.910 / 0.930 | 0.100 / 0.080 / 0.070 | 0.250 / 0.333 / 0.333 |
| real | C3 | 0.873 / 0.902 / 0.931 | 0.122 / 0.078 / 0.050 | 0.091 / 0.364 / 0.455 |
| real | DRAFT | 0.856 / 0.886 / 0.930 | 0.134 / 0.089 / 0.050 | 0.091 / 0.364 / 0.455 |
| real | C4 | 0.874 / 0.905 / 0.929 | 0.116 / 0.070 / 0.051 | 0.091 / 0.364 / 0.455 |
| diagnostic | C7 | 0.968 / 0.984 / 0.960 | 0.032 / 0.016 / 0.040 | 0.625 / 0.875 / 0.625 |
| diagnostic | C3 | 0.968 / 0.984 / 0.960 | 0.032 / 0.016 / 0.040 | 0.625 / 0.875 / 0.625 |
| diagnostic | C4 | 0.968 / 0.984 / 0.960 | 0.032 / 0.016 / 0.040 | 0.625 / 0.875 / 0.625 |

## Planned contrasts: primary vs majority vs Judge C alone (non-degenerate rows)

| Set | Contrast | Metric | Primary | 2-of-3 majority | majority, no fallback | Judge C alone |
|---|---|---|---|---|---|---|
| synthetic | C4 − C2 | support_rate | +0.027 [-0.009, +0.063] | -0.004 [-0.048, +0.036] | -0.004 [-0.048, +0.036] | -0.014 [-0.064, +0.032] |
| synthetic | C4 − C2 | factual_error_rate | -0.027 [-0.063, +0.009] | +0.000 [-0.037, +0.041] | +0.000 [-0.037, +0.041] | +0.002 [-0.042, +0.051] |
| synthetic | C4 − C2 | fully_supported | +0.219 [+0.000, +0.438] | +0.062 [-0.156, +0.281] | +0.062 [-0.156, +0.281] | +0.062 [-0.125, +0.250] |
| synthetic | C4 − C2 | numeric_precision | +0.010 [-0.008, +0.032] | +0.008 [-0.009, +0.027] | +0.008 [-0.009, +0.027] | +0.007 [-0.014, +0.028] |
| synthetic | C4 − C2 | numeric_recall | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] |
| synthetic | C4 − C1 | support_rate | +0.044 [-0.001, +0.093] | +0.055 [+0.013, +0.097] | +0.055 [+0.013, +0.097] | +0.059 [+0.011, +0.108] |
| synthetic | C4 − C1 | factual_error_rate | -0.044 [-0.093, +0.001] | -0.058 [-0.100, -0.015] | -0.058 [-0.100, -0.016] | -0.062 [-0.110, -0.012] |
| synthetic | C4 − C1 | fully_supported | +0.156 [-0.031, +0.344] | +0.188 [-0.031, +0.375] | +0.188 [-0.031, +0.375] | +0.188 [+0.031, +0.344] |
| synthetic | C4 − C1 | numeric_precision | +0.011 [-0.009, +0.040] | +0.007 [-0.009, +0.025] | +0.007 [-0.009, +0.025] | +0.007 [-0.013, +0.028] |
| synthetic | C4 − C1 | numeric_recall | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] |
| synthetic | C4 − C3 | support_rate | +0.007 [-0.000, +0.019] | +0.007 [-0.000, +0.019] | +0.007 [-0.000, +0.019] | +0.011 [+0.000, +0.025] |
| synthetic | C4 − C3 | factual_error_rate | -0.007 [-0.019, +0.000] | -0.007 [-0.019, +0.000] | -0.007 [-0.019, +0.000] | -0.011 [-0.025, +0.000] |
| synthetic | C4 − C3 | fully_supported | +0.031 [+0.000, +0.094] | +0.031 [+0.000, +0.094] | +0.031 [+0.000, +0.094] | +0.094 [+0.000, +0.219] |
| synthetic | C4 − C3 | numeric_precision | +0.002 [-0.005, +0.010] | +0.002 [-0.005, +0.010] | +0.002 [-0.005, +0.010] | +0.002 [-0.005, +0.010] |
| synthetic | C4 − C5 | support_rate | -0.000 [-0.011, +0.011] | -0.000 [-0.011, +0.011] | -0.000 [-0.011, +0.011] | -0.004 [-0.026, +0.015] |
| synthetic | C4 − C5 | factual_error_rate | +0.000 [-0.011, +0.011] | +0.000 [-0.011, +0.011] | +0.000 [-0.011, +0.011] | -0.003 [-0.017, +0.008] |
| synthetic | C4 − C5 | fully_supported | +0.000 [+0.000, +0.000] | -0.031 [-0.094, +0.000] | -0.031 [-0.094, +0.000] | +0.000 [-0.125, +0.125] |
| synthetic | C4 − C5 | numeric_precision | +0.000 [-0.006, +0.006] | +0.000 [-0.006, +0.006] | +0.000 [-0.006, +0.007] | +0.000 [-0.006, +0.007] |
| synthetic | C4 − C7 | support_rate | +0.022 [+0.004, +0.050] | +0.026 [+0.004, +0.054] | +0.026 [+0.004, +0.054] | +0.030 [+0.008, +0.059] |
| synthetic | C4 − C7 | factual_error_rate | -0.022 [-0.050, -0.004] | -0.026 [-0.054, -0.004] | -0.026 [-0.054, -0.004] | -0.030 [-0.059, -0.008] |
| synthetic | C4 − C7 | fully_supported | +0.094 [+0.000, +0.188] | +0.125 [+0.031, +0.250] | +0.125 [+0.031, +0.250] | +0.156 [+0.031, +0.281] |
| synthetic | C4 − C7 | numeric_precision | +0.008 [-0.000, +0.020] | +0.004 [-0.000, +0.010] | +0.004 [-0.000, +0.011] | +0.004 [-0.000, +0.011] |
| synthetic | C3 − C7 | support_rate | +0.015 [+0.000, +0.042] | +0.019 [+0.000, +0.047] | +0.019 [+0.000, +0.047] | +0.019 [+0.000, +0.047] |
| synthetic | C3 − C7 | factual_error_rate | -0.015 [-0.042, +0.000] | -0.019 [-0.047, +0.000] | -0.019 [-0.047, +0.000] | -0.019 [-0.047, +0.000] |
| synthetic | C3 − C7 | fully_supported | +0.062 [+0.000, +0.156] | +0.094 [+0.000, +0.219] | +0.094 [+0.000, +0.219] | +0.062 [+0.000, +0.156] |
| synthetic | C3 − C7 | numeric_precision | +0.006 [-0.000, +0.018] | +0.002 [-0.000, +0.007] | +0.002 [-0.000, +0.007] | +0.002 [-0.000, +0.007] |
| synthetic | C5 − C7 | support_rate | +0.022 [+0.004, +0.051] | +0.026 [+0.005, +0.055] | +0.026 [+0.005, +0.055] | +0.034 [+0.010, +0.066] |
| synthetic | C5 − C7 | factual_error_rate | -0.022 [-0.051, -0.004] | -0.026 [-0.055, -0.005] | -0.026 [-0.055, -0.005] | -0.026 [-0.055, -0.005] |
| synthetic | C5 − C7 | fully_supported | +0.094 [+0.000, +0.188] | +0.156 [+0.031, +0.281] | +0.156 [+0.031, +0.281] | +0.156 [+0.031, +0.281] |
| synthetic | C5 − C7 | numeric_precision | +0.008 [-0.000, +0.020] | +0.004 [-0.000, +0.010] | +0.004 [-0.000, +0.010] | +0.004 [-0.000, +0.010] |
| synthetic | C2 − C1 | support_rate | +0.017 [-0.023, +0.062] | +0.059 [+0.016, +0.110] | +0.059 [+0.017, +0.111] | +0.073 [+0.030, +0.128] |
| synthetic | C2 − C1 | factual_error_rate | -0.017 [-0.062, +0.023] | -0.058 [-0.108, -0.019] | -0.059 [-0.109, -0.019] | -0.064 [-0.117, -0.023] |
| synthetic | C2 − C1 | fully_supported | -0.062 [-0.281, +0.156] | +0.125 [-0.062, +0.312] | +0.125 [-0.062, +0.312] | +0.125 [+0.000, +0.281] |
| synthetic | C2 − C1 | numeric_precision | +0.002 [-0.008, +0.013] | -0.001 [-0.009, +0.007] | -0.001 [-0.009, +0.007] | +0.000 [-0.008, +0.009] |
| synthetic | C2 − C1 | numeric_recall | +0.000 [-0.047, +0.049] | +0.000 [-0.047, +0.049] | +0.000 [-0.047, +0.049] | +0.000 [-0.047, +0.049] |
| synthetic | C6 − C1 | support_rate | +0.025 [+0.005, +0.049] | +0.034 [+0.013, +0.059] | +0.034 [+0.013, +0.059] | +0.030 [+0.009, +0.055] |
| synthetic | C6 − C1 | factual_error_rate | -0.025 [-0.049, -0.005] | -0.034 [-0.059, -0.013] | -0.034 [-0.059, -0.013] | -0.030 [-0.055, -0.009] |
| synthetic | C6 − C1 | fully_supported | +0.094 [+0.000, +0.219] | +0.125 [+0.031, +0.250] | +0.125 [+0.031, +0.250] | +0.094 [+0.000, +0.219] |
| synthetic | C6 − C1 | numeric_precision | +0.015 [+0.000, +0.042] | +0.010 [+0.000, +0.025] | +0.010 [+0.000, +0.025] | +0.010 [+0.000, +0.026] |
| synthetic | **all 45 contrasts, majority** | | sign changes 5 | zero-exclusion changes 7 | max shift 0.188 | |
| synthetic | **all 45 contrasts, majority_strict** | | sign changes 5 | zero-exclusion changes 7 | max shift 0.188 | |
| synthetic | **all 45 contrasts, judge_C_only** | | sign changes 4 | zero-exclusion changes 7 | max shift 0.188 | |
| real | C4 − C2 | support_rate | +0.005 [-0.068, +0.086] | +0.007 [-0.077, +0.100] | -0.004 [-0.073, +0.069] | +0.008 [-0.028, +0.044] |
| real | C4 − C2 | factual_error_rate | +0.002 [-0.074, +0.066] | -0.021 [-0.099, +0.050] | -0.009 [-0.062, +0.042] | -0.029 [-0.054, -0.007] |
| real | C4 − C2 | fully_supported | -0.091 [-0.273, +0.000] | +0.091 [-0.182, +0.364] | +0.091 [-0.182, +0.364] | +0.182 [+0.000, +0.455] |
| real | C4 − C2 | numeric_precision | -0.012 [-0.048, +0.019] | +0.002 [-0.015, +0.024] | +0.002 [-0.015, +0.024] | +0.007 [-0.019, +0.038] |
| real | C4 − C2 | numeric_recall | -0.035 [-0.102, +0.025] | -0.035 [-0.102, +0.025] | -0.035 [-0.102, +0.025] | -0.035 [-0.110, +0.035] |
| real | C4 − C1 | support_rate | -0.023 [-0.079, +0.044] | -0.014 [-0.082, +0.065] | -0.025 [-0.083, +0.049] | -0.023 [-0.078, +0.037] |
| real | C4 − C1 | factual_error_rate | +0.018 [-0.046, +0.068] | -0.011 [-0.074, +0.039] | -0.000 [-0.058, +0.042] | +0.008 [-0.039, +0.051] |
| real | C4 − C1 | fully_supported | -0.182 [-0.455, +0.000] | +0.091 [-0.273, +0.455] | +0.000 [-0.364, +0.364] | +0.091 [-0.182, +0.364] |
| real | C4 − C1 | numeric_precision | -0.005 [-0.031, +0.022] | +0.009 [-0.011, +0.036] | +0.009 [-0.011, +0.036] | +0.004 [-0.018, +0.027] |
| real | C4 − C1 | numeric_recall | -0.012 [-0.073, +0.047] | -0.012 [-0.073, +0.047] | -0.012 [-0.073, +0.047] | -0.024 [-0.082, +0.024] |
| real | C4 − C3 | support_rate | +0.001 [-0.030, +0.038] | +0.002 [-0.029, +0.040] | +0.002 [-0.030, +0.040] | -0.002 [-0.004, -0.000] |
| real | C4 − C3 | factual_error_rate | -0.006 [-0.039, +0.016] | -0.008 [-0.041, +0.015] | -0.008 [-0.041, +0.015] | +0.002 [+0.000, +0.004] |
| real | C2 − C1 | support_rate | -0.009 [-0.060, +0.048] | -0.013 [-0.063, +0.034] | -0.013 [-0.057, +0.029] | -0.027 [-0.071, +0.012] |
| real | C2 − C1 | factual_error_rate | +0.004 [-0.045, +0.050] | +0.008 [-0.037, +0.052] | +0.007 [-0.031, +0.042] | +0.032 [-0.004, +0.075] |
| real | C2 − C1 | fully_supported | +0.000 [-0.333, +0.333] | +0.083 [-0.250, +0.417] | +0.000 [-0.333, +0.333] | -0.083 [-0.250, +0.000] |
| real | C2 − C1 | numeric_precision | +0.006 [-0.009, +0.025] | +0.006 [-0.009, +0.025] | +0.006 [-0.009, +0.025] | -0.003 [-0.025, +0.015] |
| real | C2 − C1 | numeric_recall | +0.022 [-0.022, +0.075] | +0.022 [-0.022, +0.075] | +0.022 [-0.022, +0.075] | +0.011 [-0.031, +0.065] |
| real | C3 − DRAFT | support_rate | +0.017 [+0.001, +0.038] | +0.016 [+0.000, +0.038] | +0.016 [+0.000, +0.038] | +0.001 [+0.000, +0.002] |
| real | C3 − DRAFT | factual_error_rate | -0.012 [-0.025, -0.001] | -0.011 [-0.025, -0.000] | -0.011 [-0.025, -0.000] | -0.001 [-0.002, +0.000] |
| real | C4 − DRAFT | support_rate | +0.018 [+0.000, +0.057] | +0.018 [+0.000, +0.058] | +0.019 [+0.000, +0.058] | -0.001 [-0.003, +0.000] |
| real | C4 − DRAFT | factual_error_rate | -0.018 [-0.057, +0.000] | -0.019 [-0.059, +0.000] | -0.019 [-0.059, +0.000] | +0.001 [+0.000, +0.003] |
| real | **all 30 contrasts, majority** | | sign changes 7 | zero-exclusion changes 0 | max shift 0.273 | |
| real | **all 30 contrasts, majority_strict** | | sign changes 7 | zero-exclusion changes 0 | max shift 0.182 | |
| real | **all 30 contrasts, judge_C_only** | | sign changes 11 | zero-exclusion changes 5 | max shift 0.273 | |
| diagnostic | C3 − C7 | support_rate | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | -0.000 [-0.002, +0.000] |
| diagnostic | C3 − C7 | factual_error_rate | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.002] |
| diagnostic | C4 − C3 | support_rate | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.002] |
| diagnostic | C4 − C3 | factual_error_rate | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | -0.000 [-0.002, +0.000] |
| diagnostic | **all 15 contrasts, majority** | | sign changes 0 | zero-exclusion changes 0 | max shift 0.000 | |
| diagnostic | **all 15 contrasts, majority_strict** | | sign changes 0 | zero-exclusion changes 0 | max shift 0.000 | |
| diagnostic | **all 15 contrasts, judge_C_only** | | sign changes 0 | zero-exclusion changes 0 | max shift 0.000 | |

Items without a 2-of-3 majority keep the adjudicated decision in the main majority column and are excluded in the no-fallback column: synthetic: 1 labels, 40 numbers; real: 9 labels, 23 numbers; diagnostic: 0 labels, 1 numbers
