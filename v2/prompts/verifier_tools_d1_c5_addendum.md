## Strength judgement (record it in submit_decision before deciding)

Before deciding, make an explicit strength judgement and record it in `submit_decision`:
1. `proposition`: the main proposition the sentence asserts, in a few words.
2. `expressed_strength`: how strongly the sentence asserts it; quote the words that set its strength (hedges, quantifiers such as "most" or "all", significance language, the quantity measured).
3. `strongest_supported`: the strongest version of the SAME proposition that the research package supports within the evaluated scope, written as one sentence. It may be stronger than, equal to, or weaker than the sentence.
4. `support_relation`: compare 3 with 2.
   - STRONGER_SUPPORTED: the evidence supports a stronger statement than the sentence makes.
   - MATCHES: the sentence states the proposition at the strength the evidence supports.
   - WEAKER_SUPPORTED: the sentence goes beyond the evidence, but a narrower version is supported.
   - NOT_SUPPORTED: no version of the proposition is supported.
   - UNDETERMINED: the package does not allow a judgement.

Then choose the decision that follows from the comparison: STRONGER_SUPPORTED -> ACCEPT (strengthening is not available), MATCHES -> ACCEPT, WEAKER_SUPPORTED -> WEAKEN, NOT_SUPPORTED -> REMOVE (or WEAKEN if a defensible narrower statement remains), UNDETERMINED -> FLAG.
