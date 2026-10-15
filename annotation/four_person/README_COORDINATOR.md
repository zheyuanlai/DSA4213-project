# Four-person annotation workflow — coordinator guide

This folder implements the amendment in [`docs/AMENDMENT_FOUR_PERSON_ANNOTATION.md`](../../docs/AMENDMENT_FOUR_PERSON_ANNOTATION.md):
two independent annotator pairs, each double-annotating a disjoint half of the human-evaluation data.
The frozen experiment, the original blinded packets (`annotation/blinded_synthetic.csv`, `annotation/pass1|pass2|real/`),
the private mappings, the TEST gold and the original scoring code are **reused unchanged**. The original two-person
workflow (`annotation/README_HUMAN_REVIEW.md`) still works.

| ID | Name | Team | Partner | Items (each person) |
|---|---|---|---|---|
| A | Zheyuan | AB | B (Yuxin) | 16 TEST cases = 61 synthetic outputs (Pass 1 and Pass 2); 6 papers = 19 paragraphs, 75 sentences |
| B | Yuxin | AB | A (Zheyuan) | same items as A, different row order |
| C | Jiajun | CD | D (Xinkai) | 16 TEST cases = 61 synthetic outputs (Pass 1 and Pass 2); 6 papers = 20 paragraphs, 76 sentences |
| D | Xinkai | CD | C (Jiajun) | same items as C, different row order |

Exact items per team: [`ASSIGNMENT.md`](ASSIGNMENT.md) (annotator-safe; case_ref, category and counts only).

> **Decision needed before Pass 1 is released.** Zheyuan is both coordinator and Annotator A. See §2 below and
> §5 of the amendment. The files are built for the requested A/B/C/D design. Team AB's ratings can only be reported as
> *self-reported blind, not verifiable* at best, and as *potentially non-blind* if Zheyuan's declaration reports any exposure.

All commands run from the repository root. They print only aggregate counts. The exception is `score`, the unblinding step, which is run only after every adjudication is final.

```bash
python -m evaluation.four_person --help
```

---

## 1. Where things are

| Path | What | In git? |
|---|---|---|
| `evaluation/four_person/` | workflow code (assignment, packets, checks, submissions, team merge, combine, report, CLI) | yes |
| `tests/test_four_person_workflow.py` | end-to-end tests on a fake repository with DUMMY labels | yes |
| `annotation/four_person/assignment.json`, `assignment_manifest.csv`, `ASSIGNMENT.md` | the fixed team split (annotator-safe) | yes |
| `annotation/four_person/templates/` | source of the personal instructions (edit these, then `build --force` **before** any release) | yes |
| `annotation/four_person/instructions/` | rendered `README_<ID>_<Name>.md` and `SUBMISSION_CHECKLIST_<ID>_<Name>.md` | yes |
| `annotation/four_person/packets/<ID>_<Name>/{0_training,1_pass1,2_pass2,3_real}/` | each person's stage folders | **no** (gitignored, regenerable) |
| `annotation/four_person/dist/*.zip` | the archives you send (one per person per stage, plus `adjudication_Team*.zip`) | **no** |
| `annotation/four_person/logs/` | `release_log.csv`, `submission_log.csv`, `blinding_declarations.csv` (evidence of the procedure) | commit at the end |
| `private/four_person/assignment_private.csv` | case_ref → case_id → matched pair → team | **no** (coordinator-only) |
| `private/four_person/submissions/<ID>/` | accepted returned files (+ `received/` every version, `superseded/`) | **no** until all adjudication is done |
| `private/four_person/teams/<AB|CD>/` | agreement, disagreement sheets, adjudication, team consensus (contains case_id) | **no** |
| `private/four_person/final/` | combined consensus in the original scoring schema | **no** |
| `results/human_agreement/four_person/` | per-team agreement reports, summary, contribution record (aggregate only) | commit at the end |

