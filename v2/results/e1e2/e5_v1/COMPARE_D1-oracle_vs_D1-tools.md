# v2/outputs/e1e2/e5_v1:D1-oracle  vs  v2/outputs/e1e2/e5_v1:D1-tools

## improved (2)

| Probe | Expected | A | B |
|---|---|---|---|
| P-CON-U2-partner | ACCEPT | WEAKEN ['ACCEPT', 'WEAKEN', 'WEAKEN'] | ACCEPT ['ACCEPT', 'ACCEPT', 'ACCEPT'] |
| P-EFF-S-partner | WEAKEN | ACCEPT ['ACCEPT', 'ACCEPT', 'ACCEPT'] | WEAKEN ['ACCEPT', 'WEAKEN', 'WEAKEN'] |

## regressed (1)

| Probe | Expected | A | B |
|---|---|---|---|
| P-EFF-U2-strong | STRENGTHEN | STRENGTHEN ['STRENGTHEN', 'STRENGTHEN', 'STRENGTHEN'] | ACCEPT ['STRENGTHEN', 'ACCEPT', 'ACCEPT'] |

## changed_same_correctness (0)


unchanged: 36
