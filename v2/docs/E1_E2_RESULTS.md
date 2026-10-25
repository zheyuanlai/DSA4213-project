# E1/E2 results: isolating the verifier's decision stage (DEV only, exploratory)

**Status: automatic results and the agent's first-pass coding are complete. Student checks of the failure coding and of
the revised sentences are pending, so every statement below is provisional.**

* Run `e1e2_v1`, 2026-10-24: 39 probes × 4 conditions × 3 repeats = 468 runs, all completed, 0 invalid decisions.
  Cost $0.070 on the V2 ledger (smoke test `smoke_v1`: $0.0014).
* Design: [`E1_E2_DESIGN.md`](E1_E2_DESIGN.md). Records: `v2/outputs/e1e2/e1e2_v1/`. Tables and sheets:
  `v2/results/e1e2/e1e2_v1/`.
* All probe-level figures use the majority decision over the 3 repeats.
* **Update 2026-10-25 (E2b):** an identical re-run of D1 one day later strengthened 9/12 probes, not 7/12 (same prompt,
  code, model and provider). Differences between conditions of about two probes in this table are within batch-to-batch
  variation. In particular, D2's advantage over D1 cannot be attributed to its prompt. See
  [`E2b_COMPARABILITY.md`](E2b_COMPARABILITY.md). The post-hoc scope-anchoring subgroup (GEN-U, ROB-U, EFF-U) is now
  reported separately in `TABLES.md`; claim-level STRENGTHEN here is D1 7/9, D2 9/9, D0 0/9.

## 1. Main table

| Measure | D0-tools (V1) | D0-oracle | D1-oracle | D2-oracle |
|---|---|---|---|---|
| Correct STRENGTHEN (of 12) | 0 | 0 | 7 | 9 |
| …excluding the proxy probe EFF-U (of 11) | 0 | 0 | 7 | 9 |
| STRENGTHEN runs on STRENGTHEN probes (of 36) | 0 | 2 | 18 | 26 |
| ACCEPT correct (of 15) | 15 | 15 | 14 | 13 |
| WEAKEN/REMOVE correct (of 12) | 10 | 10 | 11 | 11 |
| False STRENGTHEN, probes (of 27) | 0 | 0 | 0 | 1 |
| False STRENGTHEN, runs (of 81) | 0 | 0 | 0 | 4 |
| Stable probes, same decision in all 3 runs (of 39) | 36 | 36 | 31 | 36 |
| Relation correct on STRENGTHEN probes (of 12) | n/a | n/a | 7 | 9 |
| Probes whose decision contradicts the model's own relation | n/a | n/a | 0 | 0 |
| Cost (USD) | 0.0296 | 0.0093 | 0.0146 | 0.0153 |

## 2. E1: retrieval does not explain the V1 behaviour on these probes

* **The result.** With all the evidence in context, the V1 decision prompt (D0-oracle) strengthened **0 of 12** probes,
  the same as V1 with tools. The reference threshold of R1 (≤ 3) is met.
* **Retrieval was rarely the problem.** With tools (D0-tools), the decisive evidence was returned in 33 of the 36 runs
  that failed to strengthen. The 3 exceptions are all EFF-U: the verifier looked up decoder passes only.
* **Coded failure stages** (indicative, from rationales of at most 60 words):

  | Stage | D0-oracle (of 34 failed runs) | D0-tools (of 36 failed runs) |
  |---|---|---|
  | F2: noticed the decisive fact, judged the claim acceptable | 22 | 27 |
  | F1: decisive fact not mentioned | 12 | 6 |
  | F0: decisive evidence not retrieved | n/a | 3 |

* **What F2 looks like.** The rationale states the stronger fact and then praises the weaker wording:
  * "'Most' is a correct, if conservative, description; the claim is supported as stated."
  * "The claim's hedged wording ('suggest… may help reduce') is supported and appropriately scoped."
  * "…a significant paired t-test (p=0.017)… Claim of slight outperformance is supported."

  The V1 framing treats hedging as prudence, not as an error.
* **Overstatement direction.** D0 also showed one rationale–decision contradiction there. On CON-S-partner ("all six"
  when Ferrule wins five), the rationale ends "so the claim is false", yet the decision is ACCEPT (2 of 3 runs accept).
  D1 and D2 weaken this claim correctly in all runs.

## 3. E2: an explicit strength judgement largely fixes the decision

* **Clear improvement.** D1 strengthens 7 of 12 probes and D2 9 of 12, where D0-oracle strengthened none, with the same
  evidence and the same user message.
* **No loss in the other direction.** At probe level, false STRENGTHEN stays at 0/27 (D1) and 1/27 (D2), and
  WEAKEN/REMOVE accuracy is not worse (11/12 vs 10/12).
* **Wrong actions are rare.** In D1, 3 runs gave STRONGER_SUPPORTED but still chose ACCEPT (F3). D2 had none, and no
  probe's majority decision contradicts its majority relation. Rule R3 does not fire, so **code-enforced decisions (D3)
  are not needed**.
