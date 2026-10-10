# Saying What the Evidence Shows

**Overstatement and Understatement in Agent-Written Results Sections**
DSA4213 *Natural Language Processing for Data Science* (NUS, Sem 1 AY2026/27), Group 5. This is a private repository.

> **Status: technical work complete through automatic evaluation; AWAITING BLIND HUMAN ANNOTATION
> by group members.** 224/224 primary outputs, 46/48 real-paper outputs and 24/24 diagnostic outputs exist, and the blind packets are built.
> Total OpenRouter spend is $0.70, reconciled. Human-scored calibration results (H1–H3) do not exist yet. Everything labelled
> PROXY in this repository is an unvalidated automatic heuristic, not a calibration result. Start with
> [`docs/HUMAN_REVIEW_HANDOFF.md`](docs/HUMAN_REVIEW_HANDOFF.md), [`docs/AUTOMATIC_RESULTS.md`](docs/AUTOMATIC_RESULTS.md) and [`docs/FINAL_AUDIT.md`](docs/FINAL_AUDIT.md).

## What this is

Researchers have already run their experiments. An LLM gets a *research package* (question, setup,
exact result tables, statistical-test metadata, quoted cited passages) and writes a short
Results/Discussion passage. We study whether **claim-by-claim, tool-grounded evidence
verification** calibrates claim strength in **both directions**: reducing overstatement (e.g.
"significantly" with no test, "consistently" from 4/5 wins, robustness or speed claims beyond the
evidence) **without** causing understatement. The comparison is against direct generation and a
generic writer–reviewer loop.

* **Benchmark:** 48 original synthetic cases (8 categories × 6; 16 DEV / 32 TEST, built as matched pairs).
  Gold rules are in [`docs/BENCHMARK_SPEC.md`](docs/BENCHMARK_SPEC.md). TEST gold stays coordinator-private until annotation is finished. Its hash is frozen in `benchmarks/freeze_manifest.json`.
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
python -m benchmarks.validate --source private/benchmark_source   # coordinator only (needs private source)
```

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
| `outputs/` | DEV-pilot and diagnostic run records, job manifests, cost ledger + reconciliation (no secrets). TEST and real-paper raw records are withheld until annotation ends (sha256 in `outputs/WITHHELD_UNTIL_ANNOTATION.json`) |
| `evaluation/` | automatic metrics, paired bootstrap, blinding, merge/κ, human scoring |
| `annotation/` | guide, instructions, DEV-only training example; `pass1/`, `pass2/` (synthetic, two passes), `real/` (real papers): blinded packets, empty A/B sheets, viewers |
| `results/automatic/` | automatic and PROXY results (aggregate only) |
| `docs/` | plan, progress, protocol freeze, model selection, deviations, automatic results, handoff, audit |

## Human annotation (next step, by group members)

See [`annotation/README_HUMAN_REVIEW.md`](annotation/README_HUMAN_REVIEW.md) and
[`docs/HUMAN_REVIEW_HANDOFF.md`](docs/HUMAN_REVIEW_HANDOFF.md). The map from output IDs to conditions
(`private/condition_mapping.csv`) is **not** in this repository. Only the coordinator holds it.

## Credits and AI use

Planned roles from the proposal (*planning context only, not a record of work done*): Li Jiajun (benchmark and annotation protocol),
Xiao Xinkai (evidence store, tools and real-paper packages), Liu Yuxin (writer, verifier and baselines), and Lai Zheyuan (coordination, evaluation and report).
**Actual contribution shares must be confirmed by all four students for the final report.**
AI disclosure: the code, synthetic benchmark drafts, real-paper package extraction and documentation in this repository were produced
with Claude Code (Anthropic) under the coordinator's direction. AI assistants are not group members, and their work does not count as student contribution.
Real-paper excerpts are used under their CC licences ([`data/real_papers/README.md`](data/real_papers/README.md)).
