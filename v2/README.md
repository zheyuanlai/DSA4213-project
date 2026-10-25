# V2: post-hoc investigation of bidirectional claim calibration (EXPLORATORY)

V2 is a post-hoc follow-up to the completed V1 study. It was designed **after** the V1 results were known, so nothing in
this directory is part of the pre-registered V1 analysis.

## Isolation from V1

* V2 lives on the git branch `v2-calibration`. `main` keeps the V1 state.
* No V1 file is edited: `src/`, `prompts/`, `configs/`, `benchmarks/`, `data/`, `outputs/`, `results/` and `docs/`
  stay byte-identical. The freeze manifest hashes `src/*.py` (non-recursive) and the V1 prompt files, so V2 code must not
  be placed directly in `src/`.
* V2 code, prompts, data, outputs and its own cost ledger live under `v2/`. V2 imports V1 modules read-only (for example
  the evidence store, the renderer and the unchanged V1 verifier used as the reference condition).

## Layout

| Path | Contents |
|---|---|
| `v2/docs/` | experiment designs and results, one document per step |
| `v2/data/` | DEV-only probes (`dev_probes_batch1.json`); held-out V2 cases will be added separately later |
| `v2/prompts/` | V2 verifier prompts (D0 oracle prompt, D1 and D2 addenda) |
| `v2/verifier_oracle.py` | oracle-evidence verifier for E1/E2/E2b |
| `v2/verifier_tools.py` | port of V1's tool loop with injectable prompt and schema (E5) |
| `v2/scripts/` | `run_e1_e2.py` (runner), `analyze_e1_e2.py` (analysis and review sheets) |
| `v2/tests/` | offline tests (mock client) |
| `v2/outputs/` | run records and the separate V2 cost ledger (`_mock/` is git-ignored) |
| `v2/compat_win/` | Windows-only `fcntl` stand-in, for local development on Windows |

## Running

```bash
pip install -r requirements.txt
python -m pytest v2/tests                                        # offline, no API calls
python v2/scripts/run_e1_e2.py --run-tag mock_demo --mock        # free dry run
python v2/scripts/run_e1_e2.py --run-tag e1e2_v1 --real          # paid; needs OPENROUTER_API_KEY
python v2/scripts/analyze_e1_e2.py --run-dir v2/outputs/e1e2/e1e2_v1
```

**On Windows**, V1's `fcntl` import fails. Run with `PYTHONPATH=v2/compat_win` and `PYTHONUTF8=1` (Git Bash:
`export PYTHONPATH=v2/compat_win PYTHONUTF8=1`). The stand-in makes file locks no-ops, so use a single process.
Also keep `core.autocrlf=false` for this repository, because V1's integrity checks hash raw bytes. On Windows,
`scripts/verify_artifacts.py` still reports one failure, "frozen protocol files": V1 builds manifest keys with
`str(Path)`, which gives backslashes on Windows. Compared with POSIX paths, only the documented post-freeze changes
remain. On Linux CI the check passes unchanged.

## Steps

1. Phase 1 diagnosis (done, reported in conversation).
2. Phase 2, E1/E2 decision-stage experiments: design in [`docs/E1_E2_DESIGN.md`](docs/E1_E2_DESIGN.md).
   **Status: run `e1e2_v1` done; results in [`docs/E1_E2_RESULTS.md`](docs/E1_E2_RESULTS.md) (student checks pending).**
3. E2b, comparability addition D1c: [`docs/E2b_COMPARABILITY.md`](docs/E2b_COMPARABILITY.md). Run `e2b_v1` done; **D1 kept**.
   Targeted student review sheet: [`review/E2_REVIEW_SHEET.md`](review/E2_REVIEW_SHEET.md).
4. Reproducibility audit of the D1 batch-to-batch variation: [`docs/REPRODUCIBILITY_AUDIT.md`](docs/REPRODUCIBILITY_AUDIT.md).
5. E5, D1 inside the tool loop: [`docs/E5_PLAN.md`](docs/E5_PLAN.md). Run `e5_v1` done; results in
   [`docs/E5_RESULTS.md`](docs/E5_RESULTS.md) (student checks pending).
6. Phase 4 (reduced): held-out test of the V2 fix. Design [`docs/PHASE4_DESIGN.md`](docs/PHASE4_DESIGN.md);
   benchmark built, validated and **frozen** ([`docs/PHASE4_BENCHMARK.md`](docs/PHASE4_BENCHMARK.md)); TEST inference not run.
