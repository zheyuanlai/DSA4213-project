# Real papers (12; C3/C4 11): AI-judged evaluation extension

AI judges (not human annotation). Numeric verdicts are deterministic checks of AI evidence mappings. Exploratory, post-freeze; no multiplicity correction. * = planned primary comparison. n (a better / b better / tied) counts paired units.

## Experiment 2: atomic claims

| condition | texts | assessable claims | support | factual error | over | under | unsupported | numeric err | support (result claims) | fully supported passages | factually clean passages | no assessable claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 12 | 208 | 0.894 | 0.096 | 0.038 | 0.029 | 0.024 | 0.014 | 0.897 | 0.250 | 0.250 | 0.000 |
| C2 | 12 | 200 | 0.885 | 0.100 | 0.010 | 0.040 | 0.055 | 0.010 | 0.883 | 0.250 | 0.250 | 0.000 |
| C3 | 11 | 205 | 0.873 | 0.122 | 0.029 | 0.010 | 0.059 | 0.029 | 0.864 | 0.091 | 0.091 | 0.000 |
| C4 | 11 | 199 | 0.874 | 0.116 | 0.020 | 0.015 | 0.060 | 0.030 | 0.868 | 0.091 | 0.091 | 0.000 |
| DRAFT | 11 | 202 | 0.856 | 0.134 | 0.040 | 0.015 | 0.059 | 0.030 | 0.848 | 0.091 | 0.091 | 0.000 |

Claim-pooled 95% CIs (case bootstrap) for support rate: C1 [0.834, 0.942]; C2 [0.810, 0.947]; C3 [0.793, 0.936]; C4 [0.796, 0.937]; DRAFT [0.775, 0.929]

## Experiment 3: numerical fidelity (deterministic checks)

| condition | numeric assertions | precision [95% CI] | required facts | recall [95% CI] | F1 (secondary) | error types |
|---|---|---|---|---|---|---|
| C1 | 207 | 0.986 [0.964, 1.000] | 93 | 0.215 [0.097, 0.355] | 0.353 | ARITHMETIC 3 |
| C2 | 235 | 0.991 [0.976, 1.000] | 93 | 0.237 [0.089, 0.417] | 0.382 | ARITHMETIC 2 |
| C3 | 290 | 0.979 [0.947, 1.000] | 85 | 0.224 [0.085, 0.398] | 0.364 | ARITHMETIC 2, MISATTRIBUTED 4 |
| C4 | 290 | 0.979 [0.947, 1.000] | 85 | 0.224 [0.085, 0.398] | 0.364 | ARITHMETIC 2, MISATTRIBUTED 4 |
| DRAFT | 290 | 0.979 [0.947, 1.000] | 85 | 0.224 [0.085, 0.398] | 0.364 | ARITHMETIC 2, MISATTRIBUTED 4 |

## Paired comparisons (claim rates: pooled ratio difference; passages: mean difference)

| comparison | support rate | factual error rate | overstated | understated | numeric precision | numeric recall | fully supported passage |
|---|---|---|---|---|---|---|---|
| C4 − C2 * | +0.005 [-0.068, +0.086]<br>n=11 | +0.002 [-0.074, +0.066]<br>n=11 | +0.009 [-0.022, +0.041]<br>n=11 | -0.030 [-0.058, -0.007]<br>n=11 | -0.012 [-0.048, +0.019]<br>n=11 | -0.035 [-0.102, +0.025]<br>n=11 | -0.091 [-0.273, +0.000]<br>n=11 |
| C4 − C1 * | -0.023 [-0.079, +0.044]<br>n=11 | +0.018 [-0.046, +0.068]<br>n=11 | -0.012 [-0.032, +0.007]<br>n=11 | -0.012 [-0.037, +0.000]<br>n=11 | -0.005 [-0.031, +0.022]<br>n=11 | -0.012 [-0.073, +0.047]<br>n=11 | -0.182 [-0.455, +0.000]<br>n=11 |
| C4 − C3 * | +0.001 [-0.030, +0.038]<br>n=11 | -0.006 [-0.039, +0.016]<br>n=11 | -0.009 [-0.028, +0.000]<br>n=11 | +0.005 [+0.000, +0.015]<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 |
| C2 − C1 | -0.009 [-0.060, +0.048]<br>n=12 | +0.004 [-0.045, +0.050]<br>n=12 | -0.028 [-0.059, -0.000]<br>n=12 | +0.011 [-0.009, +0.034]<br>n=12 | +0.006 [-0.009, +0.025]<br>n=12 | +0.022 [-0.022, +0.075]<br>n=12 | +0.000 [-0.333, +0.333]<br>n=12 |
| C3 − DRAFT | +0.017 [+0.001, +0.038]<br>n=11 | -0.012 [-0.025, -0.001]<br>n=11 | -0.010 [-0.032, +0.000]<br>n=11 | -0.005 [-0.015, +0.000]<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 |
| C4 − DRAFT | +0.018 [+0.000, +0.057]<br>n=11 | -0.018 [-0.057, +0.000]<br>n=11 | -0.020 [-0.060, +0.000]<br>n=11 | +0.000 [+0.000, +0.001]<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 | +0.000 [+0.000, +0.000] (degenerate)<br>n=11 |

