# E1/E2 results (DEV only, exploratory)

Probe-level figures use the majority decision over repeats. Failure stages are keyword-based SUGGESTIONS pending manual coding (failure_coding.csv).

| Measure | D1-oracle | D0-tools-800 | D1-tools |
|---|---|---|---|
| n_runs | 117 | 117 | 117 |
| decision_accuracy | 34/39 | 25/39 | 35/39 |
| correct_strengthen | 9/12 | 0/12 | 8/12 |
| correct_strengthen_excl_proxy | 9/11 | 0/11 | 8/11 |
| correct_strengthen_claim_level_posthoc | 9/9 | 0/9 | 8/9 |
| correct_strengthen_scope_subgroup_posthoc | 0/3 | 0/3 | 0/3 |
| accept_accuracy | 14/15 | 15/15 | 15/15 |
| weaken_remove_accuracy | 11/12 | 10/12 | 12/12 |
| false_strengthen | 0/27 | 0/27 | 0/27 |
| run_level_strengthen_rate_on_S_probes | 25/36 | 0/36 | 23/36 |
| run_level_false_strengthen | 0/81 | 0/81 | 0/81 |
| stable_probes | 34/39 | 37/39 | 35/39 |
| relation_accuracy_S | 9/12 | None | 8/12 |
| relation_accuracy_all | 34/39 | None | 35/39 |
| action_inconsistent_probes | 0 | None | 0 |
| suggested_failure_stages_on_S_runs | {'F1': 9, 'F3': 2} | {'F0': 3, 'F1': 6, 'F2': 27} | {'F0': 3, 'F1': 6, 'F2': 4} |
| invalid_decisions | 0 | 0 | 0 |
| cost_usd | 0.022065 | 0.043097 | 0.044585 |

## Rule checks (descriptive; no automatic root cause)

* **R2 D1-oracle**: automatic part MET; human check of revisions pending (strengthen 9/12, false 0/27, weaken/remove 11/12 vs D0-oracle n/a)
* **R3 D1-oracle**: F3 most common or >=3 inconsistent probes: no (stages {'F1': 9, 'F3': 2}, inconsistent probes 0)

## E5: probes right in D1-oracle but wrong in D1-tools

* **P-EFF-U2-strong** (expected STRENGTHEN): oracle ['STRENGTHEN', 'STRENGTHEN', 'STRENGTHEN'], tools ['STRENGTHEN', 'ACCEPT', 'ACCEPT'] -> decision loss; runs: r1 STRENGTHEN retrieved=True rel=STRONGER_SUPPORTED; r2 ACCEPT retrieved=True rel=MATCHES; r3 ACCEPT retrieved=True rel=MATCHES

## Per-probe majority decisions

| Probe | Expected | D1-oracle | D0-tools-800 | D1-tools |
|---|---|---|---|---|
| P-SIG-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-SIG-U2-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-SIG-S-partner | WEAKEN | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-CON-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-CON-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-CON-U2-partner | ACCEPT | WEAKEN ✗ (AC,WE,WE) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CON-S-partner | WEAKEN | WEAKEN (WE,AC,WE) | ACCEPT ✗ (AC,AC,AC) | WEAKEN (WE,WE,WE) |
| P-EFF-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-EFF-U-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (ST,AC,AC) |
| P-EFF-U2-partner | ACCEPT/WEAKEN | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-EFF-S-partner | WEAKEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | WEAKEN (AC,WE,WE) |
| P-GEN-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-GEN-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,AC) |
| P-GEN-U2-partner | REMOVE/WEAKEN | WEAKEN (WE,WE,RE) | WEAKEN (WE,WE,WE) | WEAKEN (WE,WE,WE) |
| P-GEN-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,WE,AC) | ACCEPT (AC,AC,AC) |
| P-GEN-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-GEN-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-U-strong | STRENGTHEN | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) | ACCEPT ✗ (AC,AC,AC) |
| P-ROB-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,AC) |
| P-ROB-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-ROB-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-ROB-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-U-strong | STRENGTHEN | STRENGTHEN (ST,ST,ST) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-CIT-U-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-U2-strong | STRENGTHEN | STRENGTHEN (ST,ST,AC) | ACCEPT ✗ (AC,AC,AC) | STRENGTHEN (ST,ST,ST) |
| P-CIT-U2-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,AC,RE) | REMOVE (RE,RE,RE) |
| P-CIT-S-strong | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
| P-CIT-S-partner | REMOVE/WEAKEN | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) | REMOVE (RE,RE,RE) |
| P-CIT-Z-partner | ACCEPT | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) | ACCEPT (AC,AC,AC) |
