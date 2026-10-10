# Human Blind-Review Handoff

**Status: AWAITING BLIND HUMAN ANNOTATION BY GROUP MEMBERS.** No human labels exist yet. No human agreement
(κ) has been computed. No calibration result in this repository is human-validated.

## 1. What was completed automatically
| Item | Planned | Completed |
|---|---|---|
| Benchmark cases | 48 (16 DEV / 32 TEST) | 48, validated (`benchmarks/validate.py`) |
| Primary synthetic outputs (7 conditions × 32 TEST) | 224 | **224 completed**, 0 failed (`primary_v1`, frozen protocol) |
| Real papers | 10–15 | 12 (CC BY / CC BY-SA, licences re-verified) |
| Real-paper outputs (C1–C4 × 12) | 48 | `real_v1` (frozen limits): 35. `real_v2` (amended token limits, all re-run): **46**, with RP-02 C3/C4 failed |
| Long-package diagnostic (exploratory, C7/C3/C4 × 8) | optional | 24 completed (`diag_v2`) |
| Synthetic annotation rows | one per distinct text | **122** (from 224 runs; identical texts merged) in two passes |
| Real-paper annotation rows | one per distinct text | **39** outputs / **151** sentences (from the 46 `real_v2` outputs) |
| Human labels | 2 annotators | **none yet** |

Automatic results: `docs/AUTOMATIC_RESULTS.md`. Audit: `docs/FINAL_AUDIT.md`. Total OpenRouter spend: $0.6978 (reconciled).


## 2. Files for the annotators (hand out folder by folder, not the whole repository)
| Stage | Give the annotator | Contents |
|---|---|---|
| Training | `annotation/ANNOTATION_GUIDE.md`, `annotation/README_HUMAN_REVIEW.md`, `annotation/demo_example_NOT_TEST.md` | definitions, rules, DEV-only examples |
| Pass 1 | `annotation/pass1/` (their own `annotator_X_pass1.csv`, `viewer_annotator_X_pass1.html`, `packages/`) | expressed level, focal addressed, unsupported claims, numeric errors; packages show the focal proposition and descriptors, with **no checklists** |
| Pass 2 (only after pass 1 is submitted) | `annotation/pass2/` | coverage checklists (required findings, NUM facts, NEG findings) |
| Real papers | `annotation/real/` (`annotator_X_real.csv`, `annotator_X_real_sentences.csv`, viewer, `packages/`) | sentence-level support labels, readability, overall calibration |

Coordinator-only reference copies: `annotation/blinded_synthetic.csv`, `annotation/real/blinded_real_papers*.csv`, `annotation/adjudication_template.csv`.

## 3. Coordinator-only private artifacts (NOT in GitHub; back these up securely now)
* `private/condition_mapping.csv`, `private/condition_mapping_real.csv`, `private/case_alias_map.csv`: output_id → case alias → case → condition → run_id (+ text sha256).
* `private/packet_meta_*.json`: shuffle seeds and packet counts.
* `private/gold/test_gold.jsonl` (sha256 frozen in `benchmarks/freeze_manifest.json`), `private/gold/diagnostic_gold.jsonl`.
* `private/benchmark_source/`, `private/diagnostic_source/`: authored cases with gold.
* `outputs/synthetic/`, `outputs/real_papers/`, `outputs/real_papers_v2/`: raw run records, withheld from git because they reveal text → condition.
  Their sha256 values are in `outputs/WITHHELD_UNTIL_ANNOTATION.json`.
* `private/auto_eval/`: per-run automatic rows (contain TEST gold levels).
If the private mapping is lost, the human labels cannot be attributed to conditions. Keep at least two copies outside GitHub.

## 4. Remaining human-only steps
1. Two group members annotate independently (see `annotation/README_HUMAN_REVIEW.md`). They record their time.
2. Coordinator runs `python -m evaluation.merge_annotations ...` (validation, κ, disagreement sheet).
3. Both annotators adjudicate disagreements, still blind to condition.
4. Coordinator runs `python -m evaluation.merge_annotations ... --adjudicated ...`, then `python -m evaluation.score_human ...`
   (unblinding happens inside the scoring script via the private mapping), and `python -m evaluation.score_real_papers merge/score` for the real-paper study.
   Exact commands are in `annotation/README_HUMAN_REVIEW.md` §6.
5. All four students confirm actual contribution shares (summing to 100%) and write the final report and presentation.
   AI assistants are not group members.

## 5. Release after annotation (coordinator)
1. Copy `private/gold/test_gold.jsonl` to `data/synthetic/gold/test_gold.jsonl` and confirm its sha256 equals `gold_test_PRIVATE` in `benchmarks/build_hashes.json`.
2. Remove the "withheld until blind annotation ends" lines from `.gitignore` and `src/security_scan.py`. Run
   `python scripts/withheld_manifest.py --verify` (all files must match), then commit `outputs/synthetic/`, `outputs/real_papers/` and `outputs/real_papers_v2/`, and
   move `private/auto_eval/TEST_edit_examples.md` into `docs/`.
3. Optionally commit `private/condition_mapping*.csv` as `annotation/condition_mapping_RELEASED.csv`, with the human results.
4. Run `python scripts/security_check.py` before pushing.
