"""Secret / privacy scanner for the working tree, the git index and the full git history.

Never prints matched secret text: findings report only file, line/commit and pattern name.
The live key (if present in the environment) is checked in full and as fragments.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

GENERIC_PATTERNS = {
    "openrouter_key": re.compile(r"sk-or-v1-[0-9a-f]{32,}"),
    "openrouter_redacted_label": re.compile(r"sk-or-v1-[0-9a-f]{2,8}\.\.\.[0-9a-f]{2,8}"),
    "openai_style_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer_header": re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9\-_\.]{20,}", re.I),
    "nus_student_number": re.compile(r"\bA0\d{6}[A-Z]\b"),
}
FORBIDDEN_TRACKED = [
    re.compile(r"(^|/)\.env$"), re.compile(r"(^|/)\.env\.(?!example$)"), re.compile(r"^private/"),
    re.compile(r"condition_mapping"), re.compile(r"PRIVATE_EXECUTION", re.I), re.compile(r"openrouter\.env$"),
    re.compile(r"^data/real_papers/raw/"), re.compile(r"(^|/)test_gold\.jsonl$"),
    # withheld until blind annotation ends (remove these two lines in the release commit)
    re.compile(r"^outputs/synthetic/"), re.compile(r"^outputs/real_papers/"),
]
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".pyc", ".ico", ".woff", ".woff2"}


@dataclass
class Finding:
    where: str
    pattern: str

    def __str__(self) -> str:
        return f"{self.where}: {self.pattern}"


def live_secret_patterns(env_var: str = "OPENROUTER_API_KEY") -> dict[str, re.Pattern]:
    key = os.environ.get(env_var, "").strip()
    pats: dict[str, re.Pattern] = {}
    if len(key) >= 24:
        body = key.split("-")[-1]
        pats["live_key_full"] = re.compile(re.escape(key))
        if len(body) >= 32:
            pats["live_key_fragment_head"] = re.compile(re.escape(body[:16]))
            pats["live_key_fragment_tail"] = re.compile(re.escape(body[-16:]))
            pats["live_key_fragment_mid"] = re.compile(re.escape(body[24:40]))
    return pats


def scan_text(text: str, where: str, patterns: dict[str, re.Pattern]) -> list[Finding]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for name, pat in patterns.items():
            if pat.search(line):
                out.append(Finding(f"{where}:{i}", name))
    return out


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def candidate_files(root: Path) -> list[str]:
    """Tracked + untracked-but-not-ignored files (what a commit could include)."""
    try:
        out = _git(root, "ls-files", "--cached", "--others", "--exclude-standard")
        return [x for x in out.splitlines() if x]
    except Exception:
        return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def scan_tree(root: Path, patterns: dict[str, re.Pattern]) -> list[Finding]:
    findings = []
    for rel in candidate_files(root):
        p = root / rel
        if not p.is_file() or p.suffix.lower() in BINARY_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        findings += scan_text(text, rel, patterns)
        for fp in FORBIDDEN_TRACKED:
            if fp.search(rel):
                findings.append(Finding(rel, "forbidden_file_would_be_committed"))
    return findings


def scan_history(root: Path, patterns: dict[str, re.Pattern]) -> list[Finding]:
    findings = []
    try:
        revs = _git(root, "rev-list", "--all").split()
    except Exception:
        return findings
    seen_blobs: set[str] = set()
    for rev in revs:
        tree = _git(root, "ls-tree", "-r", rev)
        for line in tree.splitlines():
            meta, path = line.split("\t", 1)
            _, typ, blob = meta.split()
            for fp in FORBIDDEN_TRACKED:
                if fp.search(path):
                    findings.append(Finding(f"{rev[:10]}:{path}", "forbidden_file_in_history"))
            if typ != "blob" or blob in seen_blobs or Path(path).suffix.lower() in BINARY_EXT:
                continue
            seen_blobs.add(blob)
            text = subprocess.run(["git", "cat-file", "-p", blob], cwd=root, capture_output=True).stdout.decode("utf-8", "ignore")
            findings += [Finding(f"{rev[:10]}:{f.where}", f.pattern) for f in scan_text(text, path, patterns)]
    # commit messages
    try:
        msgs = _git(root, "log", "--all", "--format=%H%x00%B%x01")
        for chunk in msgs.split("\x01"):
            if "\x00" in chunk:
                h, body = chunk.split("\x00", 1)
                findings += [Finding(f"commit-msg {h.strip()[:10]}", f.pattern) for f in scan_text(body, "", patterns)]
    except Exception:
        pass
    return findings


def run_scan(root: Path, include_history: bool = True) -> list[Finding]:
    pats = {**GENERIC_PATTERNS, **live_secret_patterns()}
    f = scan_tree(root, pats)
    if include_history and (root / ".git").exists():
        f += scan_history(root, pats)
    # de-duplicate
    uniq = {(x.where, x.pattern): x for x in f}
    return list(uniq.values())
