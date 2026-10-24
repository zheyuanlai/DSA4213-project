# E1/E2: isolating the verifier's decision stage (DEV only, exploratory)

**Status: DRAFT for student review. Nothing has been implemented or run.**

## 1. Questions

* **E1.** Does the V1 verifier still fail to strengthen understated claims when it is given *all* the evidence, so that
  retrieval cannot be the cause?
* **E2.** With identical evidence, does an explicit structured strength judgement fix the decision? If it does not, is the
  failure in *recognising* the right strength or in *acting* on it?

Retrieval (E5) and any backbone or reasoning change (E3) are out of scope for this step.

## 2. Conditions

All conditions use the V1 backbone and decoding (`configs/frozen_primary.yaml`: DeepSeek V4 Flash 0731, temperature 0,
reasoning off, same provider routing) and allow STRENGTHEN (C4 setting).

| ID | Evidence | Decision framework | Role |
|---|---|---|---|
| D0-tools | V1 tools (4-call budget) | V1 adaptive verifier, **unchanged code and prompt** | reference: V1 behaviour on the new probes |
| D0-oracle | full package (identical block) | V1 verifier prompt, tool procedure removed | E1: V1 decision with retrieval removed |
| D1-oracle | full package (identical block) | D0-oracle + structured strength judgement | E2: does explicit comparison help? |
| D2-oracle | full package (identical block) | D1-oracle + generic "ways to understate" list | E2: does a strength vocabulary help? |
| D3-oracle | full package (identical block) | D1 or D2 + decision derived by code | **contingent**: only if rule R3 (section 7) fires |

**E1 contrast:** D0-tools vs D0-oracle. This is not perfectly clean, because removing tools also removes the tool-procedure
paragraph from the prompt. It is the closest feasible test.
**E2 contrasts:** D0-oracle vs D1-oracle vs D2-oracle. These differ **only** in the decision instructions and the decision
schema. The system-prompt prefix, the evidence block, the user message and the token limit are identical.

## 3. Identical evidence presentation (oracle conditions)

* The evidence block is the V1 writer view, `src.render.render_package(pkg)`. It contains all tables with values, all
  statistical tests and all cited passages, together with V1's untrusted-data note. It is generated once per case and
  reused byte-for-byte by every oracle condition and repeat.
* The user message is the V1 verifier message format (`src.verifier.claim_user_message`): draft passage with the claim
  marked `>>> <<<`, the claim text and the writer's evidence hints, preceded by the evidence block instead of the V1
  evidence index.
* The only tool offered is `submit_decision`, forced by named `tool_choice`, so the output channel matches V1.
* Token limit per call: 800 for every oracle condition. V1 used 450 per turn, which is too tight for the structured
  fields. Using the same limit for D0 keeps the E2 contrast clean.
* Validation: as in V1 (`validate_decision`), except that cited IDs must exist in the package rather than in this claim's
  tool observations. One repair turn, as in V1.

## 4. Prompts

### 4.1 D0-oracle (shared prefix of every oracle condition)

The system prompt is `prompts/common_reporting.md` (unchanged) plus the V1 adaptive verifier prompt with three edits
only: the tool *Procedure* paragraph is replaced by the first sentence below, "tool observations" becomes "the research
package", and `citable_ids` becomes package IDs. The check-list, the consistency rule and the decision definitions are V1
verbatim.

```
## Role: Claim verifier

You verify ONE sentence-level claim from a draft Results/Discussion passage against the research evidence. The complete
research package, including all table values, statistical tests and cited passages, is given in the user message; no
tools are needed.

What to check, as relevant to the claim: [V1 text verbatim]

Your decision must agree with your rationale: [V1 text verbatim]

Decisions available:
[V1 DECISION_DEFS for ACCEPT, WEAKEN, STRENGTHEN, REMOVE, FLAG, verbatim]

Rules:
- Base the decision only on the research package, and cite the package IDs (table cells such as T1.r1.acc, tests such
  as S1, passages such as P1) that the decision rests on in evidence_ids.
- [V1 rules on revised sentences and on missing evidence, verbatim]
- A sentence without factual content (e.g. a transition) may be accepted.
```