* **Remaining failures are before action selection.** Rule R4 fires: F1 and F2 dominate the remaining failures in both D1
  and D2. The design says to stop and discuss at this point.

| Remaining failures (runs) | D1 | D2 |
|---|---|---|
| F1 (all 9 in each condition are the three "scope anchoring" probes below) | 9 | 9 |
| F2: `strongest_supported` contains the stronger fact, relation MATCHES (SIG-U, CIT-U, one GEN-U2) | 6 | 1 |
| F3 | 3 | 0 |

## 4. Remaining problems found by reading the records

### 4.1 Scope anchoring (GEN-U, ROB-U, EFF-U): 0 of 9 runs strengthened in every condition

These drafts state an **accurate sub-claim**: the advantage on the Insurance domain only, the criterion met at 10%
noise only, or fewer decoder passes. The model takes that sub-claim as "the proposition". It then writes a
`strongest_supported` sentence about the same sub-claim and judges MATCHES. For example:

> proposition: "Wrenfold outperformed Fennick-Base in macro-F1 on the held-out Insurance domain"
> strongest_supported: "On the held-out Insurance domain, Wrenfold achieved higher macro-F1 …"

This is closer to the omitted-finding problem than to hedging. Strengthening here means **broadening the scope** of a
sentence to the question being asked, which the per-sentence verifier is not told to do. Whether these three probes
should count as "STRENGTHEN expected" at all is a construct question for discussion (see section 6).

### 4.2 D2 introduces false strengthening on a comparability trap

On EFF-U2-partner ("may decode faster", but Talmar's latency was measured on different, older hardware), D2 chose
STRENGTHEN in **3 of 3 runs**:
* two revisions assert an unqualified latency advantage ("decodes faster" / "has a lower median latency");
* one keeps the hardware caveat.

D1 accepted the hedged sentence in all three runs. D2's "directness" item ("…measured under comparable conditions")
did not stop it. This is the kind of error the "teaching to the benchmark" warning anticipated.

### 4.3 Revisions that need a student check

* **D1, CIT-S-partner (2 runs).** The WEAKEN revision "Varga & Sandoval (2021) is credited with cutting unsupported-entity
  hallucinations … by about 30%" still attributes the magnitude, which the excerpt does not report. If confirmed, the
  edit kept the error it was meant to remove.
* **CON-U2-partner.** D1 (2 of 3) and D2 (3 of 3) weakened "generally higher" to "five of the six datasets". The
  revision is accurate and stays at level 1. The probe's expected set (ACCEPT only) may be too strict. The label is
  **not** changed after the fact; the student check decides how to report it.
* **D2, SIG-U2-partner (1 run).** A STRENGTHEN removed "appears to slightly" and left "outperforms" with no significance
  language, which is still level 1.

### 4.4 An overstatement blind spot in every condition

EFF-S-partner ("decodes faster" with latencies from different hardware) was ACCEPTed by the majority in all four
conditions. Several rationales mention the hardware difference and still accept. This is an F2-type failure in the
weakening direction, and none of the variants fixes it.

## 5. Provisional interpretation (pending student checks)

1. V1's failure to strengthen is mainly a **decision-standard** problem (F2). The verifier sees the stronger evidence but
   treats a supported, weaker claim as acceptable, often calling the hedge appropriate. Missing retrieval and wrong
   action selection play a minor role on these probes.
2. Asking for an explicit `strongest_supported` statement and a relation before the decision corrects most of this,
   without code enforcement and without a measurable loss in the weakening direction.
3. Two problems remain:
   * **scope anchoring**, where the sentence's own sub-claim defines the proposition;
   * a **trade-off in D2**: the vocabulary list raises recall (9 vs 7 of 12) but produced false strengthening on a
     comparability trap.

## 6. Questions for discussion before the next step

1. **Variant to carry forward.** D1 is more conservative and does not teach to the benchmark. D2 has higher recall and
   showed one real false-strengthening pattern. The agent's recommendation is **D1** (possibly with one sentence on
   comparability), unless the student check of the D2 revisions is clean.
2. **Scope anchoring.** Options:
   * (a) anchor `proposition` to the research question ("the answer this sentence gives to the research question");
   * (b) treat scope broadening as out of scope for STRENGTHEN, like omitted findings, and report GEN-U/ROB-U/EFF-U as a
     separate subgroup;
   * (c) both: try (a) on DEV, and report the subgroup separately either way.

   Option (a) raises the risk of redundant or over-broad edits in multi-sentence passages, which these single-sentence
   probes cannot detect.
3. **Next experiment.** E5 (retrieval with tools) is the planned next step. On these probes D0-tools retrieved the
   decisive evidence in 33 of 36 failed runs, so retrieval may matter less than expected for claim-level strengthening.
   E5 is still needed, because the verifier sees less with tools than in the oracle setting.
