# Adjudicator test–retest (replicate r1)

Primary vs replicate adjudication by the same AI adjudicator (GPT-5.6 via Codex CLI) on verbatim identical prompts; AI-AI test-retest, not human reliability. Exploratory.

## Agreement between the two adjudications of the same disputed items

| Set | Field | Items | Same decision | Raw agreement | Cohen's κ | Changed decisions |
|---|---|---|---|---|---|---|
| synthetic | claim label | 42 | 34 | 0.810 | 0.651 | OVERSTATED->SUPPORTED ×7, SUPPORTED->OVERSTATED ×1 |
| synthetic | entailment | 42 | 34 | 0.810 | 0.619 | NOT_ENTAILED->ENTAILED ×7, ENTAILED->NOT_ENTAILED ×1 |
| synthetic | number mapping (judge A / B / own) | 231 | 230 | 0.996 | 0.955 | A->own ×1 |
| synthetic | alignment relation | 43 | 35 | 0.814 | 0.667 | MODIFIED->REWORDED ×5, REWORDED->MODIFIED ×3 |
| real | claim label | 40 | 36 | 0.900 | 0.863 | OVERSTATED->SUPPORTED ×2, UNSUPPORTED->OVERSTATED ×1, SUPPORTED->OVERSTATED ×1 |
| real | entailment | 34 | 30 | 0.882 | 0.820 | NOT_ENTAILED->ENTAILED ×2, ENTAILED->NOT_ENTAILED ×1, CONTRADICTED->NOT_ENTAILED ×1 |
| real | extraction validity | 1 | 1 | 1.000 | 1.000 | — |
| real | number mapping (judge A / B / own) | 39 | 39 | 1.000 | 1.000 | — |
| real | finding coverage | 77 | 53 | 0.688 | 0.519 | ABSENT->INCORRECT ×11, CORRECT->ABSENT ×10, INCORRECT->CORRECT ×1, ABSENT->CORRECT ×1, INCORRECT->ABSENT ×1 |
| real | alignment relation | 41 | 40 | 0.976 | 0.957 | UNCHANGED->REWORDED ×1 |
| diagnostic | claim label | 4 | 4 | 1.000 | 1.000 | — |
| diagnostic | entailment | 4 | 4 | 1.000 | 1.000 | — |
| diagnostic | number mapping (judge A / B / own) | 1 | 1 | 1.000 | 1.000 | — |
| diagnostic | finding coverage | 5 | 4 | 0.800 | 0.688 | CORRECT->INCORRECT ×1 |

## Effect on the final consensus

| Set | Claims | Final labels changed | Factual-error flags changed | Numeric verdicts changed | Coverage items changed |
|---|---|---|---|---|---|
| synthetic | 844 | 8 | 8 | 1 | — |
| real | 612 | 5 | 4 | 1 | 24 of 291 |
| diagnostic | 135 | 0 | 0 | 0 | 1 of 84 |

## Planned contrasts re-scored from the replicate consensus

