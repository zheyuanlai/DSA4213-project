# Amendment: four annotators in two independent pairs

**Status (2026-10-15):** implemented; **no human labels exist yet**. This amendment changes *who annotates which
items*. It changes nothing in the experiment, the outputs, the gold labels, the annotation guide, the metrics or the
hypotheses. It was made after the protocol freeze and before any annotation packet was released to any student.

## 1. What changed and why

The proposal and `docs/PROTOCOL_FREEZE.md` specify two blind annotators who each label the complete human-evaluation
set, followed by inter-annotator agreement and adjudication. The full set is large:
* **Synthetic:** 122 distinct outputs, deduplicated from the 224 condition-case runs, each labelled in two passes (Pass 1 strength fields; Pass 2 checklists).
* **Real papers:** 39 paragraphs with 151 sentence-level support labels.

This is too much work for two students. All four group members therefore annotate, as two independent pairs:

| Pair | Members | Items |
|---|---|---|
| Team AB | A Zheyuan, B Yuxin | 16 of the 32 TEST cases (61 outputs) and 6 of the 12 papers (19 paragraphs, 75 sentences) |
| Team CD | C Jiajun, D Xinkai | the other 16 cases (61 outputs) and 6 papers (20 paragraphs, 76 sentences) |

* **Two independent judgments per output.** Within a team, both members label every item of that team's half independently, so every output still receives two independent judgments.
* **Disjoint halves.** No case, paper, paragraph or sentence is assigned to both teams.
* **Same items, both passes.** Assignments are identical for Pass 1 and Pass 2.
* **Reduced workload.** Each student labels half of the data instead of all of it.

## 2. How the split was made (`python -m evaluation.four_person assign`, seed 4213)

**Synthetic split.** The unit of assignment is the **TEST case**, so all outputs of one case, from every condition,
stay with one team and the within-case condition comparison is untouched.
* Cases are grouped by the benchmark's **matched pairs**. Pair identity is taken from the public `pair_id` field of
  `data/synthetic/test.jsonl`, joined to the opaque `case_ref` aliases through the coordinator-private alias map.
* Each team receives **one intact matched pair per category**: 2 cases × 8 categories = 16 cases.
* By the frozen design every TEST pair holds exactly one strong (ℓ=2) member. Each team therefore gets one strong and one
  non-strong case per ordinal category, and this balance was obtained **without reading the gold file**.
* Of the 2⁸ = 256 such allocations, those minimising the difference in distinct outputs were kept (61 vs 61). One was
  drawn with `random.Random("4213:synthetic-allocation")`.
* Which non-strong cases are ℓ=1 rather than ℓ=0 was not balanced, because that would require the gold labels.

**Real-paper split.** The unit is the **paper**, so all paragraphs of a paper and all sentences of a paragraph stay together.
* All 462 distinct 6/6 partitions were searched. The search minimised, in order, the difference in paragraphs, then in
  sentences, then in words to read (package plus outputs).
* Result: 19 vs 20 paragraphs, 75 vs 76 sentences, 8,274 vs 8,292 words. Ties and the AB/CD side were drawn with the fixed seed.

**Row order.** Each person's rows are shuffled with `random.Random("4213:rows:<annotator>:<stage>")`, so partners
see the same items in different orders.

**Records.** Annotator-safe: `annotation/four_person/ASSIGNMENT.md` and `assignment.json`. Coordinator-only:
`private/four_person/assignment_private.csv` (case_ref → case_id → pair → team).

## 3. What did not change

* **Experiment:** the model outputs (none regenerated), conditions, prompts, TEST cases, gold labels and their frozen hash.
* **Packets:** the random `output_id`s and the private condition and alias mappings (sha256-baselined and checked).
* **Annotation materials:** `annotation/ANNOTATION_GUIDE.md` (frozen; copied unchanged into every packet), the field
  definitions, the permitted values and the case packages (copied byte-for-byte from the original `annotation/pass1|pass2|real/packages/`).
