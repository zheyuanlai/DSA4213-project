# Phase 4 held-out benchmark: construction, validation and freeze

**Status: FROZEN 2026-10-25** (`v2/benchmarks/freeze_manifest.json`; `python v2/scripts/phase4_freeze.py --check` → OK).
No verifier has been run on these items.

## 1. Procedure as run

| Step | What happened | Cost (V2 judge ledger) |
|---|---|---|
| Spec | `v2/benchmarks/phase4_pairs_spec.json` (8 pair types, U/U2 pattern assignments) + `v2/prompts/phase4_author.md` | none |
| Authoring r1 | GPT-5.6 (`openai/gpt-5.6-sol`, reasoning medium) authored 8 pairs. Deterministic checks passed for all 8 after a checker fix (below) | $0.78 |
| Blind validation r1 | Claude Sonnet 5.5 (`anthropic/claude-sonnet-5.5`) judged 50 items, blind to the intended levels, using V1's judge label definitions verbatim: **38/50 agree** | $0.18 |
| Revision r2 | The 6 pairs with disputes were sent back to the author once, with the reader's labels and reasons | $0.52 |
| Re-validation r2 | Revised pairs re-validated; r1 results kept for P2 and P7: **40/50 agree**. The 10 still disputed are **dropped** (20%, below the 25% stop rule) | $0.13 |
| Freeze | Public items and cases in `v2/benchmarks/test_v2/`; gold in `v2/private/phase4/gold.json` (gitignored; SHA-256 in the manifest); hashes of the 23 files the run and the scoring depend on | none |
| **Total** | OpenRouter key usage reconciles: V1 $1.22 + V2 experiments $0.21 + Phase 4 authoring/validation $1.61 = $3.03 | **$1.61** |

**Checker fix before validation.** The pair check first flagged 4 pairs whose decisive evidence was given as a whole
table (`T1`) as "identical in both members", because it compared only the table caption. It now compares every item
under the ID. Re-checking the stored pairs needed no model calls. The 4 automatic repair turns already spent on these
pairs are included in the cost above.

## 2. Final composition (40 items, 8 pairs, 16 packages)

| Expected decision | Items | Pairs contributing |
|---|---|---|
| STRENGTHEN | **12** | P1 (CI-only significance), P2 (adjusted significance), P3 (consistency with ties), P5 (throughput), P6 (robustness), P7 (negative result); 2 each |
| ACCEPT | **18** | every pair |
| WEAKEN | **6** | S on level-1 partners (P2–P7) |
| REMOVE (or WEAKEN) | **4** | P1 (S on partner), P8 (U, U2, S on partner) |

Subgroups among the 12 STRENGTHEN items:

* **8** use a weakening pattern not used in the DEV probes (text-based rule in `phase4_freeze.py`);
* **6** understate a claim that needs **no statistical test** (P3, P5, P6).

## 3. Validation findings (for the report)

**Dropped items (10).** Each is listed with the reader's label against the intended decision.

| Item | Intended | Reader | Reading |
|---|---|---|---|
| P1-U-partner, P1-U2-partner | REMOVE/WEAKEN | SUPPORTED | A hedged, descriptive "higher observed mean" is not an overstatement when the CI includes 0 |
| P3-U-partner, P3-U2-partner | ACCEPT | UNDERSTATED | The revised wording understates "4 wins and 1 tie" |
| P6-U-partner, P6-U2-partner | ACCEPT | UNDERSTATED | The revised wording became too weak for the partner |
| P4-U-strong, P4-U2-strong | STRENGTHEN | UNDERSTATED, same_proposition = false | The drafts rest on parameter counts (a proxy); correcting them would add a different fact |
| P8-U-strong, P8-U2-strong | STRENGTHEN | UNDERSTATED, same_proposition = false | The revised drafts bundle a second claim |

**A definitional finding.** V1's own judge rubric (`annotation/ai_extended/prompts/verify.md`) counts an *explicit hedge*
as understatement. It does **not** count *omitting* strength details, such as a purely descriptive comparison when a
significant test exists, or an attribution without its magnitude: "not mentioning a stronger conclusion elsewhere is
not an understatement". V1's benchmark level scale (`docs/BENCHMARK_SPEC.md`) treats both as weaker forms.

Round-1 disputes on P1-U and P8-U/U2 came from this divergence. The revisions resolved them by making the drafts overtly
hedged. As a result, **the frozen STRENGTHEN items are explicit-hedge understatements; omission-type understatements
are not represented.**

This also bears on the DEV results. DEV's SIG-U ("higher mean BLEU" with a significant test) and CIT-U were gold
STRENGTHEN under the level scale, but would be SUPPORTED under the judge rubric.

**Wording side effect.** The revisions made some drafts more explicit and less natural, for example "Descriptively, … without
implying established superiority" and "… robust to some extent, meeting the threshold at three or more of the four
severities".

## 4. Separation and its limits

* **Author.** GPT-5.6 never saw a verifier prompt, the DEV probes or any verifier output. It did see the reader's labels
  and reasons during the one revision round.
* **Validator.** Claude Sonnet 5.5 never saw intended levels or expected decisions.
* **Overlap.** GPT-5.6 is also Judge A for revisions, and Claude (Haiku) is Judge B.
* **Coordinating agent.** It wrote the spec and the verifier. It did not edit any item by hand.
* **No student validation.** Gold rests on AI authoring, AI validation and deterministic checks.

## 5. Next stage (not started; awaiting approval)

* **TEST inference.** V1 C4 (`D0-tools-800`), V2 C4 (`D1-tools`), V2 C5 (`D1-tools-C5`) on 40 items × 3 interleaved repeats
  = 360 runs. By E5's per-run cost this is about **$0.14 and about 30 min** (V2 experiment ledger, new stage
  `v2_phase4`).
* **Judging.** Distinct revised sentences only, about 60–100 expected. Grouped by package, that is at most 16 calls
  each for Judge A (GPT-5.6) and Judge B (Haiku), plus adjudications: about **$0.6–1.2** on the judge ledger (frozen stage
  cap $1.50).
* **Commands** (run `phase4_freeze.py --check` first):

```bash
python v2/scripts/run_e1_e2.py --run-tag p4_test_v1 --real --family phase4 --stage v2_phase4 --stage-cap 1.0 \
  --probes v2/benchmarks/test_v2/items.json --cases v2/benchmarks/test_v2/cases.jsonl --split test \
  --conditions D0-tools-800,D1-tools,D1-tools-C5
python v2/scripts/phase4_judge.py --run-dir v2/outputs/phase4/p4_test_v1
python v2/scripts/phase4_score.py --run-dir v2/outputs/phase4/p4_test_v1
```

* **Backup.** `v2/private/` (the gold and authoring/validation records) is not in git. It should be backed up before the
  run.
