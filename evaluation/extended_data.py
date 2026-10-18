"""Data access for the post-freeze evaluation extension (docs/EVALUATION_EXTENSION_PROTOCOL.md).

Loads the frozen run records of one *family* (synthetic TEST, real papers, long diagnostic), and builds:

* a **text registry**: every distinct final text and every starting draft, keyed by (case, sha256(text)).
  Final texts reuse the existing opaque ``output_id`` from the private condition mapping when one exists;
  other texts (long-diagnostic outputs, real-paper outline drafts) get a new opaque ID derived from a hash.
* **sentence units**: one per distinct sentence per case, ``U-<sha256(case, text)[:10]>``. Identical
  sentences in different texts are the same unit, so they get identical claims and labels.
* the **lineage** of every (case, condition) run: its final text, its starting draft, its per-sentence
  verifier traces, and its cost/tool totals.

Nothing here talks to a model. The registry links texts to conditions, so ``write_private_registry``
writes it under ``private/extended/`` (gitignored) only; blinded packets never contain it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.package_schema import CaseRecord
from src.runner import load_cases

ROOT = Path(__file__).resolve().parent.parent
MODEL_SLUG = "deepseek__deepseek-v4-flash-0731"


@dataclass(frozen=True)
class Family:
    name: str
    runs_dir: Path
    cases_path: Path
    split: Optional[str]
    conditions: tuple[str, ...]
    mapping_path: Optional[Path]
    alias_prefix: str
    # condition -> condition whose final text is the starting draft (None for draft-only conditions)
    draft_of: dict[str, Optional[str]] = field(default_factory=dict)


FAMILIES: dict[str, Family] = {
    "synthetic": Family(
        "synthetic", ROOT / "outputs" / "synthetic" / MODEL_SLUG, ROOT / "data" / "synthetic" / "test.jsonl", "test",
        ("C1", "C2", "C3", "C4", "C5", "C6", "C7"), ROOT / "private" / "condition_mapping.csv", "K",
        {"C1": None, "C7": None, "C2": "C1", "C6": "C1", "C3": "C7", "C4": "C7", "C5": "C7"}),
    "real": Family(
        "real", ROOT / "outputs" / "real_papers_v2" / MODEL_SLUG, ROOT / "data" / "real_papers" / "packages", None,
        ("C1", "C2", "C3", "C4"), ROOT / "private" / "condition_mapping_real.csv", "RP",
        # real papers have no C7 condition: C3/C4 start from the shared outline draft ("DRAFT_OUTLINE")
        {"C1": None, "C2": "C1", "C3": "DRAFT_OUTLINE", "C4": "DRAFT_OUTLINE"}),
    "diagnostic": Family(
        "diagnostic", ROOT / "outputs" / "diagnostic" / MODEL_SLUG, ROOT / "data" / "diagnostic" / "long.jsonl", None,
        ("C7", "C3", "C4"), None, "L",
        {"C7": None, "C3": "C7", "C4": "C7"}),
}

DRAFT_STAGES = {"direct_draft", "outline_draft"}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unit_id(case_id: str, text: str) -> str:
    return "U-" + sha256(case_id + "\x00" + text.strip())[:10]


def new_text_id(family: str, case_id: str, text: str) -> str:
    prefix = {"synthetic": "S", "real": "R", "diagnostic": "D"}[family]
    return prefix + "x" + sha256(family + "\x00" + case_id + "\x00" + text)[:8]


@dataclass
class TextEntry:
    text_id: str
    case_id: str
    text: str
    sentences: list[str]
    roles: set[str] = field(default_factory=set)  # e.g. {"final:C4", "draft:C3"}

    @property
    def units(self) -> list[str]:
        return [unit_id(self.case_id, s) for s in self.sentences]


@dataclass
class RunView:
    case_id: str
    condition: str
    status: str
    final_text_id: Optional[str]
    draft_text_id: Optional[str]
    claim_traces: list[dict[str, Any]]
    totals: dict[str, Any]
    record_path: Path


@dataclass
class FamilyData:
    family: Family
    cases: dict[str, CaseRecord]
    texts: dict[str, TextEntry]
    runs: dict[tuple[str, str], RunView]
    aliases: dict[str, str]  # case_id -> alias shown to judges

    def units_of_case(self, case_id: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for t in self.texts.values():
            if t.case_id == case_id:
                for s in t.sentences:
                    out.setdefault(unit_id(case_id, s), s.strip())
        return out

    def texts_of_case(self, case_id: str) -> list[TextEntry]:
        return sorted((t for t in self.texts.values() if t.case_id == case_id), key=lambda t: t.text_id)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _aliases(fam: Family, case_ids: list[str]) -> dict[str, str]:
    if fam.name == "synthetic":
        rows = _read_csv(ROOT / "private" / "case_alias_map.csv")
        return {r["case_id"]: r["case_ref"] for r in rows}
    if fam.name == "real":
        return {c: c for c in case_ids}
    # diagnostic: seeded shuffle so aliases do not follow case order (LONG-01 ... are category-ordered)
    order = sorted(case_ids)
    random.Random(4213).shuffle(order)
    return {c: f"L{i + 1:02d}" for i, c in enumerate(order)}


def load_family(name: str, runs_dir: Optional[Path] = None) -> FamilyData:
    fam = FAMILIES[name]
    runs_dir = runs_dir or fam.runs_dir
    cases = {c.case_id: c for c in load_cases(fam.cases_path) if fam.split is None or c.split == fam.split}
    out_ids: dict[tuple[str, str], str] = {}
    if fam.mapping_path is not None and fam.mapping_path.exists():
        for r in _read_csv(fam.mapping_path):
            if r["status"] == "completed" and r["output_id"]:
                out_ids[(r["case_id"], r["text_sha256"])] = r["output_id"]

    texts: dict[str, TextEntry] = {}
    by_key: dict[tuple[str, str], str] = {}

    def register(case_id: str, text: str, sentences: list[str], role: str) -> str:
        key = (case_id, sha256(text))
        tid = by_key.get(key)
        if tid is None:
            tid = out_ids.get(key) or new_text_id(name, case_id, text)
            by_key[key] = tid
            texts[tid] = TextEntry(tid, case_id, text, [s.strip() for s in sentences])
        texts[tid].roles.add(role)
        return tid

    runs: dict[tuple[str, str], RunView] = {}
    for cond in fam.conditions:
        for case_id in sorted(cases):
            p = runs_dir / cond / f"{case_id}.json"
            if not p.exists():
                runs[(case_id, cond)] = RunView(case_id, cond, "missing", None, None, [], {}, p)
                continue
            rec = json.loads(p.read_text())
            if rec.get("status") != "completed":
                runs[(case_id, cond)] = RunView(case_id, cond, rec.get("status", "failed"), None, None, [],
                                                rec.get("totals") or {}, p)
                continue
            final = register(case_id, rec["final_passage"], [s["text"] for s in rec["final_sentences"]], f"final:{cond}")
            draft_id = None
            if fam.draft_of.get(cond):
                d = next((d for d in rec["drafts"] if d["stage"] in DRAFT_STAGES), None)
                if d is None:
                    raise ValueError(f"{p}: no starting draft for {cond}")
                draft_id = register(case_id, d["passage"], [s["text"] for s in d["sentences"]], f"draft:{cond}")
            runs[(case_id, cond)] = RunView(case_id, cond, "completed", final, draft_id, rec.get("claim_traces") or [],
                                            rec.get("totals") or {}, p)
    # consistency of the shared-draft design: every run that starts from the same upstream draft must
    # carry the identical text, and for C7/C1 lineages it must equal that condition's final text
    for case_id in cases:
        for cond, src in fam.draft_of.items():
            rv = runs.get((case_id, cond))
            if not src or rv is None or rv.status != "completed":
                continue
            if src in fam.conditions:
                up = runs.get((case_id, src))
                if up and up.status == "completed" and up.final_text_id != rv.draft_text_id:
                    raise ValueError(f"{name}/{case_id}: draft of {cond} differs from final text of {src}")
        outl = {runs[(case_id, c)].draft_text_id for c, s in fam.draft_of.items()
                if s == "DRAFT_OUTLINE" and runs[(case_id, c)].status == "completed"}
        if len(outl) > 1:
            raise ValueError(f"{name}/{case_id}: outline drafts differ across conditions")
    return FamilyData(fam, cases, texts, runs, _aliases(fam, sorted(cases)))


def write_private_registry(data: FamilyData, out_dir: Path = ROOT / "private" / "extended") -> Path:
    """Unblinding registry: which text plays which role. Coordinator-private (gitignored)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"text_registry_{data.family.name}.csv"
    rows = []
    for (case_id, cond), rv in sorted(data.runs.items()):
        rows.append({"case_id": case_id, "alias": data.aliases[case_id], "condition": cond, "status": rv.status,
                     "final_text_id": rv.final_text_id or "", "draft_text_id": rv.draft_text_id or "",
                     "final_sha256": sha256(data.texts[rv.final_text_id].text) if rv.final_text_id else ""})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path