## Experiment 4: verifier edits (each system vs its own starting draft)

| system (vs its own draft) | initial errors | corrected | removed | left in unedited sentences | left after edit | substantive edits | beneficial | harmful | new errors | new unsupported | numeric fixed | numeric introduced | required findings lost | repair recall | edit precision | harmful-edit rate | unnecessary weakening |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 22 | 9 | 4 | 1 | 8 | 104 | 13 | 15 | 12 | 9 | 2 | 1 | 4 | 0.591 | 0.125 | 0.144 | 0.560 |
| C3 | 29 | 2 | 0 | 20 | 7 | 19 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0.069 | 0.053 | 0.000 | 0.500 |
| C4 | 29 | 0 | 3 | 23 | 3 | 6 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0.103 | 0.500 | 0.000 | 0.000 |

Verifier decisions (claims): C3: ACCEPT 39, WEAKEN 4; C4: ACCEPT 41, WEAKEN 2
STRENGTHEN decisions observed: 0.

## Experiment 5: finding completeness

| condition | texts | finding recall | core recall | negative/null recall | misreported | all core findings (passage) | ITT finding recall |
|---|---|---|---|---|---|---|---|
| C1 | 12 | 0.376 [0.289, 0.470] | 0.475 [0.369, 0.594] | 0.179 [0.061, 0.310] | 0.212 [0.111, 0.310] | 0.000 | same |
| C2 | 12 | 0.412 [0.310, 0.506] | 0.508 [0.387, 0.619] | 0.256 [0.139, 0.366] | 0.200 [0.098, 0.303] | 0.000 | same |
| C3 | 11 | 0.487 [0.341, 0.645] | 0.561 [0.396, 0.736] | 0.417 [0.257, 0.607] | 0.231 [0.103, 0.358] | 0.182 | 0.447 |
| C4 | 11 | 0.474 [0.321, 0.640] | 0.544 [0.367, 0.729] | 0.417 [0.257, 0.607] | 0.192 [0.081, 0.305] | 0.182 | 0.435 |
| DRAFT | 11 | 0.474 [0.321, 0.640] | 0.544 [0.367, 0.729] | 0.417 [0.257, 0.607] | 0.218 [0.097, 0.333] | 0.182 | same |

| comparison | finding recall | core recall | negative/null recall | misreported |
|---|---|---|---|---|
| C4 − C2 | +0.077 [-0.045, +0.200] (n=11) | +0.053 [-0.086, +0.211] (n=11) | +0.194 [+0.027, +0.375] (n=11) | -0.026 [-0.122, +0.063] (n=11) |
| C4 − C1 | +0.103 [-0.013, +0.231] (n=11) | +0.088 [-0.054, +0.241] (n=11) | +0.278 [+0.064, +0.514] (n=11) | -0.038 [-0.133, +0.048] (n=11) |
| C4 − C3 | -0.013 [-0.037, +0.000] (n=11) | -0.018 [-0.053, +0.000] (n=11) | +0.000 [+0.000, +0.000] (degenerate) (n=11) | -0.038 [-0.120, +0.000] (n=11) |
| C2 − C1 | +0.035 [-0.037, +0.108] (n=12) | +0.033 [-0.068, +0.129] (n=12) | +0.077 [+0.000, +0.182] (n=12) | -0.012 [-0.103, +0.081] (n=12) |
| C3 − DRAFT | +0.013 [+0.000, +0.037] (n=11) | +0.018 [+0.000, +0.053] (n=11) | +0.000 [+0.000, +0.000] (degenerate) (n=11) | +0.013 [+0.000, +0.040] (n=11) |
| C4 − DRAFT | +0.000 [+0.000, +0.000] (degenerate) (n=11) | +0.000 [+0.000, +0.000] (degenerate) (n=11) | +0.000 [+0.000, +0.000] (degenerate) (n=11) | -0.026 [-0.080, +0.000] (n=11) |

Spearman ρ, per-text finding recall vs AI readability (n=46 texts): 0.536; recall vs atomic support rate: 0.488.

## Experiment 7: efficiency (run logs)

| condition | cost USD/text | latency s/text | tool calls/text | tool calls/verified sentence | cost per strict-success passage | cost per fully supported passage | repairs/100 tool calls | verification opportunities | all decisive evidence retrieved | any decisive evidence retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.00041 | 8.2 | 0.00 | — | n/a | 0.00163 | — | — | — | — |
| C2 | 0.00115 | 18.6 | 0.00 | — | n/a | 0.00461 | — | — | — | — |
| C3 | 0.00431 | 57.8 | 15.64 | 4.000 | n/a | 0.04744 | 1.163 | 29 | 0.724 | 0.931 |
| C4 | 0.00385 | 54.2 | 12.36 | 3.163 | n/a | 0.04240 | 2.206 | 29 | 0.966 | 1.000 |

Failed runs (excluded from completed-only rates; counted as 0 in ITT rows): {'C3': ['RP-02'], 'C4': ['RP-02']}.
