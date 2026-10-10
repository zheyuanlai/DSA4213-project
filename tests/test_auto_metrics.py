"""Automatic metrics: numeric grounding, fact recall, PROXY levels, bootstrap."""
import numpy as np

from evaluation.auto_metrics import numbers_in, numeric_fact_recall, numeric_grounding, proxy_level
from evaluation.paired_bootstrap import cluster_bootstrap, paired_bootstrap


def test_numbers_in_skips_identifiers():
    toks = [t for t, _ in numbers_in("On Corvex A2 at fp16, Recall@20 rose from 0.072 to 0.085 (t(7)=3.13, p = 0.017); 1,240 ms; −1.8 points.")]
    assert "2" not in toks and "16" not in toks and "20" not in toks
    assert {"0.072", "0.085", "3.13", "0.017", "1,240", "−1.8"} <= set(toks)


def test_numeric_grounding(pkg):
    ok = numeric_grounding("Ours reached 83.7 vs 82.9 accuracy, a 0.8-point gain (p = 0.0137), and WER fell 16.9%.", pkg)
    assert ok["n_ungrounded"] == 0, ok
    bad = numeric_grounding("Ours reached 85.2 accuracy with p = 0.0042.", pkg)
    assert set(bad["ungrounded"]) == {"85.2", "0.0042"}


def test_numeric_fact_recall_with_scale():
    facts = [{"fact_id": "a", "value": 0.837, "tolerance": 0.0005}, {"fact_id": "b", "value": 0.61, "tolerance": 0.005},
             {"fact_id": "c", "value": -0.5, "tolerance": 0.05}]
    r = numeric_fact_recall("Accuracy was 83.7% and p99 was 610 ms; chrF dropped by 0.5.", facts)
    assert r["n_value_present"] == 3


def test_proxy_levels():
    terms = ["Tessaline", "Varrow-NMT"]
    assert proxy_level("statistical_significance", "Tessaline significantly outperforms Varrow-NMT (p = 0.017).", terms) == 2
    assert proxy_level("statistical_significance", "Tessaline has higher BLEU than Varrow-NMT (28.4 vs 27.6); no test was reported.", terms) == 1
    assert proxy_level("statistical_significance", "The difference between Tessaline and Varrow-NMT was not statistically significant (p = 0.36).", terms) == 0
    assert proxy_level("consistency", "Halyard has lower MAE on four of the five datasets.", ["Halyard"]) == 1
    assert proxy_level("consistency", "Halyard has lower MAE on all five datasets.", ["Halyard"]) == 2
    assert proxy_level("consistency", "Marten wins on two of the four graphs and loses on the others.", ["Marten"]) == 0
    assert proxy_level("efficiency", "Eddyline is not faster than Brenna-ODE (268 vs 241 ms) despite fewer NFE.", ["Eddyline"]) == 0
    assert proxy_level("efficiency", "Sablewing needs 6.25x fewer NFE than Ordell-DDS.", ["Sablewing"]) == 1
    assert proxy_level("efficiency", "Sablewing samples 5.6× faster than Ordell-DDS.", ["Sablewing"]) == 2
    assert proxy_level("robustness", "Robustness to label noise was not evaluated.", []) == 0
    assert proxy_level("robustness", "Stellate-Net is robust to mild and moderate blur but fails at severity 5.", []) == 1
    assert proxy_level("generalization", "The advantage generalizes to all three held-out domains.", []) == 2


def test_paired_bootstrap_basic():
    a = {f"c{i}": 1.0 for i in range(20)}
    b = {f"c{i}": 0.0 for i in range(20)}
    r = paired_bootstrap(a, b, n_boot=2000)
    assert r["diff"] == 1.0 and r["ci_low"] == 1.0 and r["n"] == 20
    rng = np.random.default_rng(0)
    a = {f"c{i}": float(rng.normal()) for i in range(30)}
    b = {k: v for k, v in a.items()}
    r = paired_bootstrap(a, b)
    assert r["diff"] == 0 and r["ci_low"] == 0 and r["ci_high"] == 0
    a["c0"] = None
    assert paired_bootstrap(a, b)["n"] == 29
    cl = cluster_bootstrap({"x1": 1.0, "x2": 1.0, "y1": 0.0, "y2": 0.0}, {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},
                           {"x1": "x", "x2": "x", "y1": "y", "y2": "y"}, n_boot=500)
    assert cl["n_clusters"] == 2 and cl["diff"] == 0.5
