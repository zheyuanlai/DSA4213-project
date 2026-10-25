# E1/E2 results (DEV only, exploratory)

Probe-level figures use the majority decision over repeats. Failure stages are keyword-based SUGGESTIONS pending manual coding (failure_coding.csv).

| Measure | D1-oracle | D1c-oracle |
|---|---|---|
| n_runs | 117 | 117 |
| decision_accuracy | 35/39 | 35/39 |
| correct_strengthen | 9/12 | 9/12 |
| correct_strengthen_excl_proxy | 9/11 | 9/11 |
| correct_strengthen_claim_level_posthoc | 9/9 | 9/9 |
| correct_strengthen_scope_subgroup_posthoc | 0/3 | 0/3 |
| accept_accuracy | 14/15 | 14/15 |
| weaken_remove_accuracy | 12/12 | 12/12 |
| false_strengthen | 0/27 | 0/27 |
| run_level_strengthen_rate_on_S_probes | 26/36 | 25/36 |
| run_level_false_strengthen | 1/81 | 1/81 |
| stable_probes | 35/39 | 34/39 |
| relation_accuracy_S | 9/12 | 9/12 |
| relation_accuracy_all | 35/39 | 34/39 |
| action_inconsistent_probes | 0 | 0 |
| suggested_failure_stages_on_S_runs | {'F1': 9, 'F2': 1} | {'F1': 9, 'F2': 2} |
| invalid_decisions | 0 | 0 |
| cost_usd | 0.015002 | 0.015074 |

## Rule checks (descriptive; no automatic root cause)

* **R2 D1-oracle**: automatic part MET; human check of revisions pending (strengthen 9/12, false 0/27, weaken/remove 12/12 vs D0-oracle n/a)
* **R3 D1-oracle**: F3 most common or >=3 inconsistent probes: no (stages {'F1': 9, 'F2': 1}, inconsistent probes 0)

## Per-probe majority decisions

| Probe | Expected | D1-oracle | D1c-oracle |
|---|---|---|---|
| P-SIG-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U2-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-S-partner | WEAKEN | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-CON-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-CON-U-partner | ACCEPT | ACCEPT (ST,AC,AC) | ACCEPT (AC,ST,AC) |
| P-CON-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-CON-U2-partner | ACCEPT | WEAKEN ✗ (WE,WE,AC) | WEAKEN ✗ (WE,WE,WE) |
| P-CON-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-S-partner | WEAKEN | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-EFF-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-EFF-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-EFF-U2-partner | ACCEPT/WEAKEN | ACCEPT (AC,AC,AC) | WEAKEN (AC,WE,WE) |
| P-EFF-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-S-partner | WEAKEN | WEAKEN (WE,WE,AC) | WEAKEN (WE,WE,WE) |
| P-GEN-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-GEN-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-GEN-U2-partner | REMOVE/WEAKEN | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-GEN-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-GEN-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-ROB-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,AC,ST) |
| P-ROB-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,AC) | STRENGTHEN (AC,ST,ST) |
| P-CIT-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | STRENGTHEN (ST,ST,ST) |
| P-CIT-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (WE,RE,RE) |
| P-CIT-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
