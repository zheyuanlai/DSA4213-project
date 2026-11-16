# Saying What the Evidence Shows

**Overstatement and Understatement in Agent-Written Results Sections**

DSA4213 *Natural Language Processing for Data Science* (NUS, Sem 1 AY2026/27), Group 5. This is a private repository.

## What this is

Researchers have already run their experiments. An LLM gets a *research package* (question, setup,
exact result tables, statistical-test metadata, quoted cited passages) and writes a short
Results/Discussion passage. We study whether **claim-by-claim, tool-grounded evidence
verification** calibrates claim strength in **both directions**: reducing overstatement (e.g.
"significantly" with no test, "consistently" from 4/5 wins, robustness or speed claims beyond the
evidence) **without** causing understatement. The comparison is against direct generation and a
generic writer–reviewer loop.

* **Benchmark:** 48 original synthetic cases (8 categories × 6; 16 DEV / 32 TEST, built as matched pairs).
  Gold rules are in [`docs/BENCHMARK_SPEC.md`](docs/BENCHMARK_SPEC.md). TEST gold stays coordinator-private. Its hash is frozen in `benchmarks/freeze_manifest.json`.
* **Agent:** deterministic evidence store and four tools (`lookup_table`, `get_test_metadata`,
  `retrieve_passage`, `compare_numbers`). A finite-state verifier makes ACCEPT / WEAKEN / STRENGTHEN / REMOVE / FLAG decisions per sentence-level claim.
* **Seven conditions** run through one shared pipeline (`src/conditions.py`):

| | Condition | Starts from | Post-draft step |
|---|---|---|---|
| C1 | Direct generation | direct draft | none |
| C2 | Writer–reviewer loop | direct draft | generic critique + revision |
| C3 | Scripted verifier | outline draft | tool checks in a **fixed** order (strengthen allowed) |
| C4 | Full agent | outline draft | **adaptive** tool checks (strengthen allowed) |
| C5 | No strengthening | outline draft | adaptive tool checks (**no** STRENGTHEN) |
| C6 | No outline | direct draft | adaptive tool checks (strengthen allowed) |
| C7 | Outline only | outline draft | none |

  C3/C4/C5/C7 share the identical outline+draft per case, and C1/C2/C6 share the identical direct draft.
  So C4 vs C5 isolates STRENGTHEN, C4 vs C3 isolates adaptive tool selection, and C4 vs C7 isolates verification.
* **Backbone (evaluated model):** one pinned OpenRouter model for every condition,
  `deepseek/deepseek-v4-flash-0731`, temperature 0, reasoning off
  ([`docs/MODEL_SELECTION.md`](docs/MODEL_SELECTION.md)). Claude Code was used only to build and orchestrate the project.
  It is **not** the evaluated model.

## Quick start

```bash
pip install -r requirements.txt          # Python >= 3.11
python -m pytest                         # offline tests; no API calls
python scripts/verify_artifacts.py       # frozen inputs, AI annotations and manifests are intact
python scripts/security_check.py         # secret and privacy scan of tree, index and history
python -m benchmarks.validate --source private/benchmark_source   # coordinator only (needs private source)
```

The first three checks run in CI on every push (`.github/workflows/tests.yml`). The coordinator can re-derive every
result from the frozen labels with `python scripts/verify_artifacts.py --regenerate`. See
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

Offline dry run of the whole pipeline with the deterministic mock model. It is free, and its outputs are flagged `is_mock` and written to `outputs/_mock/`:

```bash
python scripts/run_experiment.py --config configs/frozen_primary.yaml --cases data/synthetic/dev.jsonl \
  --family dev --run-tag mock_demo --stage dev --mock --case-ids SIG-p1a,NEG-p1a
```

Real runs read the key **only** from the environment (`export OPENROUTER_API_KEY=...`; see `.env.example`).
Re-running the same command resumes; completed and failed jobs are never silently re-run:

```bash
python scripts/run_experiment.py --config configs/frozen_primary.yaml --cases data/synthetic/test.jsonl \
  --family synthetic --run-tag primary_v1 --stage main --workers 2
python scripts/auto_evaluate.py --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 \
  --cases data/synthetic/test.jsonl --out results/automatic/synthetic_test
```

The real-paper study (`scripts/run_real_papers.py`) and the diagnostic were run with `configs/amended_secondary.yaml`.
This config is identical to the frozen one except for higher generation token limits; see `docs/DEVIATIONS_FROM_PROPOSAL.md`.

Every call goes through `src/cost_guard.py`: a hard cap of $12, per-stage caps, an append-only ledger at `outputs/cost_ledger.jsonl`, and at most 2 requests in flight.

## Repository map

| Path | Contents |
|---|---|
| `src/` | schemas, evidence store, tools, OpenRouter client + mock, cost guard, writer, verifier, conditions, runner |
| `prompts/` | versioned prompts (hashes are stored in every run record) |
| `benchmarks/` | gold/authoring schema, validator, build script, freeze manifest |
| `data/synthetic/` | public packages (`dev.jsonl`, `test.jsonl`), annotator rubrics, DEV gold |
| `data/real_papers/` | 12 CC BY / CC BY-SA arXiv-derived packages (method names aliased) + manifest + licences |
| `data/diagnostic/` | 8 exploratory long-package cases (gold private) |
| `outputs/` | DEV-pilot and diagnostic run records, job manifests, cost ledger + reconciliation (no secrets). TEST and real-paper raw records stay withheld from git because they reveal which condition wrote each text (sha256 in `outputs/WITHHELD_UNTIL_ANNOTATION.json`) |
| `evaluation/` | automatic metrics, paired bootstrap, blinding, merge/κ, human scoring |
| `annotation/` | guide and blinded human-review packets; separate AI-only labels and consensus under `annotation/ai/` |
| `results/` | automatic/PROXY results plus explicitly AI-scored exploratory results under `results/ai_*` (evidence-level extension in `results/ai_extended/`) |
| `docs/` | results, protocols, deviations, reproducibility guide and audit; index in [`docs/README.md`](docs/README.md) |
| `report/` | final report and verified BibTeX |
| `.github/workflows/` | CI: tests, artifact integrity, secret scan |