Private inputs that are read but never written: `private/case_alias_map.csv`, `private/condition_mapping.csv`,
`private/condition_mapping_real.csv`, `private/packet_meta_*.json`, `private/gold/test_gold.jsonl`.
Their sha256 values are baselined in `private/four_person/private_file_hashes.json`, and `check` fails if any of them changes.

### What needs the private files

All private inputs were present when this workflow was built. Without them:

| Step | Needs |
|---|---|
| `build`, `release`, intake of declaration / Pass 1 / real-paper / time-log files | nothing private (works from the committed `assignment.json`) |
| `assign` (only needed once; already done) | `private/case_alias_map.csv` (matched-pair identity) |
| intake of Pass 2, `agree`, `consensus`, `combine` | `private/case_alias_map.csv` (checklist IDs per case) |
| `combine` acceptance check, `score` | also `private/condition_mapping*.csv` and `private/gold/test_gold.jsonl` |

If a private file is missing, **restore it from your backup. Never rebuild it.** Rebuilding assigns new random IDs and orphans every label.

---

## 2. Blinding decision (do this first)

Every student fills a blinding declaration (`<ID>_<Name>_blinding_declaration.csv`, in the training zip). It has
Q1 TEST gold seen, Q2 output→condition mapping seen, Q3 raw outputs with conditions seen, Q4 label-revealing
automatic scores seen, Q5 access to private files, Q6 discussed such material, and Q7 commitment.
The tool derives a status per person:

| Status | Meaning | Report wording |
|---|---|---|
| `self_reported_blind` | all `no`, no access | blind (self-reported) |
| `self_reported_blind_with_private_access` | all exposure answers `no`, but had access (always the case for A) | "self-reported blind, not verifiable" |
| `potentially_non_blind` | any of Q1–Q4, Q6 answered `yes`/`unsure` | **not** blind; say so |
| `unconfirmed` | no declaration on file | cannot be released Pass 1 |

The AI-assistant session that built this workflow displayed a few private rows on the coordinator's screen. A's README
lists exactly which ones, so the declaration can be precise.

**Options if Zheyuan's declaration shows exposure** (amendment §5):
1. *Keep A/B/C/D (as requested).* Team AB is reported as independent but not fully blind. Also run the blind-member
   sensitivity analysis (§3, step 18b), which scores Team AB's items from Yuxin's independent labels alone.
2. *Scientifically preferable:* Zheyuan stays coordinator only, and Yuxin, Jiajun and Xinkai double-annotate in rotating
   pairs. Every output then gets two blind judgments, at about 2/3 of the data per person instead of 1/2. This needs a
   new 3-pair assignment, so decide **before** any Pass 1 is released.

---

## 3. Step-by-step

### Step 1 — Generate the assignment (once; already done)
```bash
python -m evaluation.four_person assign
```
Re-running recomputes and verifies that the stored assignment is reproduced exactly ("unchanged"). It refuses to
overwrite a different one. `--force` exists only for use before anything is released, and it keeps a backup.

### Step 2 — Verify the assignment manifest
Read `annotation/four_person/ASSIGNMENT.md`, then:
```bash
python -m evaluation.four_person check
```
`check` verifies every invariant:
* **Synthetic:** 32 cases, 16 per team, 2 per category per team, intact matched pairs, no overlap, and the union equals the original 122 outputs.
* **Real papers:** 12 papers, 6 per team, no paper or paragraph split, and the union equals the original 39 paragraphs and 151 sentences.
* **Partners:** each pair has identical item sets in different orders, and each person's Pass 1 and Pass 2 sets are equal.
* **Packets:** packages are byte-identical to the originals; viewers and archives hold only the person's own items; the training and Pass 1 material contains no Pass-2 checklist text.
* **Files:** the private files are unchanged, generated folders are gitignored, released archives are unchanged, and all accepted submissions re-validate.

It must print `ALL CHECKS PASSED`.

### Step 3 — Generate each person's stage files and viewers
```bash
python -m evaluation.four_person build
python -m evaluation.four_person check
```
`build` is deterministic (fixed seed 4213, fixed zip timestamps). If any generated file would change, for example after
a template edit, it stops. Use `build --force` only before anything is released; the old build goes to `_backups/`.

