"""Gold/rubric material never reaches the model; inference code never loads gold."""
import json
import re
from pathlib import Path

from src.mock_responder import mock_responder
from src.openrouter_client import MockClient
from src.render import render_package, render_verifier_context
from src.agent import run_case

ROOT = Path(__file__).resolve().parent.parent
INFERENCE_MODULES = ["agent.py", "runner.py", "writer.py", "verifier.py", "tools.py", "render.py", "evidence_store.py",
                     "openrouter_client.py", "conditions.py", "prompts.py", "package_schema.py"]


def test_public_record_has_no_gold(example_authored):
    pub = json.dumps(example_authored.public_record().model_dump())
    g = example_authored.gold
    for s in [g.justification, g.gold_decision, g.focal_proposition, g.pair_contrast] + list(g.level_descriptors.values()):
        assert s not in pub
    assert "gold" not in pub.lower()


def test_rendered_prompts_exclude_gold_and_metadata(example_authored):
    pkg = example_authored.public_record().package
    g = example_authored.gold
    for text in (render_package(pkg), render_verifier_context(pkg)):
        for s in [g.justification, g.gold_decision, g.focal_proposition] + [f.description for f in g.required_findings]:
            assert s not in text
        assert example_authored.case_id not in text and example_authored.category not in text
        assert "gold" not in text.lower()


def test_verifier_context_hides_values(example_authored):
    pkg = example_authored.public_record().package
    ctx = render_verifier_context(pkg)
    for t in pkg.results_tables:
        for r in t.rows:
            for cell in r.cells.values():
                assert cell.text not in ctx
    for s in pkg.statistical_tests:
        assert str(s.p_value) not in ctx
    full = render_package(pkg)
    assert "83.2 ± 1.0" in full and "p = 0.0055" in full


def test_inference_code_never_references_gold():
    import ast

    for m in INFERENCE_MODULES:
        tree = ast.parse((ROOT / "src" / m).read_text())
        doc_nodes = {id(n.body[0].value) for n in ast.walk(tree)
                     if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                     and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", None) or ""
                names = [a.name for a in node.names]
                assert not mod.startswith("benchmarks") and not any(n.startswith("benchmarks") for n in names), m
            if isinstance(node, ast.Name):
                assert node.id != "GoldRecord", m
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
                assert not re.search(r"gold[_/]|private/", node.value), (m, node.value)


def test_messages_sent_to_model_contain_no_gold(example_authored, tmp_path):
    rec = example_authored.public_record()
    client = MockClient(mock_responder)
    run_case(client, rec, ["C1", "C2", "C3", "C4", "C5", "C6", "C7"], tmp_path,
             {"run_tag": "t", "stage": "dev", "prompt_hashes": {}, "code_hash": "x", "config_hash": "y"})
    g = example_authored.gold
    secrets = [g.justification, g.gold_decision, g.focal_proposition, g.pair_contrast]
    for call in client.calls:
        blob = json.dumps(call["messages"])
        for s in secrets:
            assert s not in blob
        assert '"gold' not in blob


def test_public_data_files_have_no_gold_keys():
    for split in ("dev", "test"):
        p = ROOT / "data" / "synthetic" / f"{split}.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            d = json.loads(line)
            assert set(d) == {"case_id", "category", "split", "pair_id", "package", "source_manifest"}
            assert "gold" not in json.dumps(d["package"]).lower()
    rub = ROOT / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl"
    if rub.exists():
        for line in rub.read_text().splitlines():
            d = json.loads(line)
            assert "gold_level" not in d and "justification" not in d and "gold_decision" not in d
