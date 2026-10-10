"""Deterministic, package-faithful evidence store.

Built ONLY from a `ResearchPackage` (never from gold). Every addressable unit gets
a stable evidence ID (see `src/package_schema.py` for conventions). Tools in
`src/tools.py` read from this store; model-generated IDs are validated against it
and can never create new "evidence".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.package_schema import EvidenceItem, ResearchPackage, StatTest

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_STOP = set(
    "a an the of and or to in on for with by from is are was were be been that this these those as at it its we our their "
    "than then into over under about which who whom what when where how not no".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP]


@dataclass
class EvidenceStore:
    package: ResearchPackage
    items: dict[str, EvidenceItem] = field(default_factory=dict)
    tests_by_comparison: dict[tuple[str, str], list[StatTest]] = field(default_factory=dict)

    @classmethod
    def from_package(cls, pkg: ResearchPackage) -> "EvidenceStore":
        st = cls(package=pkg)
        for t in pkg.results_tables:
            st._add(
                EvidenceItem(
                    evidence_id=t.table_id,
                    kind="table",
                    table_id=t.table_id,
                    label=t.caption,
                    text=t.caption,
                    provenance=f"table {t.table_id}",
                    validity_bounds=(t.notes or None),
                )
            )
            cols = {c.column_id: c for c in t.columns}
            for r in t.rows:
                st._add(
                    EvidenceItem(
                        evidence_id=f"{t.table_id}.{r.row_id}",
                        kind="table_row",
                        table_id=t.table_id,
                        row_id=r.row_id,
                        label=r.label,
                        text="; ".join(f"{cols[c].header}: {cell.text}" for c, cell in r.cells.items()),
                        provenance=f"table {t.table_id}, row {r.row_id}",
                        validity_bounds=t.caption,
                    )
                )
                for cid, cell in r.cells.items():
                    col = cols[cid]
                    st._add(
                        EvidenceItem(
                            evidence_id=f"{t.table_id}.{r.row_id}.{cid}",
                            kind="table_cell",
                            table_id=t.table_id,
                            row_id=r.row_id,
                            column_id=cid,
                            label=f"{r.label} / {col.header}",
                            text=cell.text,
                            value=cell.value,
                            spread=cell.spread,
                            unit=col.unit,
                            higher_is_better=col.higher_is_better,
                            provenance=f"table {t.table_id}, row {r.row_id}, column {cid}",
                            validity_bounds=t.caption,
                        )
                    )
        for e in pkg.experiments:
            for c in e.comparisons:
                st._add(
                    EvidenceItem(
                        evidence_id=f"{e.experiment_id}/{c.comparison_id}",
                        kind="comparison",
                        label=c.description,
                        text=c.description,
                        provenance=f"experiment {e.experiment_id}: {e.description}",
                    )
                )
        for s in pkg.statistical_tests:
            st._add(
                EvidenceItem(
                    evidence_id=s.test_id,
                    kind="stat_test",
                    label=s.test_name,
                    text=format_test(s),
                    value=s.p_value,
                    provenance=f"statistical test for {s.experiment_id}/{s.comparison_id}",
                    validity_bounds=s.effect_description,
                )
            )
            st.tests_by_comparison.setdefault((s.experiment_id, s.comparison_id), []).append(s)
        for p in pkg.source_passages:
            st._add(
                EvidenceItem(
                    evidence_id=p.passage_id,
                    kind="passage",
                    label=f"{p.citation_key}: {p.source_title}",
                    text=p.text,
                    provenance=f"supplied excerpt from {p.citation_key}",
                )
            )
        return st

    def _add(self, item: EvidenceItem) -> None:
        if item.evidence_id in self.items:
            raise ValueError(f"duplicate evidence id {item.evidence_id}")
        self.items[item.evidence_id] = item

    # ------------------------------------------------------------------ queries
    def has(self, evidence_id: str) -> bool:
        return evidence_id in self.items

    def get(self, evidence_id: str) -> EvidenceItem | None:
        return self.items.get(evidence_id)

    def table(self, table_id: str):
        for t in self.package.results_tables:
            if t.table_id == table_id:
                return t
        return None

    def comparisons(self) -> list[tuple[str, str, str]]:
        return [
            (e.experiment_id, c.comparison_id, c.description)
            for e in self.package.experiments
            for c in e.comparisons
        ]

    def search_passages(self, query: str, k: int = 2) -> list[tuple[float, str]]:
        """Deterministic lexical retrieval over supplied passages only (no web)."""
        q = set(tokenize(query))
        scored = []
        for p in self.package.source_passages:
            toks = tokenize(f"{p.citation_key} {p.source_title} {p.text}")
            if not toks or not q:
                continue
            overlap = len(q & set(toks))
            if overlap == 0:
                continue
            score = overlap / (len(q) ** 0.5 * len(set(toks)) ** 0.5)
            scored.append((round(score, 6), p.passage_id))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[:k]


def format_test(s: StatTest) -> str:
    parts = [s.test_name]
    if s.sidedness:
        parts.append(s.sidedness)
    if s.paired is not None:
        parts.append("paired" if s.paired else "unpaired")
    if s.n is not None:
        parts.append(f"n={s.n}" + (f" {s.n_unit}" if s.n_unit else ""))
    if s.statistic is not None:
        parts.append(f"{s.statistic_name or 'statistic'}={s.statistic:g}" + (f" (df={s.df:g})" if s.df is not None else ""))
    if s.p_value_text:
        parts.append(s.p_value_text)
    elif s.p_value is not None:
        parts.append(f"p={s.p_value:g}")
    if s.ci_low is not None and s.ci_high is not None:
        lvl = f"{int(round((s.ci_level or 0.95) * 100))}% CI"
        parts.append(f"{lvl} [{s.ci_low:g}, {s.ci_high:g}]" + (f" for {s.effect_description}" if s.effect_description else ""))
    elif s.effect_description:
        parts.append(f"effect: {s.effect_description}")
    if s.alpha is not None:
        parts.append(f"alpha={s.alpha:g}")
    if s.multiple_comparison_adjustment:
        parts.append(f"adjustment: {s.multiple_comparison_adjustment}")
    if s.notes:
        parts.append(f"note: {s.notes}")
    return "; ".join(parts)
