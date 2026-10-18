# Task: adjudicate disagreements about atomic claims (prompt ext-adjudicate-claims)

Two independent readings of the same atomic claims disagree. For each disputed item below, decide from the research package alone which judgement is right. The readings are anonymous and their order is random; neither is more reliable by default. Decide only the fields listed as disputed; agreed fields are already final.

Definitions (same as the readers used):
* `entailment`: ENTAILED / NOT_ENTAILED / CONTRADICTED / NA (whether the proposition as stated is true according to the package).
* `label` (ignores exact numeric values, which a program checks): SUPPORTED (entailed and calibrated); OVERSTATED (same direction but certainty/scope/generality/significance/magnitude wording exceeds the evidence); UNDERSTATED (weaker than the package establishes, or denies an established conclusion); UNSUPPORTED (no basis, or wrong direction/attribution, equivalence from non-significance, causal claims presented as findings); NOT_VERIFIABLE (not a factual claim about the package). SUPPORTED needs ENTAILED; OVERSTATED/UNSUPPORTED need NOT_ENTAILED or CONTRADICTED; UNDERSTATED needs ENTAILED or CONTRADICTED; NOT_VERIFIABLE needs NA.
* `extraction_valid`: false only if the claim is not expressed by its sentence or distorts its meaning.
* Numeric mappings: the program's result for each reading is shown. Choose the mapping that faithfully encodes what the **text refers to** (entity, dataset, metric, comparison, direction), whether or not it makes the number correct; or give your own mapping (same format: `source_type` cell/test/text/none, `expression`, `quote`, `scale`).

Answer `UNRESOLVED` for a field only if the package genuinely does not allow a decision. Give a rationale of at most 40 words citing evidence IDs.

## Research package
{{PACKAGE}}

## Disputed items
{{ITEMS}}
