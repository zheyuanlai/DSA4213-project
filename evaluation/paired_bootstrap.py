"""Paired bootstrap confidence intervals for condition comparisons on the same cases.

* `paired_bootstrap(a, b)`: resamples CASES with replacement (case-level, paired).
* `cluster_bootstrap(a, b, clusters)`: resamples MATCHED PAIRS (both members together) as a
  sensitivity analysis for within-pair dependence.
Inputs are dicts case_id -> value (None = metric not computable for that case; such cases are
dropped from that comparison and the effective n is reported).
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def _aligned(a: dict[str, Optional[float]], b: dict[str, Optional[float]]):
    keys = sorted(k for k in set(a) & set(b) if a[k] is not None and b[k] is not None)
    return keys, np.array([a[k] for k in keys], float), np.array([b[k] for k in keys], float)


def paired_bootstrap(a: dict[str, Optional[float]], b: dict[str, Optional[float]], n_boot: int = 10000,
                     seed: int = 4213, level: float = 0.95) -> dict:
    keys, x, y = _aligned(a, b)
    n = len(keys)
    if n == 0:
        return {"n": 0, "mean_a": None, "mean_b": None, "diff": None, "ci_low": None, "ci_high": None}
    d = x - y
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = d[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [(1 - level) / 2, 1 - (1 - level) / 2])
    sd = d.std(ddof=1) if n > 1 else float("nan")
    return {"n": n, "mean_a": float(x.mean()), "mean_b": float(y.mean()), "diff": float(d.mean()),
            "ci_low": float(lo), "ci_high": float(hi), "level": level, "n_boot": n_boot,
            "dz": float(d.mean() / sd) if sd and np.isfinite(sd) and sd > 0 else None,
            "n_a_better": int((d > 0).sum()), "n_b_better": int((d < 0).sum()), "n_tied": int((d == 0).sum()),
            "resampling_unit": "case"}


def cluster_bootstrap(a: dict[str, Optional[float]], b: dict[str, Optional[float]], clusters: dict[str, str],
                      n_boot: int = 10000, seed: int = 4213, level: float = 0.95) -> dict:
    keys, x, y = _aligned(a, b)
    if not keys:
        return {"n": 0, "diff": None, "ci_low": None, "ci_high": None}
    d = x - y
    groups: dict[str, list[int]] = {}
    for i, k in enumerate(keys):
        groups.setdefault(clusters.get(k, k), []).append(i)
    gl = list(groups.values())
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for bi in range(n_boot):
        pick = rng.integers(0, len(gl), size=len(gl))
        idx = [i for g in pick for i in gl[g]]
        boots[bi] = d[idx].mean()
    lo, hi = np.quantile(boots, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {"n": len(keys), "n_clusters": len(gl), "diff": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi),
            "level": level, "n_boot": n_boot, "resampling_unit": "matched_pair"}
