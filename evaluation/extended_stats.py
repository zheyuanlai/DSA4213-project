"""Paired uncertainty for the evaluation extension (protocol §8).

Reuses the frozen ``evaluation.paired_bootstrap`` for case-level means and adds a ratio-of-sums bootstrap for
claim-pooled rates (units = cases or papers; claims inside a unit are resampled together, never independently).
Every result reports n, discordant units, and flags a degenerate interval (all paired differences zero), which
must not be read as evidence of equivalence.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from evaluation.paired_bootstrap import cluster_bootstrap, paired_bootstrap

N_BOOT = 10000
SEED = 4213


def mean_diff(a: dict[str, Optional[float]], b: dict[str, Optional[float]],
              clusters: Optional[dict[str, str]] = None) -> dict:
    res = paired_bootstrap(a, b, n_boot=N_BOOT, seed=SEED)
    res["degenerate"] = bool(res["n"]) and res.get("n_a_better", 0) == 0 and res.get("n_b_better", 0) == 0
    if clusters is not None and res["n"]:
        res["matched_pair"] = cluster_bootstrap(a, b, clusters, n_boot=N_BOOT, seed=SEED)
    return res


def ratio_diff(num_a: dict[str, float], den_a: dict[str, float], num_b: dict[str, float], den_b: dict[str, float],
               clusters: Optional[dict[str, str]] = None) -> dict:
    """Difference of pooled rates sum(num)/sum(den), a minus b, resampling units present in both."""
    keys = sorted(k for k in set(num_a) & set(num_b) & set(den_a) & set(den_b))
    if not keys:
        return {"n": 0, "diff": None, "ci_low": None, "ci_high": None, "degenerate": False}
    na, da = np.array([num_a[k] for k in keys], float), np.array([den_a[k] for k in keys], float)
    nb, db = np.array([num_b[k] for k in keys], float), np.array([den_b[k] for k in keys], float)
    if da.sum() == 0 or db.sum() == 0:
        return {"n": len(keys), "diff": None, "ci_low": None, "ci_high": None, "degenerate": False,
                "note": "zero denominator"}
    point = na.sum() / da.sum() - nb.sum() / db.sum()

    def boots(groups: list[list[int]]) -> np.ndarray:
        rng = np.random.default_rng(SEED)
        out = np.empty(N_BOOT)
        for i in range(N_BOOT):
            pick = rng.integers(0, len(groups), size=len(groups))
            idx = [j for g in pick for j in groups[g]]
            sa, sb = da[idx].sum(), db[idx].sum()
            out[i] = (na[idx].sum() / sa if sa else np.nan) - (nb[idx].sum() / sb if sb else np.nan)
        return out[~np.isnan(out)]

    b = boots([[i] for i in range(len(keys))])
    lo, hi = np.quantile(b, [0.025, 0.975])
    ra = np.where(da > 0, na / np.where(da > 0, da, 1), np.nan)
    rb = np.where(db > 0, nb / np.where(db > 0, db, 1), np.nan)
    both = ~np.isnan(ra) & ~np.isnan(rb)
    res = {"n": len(keys), "rate_a": float(na.sum() / da.sum()), "rate_b": float(nb.sum() / db.sum()),
           "diff": float(point), "ci_low": float(lo), "ci_high": float(hi), "n_boot": N_BOOT, "seed": SEED,
           "resampling_unit": "case", "den_a": float(da.sum()), "den_b": float(db.sum()),
           "n_a_better": int((ra[both] > rb[both]).sum()), "n_b_better": int((ra[both] < rb[both]).sum()),
           "n_tied": int((ra[both] == rb[both]).sum())}
    # degenerate = no difference at all and a collapsed interval (identical labels in every resample)
    res["degenerate"] = bool(abs(point) < 1e-12 and abs(res["ci_low"]) < 1e-12 and abs(res["ci_high"]) < 1e-12)
    if clusters is not None:
        groups: dict[str, list[int]] = {}
        for i, k in enumerate(keys):
            groups.setdefault(clusters.get(k, k), []).append(i)
        cb = boots(list(groups.values()))
        clo, chi = np.quantile(cb, [0.025, 0.975])
        res["matched_pair"] = {"ci_low": float(clo), "ci_high": float(chi), "n_clusters": len(groups),
                               "resampling_unit": "matched_pair"}
    return res


def rate_ci(num: dict[str, float], den: dict[str, float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Pooled rate and its case-bootstrap 95% interval for one condition (descriptive)."""
    keys = sorted(k for k in num if k in den)
    n, d = np.array([num[k] for k in keys], float), np.array([den[k] for k in keys], float)
    if not keys or d.sum() == 0:
        return None, None, None
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(keys), size=len(keys))
        s = d[idx].sum()
        if s:
            vals.append(n[idx].sum() / s)
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return float(n.sum() / d.sum()), float(lo), float(hi)