### Step 4 — Distribute the training material
```bash
python -m evaluation.four_person release --who A --stage training
python -m evaluation.four_person release --who B --stage training
python -m evaluation.four_person release --who C --stage training
python -m evaluation.four_person release --who D --stage training
```
Each command re-checks that person's packet, logs the archive's sha256 in `logs/release_log.csv` and prints the
path to send, e.g. `annotation/four_person/dist/B_Yuxin__0_training.zip`. Send each person **only** their own zip, by
private message or e-mail. The DEV examples may be discussed together.

### Step 5 — Collect the blinding declarations
```bash
python -m evaluation.four_person intake --who A --kind declaration --file ~/Downloads/A_Zheyuan_blinding_declaration.csv
python -m evaluation.four_person intake --who B --kind declaration --file ~/Downloads/B_Yuxin_blinding_declaration.csv
python -m evaluation.four_person intake --who C --kind declaration --file ~/Downloads/C_Jiajun_blinding_declaration.csv
python -m evaluation.four_person intake --who D --kind declaration --file ~/Downloads/D_Xinkai_blinding_declaration.csv
python -m evaluation.four_person status
```
Make the §2 decision now.

### Step 6 — Release Pass 1 (only after that person's declaration is accepted)
```bash
python -m evaluation.four_person release --who A --stage pass1   # likewise B, C, D
```

### Step 7 — Validate and collect Pass 1
```bash
# Zheyuan FIRST: take in your own file, post the printed sha256 in the group chat
python -m evaluation.four_person intake --who A --kind pass1 --file ~/Downloads/A_Zheyuan_pass1.csv
# only then ask Yuxin to send hers (the tool refuses B before A)
python -m evaluation.four_person intake --who B --kind pass1 --file ~/Downloads/B_Yuxin_pass1.csv
python -m evaluation.four_person intake --who C --kind pass1 --file ~/Downloads/C_Jiajun_pass1.csv
python -m evaluation.four_person intake --who D --kind pass1 --file ~/Downloads/D_Xinkai_pass1.csv
```
`intake` copies the file byte-for-byte (it never edits a submission) and validates it.

* **Valid files** are accepted as `private/four_person/submissions/<ID>/<ID>_<Name>_pass1.csv`. Every version received is also kept under `received/`.
* **Invalid files** are not accepted: send the printed list back to the student. Validation covers row set, unchanged IDs and text, allowed values, blank level fields for NUM/NEG, and so on.
* **A different file under an already accepted name** is refused. `--replace` supersedes it and keeps the old copy in `superseded/`.

### Step 8 — Release Pass 2 (only after that person's Pass 1 is accepted; the tool enforces this)
```bash
python -m evaluation.four_person release --who A --stage pass2   # likewise B, C, D, each when ready
```
For A this is self-enforced. As coordinator, Zheyuan can open the Pass 2 folders, so he must not do so before Step 7.

### Step 9 — Collect Pass 2
```bash
python -m evaluation.four_person intake --who A --kind pass2 --file ~/Downloads/A_Zheyuan_pass2.csv   # A before B
python -m evaluation.four_person intake --who B --kind pass2 --file ~/Downloads/B_Yuxin_pass2.csv
python -m evaluation.four_person intake --who C --kind pass2 --file ~/Downloads/C_Jiajun_pass2.csv
python -m evaluation.four_person intake --who D --kind pass2 --file ~/Downloads/D_Xinkai_pass2.csv
```

### Step 10 — Release and collect the real-paper annotation
The real-paper stage only requires the declaration; it is recommended after Pass 2.
```bash
python -m evaluation.four_person release --who A --stage real    # likewise B, C, D
python -m evaluation.four_person intake --who A --kind real_outputs   --file ~/Downloads/A_Zheyuan_real_outputs.csv
python -m evaluation.four_person intake --who A --kind real_sentences --file ~/Downloads/A_Zheyuan_real_sentences.csv
# then B (after A), C, D; and at the end every time log:
python -m evaluation.four_person intake --who A --kind timelog --file ~/Downloads/A_Zheyuan_time_log.csv
```

