"""Stage 30/31 statistics: spatially honest inference for n~228k coastal
transects with strong alongshore autocorrelation.

Design: naive p-values are meaningless here. Everything reports effect sizes
with block-bootstrap confidence intervals, where blocks are contiguous
alongshore chunks (base column block_id, 2 km default). Spearman is bootstrapped
as Pearson-on-global-ranks (rank once, resample blocks), the standard cheap
approximation.
"""

import numpy as np
import pandas as pd
from scipy import stats as sps
from scipy.spatial import cKDTree


def _block_indices(block_ids):
    order = np.argsort(block_ids, kind="stable")
    sorted_blocks = block_ids[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_blocks)) + 1]
    ends = np.r_[starts[1:], len(sorted_blocks)]
    return [order[s:e] for s, e in zip(starts, ends)]


def block_bootstrap_corr(x, y, block_ids, n_boot=1000, method="spearman",
                         seed=0):
    """Correlation with a moving-block bootstrap CI over alongshore blocks.

    Returns dict(rho, lo, hi, n, n_blocks). NaNs in x/y are dropped pairwise
    before anything else.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    block_ids = np.asarray(block_ids)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, block_ids = x[ok], y[ok], block_ids[ok]
    n = len(x)
    if n < 30:
        return dict(rho=np.nan, lo=np.nan, hi=np.nan, n=n, n_blocks=0)
    if method == "spearman":
        x = sps.rankdata(x)
        y = sps.rankdata(y)
    point = np.corrcoef(x, y)[0, 1]

    blocks = _block_indices(block_ids)
    nb = len(blocks)
    rng = np.random.default_rng(seed)
    reps = np.empty(n_boot)
    for i in range(n_boot):
        take = rng.integers(0, nb, nb)
        idx = np.concatenate([blocks[j] for j in take])
        xs, ys = x[idx], y[idx]
        xm, ym = xs.mean(), ys.mean()
        cov = ((xs - xm) * (ys - ym)).sum()
        reps[i] = cov / np.sqrt(((xs - xm) ** 2).sum() * ((ys - ym) ** 2).sum())
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return dict(rho=float(point), lo=float(lo), hi=float(hi), n=n, n_blocks=nb)


def alongshore_correlogram(values, island, chain_m, max_lag_m=20000,
                           lag_step_m=250):
    """Empirical autocorrelation vs alongshore lag, for block-length choice.

    Uses the regular 10 m transect spacing: bins pairs by chainage offset
    within island via shifted-series correlation.
    """
    df = pd.DataFrame({"v": values, "island": island, "chain": chain_m})
    df = df.dropna().sort_values(["island", "chain"])
    out = []
    for lag in range(lag_step_m, max_lag_m + 1, lag_step_m):
        shifted = df.groupby("island", sort=False).apply(
            lambda g: pd.Series(
                {"r": g.v.corr(g.v.shift(-int(round(lag / 10.0))))}),
            include_groups=False)
        out.append({"lag_m": lag, "r": float(shifted.r.mean())})
    return pd.DataFrame(out)


def decorrelation_length(correlogram, threshold=1 / np.e):
    below = correlogram[correlogram.r < threshold]
    return float(below.lag_m.iloc[0]) if len(below) else float(
        correlogram.lag_m.iloc[-1])


def effective_n(values, island, chain_m):
    """AR(1)-style effective sample size from lag-1 (10 m) autocorrelation."""
    df = pd.DataFrame({"v": values, "island": island, "chain": chain_m})
    df = df.dropna().sort_values(["island", "chain"])
    r1 = np.mean([g.v.corr(g.v.shift(1)) for _, g in
                  df.groupby("island", sort=False) if len(g) > 10])
    n = len(df)
    return float(n * (1 - r1) / (1 + r1)), float(r1)


def kruskal_epsilon_sq(values, groups, min_group=200):
    """Kruskal-Wallis H and epsilon-squared effect size across categories."""
    df = pd.DataFrame({"v": values, "g": groups}).dropna()
    counts = df.g.value_counts()
    keep = counts[counts >= min_group].index
    df = df[df.g.isin(keep)]
    samples = [g.v.values for _, g in df.groupby("g", observed=True)]
    if len(samples) < 2:
        return dict(H=np.nan, eps2=np.nan, k=len(samples), n=len(df))
    H, p = sps.kruskal(*samples)
    n, k = len(df), len(samples)
    eps2 = (H - k + 1) / (n - k)
    return dict(H=float(H), eps2=float(max(eps2, 0)), k=k, n=n)


def group_median_ci(values, groups, block_ids, n_boot=500, min_group=200,
                    seed=0):
    """Median per category with block-bootstrap CIs."""
    df = pd.DataFrame({"v": values, "g": groups, "b": block_ids}).dropna()
    counts = df.g.value_counts()
    df = df[df.g.isin(counts[counts >= min_group].index)]
    rng = np.random.default_rng(seed)
    rows = []
    for name, g in df.groupby("g", observed=True):
        blocks = _block_indices(g.b.values)
        nb = len(blocks)
        v = g.v.values
        reps = np.empty(n_boot)
        for i in range(n_boot):
            take = rng.integers(0, nb, nb)
            reps[i] = np.median(v[np.concatenate([blocks[j] for j in take])])
        lo, hi = np.percentile(reps, [2.5, 97.5])
        rows.append(dict(group=name, n=len(g), median=float(np.median(v)),
                         lo=float(lo), hi=float(hi)))
    return pd.DataFrame(rows).sort_values("median")


def morans_i(values, x, y, k=8, seed=0, n_perm=99):
    """Moran's I with kNN row-standardised weights (manual, no pysal dep)."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v = v[ok]
    coords = np.c_[np.asarray(x)[ok], np.asarray(y)[ok]]
    n = len(v)
    tree = cKDTree(coords)
    _, nbr = tree.query(coords, k=k + 1)
    nbr = nbr[:, 1:]
    z = v - v.mean()
    num = (z[:, None] * z[nbr]).sum() / k
    I = (num / (z ** 2).sum())
    rng = np.random.default_rng(seed)
    perms = np.empty(n_perm)
    for i in range(n_perm):
        zp = rng.permutation(z)
        perms[i] = (zp[:, None] * zp[nbr]).sum() / k / (zp ** 2).sum()
    p = (np.sum(perms >= I) + 1) / (n_perm + 1)
    return dict(I=float(I), expected=-1.0 / (n - 1), p_perm=float(p), n=n)
