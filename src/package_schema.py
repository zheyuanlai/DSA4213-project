"""Model-visible research-package schemas.

`ResearchPackage` contains ONLY fields that may be shown to the backbone model.
Case metadata (case_id, category, split, pair_id) lives on `CaseRecord`, and
evaluator-only gold lives in `benchmarks/schema.py::GoldRecord` (separate file,
separate store). Rendering for prompts goes through `src/render.py`, which uses
an explicit allowlist rather than dumping whole records.

Evidence-ID conventions (stable, deterministic, derived from the package):
  table cell      T1.r2.acc        (table_id.row_id.column_id)
  table row       T1.r2
  table           T1
  stat test       S1               (test_id)
  passage         P1               (passage_id)
  comparison      exp1/cmp1        (experiment_id/comparison_id)
IDs must therefore not contain '.', '/' or whitespace.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]*$")

CATEGORIES = (
    "statistical_significance",
    "robustness",
    "generalization",
    "consistency",
    "efficiency",
    "citation_support",
    "numerical_reporting",
    "negative_results",
)
ORDINAL_CATEGORIES = CATEGORIES[:6]
SEPARATE_PROTOCOL_CATEGORIES = CATEGORIES[6:]

Category = Literal[
    "statistical_significance",
    "robustness",
    "generalization",
    "consistency",
    "efficiency",
    "citation_support",
    "numerical_reporting",
    "negative_results",
]


def _check_id(v: str) -> str:
    if not ID_RE.match(v):
        raise ValueError(f"invalid id {v!r}: must match {ID_RE.pattern}")
    return v


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Column(_Strict):
    column_id: str
    header: str
    unit: Optional[str] = None
    higher_is_better: Optional[bool] = None

    _v = field_validator("column_id")(classmethod(lambda cls, v: _check_id(v)))


class Cell(_Strict):
    text: str = Field(description="Exactly what the table shows, e.g. '83.7 ± 1.2'")
    value: Optional[float] = Field(default=None, description="Numeric point value if any")
    spread: Optional[float] = Field(default=None, description="± value shown in the cell, if any")


class Row(_Strict):
    row_id: str
    label: str
    cells: dict[str, Cell]

    _v = field_validator("row_id")(classmethod(lambda cls, v: _check_id(v)))


class ResultTable(_Strict):
    table_id: str
    caption: str
    columns: list[Column]
    rows: list[Row]
    notes: Optional[str] = None

    _v = field_validator("table_id")(classmethod(lambda cls, v: _check_id(v)))

    @model_validator(mode="after")
    def _cells_match_columns(self) -> "ResultTable":
        col_ids = [c.column_id for c in self.columns]
        if len(set(col_ids)) != len(col_ids):
            raise ValueError(f"duplicate column ids in {self.table_id}")
        row_ids = [r.row_id for r in self.rows]
        if len(set(row_ids)) != len(row_ids):
            raise ValueError(f"duplicate row ids in {self.table_id}")
        for r in self.rows:
            extra = set(r.cells) - set(col_ids)
            if extra:
                raise ValueError(f"{self.table_id}.{r.row_id} has cells for unknown columns {extra}")
        return self


class Comparison(_Strict):
    comparison_id: str
    description: str

    _v = field_validator("comparison_id")(classmethod(lambda cls, v: _check_id(v)))


class Experiment(_Strict):
    experiment_id: str
    description: str
    comparisons: list[Comparison] = Field(default_factory=list)

    _v = field_validator("experiment_id")(classmethod(lambda cls, v: _check_id(v)))


class StatTest(_Strict):
    test_id: str
    experiment_id: str
    comparison_id: str
    test_name: str = Field(description="e.g. 'paired t-test', 'Wilcoxon signed-rank test'")
    sidedness: Optional[Literal["two-sided", "one-sided"]] = None
    paired: Optional[bool] = None
    n: Optional[int] = None
    n_unit: Optional[str] = Field(default=None, description="what n counts, e.g. 'random seeds'")
    statistic_name: Optional[str] = None
    statistic: Optional[float] = None
    df: Optional[float] = None
    p_value: Optional[float] = None
    p_value_text: Optional[str] = Field(default=None, description="as printed, e.g. 'p < 0.001'")
    alpha: Optional[float] = None
    ci_level: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    effect_description: Optional[str] = Field(default=None, description="what the CI/estimate is of")
    multiple_comparison_adjustment: Optional[str] = None
    notes: Optional[str] = None

    _v = field_validator("test_id", "experiment_id", "comparison_id")(
        classmethod(lambda cls, v: _check_id(v))
    )


class SourcePassage(_Strict):
    passage_id: str
    citation_key: str = Field(description="e.g. 'Okafor et al. (2023)' — fictional for synthetic cases")
    source_title: str
    text: str

    _v = field_validator("passage_id")(classmethod(lambda cls, v: _check_id(v)))


class ResearchPackage(_Strict):
    """Everything here MAY be shown to the backbone model. Nothing else may."""

    question: str
    methods_summary: str
    experimental_setup: str
    experiments: list[Experiment] = Field(default_factory=list)
    results_tables: list[ResultTable] = Field(default_factory=list)
    statistical_tests: list[StatTest] = Field(default_factory=list)
    source_passages: list[SourcePassage] = Field(default_factory=list)
    task_instruction: str

    @model_validator(mode="after")
    def _unique_ids(self) -> "ResearchPackage":
        def dup(xs):
            return {x for x in xs if xs.count(x) > 1}

        for name, ids in [
            ("table", [t.table_id for t in self.results_tables]),
            ("test", [s.test_id for s in self.statistical_tests]),
            ("passage", [p.passage_id for p in self.source_passages]),
            ("experiment", [e.experiment_id for e in self.experiments]),
        ]:
            d = dup(ids)
            if d:
                raise ValueError(f"duplicate {name} ids: {d}")
        comps = {(e.experiment_id, c.comparison_id) for e in self.experiments for c in e.comparisons}
        for s in self.statistical_tests:
            if (s.experiment_id, s.comparison_id) not in comps:
                raise ValueError(
                    f"test {s.test_id} references unknown comparison {s.experiment_id}/{s.comparison_id}"
                )
        return self


class SourceManifest(_Strict):
    origin: Literal["synthetic_original", "real_paper_derived", "long_package_diagnostic"]
    notes: str = ""
    citation: Optional[str] = None
    url: Optional[str] = None
    license: Optional[str] = None
    retrieved_on: Optional[str] = None
    extraction_method: Optional[str] = None
    sha256_of_source: Optional[str] = None


class CaseRecord(_Strict):
    """Public case record = metadata (never rendered to the model) + package."""

    case_id: str
    category: Optional[Category] = None  # None for real-paper packages
    split: Literal["dev", "test", "real", "diagnostic"]
    pair_id: Optional[str] = None
    package: ResearchPackage
    source_manifest: SourceManifest

    @field_validator("case_id")
    @classmethod
    def _cid(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError(f"bad case_id {v!r}")
        return v


class EvidenceItem(_Strict):
    """One addressable unit in the deterministic evidence store."""

    evidence_id: str
    kind: Literal["table_cell", "table_row", "table", "stat_test", "passage", "comparison"]
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    column_id: Optional[str] = None
    label: str = ""
    text: str = ""
    value: Optional[float] = None
    spread: Optional[float] = None
    unit: Optional[str] = None
    higher_is_better: Optional[bool] = None
    provenance: str = Field(default="", description="where in the package this came from")
    validity_bounds: Optional[str] = Field(
        default=None, description="scope note, e.g. the table caption / test scope"
    )
