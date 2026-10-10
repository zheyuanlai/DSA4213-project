# Instructions for the Two Blind Annotators

Two group members annotate **independently**. The coordinator, who holds the private
system mapping, should **not** be one of the two annotators if that can be avoided.

## 0. Before you start
1. Read `ANNOTATION_GUIDE.md` from start to finish.
2. Work through `demo_example_NOT_TEST.md`. It uses DEV cases only and contains no held-out answers or system identities.
3. Agree with your partner on the guide, but **never discuss specific TEST items** until both files are submitted.

## 1. What to open
| You are | Your sheet (copy it, then fill in the copy) | Viewer (read-only, same order) |
|---|---|---|
| Annotator A | `annotator_A_template.csv` | `viewer_annotator_A.html` |
| Annotator B | `annotator_B_template.csv` | `viewer_annotator_B.html` |
| Real-paper study (both) | `annotator_{A,B}_real_template.csv` + `annotator_{A,B}_real_sentences_template.csv` | `viewer_annotator_{A,B}_real.html` |

Each row gives an `output_id`, a `case_id`, and the passage text. The case's research package and rubric are in
`packages_synthetic/<case_id>.md` (or `packages_real/<case_id>.md`). The viewer embeds them too.

## 2. How to stay blind
* Do **not** open `outputs/`, `private/`, `results/`, `docs/AUTOMATIC_RESULTS.md`, `prompts/`, `src/`, or any run log.
  These reveal which system produced which text. Ideally the coordinator gives you a copy of only the `annotation/` folder.
* Do **not** open `data/synthetic/gold/` or any `*gold*` file. DEV gold is used only in the demo example.
* `output_id`s are random. Identical texts produced by different systems appear **once**, so you cannot tell how many
  systems produced a text, or which ones.
* Rows are in a random order that differs between A and B. Don't sort by `case_id` while labelling.

## 3. Ambiguity
Apply the tie-breaking rules in Guide §6. If still unsure: choose the lower level, set `confidence = low`, and
quote the deciding phrase in `notes`. Do not ask your partner about a specific item.

## 4. Time
We have **no measured estimate** of how long annotation takes. Please record your total time (and number of
sessions) in a line at the bottom of your notes so it can be reported in the final report.

## 5. What to submit
* Your completed CSV(s), with the same columns and **all rows**, renamed to `annotator_A.csv` / `annotator_B.csv`
  (and `annotator_A_real.csv`, `annotator_A_real_sentences.csv`, etc.). Hand them to the coordinator.
* Do not edit the `output_id`, `case_id` or `output_text` columns.

## 6. After both files are in (coordinator)
```bash
python -m evaluation.merge_annotations --a annotation/completed/annotator_A.csv --b annotation/completed/annotator_B.csv \
  --rubric data/synthetic/rubrics/test_rubric.jsonl --packet annotation/blinded_synthetic.csv --out annotation/agreement
```
This validates both files, computes Cohen's κ (unweighted, plus linear and quadratic weighted for the 0/1/2 level) and item-level κ for checklists, and writes
`annotation/agreement/adjudication_synthetic.csv` listing every disagreement. Both annotators then adjudicate together, still blind
to system identity. They fill `adjudicated_value` (use `NONE` for an empty value) and a short `rationale`. Then:
```bash
python -m evaluation.merge_annotations ... --adjudicated annotation/agreement/adjudication_synthetic.csv
python -m evaluation.score_human --consensus annotation/agreement/consensus_synthetic.csv \
  --mapping private/condition_mapping.csv --gold private/gold/test_gold.jsonl \
  --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 --out results/human_scored
```
Only after this step are the system identities unblinded, by the scoring script.
