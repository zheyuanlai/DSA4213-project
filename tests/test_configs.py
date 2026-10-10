"""Config files agree with code; frozen config pins one backbone for all conditions."""
from pathlib import Path

import yaml

from src.conditions import CONDITIONS

ROOT = Path(__file__).resolve().parent.parent


def test_conditions_yaml_mirrors_code():
    y = yaml.safe_load((ROOT / "configs" / "conditions.yaml").read_text())
    assert set(y) == set(CONDITIONS)
    for code, c in CONDITIONS.items():
        assert y[code]["upstream"] == c.upstream
        assert y[code]["generic_review"] == c.generic_review
        assert y[code]["verify_mode"] == c.verify_mode
        assert y[code]["can_strengthen"] == c.can_strengthen


def test_frozen_config_single_backbone():
    cfg = yaml.safe_load((ROOT / "configs" / "frozen_primary.yaml").read_text())
    assert cfg["model"]["id"] == "deepseek/deepseek-v4-flash-0731"
    assert cfg["model"]["decoding"]["temperature"] == 0
    assert cfg["model"]["provider_routing"]["require_parameters"] is True
    assert cfg["budget"]["hard_cap_usd"] <= 12.0
    assert sum(cfg["budget"]["stage_caps"].values()) <= 12.0 + 1e-9
