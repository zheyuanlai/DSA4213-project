# Synthetic TEST (32 cases): AI-judged evaluation extension

AI judges (not human annotation). Numeric verdicts are deterministic checks of AI evidence mappings. Exploratory, post-freeze; no multiplicity correction. * = planned primary comparison. n (a better / b better / tied) counts paired units.

## Experiment 1: strict whole-passage success (existing AI labels)

| condition | complete & correct | focal exact (n=24) | all findings covered | no unsupported claim | no numeric error | NUM all facts (n=4) | NEG all reported (n=4) | NEG no reframing (n=4) | complete & correct (atomic variant) |
|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.594 | 0.958 | 0.938 | 0.875 | 0.844 | 0.000 | 1.000 | 1.000 | 0.500 |
| C2 | 0.719 | 1.000 | 0.938 | 1.000 | 0.875 | 0.000 | 1.000 | 1.000 | 0.531 |
| C6 | 0.719 | 1.000 | 0.938 | 0.969 | 0.906 | 0.000 | 1.000 | 1.000 | 0.594 |
| C7 | 0.625 | 0.958 | 0.906 | 0.938 | 0.875 | 0.000 | 1.000 | 1.000 | 0.531 |
| C3 | 0.688 | 1.000 | 0.938 | 1.000 | 0.875 | 0.000 | 1.000 | 1.000 | 0.594 |
| C4 | 0.750 | 1.000 | 0.938 | 1.000 | 0.938 | 0.000 | 1.000 | 1.000 | 0.625 |
| C5 | 0.750 | 1.000 | 0.938 | 1.000 | 0.938 | 0.000 | 1.000 | 1.000 | 0.625 |

Paired differences (first minus second), case bootstrap 95% CI; n (a better / b better / tied); matched-pair cluster CI as sensitivity.

| comparison | complete & correct | n | matched-pair CI | atomic variant |
|---|---|---|---|---|
| C4 − C2 | +0.031 [-0.094, +0.156] | 32 (3/2/27) | [+0.000, +0.094] | +0.094 [-0.125, +0.312] |
| C4 − C1 | +0.156 [+0.000, +0.312] | 32 (6/1/25) | [+0.062, +0.281] | +0.125 [-0.062, +0.312] |
| C4 − C3 | +0.062 [+0.000, +0.156] | 32 (2/0/30) | [+0.000, +0.156] | +0.031 [+0.000, +0.094] |
| C4 − C5 | +0.000 [-0.094, +0.094] | 32 (1/1/30) | [-0.094, +0.094] | +0.000 [+0.000, +0.000] (degenerate) |
| C4 − C7 | +0.125 [+0.031, +0.250] | 32 (4/0/28) | [+0.000, +0.281] | +0.094 [+0.000, +0.188] |
| C3 − C7 | +0.062 [+0.000, +0.156] | 32 (2/0/30) | [+0.000, +0.156] | +0.062 [+0.000, +0.156] |
| C5 − C7 | +0.125 [+0.031, +0.250] | 32 (4/0/28) | [+0.031, +0.250] | +0.094 [+0.000, +0.188] |
| C2 − C1 | +0.125 [+0.000, +0.281] | 32 (5/1/26) | [+0.031, +0.250] | +0.031 [-0.156, +0.219] |
| C6 − C1 | +0.125 [+0.031, +0.250] | 32 (4/0/28) | [+0.031, +0.250] | +0.094 [+0.000, +0.219] |

## Experiment 2: atomic claims

| condition | texts | assessable claims | support | factual error | over | under | unsupported | numeric err | support (result claims) | fully supported passages | factually clean passages | no assessable claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 32 | 243 | 0.926 | 0.074 | 0.029 | 0.004 | 0.021 | 0.021 | 0.912 | 0.656 | 0.656 | 0.000 |
| C2 | 32 | 297 | 0.943 | 0.057 | 0.020 | 0.000 | 0.017 | 0.020 | 0.936 | 0.594 | 0.594 | 0.000 |
| C6 | 32 | 246 | 0.951 | 0.049 | 0.024 | 0.004 | 0.016 | 0.004 | 0.943 | 0.750 | 0.750 | 0.000 |
| C7 | 32 | 268 | 0.948 | 0.052 | 0.011 | 0.000 | 0.019 | 0.022 | 0.940 | 0.719 | 0.719 | 0.000 |
| C3 | 32 | 268 | 0.963 | 0.037 | 0.004 | 0.000 | 0.019 | 0.015 | 0.958 | 0.781 | 0.781 | 0.000 |
| C4 | 32 | 268 | 0.970 | 0.030 | 0.004 | 0.000 | 0.015 | 0.011 | 0.967 | 0.812 | 0.812 | 0.000 |
| C5 | 32 | 269 | 0.970 | 0.030 | 0.004 | 0.000 | 0.015 | 0.011 | 0.967 | 0.812 | 0.812 | 0.000 |

