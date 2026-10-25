# v2/outputs/e1e2/e1e2_v1:D1-oracle  vs  v2/outputs/e1e2/e2b_v1:D1-oracle

## improved (3)

| Probe | Expected | A | B |
|---|---|---|---|
| P-SIG-U-strong | STRENGTHEN | ACCEPT ['STRENGTHEN', 'ACCEPT', 'ACCEPT'] | STRENGTHEN ['STRENGTHEN', 'STRENGTHEN', 'STRENGTHEN'] |
| P-EFF-S-partner | WEAKEN | ACCEPT ['WEAKEN', 'ACCEPT', 'ACCEPT'] | WEAKEN ['WEAKEN', 'WEAKEN', 'ACCEPT'] |
| P-CIT-U-strong | STRENGTHEN | ACCEPT ['ACCEPT', 'ACCEPT', 'ACCEPT'] | STRENGTHEN ['STRENGTHEN', 'STRENGTHEN', 'ACCEPT'] |

## regressed (0)


## changed_same_correctness (1)

| Probe | Expected | A | B |
|---|---|---|---|
| P-CIT-S-partner | REMOVE/WEAKEN | WEAKEN ['WEAKEN', 'REMOVE', 'WEAKEN'] | REMOVE ['REMOVE', 'REMOVE', 'REMOVE'] |

unchanged: 35