Schema (V1): `rationale` (≤ 60 words), `decision`, `revised_text`, `evidence_ids`.

### 4.2 D1-oracle: added structured strength judgement

Appended to the D0-oracle system prompt:

```
Before deciding, make an explicit strength judgement and record it in submit_decision:
1. proposition: the main proposition the sentence asserts, in a few words.
2. expressed_strength: how strongly the sentence asserts it; quote the words that set its strength (hedges,
   quantifiers such as "most" or "all", significance language, the quantity measured).
3. strongest_supported: the strongest version of the SAME proposition that the research package supports within the
   evaluated scope, written as one sentence. It may be stronger than, equal to, or weaker than the sentence.
4. support_relation: compare 3 with 2.
   STRONGER_SUPPORTED: the evidence supports a stronger statement than the sentence makes.
   MATCHES: the sentence states the proposition at the strength the evidence supports.
   WEAKER_SUPPORTED: the sentence goes beyond the evidence, but a narrower version is supported.
   NOT_SUPPORTED: no version of the proposition is supported.
   UNDETERMINED: the package does not allow a judgement.
Then choose the decision that follows from the comparison: STRONGER_SUPPORTED -> STRENGTHEN, MATCHES -> ACCEPT,
WEAKER_SUPPORTED -> WEAKEN, NOT_SUPPORTED -> REMOVE (or WEAKEN if a defensible narrower statement remains),
UNDETERMINED -> FLAG.
```

Schema, in generation order: `proposition`, `expressed_strength`, `strongest_supported`, `support_relation` (enum),
`rationale`, `decision`, `revised_text`, `evidence_ids`. The judgement fields come **before** the decision on purpose.

**Design choice: a relation, not absolute levels.** The proposal frames the comparison as ℓ against ℓ̂ on a 0/1/2 scale.
That scale is defined per benchmark category relative to a focal proposition the verifier is never told. A numeric level
would therefore either rely on a scale the model has to invent, or require putting the benchmark's category rubric into
the prompt. The relation `strongest_supported` vs `expressed_strength` is the ℓ-vs-ℓ̂ comparison without that rubric.
Writing out `strongest_supported` as a sentence also targets the observed failure directly: V1 never stated what the
strongest supported claim was.

### 4.3 D2-oracle: added generic strength vocabulary

Appended to the D1-oracle system prompt:

```
A sentence can understate its evidence in several ways, for example:
- certainty: it only describes a difference, or hedges ("may", "appears"), although a valid reported test or complete
  evidence supports an unqualified statement within the tested scope;
- coverage: it says "most", "some" or gives one example, although the evidence covers all evaluated cases;
- directness: it reports only a proxy (such as a count of computation steps), although the target quantity itself was
  measured under comparable conditions;
- attribution: it cites a source only for a direction or procedure, although the quoted passage reports a specific result.
```

**Risk:** these four items are close to the benchmark categories, so D2 may partly teach to the benchmark. D2 therefore
stays a separate condition. If D1 is adequate, D1 is preferred. If D2 is used, held-out V2 cases must include
understatement forms that are not on this list.

### 4.4 D3-oracle (contingent, not built unless R3 fires)

D3 keeps the D1 (or D2) prompt, but code derives the decision from `support_relation` using the mapping in 4.2. A model
decision that disagrees triggers the existing single repair turn. A remaining mismatch is logged and the code-derived
decision is used.

## 5. Probes: `v2/data/dev_probes_batch1.json` (39 probes, DEV only)

Each draft is a single sentence placed on **both members** of a DEV matched pair, so identical text needs a different
decision depending on the evidence. Expressed and gold levels follow `docs/BENCHMARK_SPEC.md` section 4.