Claim-pooled 95% CIs (case bootstrap) for support rate: C1 [0.882, 0.965]; C2 [0.913, 0.969]; C6 [0.912, 0.983]; C7 [0.912, 0.977]; C3 [0.934, 0.987]; C4 [0.944, 0.990]; C5 [0.944, 0.992]

## Experiment 3: numerical fidelity (deterministic checks)

| condition | numeric assertions | precision [95% CI] | required facts | recall [95% CI] | F1 (secondary) | error types |
|---|---|---|---|---|---|---|
| C1 | 392 | 0.982 [0.956, 0.998] | 64 | 0.828 [0.733, 0.898] | 0.899 | ARITHMETIC 4, MISATTRIBUTED 3 |
| C2 | 429 | 0.984 [0.964, 0.998] | 64 | 0.828 [0.737, 0.894] | 0.899 | ARITHMETIC 6, MISATTRIBUTED 1 |
| C6 | 396 | 0.997 [0.992, 1.000] | 64 | 0.828 [0.733, 0.898] | 0.905 | ARITHMETIC 1 |
| C7 | 474 | 0.985 [0.971, 0.996] | 64 | 0.719 [0.620, 0.813] | 0.831 | ARITHMETIC 3, MISATTRIBUTED 3, VALUE_MISMATCH 1 |
| C3 | 469 | 0.991 [0.981, 1.000] | 64 | 0.719 [0.620, 0.813] | 0.833 | ARITHMETIC 3, VALUE_MISMATCH 1 |
| C4 | 470 | 0.994 [0.983, 1.000] | 64 | 0.719 [0.620, 0.813] | 0.834 | ARITHMETIC 2, MISATTRIBUTED 1 |
| C5 | 469 | 0.994 [0.983, 1.000] | 64 | 0.719 [0.620, 0.813] | 0.834 | ARITHMETIC 2, VALUE_MISMATCH 1 |

## Paired comparisons (claim rates: pooled ratio difference; passages: mean difference)

| comparison | support rate | factual error rate | overstated | understated | numeric precision | numeric recall | fully supported passage |
|---|---|---|---|---|---|---|---|
| C4 − C2 * | +0.027 [-0.009, +0.063]<br>n=32 | -0.027 [-0.063, +0.009]<br>n=32 | -0.016 [-0.040, +0.004]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.010 [-0.008, +0.032]<br>n=32 | -0.109 [-0.185, -0.033]<br>n=32 | +0.219 [+0.000, +0.438]<br>n=32 |
| C4 − C1 * | +0.044 [-0.001, +0.093]<br>n=32 | -0.044 [-0.093, +0.001]<br>n=32 | -0.025 [-0.064, +0.003]<br>n=32 | -0.004 [-0.013, +0.000]<br>n=32 | +0.011 [-0.009, +0.040]<br>n=32 | -0.109 [-0.185, -0.033]<br>n=32 | +0.156 [-0.031, +0.344]<br>n=32 |
| C4 − C3 * | +0.007 [-0.000, +0.019]<br>n=32 | -0.007 [-0.019, +0.000]<br>n=32 | +0.000 [-0.000, +0.000]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.002 [-0.005, +0.010]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.031 [+0.000, +0.094]<br>n=32 |
| C4 − C5 * | -0.000 [-0.011, +0.011]<br>n=32 | +0.000 [-0.011, +0.011]<br>n=32 | +0.000 [-0.000, +0.000]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.000 [-0.006, +0.006]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 |
| C4 − C7 * | +0.022 [+0.004, +0.050]<br>n=32 | -0.022 [-0.050, -0.004]<br>n=32 | -0.007 [-0.024, +0.000]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.008 [-0.000, +0.020]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.094 [+0.000, +0.188]<br>n=32 |
| C3 − C7 | +0.015 [+0.000, +0.042]<br>n=32 | -0.015 [-0.042, +0.000]<br>n=32 | -0.007 [-0.024, +0.000]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.006 [-0.000, +0.018]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.062 [+0.000, +0.156]<br>n=32 |
| C5 − C7 | +0.022 [+0.004, +0.051]<br>n=32 | -0.022 [-0.051, -0.004]<br>n=32 | -0.007 [-0.024, +0.000]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.008 [-0.000, +0.020]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.094 [+0.000, +0.188]<br>n=32 |
| C2 − C1 | +0.017 [-0.023, +0.062]<br>n=32 | -0.017 [-0.062, +0.023]<br>n=32 | -0.009 [-0.050, +0.025]<br>n=32 | -0.004 [-0.013, +0.000]<br>n=32 | +0.002 [-0.008, +0.013]<br>n=32 | +0.000 [-0.047, +0.049]<br>n=32 | -0.062 [-0.281, +0.156]<br>n=32 |
| C6 − C1 | +0.025 [+0.005, +0.049]<br>n=32 | -0.025 [-0.049, -0.005]<br>n=32 | -0.004 [-0.013, +0.000]<br>n=32 | -0.000 [-0.000, +0.000]<br>n=32 | +0.015 [+0.000, +0.042]<br>n=32 | +0.000 [+0.000, +0.000] (degenerate)<br>n=32 | +0.094 [+0.000, +0.219]<br>n=32 |

