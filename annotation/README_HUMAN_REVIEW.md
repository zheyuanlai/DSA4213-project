# Instructions for the Two Blind Annotators

> **Four-person workflow (2026-10-15):** if you received a personal package (`README_<ID>_<Name>.md`), follow that
> file instead of this one. Coordinator: `annotation/four_person/README_COORDINATOR.md`.

Two group members annotate **independently**. The coordinator, who holds the private
system mapping, should **not** be one of the two annotators if that can be avoided.

## 0. Before you start
1. Read `ANNOTATION_GUIDE.md` from start to finish.
2. Work through `demo_example_NOT_TEST.md`. It uses DEV cases only and contains no held-out answers or system identities.
3. Agree with your partner on the guide, but **never discuss specific TEST items** until both files are submitted.

## 1. What to open (two passes)
| Step | Annotator A | Annotator B |
|---|---|---|
| **Pass 1** (levels, unsupported claims, numeric errors) | `pass1/annotator_A_pass1.csv` + `pass1/viewer_annotator_A_pass1.html` | `pass1/annotator_B_pass1.csv` + `pass1/viewer_annotator_B_pass1.html` |
| **Pass 2** (checklists): only after submitting pass 1 | `pass2/annotator_A_pass2.csv` + `pass2/viewer_annotator_A_pass2.html` | `pass2/annotator_B_pass2.csv` + `pass2/viewer_annotator_B_pass2.html` |
| **Real-paper study** (single pass) | `real/annotator_A_real.csv`, `real/annotator_A_real_sentences.csv`, `real/viewer_annotator_A_real.html` | same with `B` |

Each row gives an `output_id`, an opaque case alias `case_ref`, and the passage. The package for each alias is in
`<pass>/packages/<case_ref>.md` (the viewer embeds it). Copy your sheet before filling it, and keep all columns and rows.

## 2. How to stay blind
* Ideally the coordinator gives you **only the folders you need**: first `annotation/pass1/` with the guide, README and demo file,
  then `annotation/pass2/` after your pass-1 sheet is submitted, then `annotation/real/`. Please don't work from a full clone of the repository.
* If you do have the repository, **do not open**: `outputs/`, `private/`, `results/`, `data/` (it contains case IDs, rubrics and DEV gold),
  `benchmarks/`, `docs/` (including `BENCHMARK_SPEC.md`, which describes the pair design, and `AUTOMATIC_RESULTS.md`), `prompts/`, `src/`, `report/`,
  or any run log. Do not open `annotation/pass2/` before submitting pass 1.
* `output_id`s are random. Identical texts produced by different systems appear **once**, so you cannot tell how many
  systems produced a text, or which ones.
* Rows are in a random order that differs between A and B and between passes. Don't sort by `case_ref` while labelling.

## 3. Ambiguity
Apply the tie-breaking rules in Guide §6. If still unsure: choose the lower level, set `confidence_p1 = low`, and
quote the deciding phrase in `notes_p1`. Do not ask your partner about a specific item.

## 4. Time
We have **no measured estimate** of how long annotation takes. Please record your total time (and number of
sessions) in a line at the bottom of your notes so it can be reported in the final report.

## 5. What to submit
* `annotator_A_pass1.csv` (then later `annotator_A_pass2.csv`) and the real-paper sheets, with **all rows** and unchanged
  `output_id`, `case_ref` and text columns. Hand them to the coordinator, who stores them in `annotation/completed/`.

## 6. After both annotators have submitted (coordinator)
```bash
python -m evaluation.merge_annotations \
  --a annotation/completed/annotator_A_pass1.csv,annotation/completed/annotator_A_pass2.csv \
  --b annotation/completed/annotator_B_pass1.csv,annotation/completed/annotator_B_pass2.csv \
  --packet annotation/blinded_synthetic.csv --alias-map private/case_alias_map.csv \
  --rubric data/synthetic/rubrics/test_rubric.jsonl --out annotation/agreement
```
This validates both files, computes Cohen's κ (unweighted, plus linear and quadratic weighted for the 0/1/2 level) and item-level κ for checklists, and writes
`annotation/agreement/adjudication_synthetic.csv` listing every disagreement. Both annotators adjudicate together, still blind
to system identity. They fill `adjudicated_value` (use `NONE` for an empty value) and a short `rationale`. Then:
```bash
python -m evaluation.merge_annotations ...same args... --adjudicated annotation/agreement/adjudication_synthetic.csv
python -m evaluation.score_human --consensus annotation/agreement/consensus_synthetic.csv \
  --mapping private/condition_mapping.csv --gold private/gold/test_gold.jsonl \
  --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 --out results/human_scored
```
Real-paper study:
```bash
python -m evaluation.score_real_papers merge \
  --a annotation/completed/annotator_A_real.csv,annotation/completed/annotator_A_real_sentences.csv \
  --b annotation/completed/annotator_B_real.csv,annotation/completed/annotator_B_real_sentences.csv --out annotation/agreement_real
python -m evaluation.score_real_papers merge ...same args... --adjudicated annotation/agreement_real/adjudication_real.csv
python -m evaluation.score_real_papers score --consensus-outputs annotation/agreement_real/consensus_real_outputs.csv \
  --consensus-sentences annotation/agreement_real/consensus_real_sentences.csv --mapping private/condition_mapping_real.csv
```
Only the scoring scripts unblind system identities, through the private mappings. They refuse to score if any completed output lacks a label.
