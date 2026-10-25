"""Offline tests for V2 E1/E2 (mock client only; no API calls).  Run: python -m pytest v2/tests"""
import json
from collections import Counter
from pathlib import Path

import pytest

from src.evidence_store import EvidenceStore
from src.openrouter_client import MockClient
from src.prompts import DECISION_DEFS
from src.runner import load_cases
from src.schemas import ClaimDraft, Draft
from src.tools import submit_decision_schema
from v2.mock_responder import oracle_mock_responder
from v2.verifier_oracle import (
    ALL_DECISIONS, RELATIONS, action_consistent, decision_schema, oracle_evidence, system_prompt, user_message,
    verify_claim_oracle,
)

ROOT = Path(__file__).resolve().parents[2]
PROBES = json.loads((ROOT / "v2" / "data" / "dev_probes_batch1.json").read_text(encoding="utf-8"))["probes"]
CASES = {c.case_id: c for c in load_cases(ROOT / "data" / "synthetic" / "dev.jsonl")}


def _draft(text, hints=()):
    return Draft(sentences=[ClaimDraft(claim_id="s1", text=text, evidence_ids=list(hints))])


# ------------------------------------------------------------------ probes file
def test_probe_counts_and_design():
    assert len(PROBES) == 39
    assert len({p["probe_id"] for p in PROBES}) == 39
    c = Counter(p["expected_decision"] for p in PROBES)
    assert c["STRENGTHEN"] == 12 and c["ACCEPT"] == 15 and c["WEAKEN"] + c["REMOVE"] == 12
    for p in PROBES:
        assert CASES[p["case_id"]].split == "dev"
        assert p["expected_decision"] in p["acceptable_decisions"]
        if p["expected_decision"] == "STRENGTHEN":
            assert p["case_gold_level"] == 2 and p["draft_expressed_level"] < 2 and p["decisive_fact"]


def test_identical_draft_text_across_pair_members():
    by = {}
    for p in PROBES:
        by.setdefault((p["pair"], p["draft_key"]), set()).add(p["draft_text"])
    assert all(len(v) == 1 for v in by.values())


def test_decisive_and_hint_ids_exist_in_strong_case():
    for p in PROBES:
        if p["expected_decision"] != "STRENGTHEN":
            continue
        store = EvidenceStore.from_package(CASES[p["case_id"]].package)
        assert all(store.has(i) for i in p["decisive_evidence_ids"]), p["probe_id"]
        assert all(store.has(i) for i in p["writer_evidence_hints"]), p["probe_id"]


# ------------------------------------------------------------------ prompts / evidence
def test_prompt_prefixes_and_content():
    allowed = list(ALL_DECISIONS)
    d0, d1, d2 = (system_prompt(v, allowed) for v in ("D0", "D1", "D2"))
    assert d1.startswith(d0) and d2.startswith(d1) and d0 != d1 != d2
    for d in ALL_DECISIONS:
        assert DECISION_DEFS[d] in d0
    assert "call exactly one tool" not in d0 and "{{" not in d2
    assert "support_relation" in d1 and "support_relation" not in d0


def test_d1c_is_d1_plus_comparability_paragraph():
    allowed = list(ALL_DECISIONS)
    d1, d1c = system_prompt("D1", allowed), system_prompt("D1c", allowed)
    assert d1c.startswith(d1) and "## Comparisons" in d1c and "## Comparisons" not in d1
    assert decision_schema("D1c", allowed) == decision_schema("D1", allowed)


def test_compare_conditions_mock(tmp_path):
    from v2.scripts import compare_conditions, run_e1_e2

    out = tmp_path / "run"
    run_e1_e2.main(["--run-tag", "t", "--mock", "--repeats", "1", "--probe-ids", "P-CON-U-strong,P-SIG-S-partner",
                    "--out-root", str(out), "--conditions", "D1-oracle,D1c-oracle", "--workers", "1"])
    probes = [p for p in PROBES if p["probe_id"] in ("P-CON-U-strong", "P-SIG-S-partner")]
    res = compare_conditions.compare(compare_conditions.load(f"{out}:D1-oracle"),
                                     compare_conditions.load(f"{out}:D1c-oracle"), probes)
    assert len(res["unchanged"]) == 2  # mock is variant-independent


def test_oracle_evidence_has_all_values_and_no_task():
    pkg = CASES["SIG-p1a"].package
    ev = oracle_evidence(pkg)
    assert "p = 0.017" in ev and "28.4" in ev and "## Task" not in ev
    msg = user_message(pkg, _draft("X is better."), 0)
    assert msg.startswith(ev) and '>>> X is better. <<<' in msg


def test_decision_schema_order():
    allowed = list(ALL_DECISIONS)
    assert decision_schema("D0", allowed) == submit_decision_schema(allowed)
    props = list(decision_schema("D1", allowed)["function"]["parameters"]["properties"])
    assert props[:4] == ["proposition", "expressed_strength", "strongest_supported", "support_relation"]
    assert props.index("support_relation") < props.index("decision")
    assert decision_schema("D2", allowed) == decision_schema("D1", allowed)


