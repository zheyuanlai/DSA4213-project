"""Four-person human annotation workflow (amendment; see docs/AMENDMENT_FOUR_PERSON_ANNOTATION.md).

Two independent annotator pairs (Team AB, Team CD) each double-annotate a disjoint half of the
human-evaluation data. The frozen experiment, the original blinded packets, the private mappings,
the gold files and the original scoring code are reused unchanged:

* assignment   — split the 32 TEST cases (by intact matched pair) and the 12 real papers between teams
* packets      — per-person, per-stage folders, viewers and zip archives built from the ORIGINAL packets
* checks       — integrity / blinding / stage-separation invariants
* submissions  — intake and validation of the students' CSVs (never edited)
* team_merge   — per-team agreement (existing kappa code), disagreement sheets, adjudication, consensus
* combine      — merge both teams' consensus into the exact schemas the original scoring scripts expect

Entry point: ``python -m evaluation.four_person --help``.
"""