| Pair (strong / partner level) | U (level 1) | U2 (level 1, hedged) | S (level 2) | Z (level 0, only on the level-0 case) |
|---|---|---|---|---|
| SIG (2 / 1) | "higher mean BLEU" | "appears to slightly outperform" | "significantly outperformed" | none |
| CON (2 / 1) | "on most of the six" | "generally higher" | "on all six" | none |
| EFF (2 / 1) | fewer decoder passes (proxy) | "may decode faster" | "decodes faster" | none |
| GEN (2 / 0) | advantage on Insurance only | "may extend to" unseen domains | transferred to all three | "transfer was not tested" |
| ROB (2 / 0) | criterion met at 10% noise | "appears somewhat robust" | robust at 10/20/30% | "not evaluated" |
| CIT (2 / 0) | reported a reduction (no magnitude) | "suggest … may help reduce" | reported the 31% reduction | "cited for procedure only" |

Expected decisions:

| | Strong case (gold 2) | Partner with gold 1 | Partner with gold 0 |
|---|---|---|---|
| U, U2 (level 1) | **STRENGTHEN** (12) | ACCEPT (6) | REMOVE or WEAKEN (6) |
| S (level 2) | ACCEPT (6) | WEAKEN (3) | REMOVE or WEAKEN (3) |
| Z (level 0) | none | none | ACCEPT (3) |

That gives 12 STRENGTHEN, 15 ACCEPT and 12 WEAKEN/REMOVE probes.

* Every probe states the focal proposition at some strength. The V1 H2 "omitted-finding" drafts (ROB/GEN/CIT with an
  unrelated fact) are **excluded**, because recovering an omitted finding is a different capability from strengthening.
* Two probes are flagged borderline:
  * **EFF-U (strong case)** is a proxy-to-target case: the sentence mentions only decoder passes, so strengthening means
    introducing latency. It is reported as its own subgroup and also with the main set excluded.
  * **EFF-U2 (partner)** also accepts a WEAKEN that only adds the different-hardware caveat, because the level stays 1.
* SIG-U and CON-U are identical to the V1 H2 drafts, which allows a direct comparison with `h2diag_v1`.

## 6. Procedure and measures

* 39 probes × 4 conditions (D0-tools, D0-oracle, D1-oracle, D2-oracle) × **3 repeats**. Temperature 0 is not
  deterministic across providers, so the repeats estimate stability.
