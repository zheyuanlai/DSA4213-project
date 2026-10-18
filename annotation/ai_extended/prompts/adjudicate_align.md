# Task: adjudicate disagreements about claim alignment (prompt ext-adjudicate-align)

Two independent readings disagree on what happened to a claim between Version X and a later Version Y of a passage. The readings are anonymous and in random order. Decide from meaning.
* `relation`: UNCHANGED, REWORDED (same meaning), MODIFIED (content changed), DELETED (no counterpart in Y).
* `direction` (MODIFIED only, else null): WEAKENED, STRENGTHENED, NUMBER_CHANGED, SCOPE_CHANGED, OTHER.
* `matched_y`: the Version Y claim IDs that express it (empty if DELETED).
Answer `UNRESOLVED` only if the texts genuinely do not allow a decision. Rationale: at most 30 words.

## Disputed items
{{ITEMS}}
