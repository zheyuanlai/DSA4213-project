# AI-scored results

These are multi-agent AI judgments, not human annotations.

## Synthetic TEST (ITT)

| condition | exact accuracy | macro-F1 | ordinal MAE | |error|=2 | overstatement | understatement | omission | finding coverage | outputs w/ unsupported | numeric errors/output | NUM fact accuracy | NEG recall | NEG reframed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.958 | 0.956 | 0.083 | 0.042 | 0.042 | 0.000 | 0.000 | 0.973 | 0.125 | 0.281 | 0.866 | 1.000 | 0.000 |
| C2 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.973 | 0.000 | 0.219 | 0.866 | 1.000 | 0.000 |
| C3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.042 | 0.973 | 0.000 | 0.125 | 0.692 | 1.000 | 0.000 |
| C4 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.042 | 0.973 | 0.000 | 0.062 | 0.692 | 1.000 | 0.000 |
| C5 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.042 | 0.973 | 0.000 | 0.062 | 0.692 | 1.000 | 0.000 |
| C6 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.973 | 0.031 | 0.125 | 0.866 | 1.000 | 0.000 |
| C7 | 0.958 | 0.956 | 0.083 | 0.042 | 0.042 | 0.000 | 0.000 | 0.959 | 0.062 | 0.156 | 0.692 | 1.000 | 0.000 |

## Real papers

| condition | supported | overstated | understated | unsupported | numeric error | readability | papers |
|---|---|---|---|---|---|---|---|
| C1 | 0.819 | 0.021 | 0.000 | 0.000 | 0.160 | 4.750 | 12 |
| C2 | 0.826 | 0.000 | 0.017 | 0.000 | 0.157 | 4.417 | 12 |
| C3 | 0.773 | 0.000 | 0.068 | 0.000 | 0.159 | 4.455 | 11 |
| C4 | 0.773 | 0.000 | 0.045 | 0.000 | 0.182 | 4.455 | 11 |

## Synthetic paired comparisons (first minus second; case-bootstrap 95% CI)