* Per probe, the majority decision over the 3 repeats is primary. All runs are also reported.
* Automatic measures, per condition:
  * decision accuracy: decision in `acceptable_decisions`, overall and per expected-decision group;
  * correct STRENGTHEN (out of 12);
  * false STRENGTHEN: STRENGTHEN on the 27 probes not expected to strengthen;
  * WEAKEN/REMOVE accuracy: so that V2 does not break the overstatement direction;
  * D1/D2 only: **relation accuracy** (`support_relation` in `expected_support_relation`) and **action consistency**
    (the decision equals the mapping of the model's own relation);
  * **failure stage** of every run on the 12 STRENGTHEN probes that did not strengthen (taxonomy below);
  * tokens and cost.

**Failure-stage taxonomy (STRENGTHEN probes that were not strengthened).** In the oracle conditions the evidence is in
context, so retrieval is excluded. A failure can still happen at one of three later stages:

| Stage | Meaning | D1/D2 coding (from the structured fields) | D0 coding (from the rationale) |
|---|---|---|---|
| F1 not noticed | the decisive fact does not enter the judgement | `strongest_supported` does not contain the decisive fact | rationale does not mention the decisive fact |
| F2 noticed, wrong standard | the stronger fact is seen, but the claim is judged acceptable as it is | `strongest_supported` contains the decisive fact, but `support_relation` = MATCHES (or another non-STRONGER value) | rationale mentions the decisive fact, and the decision is not STRENGTHEN |
| F3 judged understated, wrong action | the claim is judged understated, but the action does not follow | `support_relation` = STRONGER_SUPPORTED, but the decision is not STRENGTHEN | not codable (no explicit judgement) |

* The decisive fact for each probe is fixed in advance from the pair contrast. Examples: the S2 test (SIG), the sixth win
  on Ivel-Fraud (CON), the same-hardware latency (EFF), the other held-out domains (GEN), the 20% and 30% noise results
  (ROB), and the 31% figure in P1 (CIT). The list is stored in the probe file (`decisive_evidence_ids`, `decisive_fact`).
* Coding is done by the coordinating agent, and every case is checked by a student.
* **Limitation of the D0 coding:** a rationale of at most 60 words that does not mention a fact is weak evidence that the
  fact was not noticed. D0's F1/F2 split is therefore indicative only, and F3 cannot be separated from F2 in D0. The
  structured fields of D1/D2 give the more reliable split.
* **Human check** (students): every revised sentence from STRENGTHEN or WEAKEN decisions, labelled with its expressed
  level and checked for new factual errors. Expected volume is at most a few dozen sentences. A shared sheet will be
  generated.

## 7. Decision rules, fixed before the run

These rules guide the next development step. **None of them determines a root cause automatically.** Root-cause
statements are made after reading the failure-stage distribution (section 6) and are discussed with the students first.

* **R1 (E1 reference threshold, descriptive).** If D0-oracle strengthens at most 3 of the 12 STRENGTHEN probes (majority
  of 3), this only shows that providing all the evidence is not enough. Retrieval alone does not explain the V1
  behaviour. *Where* the failure happens after retrieval (F1, F2 or F3) is read from the failure-stage taxonomy, not from
  this threshold.
* **R2 (adequate variant).** A variant is adequate if all of the following hold:
  * correct STRENGTHEN ≥ 9/12;
  * false STRENGTHEN ≤ 2/27;
  * WEAKEN/REMOVE accuracy at most 1 probe below D0-oracle;
  * the human check finds ≥ 80% of its STRENGTHEN revisions at the target level without new errors.
* **R3 (build D3).** Consider D3 only if, for D1 or D2, F3 (judged understated, wrong action) is the most common failure
  stage, or decisions disagree with the model's own relation on ≥ 3 probes overall. Code enforcement only fixes F3.
* **R4 (F1/F2 dominate).** If most remaining failures in both D1 and D2 are F1 (not noticed) or F2 (wrong standard), the
  problem lies before action selection, and code enforcement would not help. We stop and discuss options first. For F1
  these include directing attention to the comparison the question asks about, or E3. For F2 they include changing the
  acceptance criterion.
* **R5.** The simplest adequate variant (preference D1 > D2 > D3) goes forward to the retrieval step (E5).

These probes are DEV data. If prompts are revised after this run, each revision and its re-run are logged in a dated
results document. The held-out V2 cases are separate, written later, and never used for tuning.

## 8. Implementation footprint (after approval)

* `v2/verifier_oracle.py`: oracle verification loop. It reuses V1's renderer, evidence store, decision definitions and
  validator logic read-only.
* `v2/prompts/`: the D0/D1/D2 prompt files exactly as in section 4, with hashes recorded in every run record.
* `v2/scripts/run_e1_e2.py`: runs the four conditions. D0-tools calls V1's unchanged `src.verifier.verify_draft`, as the V1
  H2 diagnostic did.
* `v2/scripts/analyze_e1_e2.py`: measures, rule checks and the human-review sheet.
* `v2/tests/`: offline tests with the mock client.
* Outputs and a **separate** cost ledger go under `v2/outputs/`, so the reconciled V1 ledger is untouched.

## 9. Budget

Estimate: about 470 oracle calls and about 117 tool-loop verifications, roughly $0.25–0.35 at V1 prices. Hard cap for
this step: **$1.00**, enforced by V1's CostGuard class pointed at the V2 ledger.
