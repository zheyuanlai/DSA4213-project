"""Deterministic checks for an authored Phase 4 pair (no model calls).

Reuses V1's package schema, evidence store, statistical-test check, cell checks and rubric-leak patterns
(`benchmarks/validate.py`). Adds the V2 pair checks: the two packages differ only around the declared contrast, the
decisive evidence exists and differs, draft numbers exist in the packages, no DEV/TEST name reuse, and draft rules.
`check_pair` returns (errors, warnings). Errors block the item set; warnings are reviewed by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from benchmarks.validate import LEAK_PATTERNS, NUM_RE, check_stat_test
from src.evidence_store import EvidenceStore
from src.package_schema import ResearchPackage

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / "v2" / "benchmarks" / "phase4_pairs_spec.json").read_text(encoding="utf-8"))
PAIR_SPEC = {p["pair_id"]: p for p in SPEC["pairs"]}
DRAFT_KEYS = ("U", "U2", "S", "Z")
MAX_DIFF_LEAVES = 14


def known_names() -> set[str]:
    """Hyphenated names, row labels and citation keys used in V1 DEV and TEST packages (must not be reused)."""
    names: set[str] = set()
    for f in ("dev.jsonl", "test.jsonl"):
        for line in (ROOT / "data" / "synthetic" / f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            p = json.loads(line)["package"]
            txt = json.dumps(p, ensure_ascii=False)
            names |= set(re.findall(r"\b[A-Z][a-z]+(?:-[A-Z0-9][A-Za-z0-9]*)+\b", txt))
            for t in p["results_tables"]:
                for r in t["rows"]:
                    lab = r["label"].split(" (")[0].strip()
                    if re.match(r"^[A-Z][A-Za-z0-9\-]{3,}$", lab):
                        names.add(lab)
            for s in p["source_passages"]:
                names.add(s["citation_key"].split(" (")[0].split(" et al")[0].split(" &")[0].strip())
    generic = {"Macro-F1", "Insurance", "Telecom", "Utilities", "Banking", "Travel", "Mean"}
    return {n for n in names if len(n) >= 4 and n not in generic}


def _leaves(x: Any, path: str = "") -> dict[str, Any]:
    if isinstance(x, dict):
        out: dict[str, Any] = {}
        for k, v in x.items():
            out.update(_leaves(v, f"{path}/{k}"))
        return out
    if isinstance(x, list):
        out = {}
        for i, v in enumerate(x):
            key = v.get("table_id") or v.get("row_id") or v.get("test_id") or v.get("passage_id") or \
                v.get("experiment_id") or v.get("comparison_id") or v.get("column_id") or str(i) \
                if isinstance(v, dict) else str(i)
            out.update(_leaves(v, f"{path}[{key}]"))
        return out
    return {path: x}


def package_diff(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    la, lb = _leaves(a), _leaves(b)
    return sorted(k for k in set(la) | set(lb) if la.get(k) != lb.get(k))


def package_numbers(pkg: dict[str, Any]) -> set[float]:
    txt = json.dumps(pkg, ensure_ascii=False).replace(",", "")
    out = set()
    for tok in NUM_RE.findall(txt.replace("−", "-")):
        try:
            out.add(round(abs(float(tok)), 6))
        except ValueError:
            pass
    return out


def draft_numbers(text: str) -> list[float]:
    out = []
    for tok in NUM_RE.findall(text.replace(",", "").replace("−", "-")):
        v = abs(float(tok))
        out.append(round(v, 6))
    return out


def check_package(name: str, raw: dict[str, Any]) -> tuple[list[str], ResearchPackage | None]:
    errs: list[str] = []
    try:
        pkg = ResearchPackage.model_validate(raw)
    except Exception as e:  # pydantic error text is informative enough for a repair turn
        return [f"{name}: package schema: {str(e)[:600]}"], None
    try:
        EvidenceStore.from_package(pkg)
    except Exception as e:
        return [f"{name}: evidence store: {e}"], None
    for t in pkg.results_tables:
        for r in t.rows:
            for cid, cell in r.cells.items():
                nums = NUM_RE.findall(cell.text.replace(",", ""))
                if cell.value is not None and (not nums or abs(float(nums[0].replace("−", "-")) - cell.value) > 1e-6):
                    errs.append(f"{name}: {t.table_id}.{r.row_id}.{cid} value {cell.value} != text {cell.text!r}")
                if cell.spread is not None and "±" not in cell.text:
                    errs.append(f"{name}: {t.table_id}.{r.row_id}.{cid} spread set but no ± in text")
    for s in pkg.statistical_tests:
        errs += check_stat_test(name, s)
    visible = json.dumps(pkg.model_dump(), ensure_ascii=False).lower()
    for pat in LEAK_PATTERNS:
        if re.search(pat, visible):
            errs.append(f"{name}: package contains rubric word matching {pat!r}")
    if len(visible) > 12000:
        errs.append(f"{name}: package too long ({len(visible)} chars)")
    return errs, pkg


def check_pair(obj: dict[str, Any], avoid: set[str] | None = None) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warn: list[str] = []
    pid = obj.get("pair_id")
    spec = PAIR_SPEC.get(pid)
    if spec is None:
        return [f"unknown pair_id {pid!r}"], []
    for k in ("focal_proposition", "level_descriptors", "pair_contrast", "decisive_evidence_ids", "strong_package",
              "partner_package", "drafts"):
        if k not in obj:
            errs.append(f"{pid}: missing field {k}")
    if errs:
        return errs, warn
    e1, strong = check_package(f"{pid}/strong", obj["strong_package"])
    e2, partner = check_package(f"{pid}/partner", obj["partner_package"])
    errs += e1 + e2
    if strong is None or partner is None:
        return errs, warn
    sd, pd = strong.model_dump(), partner.model_dump()
    for f in ("question", "task_instruction"):
        if sd[f] != pd[f]:
            errs.append(f"{pid}: {f} differs between members")
    diff = package_diff(sd, pd)
    if not diff:
        errs.append(f"{pid}: packages are identical")
    elif len(diff) > MAX_DIFF_LEAVES:
        warn.append(f"{pid}: packages differ in {len(diff)} fields (review that only the contrast differs): {diff[:8]}")
    ss, ps = EvidenceStore.from_package(strong), EvidenceStore.from_package(partner)
    dec = obj["decisive_evidence_ids"]
    if not dec:
        errs.append(f"{pid}: no decisive evidence ids")
    for d in dec:
        if not ss.has(d):
            errs.append(f"{pid}: decisive id {d!r} not in strong package")
    def _differs(d: str) -> bool:
        """A decisive ID differs if any evidence item at or under it (a table's rows and cells, a row's cells) differs
        in text, value or scope note between members, or is missing in the partner."""
        keys = [k for k in ss.items if k == d or k.startswith(d + ".")]
        for k in keys:
            a, b = ss.get(k), ps.get(k)
            if b is None or (a.text, a.value, a.validity_bounds) != (b.text, b.value, b.validity_bounds):
                return True
        return False

    if dec and not any(_differs(d) for d in dec if ss.has(d)):
        errs.append(f"{pid}: decisive evidence is identical in both members")
    drafts = {d.get("key"): d for d in obj["drafts"]}
    need = ["U", "U2", "S"] + (["Z"] if spec["partner_level"] == 0 else [])
    for k in need:
        if k not in drafts:
            errs.append(f"{pid}: missing draft {k}")
    extra = set(drafts) - set(need)
    if extra:
        errs.append(f"{pid}: unexpected drafts {sorted(extra)}")
    want_level = {"U": 1, "U2": 1, "S": 2, "Z": 0}
    sn, pn = package_numbers(sd), package_numbers(pd)
    for k, d in drafts.items():
        if k not in want_level:
            continue
        text = d.get("text", "")
        if d.get("expressed_level") != want_level[k]:
            errs.append(f"{pid}/{k}: expressed_level must be {want_level[k]}")
        if len(text.split()) > 40:
            errs.append(f"{pid}/{k}: draft longer than 40 words")
        if re.search(r"\b(T\d+\.r\d+|S\d+|P\d+|exp\d+)\b", text):
            errs.append(f"{pid}/{k}: draft contains evidence IDs")
        for pat in LEAK_PATTERNS:
            if re.search(pat, text.lower()):
                errs.append(f"{pid}/{k}: draft contains rubric word matching {pat!r}")
        nums = draft_numbers(text)
        home = sn if k == "S" else (pn if k == "Z" else sn)
        # small integers are usually counts written as words in the package ("five tasks"): warn only
        small = lambda n: n == int(n) and n <= 10  # noqa: E731
        missing = [n for n in nums if n not in home]
        where = "partner" if k == "Z" else "strong"
        if [n for n in missing if not small(n)]:
            errs.append(f"{pid}/{k}: numbers {[n for n in missing if not small(n)]} not found in the {where} package")
        if [n for n in missing if small(n)]:
            warn.append(f"{pid}/{k}: small numbers {[n for n in missing if small(n)]} not found in the {where} package")
        if k in ("U", "U2") and spec["partner_level"] == 1:
            miss_p = [n for n in nums if n not in pn and not small(n)]
            if miss_p:
                errs.append(f"{pid}/{k}: numbers {miss_p} not in partner package (U/U2 must be accurate on a level-1 partner)")
        for h in d.get("writer_evidence_hints", []):
            if not ss.has(h) and not ps.has(h):
                warn.append(f"{pid}/{k}: hint {h!r} not in either package")
    if drafts.get("U", {}).get("text", "").strip().lower() == drafts.get("U2", {}).get("text", "").strip().lower():
        errs.append(f"{pid}: U and U2 are identical")
    avoid = known_names() if avoid is None else avoid
    blob = json.dumps({"s": sd, "p": pd, "d": obj["drafts"]}, ensure_ascii=False)
    reused = sorted(n for n in avoid if re.search(rf"\b{re.escape(n)}\b", blob))
    if reused:
        errs.append(f"{pid}: reuses V1 benchmark names {reused}")
    return errs, warn
