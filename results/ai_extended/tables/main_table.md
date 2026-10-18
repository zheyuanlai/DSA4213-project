# Main results table (C1–C4)

AI-judged labels (two judge families plus AI adjudication); numeric verdicts deterministic. Rates pool claims or findings over cases; intervals are paired case (paper) bootstraps, 10,000 resamples, seed 4213. Real-paper intervals use the 11 papers where both systems completed.

| Synthetic TEST (32 cases) | C1 direct | C2 writer–reviewer | C3 scripted verifier | C4 full agent | C4 − C2 [95% CI] |
|---|---|---|---|---|---|
| Focal exact accuracy (24 ordinal cases) | 0.958 | 1.000 | 1.000 | 1.000 | +0.000 [+0.000, +0.000] (degenerate) |
| Strict complete-and-correct passage | 0.594 | 0.719 | 0.688 | 0.750 | +0.031 [-0.094, +0.156] |
| Atomic claim support rate | 0.926 | 0.943 | 0.963 | 0.970 | +0.027 [-0.009, +0.063] |
| Atomic factual error rate | 0.074 | 0.057 | 0.037 | 0.030 | -0.027 [-0.063, +0.009] |
| Fully supported passage | 0.656 | 0.594 | 0.781 | 0.812 | +0.219 [+0.000, +0.438] |
| Numeric precision | 0.982 | 0.984 | 0.991 | 0.994 | +0.010 [-0.008, +0.032] |
| Numeric recall (64 required facts) | 0.828 | 0.828 | 0.719 | 0.719 | -0.109 [-0.185, -0.033] |
| Cost per passage (USD) | 0.00023 | 0.00068 | 0.00241 | 0.00209 | — |
| Evidence-tool calls per passage | 0.0 | 0.0 | 12.9 | 9.2 | — |

| Real papers (12; C3/C4 completed on 11) | C1 direct | C2 writer–reviewer | C3 scripted verifier | C4 full agent | C4 − C2 [95% CI] |
|---|---|---|---|---|---|
| Atomic claim support rate | 0.894 | 0.885 | 0.873 | 0.874 | +0.005 [-0.068, +0.086] |
| Atomic factual error rate | 0.096 | 0.100 | 0.122 | 0.116 | +0.002 [-0.074, +0.066] |
| Finding recall (package checklist) | 0.376 | 0.412 | 0.487 | 0.474 | +0.077 [-0.045, +0.200] |
| Negative/null-finding recall | 0.179 | 0.256 | 0.417 | 0.417 | +0.194 [+0.027, +0.375] |
| Numeric precision | 0.986 | 0.991 | 0.979 | 0.979 | -0.012 [-0.048, +0.019] |
| Numeric recall (checklist facts) | 0.215 | 0.237 | 0.224 | 0.224 | -0.035 [-0.102, +0.025] |
| Cost per passage (USD) | 0.00041 | 0.00115 | 0.00431 | 0.00385 | — |
