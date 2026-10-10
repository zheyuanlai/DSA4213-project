# Exploratory Long-Package Diagnostic (separate from the primary study)

**Status:** design frozen before any diagnostic call (this file and `benchmarks/diagnostic_hashes.json` were committed
first). It is **exploratory**. It is not one of the pre-registered hypotheses' primary tests, and it never replaces or mixes with
the 32-case primary TEST split.

## Motivation
The proposal anticipated that short packages (1–2 tables) might let a fixed-checklist verifier check everything cheaply,
which would hide any benefit of adaptive tool selection (H3). This diagnostic uses **long** packages: 3–5 results tables,
several experiments, and 2–4 cited passages that are mostly realistic but irrelevant. Only one or two evidence items decide the focal claim.

## Frozen design
* **Cases:** 8 original synthetic cases `LONG-01…08` (`data/diagnostic/long.jsonl`, sha256 in `benchmarks/diagnostic_hashes.json`).
  Categories: SIG×2, ROB, GEN, CON×2, EFF, CIT. Gold: four ℓ=2, two ℓ=1, two ℓ=0, kept in `private/gold/diagnostic_gold.jsonl`.
  The cases were written by a subagent to the same rules as `docs/BENCHMARK_SPEC.md` and validated with the same consistency checks.
* **Conditions:** C7 (shared outline draft, no verification), C3 (scripted fixed-order verifier) and C4 (adaptive verifier).
  All three share the identical outline draft per case.
* **Configuration:** `configs/amended_secondary.yaml`, cost stage `buffer`, run tag `diag_v2`, output family `diagnostic`.
  **Amendment (2026-10-10 ~12:12 UTC, before any diagnostic call):** the originally frozen choice was `configs/frozen_primary.yaml`
  with run tag `diag_v1`. During the real-paper run, the frozen 700-token outline limit truncated outlines on several long real-paper
  packages. All three diagnostic conditions depend on the outline, and these packages are even longer, so the diagnostic uses the amended config.
  It is identical except for the generation `max_tokens` limits (writer 1200, outline 1500, reviser 1200, instead of 700 each). No diagnostic output was produced under the original choice: the input file was
  temporarily withheld so that the queued `diag_v1` command failed before making any call.
* **Outcomes (automatic):** evidence-tool calls per claim, model calls, tokens, latency, billed cost, decision distribution,
  share of passages changed from the draft, numeric grounding, and the C4 tool trajectories (first tool, sequences, early stopping).
  Expected direction (not a pre-registered hypothesis): C4 uses fewer tool calls than C3 at similar outcomes.
* **Outcomes (PROXY, unvalidated):** lexical strength proxy vs gold, reported only in aggregate and labelled PROXY.
* **Human labels:** none planned in the primary annotation packet. If the group wants them, the same packet tooling can be run on these outputs later.
