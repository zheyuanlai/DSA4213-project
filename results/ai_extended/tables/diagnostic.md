# Long diagnostic (8 cases): AI-judged evaluation extension

AI judges (not human annotation). Numeric verdicts are deterministic checks of AI evidence mappings. Exploratory, post-freeze; no multiplicity correction. * = planned primary comparison. n (a better / b better / tied) counts paired units.

## Experiment 2: atomic claims

| condition | texts | assessable claims | support | factual error | over | under | unsupported | numeric err | support (result claims) | fully supported passages | factually clean passages | no assessable claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C7 | 8 | 126 | 0.968 | 0.032 | 0.016 | 0.000 | 0.000 | 0.016 | 0.975 | 0.625 | 0.625 | 0.000 |
| C3 | 8 | 125 | 0.968 | 0.032 | 0.016 | 0.000 | 0.000 | 0.016 | 0.975 | 0.625 | 0.625 | 0.000 |
| C4 | 8 | 126 | 0.968 | 0.032 | 0.016 | 0.000 | 0.000 | 0.016 | 0.975 | 0.625 | 0.625 | 0.000 |

Claim-pooled 95% CIs (case bootstrap) for support rate: C7 [0.933, 0.993]; C3 [0.933, 0.993]; C4 [0.933, 0.993]

## Experiment 3: numerical fidelity (deterministic checks)

| condition | numeric assertions | precision [95% CI] | required facts | recall [95% CI] | F1 (secondary) | error types |
|---|---|---|---|---|---|---|
| C7 | 224 | 0.991 [0.971, 1.000] | 56 | 0.500 [0.328, 0.656] | 0.665 | ARITHMETIC 2 |
| C3 | 224 | 0.991 [0.971, 1.000] | 56 | 0.500 [0.328, 0.656] | 0.665 | ARITHMETIC 2 |
| C4 | 224 | 0.991 [0.971, 1.000] | 56 | 0.500 [0.328, 0.656] | 0.665 | ARITHMETIC 2 |

## Paired comparisons (claim rates: pooled ratio difference; passages: mean difference)

| comparison | support rate | factual error rate | overstated | understated | numeric precision | numeric recall | fully supported passage |
|---|---|---|---|---|---|---|---|
| C4 − C7 * | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 |
| C3 − C7 | -0.000 [-0.001, +0.000]<br>n=8 | +0.000 [+0.000, +0.001]<br>n=8 | +0.000 [+0.000, +0.000]<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 |
| C4 − C3 * | +0.000 [+0.000, +0.001]<br>n=8 | -0.000 [-0.001, +0.000]<br>n=8 | -0.000 [-0.000, +0.000]<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 | +0.000 [+0.000, +0.000] (degenerate)<br>n=8 |

## Experiment 4: verifier edits (each system vs its own starting draft)

| system (vs its own draft) | initial errors | corrected | removed | left in unedited sentences | left after edit | substantive edits | beneficial | harmful | new errors | new unsupported | numeric fixed | numeric introduced | required findings lost | repair recall | edit precision | harmful-edit rate | unnecessary weakening |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C3 | 4 | 0 | 0 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | undefined |
| C4 | 4 | 0 | 0 | 4 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | undefined |

Verifier decisions (claims): C3: ACCEPT 31, WEAKEN 1; C4: ACCEPT 31, WEAKEN 1
STRENGTHEN decisions observed: 0.

## Experiment 5: finding completeness

| condition | texts | gold required-finding recall | finding recall | core recall | negative/null recall | misreported | all core findings (passage) | ITT finding recall |
|---|---|---|---|---|---|---|---|---|
| C7 | 8 | 0.824 [0.647, 0.950] | 0.627 [0.481, 0.800] | 0.621 [0.469, 0.815] | 0.625 [0.357, 0.842] | 0.098 [0.017, 0.213] | 0.375 | same |
| C3 | 8 | 0.824 [0.647, 0.950] | 0.627 [0.481, 0.800] | 0.621 [0.469, 0.815] | 0.625 [0.357, 0.842] | 0.098 [0.017, 0.213] | 0.375 | same |
| C4 | 8 | 0.824 [0.647, 0.950] | 0.627 [0.481, 0.800] | 0.621 [0.469, 0.815] | 0.625 [0.357, 0.842] | 0.098 [0.017, 0.213] | 0.375 | same |

| comparison | gold required-finding recall | finding recall | core recall | negative/null recall | misreported |
|---|---|---|---|---|---|
| C4 − C7 | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) |
| C3 − C7 | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) |
| C4 − C3 | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) | +0.000 [+0.000, +0.000] (degenerate) (n=8) |

## Experiment 7: efficiency (run logs)

| condition | cost USD/text | latency s/text | tool calls/text | tool calls/verified sentence | cost per strict-success passage | cost per fully supported passage | repairs/100 tool calls | verification opportunities | all decisive evidence retrieved | any decisive evidence retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| C7 | 0.00110 | 8.3 | 0.00 | — | n/a | 0.00176 | — | — | — | — |
| C3 | 0.00376 | 53.5 | 16.00 | 4.000 | n/a | 0.00601 | 0.000 | 4 | 0.750 | 1.000 |
| C4 | 0.00310 | 42.2 | 9.38 | 2.344 | n/a | 0.00497 | 0.000 | 4 | 0.750 | 1.000 |
