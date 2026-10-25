# Phase 4 TEST results: p4_test_v1

| Metric (rate; runs) | V1 C4 | V2 C4 | V2 C5 |
|---|---|---|---|
| correct_strengthen | 0.33 (12/36) | 0.78 (28/36) | 0.00 (0/36) |
| false_strengthen | 0.00 (0/84) | 0.00 (0/84) | 0.00 (0/84) |
| overstatement_corrected | 0.70 (21/30) | 0.73 (22/30) | 0.90 (27/30) |
| control_preserved | 1.00 (54/54) | 1.00 (54/54) | 1.00 (54/54) |
| harmful_edit | 0.00 (0/54) | 0.00 (0/54) | 0.00 (0/54) |
| decision_correct | 0.70 (84/120) | 0.85 (102/120) | 0.57 (68/120) |
| cost_usd_total | 0.039847 | 0.041206 | 0.035968 |
| latency_s_per_run | 11.05 | 13.93 | 13.79 |
| tool_calls_per_run | 2.77 | 3.03 | 2.73 |

## Paired contrasts (cluster bootstrap over pairs, 95%)

* V2 C4 - V1 C4, correct_strengthen: +0.444 [+0.139, +0.778] (n=12)
* V2 C4 - V1 C4, false_strengthen: +0.000 [+0.000, +0.000] (n=28)
* V2 C4 - V1 C4, overstatement_corrected: +0.033 [-0.056, +0.167] (n=10)
* V2 C4 - V1 C4, control_preserved: +0.000 [+0.000, +0.000] (n=18)
* V2 C4 - V1 C4, harmful_edit: +0.000 [+0.000, +0.000] (n=18)
* V2 C4 - V1 C4, decision_correct: +0.150 [+0.008, +0.307] (n=40)
* V2 C4 - V2 C5, correct_strengthen: +0.778 [+0.444, +1.000] (n=12)
* V2 C4 - V2 C5, false_strengthen: +0.000 [+0.000, +0.000] (n=28)
* V2 C4 - V2 C5, overstatement_corrected: -0.167 [-0.300, -0.042] (n=10)
* V2 C4 - V2 C5, control_preserved: +0.000 [+0.000, +0.000] (n=18)
* V2 C4 - V2 C5, harmful_edit: +0.000 [+0.000, +0.000] (n=18)
* V2 C4 - V2 C5, decision_correct: +0.283 [+0.143, +0.419] (n=40)

## Subgroups (correct strengthening, runs)

* pattern_new_vs_dev: V1 C4 6.0/24; V2 C4 19.0/24; V2 C5 0.0/24
* no_test_needed: V1 C4 1.0/18; V2 C4 12.0/18; V2 C5 0.0/18