* **Two-pass protocol:** Pass 2 checklists are never visible in Pass 1. They now ship as a separate archive, released
  only after that person's Pass 1 file has been accepted.
* **Scoring:** the metrics and hypotheses (H1–H3) and the scoring code (`evaluation/score_human.py`,
  `evaluation/score_real_papers.py`, `evaluation/paired_bootstrap.py`). The consensus labels of both teams are
  combined **at the item level** into the original consensus schema. The original scripts then compute every
  condition-level metric once over all items, with the original private mappings, ITT and completed-only policies, and
  case-level plus matched-pair bootstrap. No team-level metric is computed or averaged.
* **Original workflow:** the two-person workflow and its packets remain available.

## 4. Agreement and adjudication

* Agreement is computed **separately for Team AB (A × B) and Team CD (C × D)**, each on its own subset, with the
  original functions:
  * **Synthetic:** Cohen's κ for `expressed_level` (unweighted, linear and quadratic weighted) and for `focal_addressed`; κ on "any" `unsupported_claims` and `numeric_errors`, plus exact-count agreement; item-level κ for the checklists; κ for `neg_reframed_positive`.
  * **Real papers:** κ for readability (quadratic weighted), overall calibration and sentence support label.
* Each report names the annotator pair and the number of overlapping items.
* A κ that is 0/0 because both annotators used a single identical label is reported as **undefined**, with percent
  agreement. The original helper would return 1.0 there.
* **No κ is pooled across the two pairs.** A pooled *percent* agreement is shown only as a descriptive figure.
* Only disagreements go to adjudication; matching labels are kept automatically. Each pair adjudicates its own
  disagreements from the research package and the guide, still blind to system identity and gold. Every adjudicated
  value needs a valid label and a rationale; an incomplete or invalid sheet blocks consensus. No disagreement is
  resolved automatically in favour of either annotator.

## 5. Blinding, and a limitation specific to Team AB

Before any TEST material is released, every student completes a blinding declaration. It asks whether they have seen
TEST gold, the output→condition mapping, raw outputs with condition identities, or label-revealing automatic scores;
whether they have had access to the coordinator-private files; and whether they have discussed such material.
Each student also commits to independence. The declarations are logged in `annotation/four_person/logs/blinding_declarations.csv`.

**Zheyuan (Annotator A) is also the project coordinator.** He holds the private mapping, the gold and the raw outputs,
and directed the automatic evaluation. Reshuffling files cannot restore blindness that has already been lost. Therefore:
* Even with a declaration of no exposure, A's labels can only be described as **self-reported blind, not verifiable**.
  With any reported exposure they are **potentially non-blind**. Team AB's agreement and consensus must then not be
  described as fully independent *blind* ratings.
* A concrete, documented exposure exists. The AI-assistant session that built this workflow (2026-10-15) displayed on the
  coordinator's screen:
  * 4 rows of the case-alias map: three of those cases are in Team AB, which shows their category, pair and pair member (not gold).
  * The condition labels of 2 synthetic outputs in one Team AB case.
  * The condition labels of 2 real-paper outputs in one Team CD paper.
  * The names, but not the descriptions, of 3 Pass-2 checklist IDs.

  A's personal instructions list these so the declaration can be precise.
* **Independence safeguards:**
  * Zheyuan takes in his own file for each stage before Yuxin's (the tool enforces this order) and posts its sha256 in the group chat.
  * Pass-2 gating is self-enforced for him.
  * The adjudication summary records how often each annotator's value was chosen.
* **Sensitivity analysis.** `combine --single-annotator AB=B` rescored Team AB's items from Yuxin's independent labels
  alone, with the same original scoring. If the primary and sensitivity results agree, A's potential non-blindness is
  unlikely to drive the conclusions.

