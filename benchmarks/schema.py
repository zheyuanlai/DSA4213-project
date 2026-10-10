"""Benchmark authoring + evaluator-only gold schemas.

An authored case (`AuthoredCase`) = public `CaseRecord` fields + a `GoldRecord`.
`benchmarks/build.py` splits each authored case with an explicit allowlist into
  * public package  -> data/synthetic/{dev,test}.jsonl            (model-visible)
  * annotator rubric-> data/synthetic/rubrics/{dev,test}.jsonl    (no gold level)
  * gold            -> data/synthetic/gold/dev_gold.jsonl         (DEV: public)
                       private/gold/test_gold.jsonl               (TEST: coordinator-only
                                                                    until annotation ends)
Gold is NEVER read by the inference runner (enforced by tests/test_gold_leakage.py).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.package_schema import (
    ORDINAL_CATEGORIES,
    Category,
    CaseRecord,
    ResearchPackage,
    SourceManifest,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequiredFinding(_Strict):
    finding_id: str
    description: str = Field(description="What a complete report must convey, in plain words")
    evidence_ids: list[str] = Field(default_factory=list)
    polarity: Literal["positive", "negative", "null", "mixed", "neutral"] = "neutral"


class ForbiddenClaim(_Strict):
    claim_id: str
    description: str
    claim_type: Literal[
        "unsupported_significance",
        "equivalence_from_nonsignificance",
        "unsupported_robustness",
        "unsupported_generalization",
        "overgeneralized_consistency",
        "unsupported_speedup",
        "misattributed_citation",
        "practical_importance_overclaim",
        "negative_reframed_as_positive",
        "omitted_negative",
        "wrong_number",
        "wrong_direction",
        "wrong_unit",
        "wrong_row_or_dataset",
        "fabricated_statistic",
        "other",
    ]


class NumericFact(_Strict):
    fact_id: str
    description: str
    value: float
    tolerance: float = Field(description="absolute tolerance for a match, e.g. 0.05 for 1-dp values")
    unit: Optional[str] = None
    evidence_id: str = Field(description="cell / test id the value comes from (or 'derived')")
    entity: str = Field(description="method/dataset association the number must be attached to")
    derivation: Optional[str] = Field(default=None, description="if derived, e.g. 'T1.r1.wer - T1.r2.wer'")


class GoldRecord(_Strict):
    case_id: str
    category: Category
    scoring_protocol: Literal["ordinal", "numerical", "negative"]
    # ordinal-only -----------------------------------------------------------
    focal_proposition: Optional[str] = Field(
        default=None, description="The proposition whose expressed strength is graded"
    )
    level_descriptors: Optional[dict[str, str]] = Field(
        default=None,
        description="Case-specific description of what an output expressing level 0/1/2 says. "
        "Shown to annotators (does not reveal which level is gold).",
    )
    gold_level: Optional[int] = Field(default=None, ge=0, le=2)
    # all --------------------------------------------------------------------
    gold_decision: str = Field(description="One-line statement of the correct reporting decision")
    justification: str
    evidence_ids: list[str]
    required_findings: list[RequiredFinding] = Field(default_factory=list)
    forbidden_claims: list[ForbiddenClaim] = Field(default_factory=list)
    numeric_facts: list[NumericFact] = Field(default_factory=list)
    pair_contrast: str = Field(description="What single evidence fact differs from the pair partner")

    @model_validator(mode="after")
    def _protocol_fields(self) -> "GoldRecord":
        if self.category in ORDINAL_CATEGORIES:
            if self.scoring_protocol != "ordinal":
                raise ValueError(f"{self.case_id}: ordinal category needs ordinal protocol")
            if self.gold_level is None or not self.focal_proposition or not self.level_descriptors:
                raise ValueError(f"{self.case_id}: ordinal case needs gold_level, focal_proposition, level_descriptors")
            if set(self.level_descriptors) != {"0", "1", "2"}:
                raise ValueError(f"{self.case_id}: level_descriptors must have keys '0','1','2'")
        else:
            if self.gold_level is not None:
                raise ValueError(f"{self.case_id}: non-ordinal category must not have gold_level")
            want = "numerical" if self.category == "numerical_reporting" else "negative"
            if self.scoring_protocol != want:
                raise ValueError(f"{self.case_id}: expected protocol {want}")
            if want == "numerical" and len(self.numeric_facts) < 2:
                raise ValueError(f"{self.case_id}: numerical case needs >=2 numeric_facts")
            if want == "negative" and not any(
                f.polarity in ("negative", "null", "mixed") for f in self.required_findings
            ):
                raise ValueError(f"{self.case_id}: negative case needs a negative/null required finding")
        if not self.required_findings:
            raise ValueError(f"{self.case_id}: needs >=1 required finding")
        return self


class AuthoredCase(_Strict):
    """Single source of truth used by authors. Lives in private/benchmark_source/."""

    case_id: str
    category: Category
    split: Literal["dev", "test"]
    pair_id: str
    package: ResearchPackage
    source_manifest: SourceManifest
    gold: GoldRecord

    @model_validator(mode="after")
    def _consistent(self) -> "AuthoredCase":
        if self.gold.case_id != self.case_id or self.gold.category != self.category:
            raise ValueError(f"{self.case_id}: gold case_id/category mismatch")
        return self

    # Explicit allowlists ----------------------------------------------------
    def public_record(self) -> CaseRecord:
        return CaseRecord(
            case_id=self.case_id,
            category=self.category,
            split=self.split,
            pair_id=self.pair_id,
            package=ResearchPackage.model_validate(self.package.model_dump()),
            source_manifest=SourceManifest.model_validate(self.source_manifest.model_dump()),
        )

    def annotator_rubric(self) -> dict:
        """What blind annotators may see: rubric without gold level/justification."""
        g = self.gold
        return {
            "case_id": self.case_id,
            "category": self.category,
            "scoring_protocol": g.scoring_protocol,
            "focal_proposition": g.focal_proposition,
            "level_descriptors": g.level_descriptors,
            "required_findings": [
                {"finding_id": f.finding_id, "description": f.description} for f in g.required_findings
            ],
            "numeric_facts": [
                {"fact_id": n.fact_id, "description": n.description, "entity": n.entity}
                for n in g.numeric_facts
            ],
        }
