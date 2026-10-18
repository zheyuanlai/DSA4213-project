"""Adjudication replicates (test–retest): isolation from primary files, cache salt, agreement statistics."""
from __future__ import annotations

import re

from evaluation import adjudicator_stability as S
from evaluation import extended_consensus as C
from evaluation import extended_pipeline as P
from evaluation import judges
from tests.test_extended_pipeline_e2e import fixture_family, run_fixture_pipeline  # noqa: F401  (fixture)
from tests.test_numeric_fidelity import ev  # noqa: F401  (fixture)


def test_replicate_reasks_identical_prompts_and_never_touches_primary_files(fixture_family, tmp_path, monkeypatch):  # noqa: F811
    data, packets, out, prompts = run_fixture_pipeline(fixture_family, tmp_path, monkeypatch)
    ext = tmp_path / "ext"
    primary_adj = (ext / "adjudication" / "fixture_claims.jsonl").read_text()
    primary_cons = (ext / "consensus" / "fixture_claims.jsonl").read_text()
    seen: list[str] = []

    def flip(prompt, schema):  # the replicate adjudicator decides the significance claim the other way
        seen.append(prompt)
        out = []
        for it in re.findall(r"### Item (\S+)", prompt):
            block = prompt.split(f"### Item {it}")[1].split("### Item")[0]
            nums = [{"number_id": n, "choice": "own", "source_type": "cell", "expression": "T1.r2.d1", "quote": None,
                     "scale": 1} for n in dict.fromkeys(re.findall(r"number (\S+\.n\d+) ", block))]
            out.append({"item_id": it, "label": "SUPPORTED", "entailment": "ENTAILED", "extraction_valid": True,
                        "numbers": nums, "rationale": "Decided from S1.", "evidence_ids": ["S1"]})
        return {"decisions": out}

    monkeypatch.setitem(judges.MOCK_RESPONDERS, "adjudicate_claims", flip)
    C.run_claim_adjudication(data, packets, workers=1, replicate="r1")
    C.run_alignment_adjudication(data, packets, workers=1, replicate="r1")
    C.build_consensus(data, packets, replicate="r1")
    # the replicate asked the very same prompt (no salt in the text) and wrote only under replicates/r1
    primary_prompts = [p for p in prompts if p.startswith("# Task: adjudicate disagreements about atomic claims")]
    assert seen and seen == primary_prompts
    assert (ext / "adjudication" / "fixture_claims.jsonl").read_text() == primary_adj
    assert (ext / "consensus" / "fixture_claims.jsonl").read_text() == primary_cons
    assert (ext / "replicates" / "r1" / "adjudication" / "fixture_claims.jsonl").exists()
    assert list((ext / "replicates" / "r1" / "raw").rglob("*.json"))
    # rerunning the primary adjudication is fully cached: the flipped responder is never consulted
    seen.clear()
    C.run_claim_adjudication(data, packets, workers=1)
    assert not seen
    tr = S.test_retest("fixture", "r1", ext=ext)
    assert tr["label"]["n"] == 1 and tr["label"]["agree"] == 0 and tr["label"]["changes"] == {"OVERSTATED->SUPPORTED": 1}
    ch = S.consensus_changes("fixture", "r1", ext=ext)
    assert ch["final_label_changed"] == 1 and ch["final_label_changes"] == {"OVERSTATED->SUPPORTED": 1}


def test_salt_changes_only_the_cache_key(tmp_path, monkeypatch):
    calls = {"n": 0}

    def responder(prompt, schema):
        calls["n"] += 1
        return {"judgments": [{"passage": "A", "item_id": "F1", "status": "ABSENT", "justification": "-"}]}

    monkeypatch.setitem(judges.MOCK_RESPONDERS, "coverage", responder)
    spec = judges.JudgeSpec("M", "mock", "mock")
    r0 = judges.call_judge(spec, "coverage", "k", "coverage", "P", data_segments=[], raw_dir=tmp_path)
    r1 = judges.call_judge(spec, "coverage", "k", "coverage", "P", data_segments=[], raw_dir=tmp_path, salt="replicate=r1")
    r1b = judges.call_judge(spec, "coverage", "k", "coverage", "P", data_segments=[], raw_dir=tmp_path, salt="replicate=r1")
    assert calls["n"] == 2 and r1b.cached
    assert r0.record["cache_key"] != r1.record["cache_key"] and r0.record["prompt_sha256"] == r1.record["prompt_sha256"]


def test_contrast_sensitivity_flags_sign_and_zero_exclusion_changes():
    d = lambda diff, lo, hi: {"diff": diff, "ci_low": lo, "ci_high": hi, "n": 10, "degenerate": False}  # noqa: E731
    keys = S.CLAIM_KEYS
    prim = {"claims": {"comparisons": {"C4_vs_C2": {k: d(0.05, 0.01, 0.09) for k in keys}}}}
    rep = {"claims": {"comparisons": {"C4_vs_C2": {k: d(-0.01, -0.04, 0.02) for k in keys}}}}
    rows = S.contrast_sensitivity(prim, rep)
    assert len(rows) == len(keys)
    assert all(r["same_sign"] is False and r["primary_excludes_zero"] and not r["replicate_excludes_zero"] for r in rows)


def test_markdown_report_lists_changes_and_skips_degenerate_rows():
    blk = lambda n, agree, ch: {"n": n, "agree": agree, "pct_agree": agree / n, "cohen_kappa": 0.5, "changes": ch}  # noqa: E731
    empty = {"n": 0, "agree": 0, "pct_agree": None, "cohen_kappa": None, "changes": {}}
    tr = {"label": blk(10, 8, {"SUPPORTED->OVERSTATED": 2}), "entailment": empty, "extraction_valid": empty,
          "number_mapping_choice": blk(5, 5, {}), "coverage_status": empty, "alignment_relation": empty}
    deg = {"diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 8, "degenerate": True}
    live = {"diff": 0.02, "ci_low": -0.01, "ci_high": 0.05, "n": 8, "degenerate": False}
    report = {"replicate": "r1", "provenance": "AI-AI test-retest.", "families": {"synthetic": {
        "test_retest": tr, "consensus_changes": {"claims": 10, "final_label_changed": 2, "factual_error_changed": 2,
                                                 "number_verdicts_changed": 0},
        "contrasts": [{"contrast": "C4_vs_C5", "metric": "support_rate", "primary": deg, "replicate": deg, "same_sign": True,
                       "primary_excludes_zero": False, "replicate_excludes_zero": False, "shift": 0.0},
                      {"contrast": "C4_vs_C2", "metric": "support_rate", "primary": live, "replicate": live, "same_sign": True,
                       "primary_excludes_zero": False, "replicate_excludes_zero": False, "shift": 0.0}],
        "contrast_summary": {"n": 2, "sign_changes": 0, "zero_exclusion_changes": 0, "max_abs_shift": 0.0}}}}
    md = S.render_markdown(report)
    assert "SUPPORTED->OVERSTATED ×2" in md and "C4 − C2" in md and "C4 − C5" not in md
