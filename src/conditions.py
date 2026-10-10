"""The seven experimental conditions, as switches over ONE shared pipeline.

Shared-upstream design (documented in docs/PROTOCOL_FREEZE.md):
  direct draft D  (writer_direct)            -> C1 = D
                                             -> C2 = generic review + revision of D
                                             -> C6 = adaptive verification of D (strengthen allowed)
  outline O + outline-draft OD               -> C7 = OD
                                             -> C3 = scripted verification of OD (strengthen allowed)
                                             -> C4 = adaptive verification of OD (strengthen allowed)
                                             -> C5 = adaptive verification of OD (strengthen NOT allowed)
So C4 vs C5 start from the identical draft and differ only in STRENGTHEN; C4 vs C3 differ
only in tool-selection policy; C4 vs C7 isolates verification; C6 vs C4 isolates the outline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.verifier import VerifierConfig


@dataclass(frozen=True)
class ConditionConfig:
    code: str
    name: str
    upstream: Literal["direct", "outline"]
    generic_review: bool = False
    verify_mode: Optional[Literal["adaptive", "scripted"]] = None
    can_strengthen: bool = False
    hypothesis: str = ""

    def __post_init__(self):
        if self.generic_review and self.verify_mode:
            raise ValueError(f"{self.code}: generic review and tool verification are exclusive")
        if self.can_strengthen and not self.verify_mode:
            raise ValueError(f"{self.code}: can_strengthen only meaningful with a verifier")

    @property
    def uses_outline(self) -> bool:
        return self.upstream == "outline"

    @property
    def uses_tools(self) -> bool:
        return self.verify_mode is not None

    @property
    def adaptive(self) -> bool:
        return self.verify_mode == "adaptive"

    def verifier_config(self, max_tool_calls: int = 4, max_claims: int = 6) -> Optional[VerifierConfig]:
        if not self.verify_mode:
            return None
        return VerifierConfig(mode=self.verify_mode, can_strengthen=self.can_strengthen,
                              max_tool_calls=max_tool_calls, max_claims=max_claims)


CONDITIONS: dict[str, ConditionConfig] = {
    "C1": ConditionConfig("C1", "Direct generation", "direct", hypothesis="baseline"),
    "C2": ConditionConfig("C2", "Writer-reviewer loop", "direct", generic_review=True, hypothesis="H1"),
    "C3": ConditionConfig("C3", "Scripted verifier", "outline", verify_mode="scripted", can_strengthen=True, hypothesis="H3"),
    "C4": ConditionConfig("C4", "Full agent", "outline", verify_mode="adaptive", can_strengthen=True, hypothesis="main"),
    "C5": ConditionConfig("C5", "No strengthening", "outline", verify_mode="adaptive", can_strengthen=False, hypothesis="H2"),
    "C6": ConditionConfig("C6", "No outline", "direct", verify_mode="adaptive", can_strengthen=True, hypothesis="outline ablation"),
    "C7": ConditionConfig("C7", "Outline only", "outline", hypothesis="outline contribution"),
}
ALL_CONDITIONS = tuple(CONDITIONS)
REAL_PAPER_CONDITIONS = ("C1", "C2", "C3", "C4")