| Set | Contrast | Metric | Primary | Replicate | Sign kept | Zero-exclusion kept |
|---|---|---|---|---|---|---|
| synthetic | C4 − C2 | support_rate | +0.027 [-0.009, +0.063] | +0.024 [-0.006, +0.052] | yes | yes |
| synthetic | C4 − C2 | factual_error_rate | -0.027 [-0.063, +0.009] | -0.024 [-0.052, +0.006] | yes | yes |
| synthetic | C4 − C2 | fully_supported | +0.219 [+0.000, +0.438] | +0.250 [+0.062, +0.438] | yes | no |
| synthetic | C4 − C2 | numeric_precision | +0.010 [-0.008, +0.032] | +0.010 [-0.008, +0.033] | yes | yes |
| synthetic | C4 − C2 | numeric_recall | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | yes | yes |
| synthetic | C4 − C1 | support_rate | +0.044 [-0.001, +0.093] | +0.044 [-0.000, +0.091] | yes | yes |
| synthetic | C4 − C1 | factual_error_rate | -0.044 [-0.093, +0.001] | -0.044 [-0.091, +0.000] | yes | yes |
| synthetic | C4 − C1 | fully_supported | +0.156 [-0.031, +0.344] | +0.188 [-0.031, +0.375] | yes | yes |
| synthetic | C4 − C1 | numeric_precision | +0.011 [-0.009, +0.040] | +0.011 [-0.009, +0.040] | yes | yes |
| synthetic | C4 − C1 | numeric_recall | -0.109 [-0.185, -0.033] | -0.109 [-0.185, -0.033] | yes | yes |
| synthetic | C4 − C3 | support_rate | +0.007 [-0.000, +0.019] | +0.007 [-0.000, +0.019] | yes | yes |
| synthetic | C4 − C3 | factual_error_rate | -0.007 [-0.019, +0.000] | -0.007 [-0.019, +0.000] | yes | yes |
| synthetic | C4 − C3 | fully_supported | +0.031 [+0.000, +0.094] | +0.031 [+0.000, +0.094] | yes | yes |
| synthetic | C4 − C3 | numeric_precision | +0.002 [-0.005, +0.010] | +0.002 [-0.005, +0.010] | yes | yes |
| synthetic | C4 − C5 | support_rate | -0.000 [-0.011, +0.011] | -0.000 [-0.011, +0.011] | yes | yes |
| synthetic | C4 − C5 | factual_error_rate | +0.000 [-0.011, +0.011] | +0.000 [-0.011, +0.011] | yes | yes |
| synthetic | C4 − C5 | numeric_precision | +0.000 [-0.006, +0.006] | +0.000 [-0.006, +0.006] | yes | yes |
| synthetic | C4 − C7 | support_rate | +0.022 [+0.004, +0.050] | +0.015 [+0.004, +0.030] | yes | yes |
| synthetic | C4 − C7 | factual_error_rate | -0.022 [-0.050, -0.004] | -0.015 [-0.030, -0.004] | yes | yes |
| synthetic | C4 − C7 | fully_supported | +0.094 [+0.000, +0.188] | +0.094 [+0.000, +0.188] | yes | yes |
| synthetic | C4 − C7 | numeric_precision | +0.008 [-0.000, +0.020] | +0.008 [-0.000, +0.020] | yes | yes |
| synthetic | C3 − C7 | support_rate | +0.015 [+0.000, +0.042] | +0.007 [+0.000, +0.019] | yes | yes |
| synthetic | C3 − C7 | factual_error_rate | -0.015 [-0.042, +0.000] | -0.007 [-0.019, +0.000] | yes | yes |
| synthetic | C3 − C7 | fully_supported | +0.062 [+0.000, +0.156] | +0.062 [+0.000, +0.156] | yes | yes |
| synthetic | C3 − C7 | numeric_precision | +0.006 [-0.000, +0.018] | +0.006 [-0.000, +0.018] | yes | yes |
| synthetic | C5 − C7 | support_rate | +0.022 [+0.004, +0.051] | +0.015 [+0.004, +0.030] | yes | yes |
| synthetic | C5 − C7 | factual_error_rate | -0.022 [-0.051, -0.004] | -0.015 [-0.030, -0.004] | yes | yes |
| synthetic | C5 − C7 | fully_supported | +0.094 [+0.000, +0.188] | +0.094 [+0.000, +0.188] | yes | yes |
| synthetic | C5 − C7 | numeric_precision | +0.008 [-0.000, +0.020] | +0.008 [-0.000, +0.020] | yes | yes |
| synthetic | C2 − C1 | support_rate | +0.017 [-0.023, +0.062] | +0.019 [-0.020, +0.065] | yes | yes |
| synthetic | C2 − C1 | factual_error_rate | -0.017 [-0.062, +0.023] | -0.019 [-0.065, +0.020] | yes | yes |
| synthetic | C2 − C1 | fully_supported | -0.062 [-0.281, +0.156] | -0.062 [-0.281, +0.156] | yes | yes |
| synthetic | C2 − C1 | numeric_precision | +0.002 [-0.008, +0.013] | +0.002 [-0.008, +0.013] | yes | yes |
| synthetic | C2 − C1 | numeric_recall | +0.000 [-0.047, +0.049] | +0.000 [-0.047, +0.049] | yes | yes |
| synthetic | C6 − C1 | support_rate | +0.025 [+0.005, +0.049] | +0.021 [+0.005, +0.039] | yes | yes |
| synthetic | C6 − C1 | factual_error_rate | -0.025 [-0.049, -0.005] | -0.021 [-0.039, -0.005] | yes | yes |
| synthetic | C6 − C1 | fully_supported | +0.094 [+0.000, +0.219] | +0.094 [+0.000, +0.219] | yes | yes |
| synthetic | C6 − C1 | numeric_precision | +0.015 [+0.000, +0.042] | +0.015 [+0.000, +0.042] | yes | yes |
| synthetic | C4 − C2 | complete_correct_atomic | +0.094 [-0.125, +0.312] | +0.125 [-0.062, +0.312] | yes | yes |
| synthetic | C4 − C1 | complete_correct_atomic | +0.125 [-0.062, +0.312] | +0.156 [-0.031, +0.344] | yes | yes |
| synthetic | C4 − C3 | complete_correct_atomic | +0.031 [+0.000, +0.094] | +0.031 [+0.000, +0.094] | yes | yes |
| synthetic | C4 − C7 | complete_correct_atomic | +0.094 [+0.000, +0.188] | +0.094 [+0.000, +0.188] | yes | yes |
| synthetic | C3 − C7 | complete_correct_atomic | +0.062 [+0.000, +0.156] | +0.062 [+0.000, +0.156] | yes | yes |
| synthetic | C5 − C7 | complete_correct_atomic | +0.094 [+0.000, +0.188] | +0.094 [+0.000, +0.188] | yes | yes |
| synthetic | C2 − C1 | complete_correct_atomic | +0.031 [-0.156, +0.219] | +0.031 [-0.188, +0.219] | yes | yes |
| synthetic | C6 − C1 | complete_correct_atomic | +0.094 [+0.000, +0.219] | +0.094 [+0.000, +0.219] | yes | yes |
| synthetic | **all 54 contrasts** | | | | sign changes: 0 | zero-exclusion changes: 1; max shift 0.031 |
| real | C4 − C2 | support_rate | +0.005 [-0.068, +0.086] | +0.000 [-0.073, +0.082] | yes | yes |
| real | C4 − C2 | factual_error_rate | +0.002 [-0.074, +0.066] | +0.007 [-0.071, +0.071] | yes | yes |
| real | C4 − C2 | fully_supported | -0.091 [-0.273, +0.000] | -0.091 [-0.273, +0.000] | yes | yes |
| real | C4 − C2 | numeric_precision | -0.012 [-0.048, +0.019] | -0.012 [-0.048, +0.019] | yes | yes |
| real | C4 − C2 | numeric_recall | -0.035 [-0.102, +0.025] | -0.035 [-0.102, +0.025] | yes | yes |
| real | C4 − C1 | support_rate | -0.023 [-0.079, +0.044] | -0.028 [-0.085, +0.041] | yes | yes |
| real | C4 − C1 | factual_error_rate | +0.018 [-0.046, +0.068] | +0.023 [-0.043, +0.075] | yes | yes |
| real | C4 − C1 | fully_supported | -0.182 [-0.455, +0.000] | -0.182 [-0.455, +0.000] | yes | yes |
| real | C4 − C1 | numeric_precision | -0.005 [-0.031, +0.022] | -0.005 [-0.031, +0.022] | yes | yes |
| real | C4 − C1 | numeric_recall | -0.012 [-0.073, +0.047] | -0.012 [-0.073, +0.047] | yes | yes |
| real | C4 − C3 | support_rate | +0.001 [-0.030, +0.038] | +0.001 [-0.030, +0.038] | yes | yes |
| real | C4 − C3 | factual_error_rate | -0.006 [-0.039, +0.016] | -0.006 [-0.038, +0.016] | yes | yes |
| real | C2 − C1 | support_rate | -0.009 [-0.060, +0.048] | -0.014 [-0.061, +0.036] | yes | yes |
| real | C2 − C1 | factual_error_rate | +0.004 [-0.045, +0.050] | +0.009 [-0.037, +0.051] | yes | yes |
| real | C2 − C1 | fully_supported | +0.000 [-0.333, +0.333] | +0.000 [-0.333, +0.333] | yes | yes |
| real | C2 − C1 | numeric_precision | +0.006 [-0.009, +0.025] | +0.006 [-0.009, +0.025] | yes | yes |
| real | C2 − C1 | numeric_recall | +0.022 [-0.022, +0.075] | +0.022 [-0.022, +0.075] | yes | yes |
| real | C3 − DRAFT | support_rate | +0.017 [+0.001, +0.038] | +0.017 [+0.001, +0.038] | yes | yes |
| real | C3 − DRAFT | factual_error_rate | -0.012 [-0.025, -0.001] | -0.012 [-0.025, -0.001] | yes | yes |
| real | C4 − DRAFT | support_rate | +0.018 [+0.000, +0.057] | +0.018 [+0.000, +0.056] | yes | yes |
| real | C4 − DRAFT | factual_error_rate | -0.018 [-0.057, +0.000] | -0.018 [-0.057, +0.000] | yes | yes |
| real | C4 − C2 | finding_recall | +0.077 [-0.045, +0.200] | +0.103 [+0.000, +0.208] | yes | yes |
| real | C4 − C2 | negative_finding_recall | +0.194 [+0.027, +0.375] | +0.250 [+0.071, +0.429] | yes | yes |
| real | C4 − C2 | core_finding_recall | +0.053 [-0.086, +0.211] | +0.053 [-0.069, +0.196] | yes | yes |
| real | C4 − C1 | finding_recall | +0.103 [-0.013, +0.231] | +0.128 [+0.013, +0.250] | yes | no |
| real | C4 − C1 | negative_finding_recall | +0.278 [+0.064, +0.514] | +0.306 [+0.086, +0.531] | yes | yes |
| real | C4 − C1 | core_finding_recall | +0.088 [-0.054, +0.241] | +0.088 [-0.054, +0.241] | yes | yes |
| real | C4 − C3 | finding_recall | -0.013 [-0.037, +0.000] | -0.013 [-0.037, +0.000] | yes | yes |
| real | C4 − C3 | core_finding_recall | -0.018 [-0.053, +0.000] | -0.018 [-0.053, +0.000] | yes | yes |
| real | C2 − C1 | finding_recall | +0.035 [-0.037, +0.108] | +0.035 [-0.026, +0.101] | yes | yes |
| real | C2 − C1 | negative_finding_recall | +0.077 [+0.000, +0.182] | +0.051 [+0.000, +0.150] | yes | yes |
| real | C2 − C1 | core_finding_recall | +0.033 [-0.068, +0.129] | +0.033 [-0.053, +0.123] | yes | yes |
| real | C3 − DRAFT | finding_recall | +0.013 [+0.000, +0.037] | +0.013 [+0.000, +0.037] | yes | yes |
| real | C3 − DRAFT | core_finding_recall | +0.018 [+0.000, +0.053] | +0.018 [+0.000, +0.053] | yes | yes |
| real | **all 48 contrasts** | | | | sign changes: 0 | zero-exclusion changes: 1; max shift 0.056 |
| diagnostic | C3 − C7 | support_rate | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | yes | yes |
| diagnostic | C3 − C7 | factual_error_rate | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | yes | yes |
| diagnostic | C4 − C3 | support_rate | +0.000 [+0.000, +0.001] | +0.000 [+0.000, +0.001] | yes | yes |
| diagnostic | C4 − C3 | factual_error_rate | -0.000 [-0.001, +0.000] | -0.000 [-0.001, +0.000] | yes | yes |
| diagnostic | **all 24 contrasts** | | | | sign changes: 0 | zero-exclusion changes: 0; max shift 0.000 |

Rows where both versions are degenerate (identical labels in every paired unit) are omitted.
