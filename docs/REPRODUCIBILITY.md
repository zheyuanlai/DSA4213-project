# Reproducibility Guide

The repository supports three levels of reproduction. Each level needs a little more than the one before.

| Level | Who | Needs | What it reproduces |
|---|---|---|---|
| 1. Public checks | anyone with the repository; CI on every push | Python ≥ 3.11 | tests, integrity of frozen inputs, AI annotations and manifests, secret scan |
| 2. Re-derive results | coordinator | `private/` (gold, condition mappings) and the withheld raw outputs | every table, figure and JSON under `results/` from the frozen labels, with no API calls |
| 3. Re-run model calls | coordinator | API access (OpenRouter key; Codex and Claude CLIs) | new generations or new judge calls; these get new run tags or cache salts and never overwrite frozen artifacts |

## Level 1: public checks (also run by CI)

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/verify_artifacts.py
python scripts/security_check.py
```

* The tests are offline and make no API calls. Tests that need coordinator-private gold skip themselves when `private/` is absent.
* `scripts/verify_artifacts.py` reports PASS, FAIL or SKIP for each check:
  * the frozen protocol files match `benchmarks/freeze_manifest.json`, except the documented post-freeze changes listed in
    `docs/DEVIATIONS_FROM_PROPOSAL.md`;
  * the frozen atomic claims (1,591) and the real and long-package checklists match their sha256 files;
  * every consensus manifest (`annotation/ai_extended/**/MANIFEST_*.json`, primary and replicate) matches;
  * no private, withheld or key file is tracked, no OpenRouter key appears in any tracked file, and public results carry no output IDs.

  Checks that need `private/` or the withheld raw outputs print SKIP.
* `scripts/security_check.py` scans the working tree, the index, the full history and the commit messages. When
  `OPENROUTER_API_KEY` is set, it also searches for that live key and its fragments.
* The workflow is `.github/workflows/tests.yml`: Ubuntu, Python 3.11, full history.

## Level 2: re-derive every result from frozen labels (coordinator)

These commands read the coordinator-private condition mappings and the withheld raw run records. They make no model calls.

```bash
python scripts/verify_artifacts.py --regenerate      # all Level-1 checks + gold hashes + withheld-output hashes
                                                     # + re-run score/report/majority/stability and require no git diff
```

The individual stages are:

```bash
python scripts/auto_evaluate.py --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 \
  --cases data/synthetic/test.jsonl --out results/automatic/synthetic_test        # automatic and PROXY metrics
python scripts/ai_annotation_pipeline.py score                                    # multi-agent AI focal annotation
python scripts/run_extended_evaluation.py score                                   # evidence-level metrics (unblinds)
python scripts/run_extended_evaluation.py report                                  # tables, figures, main table
python scripts/run_extended_evaluation.py stability --replicate r1                # adjudicator test–retest
python scripts/run_extended_evaluation.py majority                                # third judge, 2-of-3 majority
```

Every judge call in the evidence-level evaluation is cached by a hash of its full input under
`annotation/ai_extended/raw/`. Re-running `extract`, `verify`, `coverage`, `align` or `adjudicate` therefore returns
the frozen readings without new calls. The consensus files are frozen with sha256 manifests, which
`scripts/verify_artifacts.py` checks.

## Level 3: new model calls

* **Backbone runs** (`scripts/run_experiment.py`, `scripts/run_real_papers.py`) read `OPENROUTER_API_KEY` from the environment
  only. They pass through `src/cost_guard.py`, which enforces a hard cap, per-stage caps and an append-only ledger
  (`outputs/cost_ledger.jsonl`). A new run needs a new run tag and never overwrites the frozen primary outputs.
* **Judge calls** use the Codex CLI (Judge A, adjudicator), the Claude CLI (Judge B) and OpenRouter (Judge C). See
  `docs/EVALUATION_EXTENSION_PROTOCOL.md` §11 and the commands in `docs/EVALUATION_EXTENSION_RESULTS.md` §12. A
  replicate (`--replicate r1`) salts the cache key so that no answer is reused, and writes to its own directory.
* LLM outputs are not bit-reproducible across providers or dates, even at temperature 0. The frozen outputs and labels
  in this repository are the record. Re-running produces a new sample, not a check of the old one.

## What is frozen, and where it is recorded

| Artifact | Record |
|---|---|
| Protocol files, prompts, configs, TEST gold hash | `benchmarks/freeze_manifest.json` (`python scripts/freeze_protocol.py --config configs/frozen_primary.yaml --check`) |
| Diagnostic gold hash | `benchmarks/diagnostic_hashes.json` |
| Withheld TEST and real-paper raw outputs | `outputs/WITHHELD_UNTIL_ANNOTATION.json` |
| Primary-run commit | `04bc5e5`, now `a32d2b5` after a message-only rewrite (`docs/COMMIT_SHA_MAPPING.md`) |
| Atomic claims, checklists, consensus | `annotation/ai_extended/claims/`, `checklists/*.sha256`, `consensus/MANIFEST_*.json` |
| Spend | `outputs/cost_ledger.jsonl`, `outputs/ledger_summary.json`; judge records in `annotation/ai_extended/raw/` |

## Known limits of reproduction

* People without `private/` can verify integrity but cannot re-score by condition, by design: the condition mapping
  would unblind the outputs for any future human audit.
* The Codex CLI calls ran on a subscription and the Claude CLI calls at metered list price. Their model versions are
  recorded per call, but the providers may retire them.
* Python 3.11 and 3.13 were both tested. Bootstrap intervals use NumPy's seeded generator (seed 4213), so a different
  NumPy major version could change the last digit of an interval.
