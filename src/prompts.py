"""Versioned prompt loading. Every prompt file is hashed; hashes go into run records."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_FILES = (
    "common_reporting.md",
    "writer_direct.md",
    "claim_outline.md",
    "draft_writer.md",
    "reviewer_generic.md",
    "reviser_generic.md",
    "verifier_adaptive.md",
    "verifier_scripted.md",
)

DECISION_DEFS = {
    "ACCEPT": "ACCEPT — the claim is supported as stated, at the right strength and scope.",
    "WEAKEN": (
        "WEAKEN — the claim is stronger or broader than the evidence supports, or misstates it (e.g. unsupported "
        "significance, generality, robustness, speed, consistency or attribution, or a wrong number); give the "
        "corrected, narrower sentence in revised_text."
    ),
    "STRENGTHEN": (
        "STRENGTHEN — the evidence supports a stronger or more informative claim than the sentence makes (e.g. it "
        "omits a reported valid test result or understates a complete evaluation); give the corrected, stronger "
        "sentence in revised_text, scoped to what was evaluated."
    ),
    "REMOVE": "REMOVE — the claim has no support in the evidence and no defensible narrower version is worth keeping.",
    "FLAG": "FLAG — support cannot be determined with the available tools; the sentence is kept unchanged and flagged.",
}
NO_STRENGTHEN_NOTE = (
    "(Strengthening is not available in this configuration. If a sentence is accurate but weaker than the evidence "
    "would allow, ACCEPT it.)"
)


@lru_cache(maxsize=None)
def load(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def prompt_hashes() -> dict[str, str]:
    return {n: sha256_text(load(n))[:16] for n in PROMPT_FILES}


def decision_block(allowed: list[str]) -> str:
    lines = [f"- {DECISION_DEFS[d]}" for d in allowed]
    if "STRENGTHEN" not in allowed:
        lines.append(NO_STRENGTHEN_NOTE)
    return "\n".join(lines)


def system_prompt(role_file: str, **subs: str) -> str:
    body = load(role_file)
    for k, v in subs.items():
        body = body.replace("{{" + k + "}}", v)
    if "{{" in body:
        raise ValueError(f"unfilled placeholder in {role_file}")
    return load("common_reporting.md").strip() + "\n\n" + body.strip()