# ------------------------------------------------------------------ verification loop
@pytest.mark.parametrize("variant", ["D0", "D1", "D2"])
def test_oracle_strengthen_path(variant):
    client = MockClient(oracle_mock_responder)
    pkg = CASES["CON-p1a"].package
    r = verify_claim_oracle(client, pkg, _draft("Ferrule wins on most of the six datasets."), 0, variant,
                            {"stage": "test"})
    assert r.decision.decision == "STRENGTHEN" and r.decision.valid and r.model_calls == 1
    assert (r.judgement.get("support_relation") == "STRONGER_SUPPORTED") == (variant != "D0")
    sent = client.calls[0]
    assert sent["tool_choice"] == {"type": "function", "function": {"name": "submit_decision"}}
    assert sent["tools"] == ["submit_decision"]


def test_oracle_repair_turn_and_no_strengthen_setting():
    client = MockClient(oracle_mock_responder)
    pkg = CASES["CON-p1a"].package
    r = verify_claim_oracle(client, pkg, _draft("MOCK_INVALID claim."), 0, "D1", {"stage": "test"})
    assert r.model_calls == 2 and r.protocol_errors and r.decision.valid
    r2 = verify_claim_oracle(client, pkg, _draft("Ferrule wins on most datasets."), 0, "D0", {"stage": "test"},
                             can_strengthen=False)
    assert r2.decision.decision == "FLAG" and not r2.decision.valid  # STRENGTHEN rejected when disabled


def test_identical_inputs_across_variants():
    pkg = CASES["SIG-p1a"].package
    users = []
    for v in ("D0", "D1", "D2"):
        client = MockClient(oracle_mock_responder)
        verify_claim_oracle(client, pkg, _draft("A is higher."), 0, v, {"stage": "test"})
        users.append(client.calls[0]["messages"][1]["content"])
    assert users[0] == users[1] == users[2]


def test_action_consistency_mapping():
    assert action_consistent({"support_relation": "STRONGER_SUPPORTED"}, "ACCEPT") is False
    assert action_consistent({"support_relation": "MATCHES"}, "ACCEPT") is True
    assert action_consistent({"support_relation": "NOT_SUPPORTED"}, "WEAKEN") is True
    assert action_consistent({}, "ACCEPT") is None
    assert set(RELATIONS) >= {"STRONGER_SUPPORTED", "MATCHES"}


# ------------------------------------------------------------------ end-to-end (mock)
def test_run_and_analyse_mock_end_to_end(tmp_path):
    from v2.scripts import analyze_e1_e2, run_e1_e2

    ids = "P-CON-U-strong,P-CON-S-partner,P-GEN-U-partner,P-SIG-U-partner"
    out = tmp_path / "run"
    args = ["--run-tag", "t", "--mock", "--repeats", "2", "--probe-ids", ids, "--out-root", str(out), "--workers", "1"]
    assert run_e1_e2.main(args) == 0
    files = list(out.glob("*/*.json"))
    assert len(files) == 4 * 4 * 2
    rec = json.loads((out / "D1-oracle" / "P-CON-U-strong__r1.json").read_text(encoding="utf-8"))
    assert rec["decision"] == "STRENGTHEN" and rec["is_mock"] and rec["judgement"]["support_relation"]
    tools_rec = json.loads((out / "D0-tools" / "P-CON-U-strong__r1.json").read_text(encoding="utf-8"))
    assert tools_rec["tools"]  # V1 verifier made tool calls
    assert run_e1_e2.main(args) == 0  # resume: nothing left to run
    assert len(list(out.glob("*/*.json"))) == 32
    res_dir = tmp_path / "res"
    assert analyze_e1_e2.main(["--run-dir", str(out), "--out", str(res_dir)]) == 0
    s = json.loads((res_dir / "summary.json").read_text(encoding="utf-8"))
    assert set(s["conditions"]) == {"D0-tools", "D0-oracle", "D1-oracle", "D2-oracle"}
    assert (res_dir / "failure_coding.csv").exists() and (res_dir / "revision_review.csv").exists()
    assert "R1" in s["rule_checks"]


def test_run_refuses_changed_meta(tmp_path):
    from v2.scripts import run_e1_e2

    out = tmp_path / "run"
    base = ["--run-tag", "t", "--mock", "--repeats", "1", "--probe-ids", "P-CON-U-strong", "--out-root", str(out),
            "--conditions", "D0-oracle"]
    run_e1_e2.main(base)
    meta = json.loads((out / "run_meta.json").read_text(encoding="utf-8"))
    meta["v2_code_hash"] = "different"
    (out / "run_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(SystemExit):
        run_e1_e2.main(base)


def test_real_mode_requires_flag():
    from v2.scripts import run_e1_e2

    with pytest.raises(SystemExit):
        run_e1_e2.main(["--run-tag", "t"])  # neither --mock nor --real
