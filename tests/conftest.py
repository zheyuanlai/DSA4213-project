import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchmarks.schema import AuthoredCase  # noqa: E402
from src.evidence_store import EvidenceStore  # noqa: E402
from src.package_schema import (  # noqa: E402
    CaseRecord, Cell, Column, Comparison, Experiment, ResearchPackage, ResultTable, Row, SourceManifest, SourcePassage,
    StatTest,
)


@pytest.fixture
def example_authored() -> AuthoredCase:
    return AuthoredCase.model_validate(json.loads((ROOT / "docs" / "benchmark_example_case_NOT_IN_BENCHMARK.json").read_text()))


@pytest.fixture
def example_record(example_authored) -> CaseRecord:
    return example_authored.public_record()


def make_package() -> ResearchPackage:
    t1 = ResultTable(
        table_id="T1", caption="WER (%) and accuracy on two sets",
        columns=[Column(column_id="wer", header="WER (%)", unit="%", higher_is_better=False),
                 Column(column_id="acc", header="Accuracy (%)", unit="%", higher_is_better=True),
                 Column(column_id="lat", header="Latency (ms)", unit="ms", higher_is_better=False)],
        rows=[Row(row_id="r1", label="Ours", cells={"wer": Cell(text="7.4", value=7.4), "acc": Cell(text="83.7 ± 1.2", value=83.7, spread=1.2),
                                                   "lat": Cell(text="120", value=120)}),
              Row(row_id="r2", label="Baseline", cells={"wer": Cell(text="8.9", value=8.9), "acc": Cell(text="82.9 ± 1.4", value=82.9, spread=1.4),
                                                       "lat": Cell(text="n/a")})],
    )
    return ResearchPackage(
        question="How does Ours compare with Baseline?", methods_summary="Ours is a model.",
        experimental_setup="Five seeds.",
        experiments=[Experiment(experiment_id="exp1", description="main", comparisons=[
            Comparison(comparison_id="cmp1", description="Ours vs Baseline accuracy"),
            Comparison(comparison_id="cmp2", description="Ours vs Baseline WER")])],
        results_tables=[t1],
        statistical_tests=[StatTest(test_id="S1", experiment_id="exp1", comparison_id="cmp1", test_name="paired t-test",
                                    paired=True, n=5, n_unit="seeds", statistic_name="t", statistic=4.2, df=4,
                                    p_value=0.0137, ci_low=0.3, ci_high=1.3, ci_level=0.95, alpha=0.05)],
        source_passages=[SourcePassage(passage_id="P1", citation_key="Okafor et al. (2023)", source_title="Span alignment",
                                       text="We apply span alignment to align entity spans across languages."),
                         SourcePassage(passage_id="P2", citation_key="Lind and Mesa (2022)", source_title="Noise study",
                                       text="Label noise degraded accuracy by 4 points in our experiments.")],
        task_instruction="Write 2-4 sentences.",
    )


@pytest.fixture
def pkg() -> ResearchPackage:
    return make_package()


@pytest.fixture
def store(pkg) -> EvidenceStore:
    return EvidenceStore.from_package(pkg)


@pytest.fixture
def record(pkg) -> CaseRecord:
    return CaseRecord(case_id="UNIT-1", category="statistical_significance", split="dev", pair_id="UNIT",
                      package=pkg, source_manifest=SourceManifest(origin="synthetic_original"))
