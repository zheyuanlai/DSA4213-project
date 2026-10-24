# V2: post-hoc investigation of bidirectional claim calibration (EXPLORATORY)

V2 is a post-hoc follow-up to the completed V1 study. It was designed **after** the V1 results were known, so nothing in
this directory is part of the pre-registered V1 analysis.

## Isolation from V1

* V2 lives on the git branch `v2-calibration`. `main` keeps the V1 state.
* No V1 file is edited: `src/`, `prompts/`, `configs/`, `benchmarks/`, `data/`, `outputs/`, `results/` and `docs/`
  stay byte-identical, so `python scripts/freeze_protocol.py --check` and `python scripts/verify_artifacts.py` keep passing.
  The freeze manifest hashes `src/*.py` (non-recursive) and the V1 prompt files, so V2 code must not be placed directly in `src/`.
* V2 code, prompts, data, outputs and its own cost ledger live under `v2/`. V2 may import V1 modules read-only
  (for example the evidence store, the renderer and the unchanged V1 verifier used as the reference condition).

## Layout

| Path | Contents |
|---|---|
| `v2/docs/` | experiment designs and results, one document per step |
| `v2/data/` | DEV-only probes (`dev_probes_batch1.json`); held-out V2 cases will be added separately later |
| `v2/` code, prompts, outputs | added only after the corresponding design is approved |

## Steps

1. Phase 1 diagnosis (done, reported in conversation).
2. Phase 2, E1/E2 decision-stage experiments: design in [`docs/E1_E2_DESIGN.md`](docs/E1_E2_DESIGN.md). **Status: design draft, not run.**
