# Task: align claims between two versions of a passage (prompt ext-align)

Each pair below shows the atomic claims that differ between two versions of a passage about the same research package (claims in sentences shared by both versions are already aligned and are not shown). Version X came first; Version Y is a later version. For **every Version X claim**, say what happened to it in Version Y, and list Version Y claims that have no counterpart in X.

* `relation`: `UNCHANGED` (the same proposition is in Y with the same wording); `REWORDED` (same meaning, different wording); `MODIFIED` (same topic but the content changed); `DELETED` (no counterpart in Y).
* `direction` (only for MODIFIED, else null): `WEAKENED` (less certain, narrower, hedged, or significance/generality removed), `STRENGTHENED` (more certain, broader, or significance/generality added), `NUMBER_CHANGED` (a number changed, otherwise the same), `SCOPE_CHANGED` (different dataset/metric/entity, neither weaker nor stronger), `OTHER`.
* `matched_y`: the Version Y claim IDs expressing this claim (possibly several if it was split; empty if DELETED).
* `added_y`: Version Y claim IDs that express content not present in any Version X claim.
Decide from meaning, not from wording overlap. Every Version Y claim must appear either in some `matched_y` or in `added_y`.

## Research package
{{PACKAGE}}

## Pairs
{{PAIRS}}
