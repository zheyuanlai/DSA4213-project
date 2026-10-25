# Phase 4: deviations from the frozen protocol

The freeze is `v2/benchmarks/freeze_manifest.json` (2026-10-25). Every later change to a frozen file is listed here,
with the time, the reason and the new hash. `phase4_freeze.py --check` will report these files as changed.

## D1 (2026-10-25, after TEST inference, before any judge label existed)

* **File.** `v2/scripts/phase4_judge.py`, new SHA-256 `c2cf732e3688d08a7cb0d1db7b50326ebf6b7f6295bc5dedbdcc93a1ceca7cfa`.
* **Problem.** The first Judge A call returned JSON that put the numeric mappings in a top-level `numbers` array. V1's
  verify schema rejects this (`jsonschema`: "Additional properties are not allowed ('numbers' was unexpected)"), so the
  script stopped. V1's judges enforced the output schema through the Codex and Claude CLIs. The frozen OpenRouter path
  asked only for "a JSON object" and never showed the model the schema.
* **Change.** The output schema is appended to each judge and adjudication prompt, with **the same wording V1's Claude
  backend uses** (`evaluation/judges.py::_claude_call`). On a schema violation there is one repair turn.
* **Not changed.** The verify and adjudication prompts, the schemas, the label definitions, the numeric checks, the
  scoring rules (`phase4_score.py`), the verifier and the TEST items.
* **What had been seen.** No judge label existed. The coordinating agent had seen only the runner's progress lines.
* **Cost of the failed call.** About $0.05 (one Judge A call), on the judge ledger.

## D2 (2026-10-25, during judging, before any score was computed)

* **Files and new SHA-256.** `v2/scripts/phase4_judge.py` `d7631df19b1ae779e767245245fc4ab1273075fa12ae6ae83a5aa7e43e9fdfb3`; `v2/or_judge.py` `68355415caef02a793a63852e5a0d1e5fc755a0e069e0c23499375c70f31e78c`.
* **Problem.** Claude Haiku 5.5 (Judge B) reasons by default, and its reasoning tokens count against the per-call limit.
  The verify reply for one package hit the 6,000-token limit (`finish_reason = length`), and so did its repair turn,
  so the JSON was cut off.
* **Changes.**
  1. The verify-call token limit is raised from 6,000 to 16,000. Billing is by actual use.
  2. The cache never reuses a truncated reply; such files are renamed `*.truncated.json` and kept.
  3. The judge-ledger stage cap `p4_judge` is raised from $1.50 to $2.50. Observed Judge A cost is $0.06–0.14 per
     package, against an expected $0.04–0.05, which projects to about $1.6–1.8 in total.
* **Not changed.** Prompts, schemas, labels, numeric checks, scoring rules, verifier, items.
* **What had been seen.** Judge labels for P1 only, at the level of these log lines. No score had been computed.

## D0 (record correction, 2026-10-25, written after scoring)

* **Correction.** `PHASE4_BENCHMARK.md` said that the gold was kept only in the gitignored `v2/private/`. That is not
  accurate. The raw authoring and validation replies under `v2/outputs/judge_raw/p4_author/` and `p4_validate/` contain
  each draft's intended level, and the validator's labels. They were committed in `cc34177`, before the freeze and
  before TEST inference.
* **Effect on results: none.** No component of the run can read the repository:
  * the verifier sees only the package and the draft;
  * the judges see only blinded prompts, checked by `check_leakage`.

  The branch was never pushed. The freeze manifest's gold hash and the scoring are unaffected.
