# Commit SHA mapping (commit messages rewritten on 2026-10-10)

Commit messages were shortened after the fact. Only the messages changed: every commit's file tree is byte-identical.
Older SHAs recorded in `benchmarks/freeze_manifest.json` (frozen commit `04bc5e5…`) and in run records (`run_meta_*.json`,
`git_commit`) refer to the left column. Check with `git rev-parse <new>^{tree}`, which must equal the tree column.

| old commit | new commit | tree (unchanged) | message |
|---|---|---|---|
| `cea5e07a110e` | `a238077ecdcd` | `0924f6ef059e` | Add core pipeline: schemas, evidence tools, verifier, conditions, runner, tests |
| `04bc5e5a8056` | `a32d2b59fb8d` | `c5139f756323` | Add benchmark, real-paper packages, DEV pilots, evaluation and annotation tooling |
| `5c6737b9c975` | `80faa2f50fc8` | `322ffd3bba8b` | Freeze protocol |
| `372a2219cfa1` | `5d2331d0c90a` | `351a8c6062a0` | Fix audit findings, withhold TEST outputs, add diagnostic design |
| `5a16432c75a2` | `7766499b0424` | `51a691a9b157` | Add amended secondary config, synthetic annotation packet, TEST results |
| `1d832760352e` | `0fe591fca9e5` | `ac9705c79f1a` | Add automatic results draft and withheld-output manifest |
| `eff172082ff4` | `a3b9fc2557b6` | `366521409d58` | Add real-paper and diagnostic results, real-paper packet, final docs |
