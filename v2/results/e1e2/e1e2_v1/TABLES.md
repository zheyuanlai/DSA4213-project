# E1/E2 results (DEV only, exploratory)

Probe-level figures use the majority decision over repeats. Failure stages are keyword-based SUGGESTIONS pending manual coding (failure_coding.csv).

| Measure | D0-tools | D0-oracle | D1-oracle | D2-oracle |
|---|---|---|---|---|
| n_runs | 117 | 117 | 117 | 117 |
| decision_accuracy | 25/39 | 25/39 | 32/39 | 33/39 |
| correct_strengthen | 0/12 | 0/12 | 7/12 | 9/12 |
| correct_strengthen_excl_proxy | 0/11 | 0/11 | 7/11 | 9/11 |
| correct_strengthen_claim_level_posthoc | 0/9 | 0/9 | 7/9 | 9/9 |
| correct_strengthen_scope_subgroup_posthoc | 0/3 | 0/3 | 0/3 | 0/3 |
| accept_accuracy | 15/15 | 15/15 | 14/15 | 13/15 |
| weaken_remove_accuracy | 10/12 | 10/12 | 11/12 | 11/12 |
| false_strengthen | 0/27 | 0/27 | 0/27 | 1/27 |
| run_level_strengthen_rate_on_S_probes | 0/36 | 2/36 | 18/36 | 26/36 |
| run_level_false_strengthen | 0/81 | 0/81 | 0/81 | 4/81 |
| stable_probes | 36/39 | 36/39 | 31/39 | 36/39 |
| relation_accuracy_S | None | None | 7/12 | 9/12 |
| relation_accuracy_all | None | None | 32/39 | 33/39 |
| action_inconsistent_probes | None | None | 0 | 0 |
| suggested_failure_stages_on_S_runs | {'F0': 3, 'F1': 6, 'F2': 27} | {'F1': 12, 'F2': 22} | {'F1': 9, 'F2': 6, 'F3': 3} | {'F1': 9, 'F2': 1} |
| invalid_decisions | 0 | 0 | 0 | 0 |
| cost_usd | 0.02957 | 0.009336 | 0.014608 | 0.015287 |

## Rule checks (descriptive; no automatic root cause)

* **R1**: D0-oracle strengthened 0/12 STRENGTHEN probes: full evidence alone does not fix V1 (reference threshold <= 3 met). Suggested failure stages (runs): {'F1': 12, 'F2': 22}
* **R2 D1-oracle**: automatic part NOT met (strengthen 7/12, false 0/27, weaken/remove 11/12 vs D0-oracle 10/12)
* **R3 D1-oracle**: F3 most common or >=3 inconsistent probes: no (stages {'F1': 9, 'F2': 6, 'F3': 3}, inconsistent probes 0)
* **R2 D2-oracle**: automatic part MET; human check of revisions pending (strengthen 9/12, false 1/27, weaken/remove 11/12 vs D0-oracle 10/12)
* **R3 D2-oracle**: F3 most common or >=3 inconsistent probes: no (stages {'F1': 9, 'F2': 1}, inconsistent probes 0)
* **R4**: F1/F2 dominate remaining failures in both D1 and D2: stop and discuss

## Per-probe majority decisions

| Probe | Expected | D0-tools | D0-oracle | D1-oracle | D2-oracle |
|---|---|---|---|---|---|
| P-SIG-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (ST,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,ST,AC) | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U2-partner | ACCEPT | ACCEPT (AC,WE,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (ST,AC,AC) |
| P-SIG-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-S-partner | WEAKEN | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-CON-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,ST) | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-CON-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,AC,ST) | STRENGTHEN (ST,ST,ST) |
| P-CON-U2-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | WEAKEN ✗ (WE,WE,AC) | WEAKEN ✗ (WE,WE,WE) |
| P-CON-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-S-partner | WEAKEN | ACCEPT ✗ (AC,AC,WE) | ACCEPT ✗ (AC,AC,AC) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-EFF-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-EFF-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,AC,ST) | STRENGTHEN (ST,ST,ST) |
| P-EFF-U2-partner | ACCEPT/WEAKEN | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | STRENGTHEN ✗ (ST,ST,ST) |
| P-EFF-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-S-partner | WEAKEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (WE,AC,AC) | ACCEPT ✗ (AC,AC,WE) |
| P-GEN-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-GEN-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,AC,ST) | STRENGTHEN (ST,ST,ST) |
| P-GEN-U2-partner | REMOVE/WEAKEN | WEAKEN (WE,WE,WE) | REMOVE (RE,RE,WE) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-GEN-S-strong | ACCEPT | ACCEPT (WE,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-GEN-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-ROB-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-ROB-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,AC,ST) |
| P-CIT-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-U2-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (AC,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-CIT-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | WEAKEN (WE,RE,WE) | REMOVE (RE,RE,RE) |
| P-CIT-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