## Experiment 4: verifier edits (each system vs its own starting draft)

| system (vs its own draft) | initial errors | corrected | removed | left in unedited sentences | left after edit | substantive edits | beneficial | harmful | new errors | new unsupported | numeric fixed | numeric introduced | required findings lost | repair recall | edit precision | harmful-edit rate | unnecessary weakening |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 18 | 9 | 1 | 0 | 8 | 141 | 10 | 9 | 9 | 3 | 1 | 1 | 0 | 0.556 | 0.071 | 0.064 | 0.700 |
| C6 | 18 | 5 | 1 | 10 | 2 | 14 | 6 | 0 | 0 | 0 | 3 | 0 | 0 | 0.333 | 0.429 | 0.000 | 0.500 |
| C3 | 14 | 2 | 2 | 8 | 2 | 10 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0.286 | 0.400 | 0.000 | 0.500 |
| C4 | 14 | 4 | 2 | 6 | 2 | 15 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 0.429 | 0.400 | 0.000 | 0.500 |
| C5 | 14 | 4 | 2 | 7 | 1 | 14 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 0.429 | 0.429 | 0.000 | 0.500 |

Verifier decisions (claims): C6: ACCEPT 88, WEAKEN 9; C3: ACCEPT 98, WEAKEN 5; C4: ACCEPT 94, WEAKEN 9; C5: ACCEPT 96, WEAKEN 7
STRENGTHEN decisions observed: 0.

## Experiment 7: efficiency (run logs)

| condition | cost USD/text | latency s/text | tool calls/text | tool calls/verified sentence | cost per strict-success passage | cost per fully supported passage | repairs/100 tool calls | verification opportunities | all decisive evidence retrieved | any decisive evidence retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.00023 | 2.0 | 0.00 | — | 0.00038 | 0.00035 | — | — | — | — |
| C2 | 0.00068 | 9.2 | 0.00 | — | 0.00094 | 0.00114 | — | — | — | — |
| C6 | 0.00163 | 31.1 | 8.88 | 2.928 | 0.00227 | 0.00218 | 2.113 | 18 | 0.389 | 1.000 |
| C7 | 0.00060 | 5.5 | 0.00 | — | 0.00096 | 0.00083 | — | — | — | — |
| C3 | 0.00241 | 38.7 | 12.88 | 4.000 | 0.00351 | 0.00309 | 0.971 | 14 | 0.929 | 1.000 |
| C4 | 0.00209 | 34.7 | 9.22 | 2.864 | 0.00278 | 0.00257 | 2.034 | 14 | 0.714 | 1.000 |
| C5 | 0.00191 | 34.6 | 9.50 | 2.951 | 0.00254 | 0.00235 | 1.974 | 14 | 0.714 | 1.000 |
