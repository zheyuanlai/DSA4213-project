# Human Blind-Review Handoff

**Status: AWAITING BLIND HUMAN ANNOTATION BY GROUP MEMBERS.** No human labels exist yet. No human agreement
(κ) has been computed. No calibration result in this repository is human-validated.

## 1. What was completed automatically
COUNTS_PLACEHOLDER

## 2. Files for the annotators (give them ONLY the `annotation/` folder)
| File | Purpose |
|---|---|
| `annotation/ANNOTATION_GUIDE.md` | definitions, 0/1/2 rules per category, omission/flag policy, NUM/NEG rubrics, real-paper labels |
| `annotation/README_HUMAN_REVIEW.md` | step-by-step instructions, blinding rules, what to submit |
| `annotation/demo_example_NOT_TEST.md` | DEV-only training examples (no TEST case, no system identity) |
| `annotation/annotator_A_template.csv`, `annotation/annotator_B_template.csv` | **empty** synthetic sheets; same random IDs, independent random orders |
| `annotation/viewer_annotator_{A,B}.html` | read-only viewers in each annotator's order, with package and rubric embedded |
| `annotation/packages_synthetic/<case>.md` | human-readable package + rubric (no gold level, no justification) |
| `annotation/annotator_{A,B}_real_template.csv`, `..._real_sentences_template.csv`, `viewer_annotator_{A,B}_real.html`, `packages_real/` | real-paper study (output-level readability + sentence-level support) |
| `annotation/blinded_synthetic.csv`, `annotation/blinded_real_papers*.csv` | master packets (coordinator reference; same content, master order) |
| `annotation/adjudication_template.csv` | header for the adjudication sheet (the merge script generates the real one) |

## 3. Coordinator-only private artifacts (NOT in GitHub; back these up securely now)
* `private/condition_mapping.csv` and `private/condition_mapping_real.csv`: output_id → case → condition → run_id (+ text sha256).
* `private/packet_meta_*.json`: shuffle seeds and packet counts.
* `private/gold/test_gold.jsonl` (sha256 frozen in `benchmarks/freeze_manifest.json`), `private/gold/diagnostic_gold.jsonl`.
* `private/benchmark_source/`, `private/diagnostic_source/`: authored cases with gold.
* `outputs/synthetic/`, `outputs/real_papers/`: raw run records, withheld from git because they reveal text → condition.
  Their sha256 values are in `outputs/WITHHELD_UNTIL_ANNOTATION.json`.
* `private/auto_eval/`: per-run automatic rows (contain TEST gold levels).
If the private mapping is lost, the human labels cannot be attributed to conditions. Keep at least two copies outside GitHub.

## 4. Remaining human-only steps
1. Two group members annotate independently (see `annotation/README_HUMAN_REVIEW.md`). They record their time.
2. Coordinator runs `python -m evaluation.merge_annotations ...` (validation, κ, disagreement sheet).
3. Both annotators adjudicate disagreements, still blind to condition.
4. Coordinator runs `python -m evaluation.merge_annotations ... --adjudicated ...`, then `python -m evaluation.score_human ...`
   (unblinding happens inside the scoring script via the private mapping), and the equivalent for the real-paper study.
5. All four students confirm actual contribution shares (summing to 100%) and write the final report and presentation.
   AI assistants are not group members.

## 5. Release after annotation (coordinator)
1. Copy `private/gold/test_gold.jsonl` to `data/synthetic/gold/test_gold.jsonl` and confirm its sha256 equals `gold_test_PRIVATE` in `benchmarks/build_hashes.json`.
2. Remove the "withheld until blind annotation ends" lines from `.gitignore` and `src/security_scan.py`. Run
   `python scripts/withheld_manifest.py --verify` (all files must match), then commit `outputs/synthetic/` and `outputs/real_papers/`.
3. Optionally commit `private/condition_mapping*.csv` as `annotation/condition_mapping_RELEASED.csv`, with the human results.
4. Run `python scripts/security_check.py` before pushing.