### Step 11 — Validate all completed CSVs
```bash
python -m evaluation.four_person status
python -m evaluation.four_person check
```

### Step 12 — Team AB agreement (A × B, Team AB's subset only)
```bash
python -m evaluation.four_person agree --team AB
```
This re-validates both members' accepted files with the original validators
(`merge_annotations.validate`, `score_real_papers.validate`) and computes agreement with the original functions on
Team AB's items only. It writes:
* `private/four_person/teams/AB/agreement_TeamAB.json` and `agreement_report_TeamAB.md`.
* Copies of the report in `results/human_agreement/four_person/`. The report names the annotator pair, the number of
  overlapping items, each person's blinding status, and every κ; a κ that is 0/0 because of no label variation is shown as *undefined*.
* The disagreement sheets plus an adjudication viewer, zipped as `annotation/four_person/dist/adjudication_TeamAB.zip`.

### Step 13 — Team CD agreement (C × D)
```bash
python -m evaluation.four_person agree --team CD
```

### Step 14 — Send the disagreement sheets
Send `dist/adjudication_TeamAB.zip` to A and B only, and `dist/adjudication_TeamCD.zip` to C and D only. Each bundle
contains only that team's disagreements; matching labels are kept automatically. Each bundle has:
* `adjudication_synthetic_Team*.csv`, with columns `output_id, case_ref, category, field, value_X, value_Y, adjudicated_value, rationale`.
* `adjudication_real_Team*.csv`, with columns `item, case_ref, field, sentence_text, value_X, value_Y, adjudicated_value, rationale`.
* The viewer, showing the texts, both values, both annotators' notes and the research packages.

System identities and gold stay hidden. Write `NONE` for an empty synthetic list; this is the original convention.

### Step 15 — Collect the adjudications and build each team's consensus
```bash
python -m evaluation.four_person consensus --team AB --synthetic ~/Downloads/adjudication_synthetic_TeamAB.csv --real ~/Downloads/adjudication_real_TeamAB.csv
python -m evaluation.four_person consensus --team CD --synthetic ~/Downloads/adjudication_synthetic_TeamCD.csv --real ~/Downloads/adjudication_real_TeamCD.csv
```
The sheets must cover exactly the recomputed disagreements, each with a valid `adjudicated_value` and a `rationale`.
The value columns must match the submissions, which detects stale or edited sheets. Otherwise **nothing is accepted
or written** and the problems are listed, so send them back to the team.

### Step 16 — Team-level consensus (written by Step 15)
The consensus files are built with the original `merge_annotations.consensus()`:
* `private/four_person/teams/<T>/consensus_synthetic_Team<T>.csv`
* `private/four_person/teams/<T>/consensus_real_outputs_Team<T>.csv`
* `private/four_person/teams/<T>/consensus_real_sentences_Team<T>.csv`

`adjudication_summary_Team<T>.json` records how often each annotator's value was chosen. This is useful for reporting
any coordinator influence in Team AB. After adjudication is accepted, `agree` refuses to regenerate the sheets
unless `--force` is given.

### Step 17 — Combine both teams
```bash
python -m evaluation.four_person combine
```
This combines at the **item level** into the exact files and schemas the original scripts read:
* `private/four_person/final/consensus_synthetic.csv` (122 rows)
* `consensus_real_outputs.csv` (39 rows)
* `consensus_real_sentences.csv` (151 rows)

It refuses on any missing, duplicated, extra or invalid label (a blank is an error, never a 0). It then runs the original
`score_human.score` and `score_real_papers.score` in memory to confirm they accept the files.