**Scientifically preferable alternative (not implemented, needs the group's decision before Pass 1):**
* Zheyuan remains coordinator only. Yuxin, Jiajun and Xinkai double-annotate in rotating pairs: B×C, C×D and B×D, each on
  one third of the cases (by intact matched pair) and papers.
* Every output then receives two judgments from fully blind annotators.
* The cost: each of the three labels about 2/3 of the data instead of 1/2. That is ≈81 instead of 61 synthetic outputs
  per pass, ≈26 instead of ≈20 paragraphs, and ≈101 instead of ≈75 sentences.
* Agreement would then come from three smaller pairs (≈40 outputs each).

The packets in this repository follow the A/B/C/D design the group asked for.

## 6. Limitations

* **Different raters, different halves.** Team AB and Team CD label different items, so rater effects are confounded
  with item subsets. Agreement is per pair and cannot be generalised as one inter-rater reliability for the whole set.
  Condition comparisons are unaffected in expectation, because every condition's outputs for a case are labelled by the
  same pair, but pair-specific leniency adds noise.
* **Smaller samples.** Each pair's κ rests on half the items: 61 synthetic outputs, of which 49 (AB) and 48 (CD) fall in ordinal
  categories, and about 20 paragraphs and 75 sentences. κ will have wide uncertainty and can be undefined for rare labels.
* **Strength balance only.** The split balances strong and non-strong ordinal cases by design. It does not balance ℓ=1
  against ℓ=0 (gold unread) or pair-level difficulty.
* **Team AB blinding.** Team AB's blinding is limited as described in §5.
* **Pair structure is visible.** Each annotator sees two cases per category. Someone who has read
  `docs/BENCHMARK_SPEC.md` could infer that they form a matched pair. This is also true of the original packets.

## 7. Paragraph for the final report (adapt; numbers in [brackets] are filled only after annotation)

> *Human annotation.* Because double-annotating all 122 synthetic outputs (two passes) and 151 real-paper sentences
> was infeasible for two people, we used two independent annotator pairs, each covering a disjoint half of the data.
> Cases were assigned by intact matched pair, one pair per category per team (16 TEST cases and 61 outputs each), and
> real papers by a balanced 6/6 split (19/20 paragraphs, 75/76 sentences). Within each pair, both members labelled every
> assigned item independently, following the frozen guide and the two-pass protocol (checklists released only after the
> strength labels were submitted). Agreement was computed separately per pair: expressed-level quadratic-weighted
> κ = [κ_AB] (n = [n_AB]) and [κ_CD] (n = [n_CD]); sentence support-label κ = [..] and [..]. Disagreements were
> adjudicated within each pair, blind to system identity, before the two consensus sets were merged at the item level
> and scored with the pre-registered metrics. One annotator was also the project coordinator with access to the
> condition mapping, so pair AB's labels are [self-reported blind but not verifiable / potentially non-blind]. A
> sensitivity analysis using only the other AB member's independent labels [did / did not] change the conclusions ([details]).

If the group adopts the rotating three-annotator design instead, replace the pair description accordingly and drop the
last two sentences.

## 8. Implementation and verification

* **Code:** `evaluation/four_person/` (CLI `python -m evaluation.four_person`). The coordinator guide is
  `annotation/four_person/README_COORDINATOR.md`, and the personal instructions are
  `annotation/four_person/instructions/README_<ID>_<Name>.md`.
* **Tests:** `tests/test_four_person_workflow.py` runs the whole workflow on a fake repository with clearly marked
  DUMMY labels. It covers:
  * assignment invariants, determinism and overwrite protection;
  * packet and blinding checks, including detection of planted leaks;
  * stage gates and intake validation;
  * the browser self-check matching the Python validator;
  * per-team agreement, adjudication refusal and acceptance;
  * the combination accepted by the original scorers, and the sensitivity variant;
  * an explicit error for missing labels.
* **Dry run:** the full chain was also run once on a scratch copy of the real packets with dummy labels, through
  acceptance by the original scorers, and then deleted. No dummy label or result was kept or reported.