| comparison | metric | diff | 95% CI | n |
|---|---|---|---|---|
| H1_C4_vs_C2 | correct | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C2 | abs_error | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C2 | severe_error | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C2 | over | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C2 | under | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C2 | coverage | 0.000 | [-0.047, 0.047] | 32 |
| H1_C4_vs_C2 | unsupported | 0.000 | [0.000, 0.000] | 32 |
| H1_C4_vs_C2 | numeric_errors | -0.156 | [-0.375, 0.031] | 32 |
| H1_C4_vs_C2 | num_fact_acc | -0.174 | [-0.286, -0.062] | 4 |
| H1_C4_vs_C2 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| H1_C4_vs_C2 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| H1_C4_vs_C1 | correct | 0.042 | [0.000, 0.125] | 24 |
| H1_C4_vs_C1 | abs_error | -0.083 | [-0.250, 0.000] | 24 |
| H1_C4_vs_C1 | severe_error | -0.042 | [-0.125, 0.000] | 24 |
| H1_C4_vs_C1 | over | -0.042 | [-0.125, 0.000] | 24 |
| H1_C4_vs_C1 | under | 0.000 | [0.000, 0.000] | 24 |
| H1_C4_vs_C1 | coverage | 0.000 | [-0.047, 0.047] | 32 |
| H1_C4_vs_C1 | unsupported | -0.125 | [-0.250, -0.031] | 32 |
| H1_C4_vs_C1 | numeric_errors | -0.219 | [-0.500, 0.000] | 32 |
| H1_C4_vs_C1 | num_fact_acc | -0.174 | [-0.286, -0.062] | 4 |
| H1_C4_vs_C1 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| H1_C4_vs_C1 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| H1_C6_vs_C2_same_draft | correct | 0.000 | [0.000, 0.000] | 24 |
| H1_C6_vs_C2_same_draft | abs_error | 0.000 | [0.000, 0.000] | 24 |
| H1_C6_vs_C2_same_draft | severe_error | 0.000 | [0.000, 0.000] | 24 |
| H1_C6_vs_C2_same_draft | over | 0.000 | [0.000, 0.000] | 24 |
| H1_C6_vs_C2_same_draft | under | 0.000 | [0.000, 0.000] | 24 |
| H1_C6_vs_C2_same_draft | coverage | 0.000 | [0.000, 0.000] | 32 |
| H1_C6_vs_C2_same_draft | unsupported | 0.031 | [0.000, 0.094] | 32 |
| H1_C6_vs_C2_same_draft | numeric_errors | -0.094 | [-0.312, 0.062] | 32 |
| H1_C6_vs_C2_same_draft | num_fact_acc | 0.000 | [0.000, 0.000] | 4 |
| H1_C6_vs_C2_same_draft | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| H1_C6_vs_C2_same_draft | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| H2_C4_vs_C5 | correct | 0.000 | [0.000, 0.000] | 24 |
| H2_C4_vs_C5 | abs_error | 0.000 | [0.000, 0.000] | 24 |
| H2_C4_vs_C5 | severe_error | 0.000 | [0.000, 0.000] | 24 |
| H2_C4_vs_C5 | over | 0.000 | [0.000, 0.000] | 24 |
| H2_C4_vs_C5 | under | 0.000 | [0.000, 0.000] | 24 |
| H2_C4_vs_C5 | coverage | 0.000 | [0.000, 0.000] | 32 |
| H2_C4_vs_C5 | unsupported | 0.000 | [0.000, 0.000] | 32 |
| H2_C4_vs_C5 | numeric_errors | 0.000 | [-0.094, 0.094] | 32 |
| H2_C4_vs_C5 | num_fact_acc | 0.000 | [0.000, 0.000] | 4 |
| H2_C4_vs_C5 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| H2_C4_vs_C5 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| H3_C4_vs_C3 | correct | 0.000 | [0.000, 0.000] | 24 |
| H3_C4_vs_C3 | abs_error | 0.000 | [0.000, 0.000] | 24 |
| H3_C4_vs_C3 | severe_error | 0.000 | [0.000, 0.000] | 24 |
| H3_C4_vs_C3 | over | 0.000 | [0.000, 0.000] | 24 |
| H3_C4_vs_C3 | under | 0.000 | [0.000, 0.000] | 24 |
| H3_C4_vs_C3 | coverage | 0.000 | [0.000, 0.000] | 32 |
| H3_C4_vs_C3 | unsupported | 0.000 | [0.000, 0.000] | 32 |
| H3_C4_vs_C3 | numeric_errors | -0.062 | [-0.156, 0.000] | 32 |
| H3_C4_vs_C3 | num_fact_acc | 0.000 | [0.000, 0.000] | 4 |
| H3_C4_vs_C3 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| H3_C4_vs_C3 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| verification_C4_vs_C7 | correct | 0.042 | [0.000, 0.125] | 24 |
| verification_C4_vs_C7 | abs_error | -0.083 | [-0.250, 0.000] | 24 |
| verification_C4_vs_C7 | severe_error | -0.042 | [-0.125, 0.000] | 24 |
| verification_C4_vs_C7 | over | -0.042 | [-0.125, 0.000] | 24 |
| verification_C4_vs_C7 | under | 0.000 | [0.000, 0.000] | 24 |
| verification_C4_vs_C7 | coverage | 0.016 | [0.000, 0.047] | 32 |
| verification_C4_vs_C7 | unsupported | -0.062 | [-0.156, 0.000] | 32 |
| verification_C4_vs_C7 | numeric_errors | -0.094 | [-0.219, 0.000] | 32 |
| verification_C4_vs_C7 | num_fact_acc | 0.000 | [0.000, 0.000] | 4 |
| verification_C4_vs_C7 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| verification_C4_vs_C7 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |
| outline_C4_vs_C6 | correct | 0.000 | [0.000, 0.000] | 24 |
| outline_C4_vs_C6 | abs_error | 0.000 | [0.000, 0.000] | 24 |
| outline_C4_vs_C6 | severe_error | 0.000 | [0.000, 0.000] | 24 |
| outline_C4_vs_C6 | over | 0.000 | [0.000, 0.000] | 24 |
| outline_C4_vs_C6 | under | 0.000 | [0.000, 0.000] | 24 |
| outline_C4_vs_C6 | coverage | 0.000 | [-0.047, 0.047] | 32 |
| outline_C4_vs_C6 | unsupported | -0.031 | [-0.094, 0.000] | 32 |
| outline_C4_vs_C6 | numeric_errors | -0.062 | [-0.250, 0.094] | 32 |
| outline_C4_vs_C6 | num_fact_acc | -0.174 | [-0.286, -0.062] | 4 |
| outline_C4_vs_C6 | neg_recall | 0.000 | [0.000, 0.000] | 4 |
| outline_C4_vs_C6 | neg_reframed | 0.000 | [0.000, 0.000] | 4 |

## Real-paper paired comparisons (first minus second; case-bootstrap 95% CI)

| comparison | metric | diff | 95% CI | n |
|---|---|---|---|---|
| C4_vs_C2 | supported_rate | -0.038 | [-0.164, 0.079] | 11 |
| C4_vs_C2 | overstated_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C2 | understated_rate | 0.027 | [-0.036, 0.095] | 11 |
| C4_vs_C2 | unsupported_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C2 | numeric_error_rate | 0.011 | [-0.073, 0.082] | 11 |
| C4_vs_C2 | readability | 0.091 | [-0.182, 0.364] | 11 |
| C4_vs_C1 | supported_rate | -0.030 | [-0.114, 0.053] | 11 |
| C4_vs_C1 | overstated_rate | -0.023 | [-0.068, 0.000] | 11 |
| C4_vs_C1 | understated_rate | 0.045 | [0.000, 0.114] | 11 |
| C4_vs_C1 | unsupported_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C1 | numeric_error_rate | 0.008 | [-0.030, 0.061] | 11 |
| C4_vs_C1 | readability | -0.273 | [-0.545, 0.000] | 11 |
| C4_vs_C3 | supported_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C3 | overstated_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C3 | understated_rate | -0.023 | [-0.068, 0.000] | 11 |
| C4_vs_C3 | unsupported_rate | 0.000 | [0.000, 0.000] | 11 |
| C4_vs_C3 | numeric_error_rate | 0.023 | [0.000, 0.068] | 11 |
| C4_vs_C3 | readability | 0.000 | [0.000, 0.000] | 11 |