### Step 18 — Run the original human-scored evaluation (unblinding)
```bash
python -m evaluation.four_person score
```
This is equivalent to the original commands:
```bash
python -m evaluation.score_human --consensus private/four_person/final/consensus_synthetic.csv --mapping private/condition_mapping.csv --gold private/gold/test_gold.jsonl --rubric data/synthetic/rubrics/test_rubric.jsonl --runs outputs/synthetic/deepseek__deepseek-v4-flash-0731 --out results/human_scored
```
```bash
python -m evaluation.score_real_papers score --consensus-outputs private/four_person/final/consensus_real_outputs.csv --consensus-sentences private/four_person/final/consensus_real_sentences.csv --mapping private/condition_mapping_real.csv --out results/human_scored_real
```
The same conditions, metrics, ITT/completed-only policies and case-level plus matched-pair paired bootstrap are computed
over all items at once. Team metrics are never computed or averaged.

**18b (recommended if Team AB is not fully blind):** blind-member sensitivity analysis.
```bash
python -m evaluation.four_person combine --single-annotator AB=B
python -m evaluation.four_person score --single-annotator AB=B
python -m evaluation.four_person tables --single-annotator AB=B
```
Team AB's items then carry Yuxin's independent, unadjudicated labels. Outputs go to separate folders
(`private/four_person/final_sensitivity_AB_B_only/`, `results/human_scored_sensitivity_AB_B_only/`) and never replace the primary files.

### Step 19 — Tables and statistics for the report
```bash
python -m evaluation.four_person tables    # results/human_scored/TABLES_HUMAN.md (rendered from the scorers' JSON)
python -m evaluation.four_person report    # results/human_agreement/four_person/SUMMARY.md: per-team kappa, descriptive pooled %,
                                           # blinding status, contribution record (items, accepted files, reported time)
```
Report κ per team and never as a pooled κ.

---

## 4. Coordinator-as-annotator protocol (Zheyuan)
* Do not open `private/`, `outputs/`, `results/automatic/` or `docs/AUTOMATIC_RESULTS.md` while annotating or adjudicating.
  The four-person commands print only counts. `score` and `tables` come last.
* For every stage, take in **your own** file first and post its sha256 in the group chat; then Yuxin sends hers.
  `intake` refuses B's file of a given kind until A's is accepted.
* Do not open your `2_pass2` folder (or `annotation/pass2/`) before your Pass 1 is taken in.
* In Team AB adjudication, argue from the package evidence only. Consider asking Jiajun or Xinkai to read
  `adjudication_summary_TeamAB.json` and a sample of rationales.

## 5. Re-running safely
* `assign`, `build` and `check` are idempotent. A changed result stops with an explanation instead of overwriting.
* Submissions live in `private/four_person/submissions/`, which `build` never touches. Accepted files are never overwritten without `--replace`, and old copies are kept.
* `release` refuses to log an archive whose content differs from the copy already released, unless `--rerelease` is given.
* Output IDs are copied from the original packets and never generated.

## 6. Common validation messages
| Message | Fix |
|---|---|
| `column output_text was changed (... encoding ...)` | The student saved with the wrong encoding. Ask for *CSV UTF-8*, or Google Sheets download. |
| `expressed_level must be blank for numerical_reporting` | NUM/NEG rows: clear `expressed_level` and `focal_addressed`. |
| `findings_covered has unknown ids` | Use only the IDs printed in that case's Pass-2 checklist, separated by `;`. |
| `N assigned row(s) missing` / `not assigned to you` | The student sent the wrong file or deleted rows. Ask for their own unmodified sheet. |
| `... is both coordinator and B_Yuxin's partner` | Take in A's file of that kind first (Step 7). |

## 7. At the end (after every adjudication)
Commit `annotation/four_person/logs/`, `results/human_agreement/four_person/`, `results/human_scored*/`. Optionally,
following the original release plan, commit the completed submissions too, moving them out of `private/`. Never commit
`private/` or the condition mapping before the release step in `docs/HUMAN_REVIEW_HANDOFF.md` §5. Run
`python scripts/security_check.py` before pushing.
