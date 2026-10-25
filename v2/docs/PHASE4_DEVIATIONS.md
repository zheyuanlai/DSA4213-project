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
