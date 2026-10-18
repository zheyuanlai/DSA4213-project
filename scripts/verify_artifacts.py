"""Integrity audit of frozen inputs, frozen AI annotations and published results.

    python scripts/verify_artifacts.py                 # checks that need only the public repository (CI)
    python scripts/verify_artifacts.py --regenerate    # coordinator: also re-derive results and require no diff

Checks (PASS / FAIL / SKIP when an input is not available, e.g. private/ in CI):
  1. frozen protocol files: only the documented post-freeze changes differ from benchmarks/freeze_manifest.json
  2. private TEST gold and diagnostic gold match their frozen hashes (coordinator only)
  3. withheld raw outputs match outputs/WITHHELD_UNTIL_ANNOTATION.json (coordinator only)
  4. frozen extension artifacts: claims, checklists and every consensus manifest (primary and replicate)
  5. nothing private is tracked by git (private/, withheld outputs, keys); public results carry no output IDs
  6. with --regenerate: score/report/majority/stability are re-run from frozen consensus and every file under
     results/ and annotation/ is byte-identical before and after
Exit status is non-zero if any check fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Frozen files changed after the freeze, each documented in docs/DEVIATIONS_FROM_PROPOSAL.md / docs/FINAL_AUDIT.md
# (audit fixes before any packet release, a documentation correction, and post-run hardening/blinding guards).
DOCUMENTED_POST_FREEZE = {
    "annotation/ANNOTATION_GUIDE.md", "docs/BENCHMARK_SPEC.md", "evaluation/auto_metrics.py",
    "evaluation/score_human.py", "src/agent.py", "src/runner.py", "src/security_scan.py", "src/verifier.py",
}
RESULTS: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def check_freeze() -> None:
    from scripts.freeze_protocol import MANIFEST, tracked_hashes
    m = json.loads(MANIFEST.read_text())
    now = tracked_hashes(ROOT / m.get("config", "configs/frozen_primary.yaml"))
    changed = {k for k in m["file_sha256"] if m["file_sha256"][k] != now.get(k)}
    unexpected = sorted(changed - DOCUMENTED_POST_FREEZE)
    record("frozen protocol files", "FAIL" if unexpected else "PASS",
           f"undocumented changes {unexpected}" if unexpected else f"{len(changed)} documented post-freeze changes only")


def check_private_gold() -> None:
    gold = ROOT / "private" / "gold" / "test_gold.jsonl"
    if not gold.exists():
        record("TEST gold hash", "SKIP", "private/ not present")
        return
    manifest_text = (ROOT / "benchmarks" / "freeze_manifest.json").read_text()
    record("TEST gold hash", "PASS" if sha(gold) in manifest_text else "FAIL")
    dg = ROOT / "private" / "gold" / "diagnostic_gold.jsonl"
    dh = ROOT / "benchmarks" / "diagnostic_hashes.json"
    if dg.exists() and dh.exists():
        record("diagnostic gold hash", "PASS" if sha(dg) in dh.read_text() else "FAIL")


def check_withheld() -> None:
    m = json.loads((ROOT / "outputs" / "WITHHELD_UNTIL_ANNOTATION.json").read_text())
    items = m.get("files", m) if isinstance(m, dict) else m
    if isinstance(items, dict):
        items = [{"path": k, "sha256": v} for k, v in items.items()]
    present = [it for it in items if (ROOT / it["path"]).exists()]
    if not present:
        record("withheld raw outputs", "SKIP", "withheld outputs not present")
        return
    bad = [it["path"] for it in present if sha(ROOT / it["path"]) != it["sha256"]]
    record("withheld raw outputs", "FAIL" if bad else "PASS",
           f"{len(bad)} mismatches, e.g. {bad[:2]}" if bad else f"{len(present)} files match")


def check_extension() -> None:
    ext = ROOT / "annotation" / "ai_extended"
    for fam in ("real", "diagnostic"):
        p = ext / "checklists" / f"{fam}.json"
        ok = sha(p) == (ext / "checklists" / f"{fam}.sha256").read_text().strip()
        record(f"frozen checklist {fam}", "PASS" if ok else "FAIL")
    claims = sum(1 for f in ("synthetic", "real", "diagnostic") for _ in open(ext / "claims" / f"{f}.jsonl"))
    record("frozen atomic claims", "PASS" if claims == 1591 else "FAIL", f"{claims} claims")
    for man in sorted(ext.rglob("MANIFEST_*.json")):
        m = json.loads(man.read_text())
        bad = [k for k, v in m.items() if sha(ROOT / v["path"]) != v["sha256"]]
        record(f"consensus {man.relative_to(ext)}", "FAIL" if bad else "PASS", f"changed: {bad}" if bad else "")


def check_tracked() -> None:
    tracked = git("ls-files").splitlines()
    leaks = [t for t in tracked if t.startswith(("private/", "outputs/synthetic/", "outputs/real_papers/",
                                                 "outputs/real_papers_v2/")) or t in (".env",) or t.endswith(".key")]
    record("no private or withheld files tracked", "FAIL" if leaks else "PASS", f"{leaks[:3]}" if leaks else "")
    key_re = re.compile(r"sk-or-v1-[0-9a-f]{20,}")
    hits = [t for t in tracked if (ROOT / t).is_file() and (ROOT / t).stat().st_size < 20_000_000
            and key_re.search((ROOT / t).read_text(errors="ignore"))]
    record("no API keys in tracked files", "FAIL" if hits else "PASS", f"{hits[:3]}" if hits else "")
    ids = [p for p in (ROOT / "results" / "ai_extended").glob("*/results.json") if '"text_id"' in p.read_text()]
    record("public results carry no output IDs", "FAIL" if ids else "PASS", f"{ids}" if ids else "")


def check_regeneration() -> None:
    if not (ROOT / "private" / "condition_mapping.csv").exists():
        record("results regenerate without change", "SKIP", "needs private/ (unblinded scoring)")
        return
    def snapshot() -> dict[str, str]:
        return {str(p.relative_to(ROOT)): sha(p) for d in ("results", "annotation") for p in (ROOT / d).rglob("*")
                if p.is_file()}

    before = snapshot()
    py = sys.executable
    for stage in (["score"], ["report"], ["majority"], ["stability", "--replicate", "r1"]):
        subprocess.run([py, "scripts/run_extended_evaluation.py", *stage], cwd=ROOT, check=True, capture_output=True)
    after = snapshot()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    record("results regenerate without change", "FAIL" if changed else "PASS", f"changed: {changed[:5]}" if changed else
           "score, report, majority and stability reproduce the existing files byte for byte")
    dirty = git("status", "--porcelain", "--", "results/", "annotation/").strip()
    if dirty:
        print(f"  note: results/ or annotation/ differ from the last commit:\n{dirty[:300]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerate", action="store_true")
    a = ap.parse_args(argv)
    check_freeze()
    check_private_gold()
    check_withheld()
    check_extension()
    check_tracked()
    if a.regenerate:
        check_regeneration()
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print(f"\n{len(RESULTS)} checks: {sum(r[1] == 'PASS' for r in RESULTS)} pass, {len(fails)} fail, "
          f"{sum(r[1] == 'SKIP' for r in RESULTS)} skipped")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
