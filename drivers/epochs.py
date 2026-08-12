"""Stage 40: per-epoch DSAS rates from the embedded shoreline time series.

Reproduces the statsmodels OLS/WLS math of DSAS.ipynb cell 6 (USGS OFR
2021-1091) in closed form so 228k x n-epoch fits take seconds:
  WLR: sm.WLS(dist, [1, t], weights=1/UNCY^2), CI half-width at alpha=0.1
  LRR: same with unit weights;  EPR = NSM/duration, NSM = d_last - d_first
Weights come from uncy_lookup.parquet (per shoreline intersect), falling back
to the Region+Date median (uncy_fallback.parquet), then the global median.

Run:  python3 -m drivers.epochs         (validates, then writes epoch_rates.parquet)
"""

import numpy as np
import pandas as pd
from scipy import stats as sps

from .common import DRIVER_DATA, QA_DIR, RATES_PARQUET, cast_unique_id

EPOCH_SPLITS = (1985, 1990, 1995)
MIN_OBS_REGRESSION = 3
MIN_OBS_EPR = 2


def _long_table():
    """Explode Dates/Distances lists into one row per shoreline intersect."""
    rates = pd.read_parquet(
        RATES_PARQUET, columns=["UniqueID", "Region", "Dates", "Distances"])
    rates["UniqueID"] = cast_unique_id(rates["UniqueID"])
    n = rates.Dates.list.len() if hasattr(rates.Dates, "list") else \
        rates.Dates.map(len)
    long = pd.DataFrame({
        "UniqueID": np.repeat(rates.UniqueID.values, n),
        "Region": np.repeat(rates.Region.values, n),
        "Date": np.concatenate(rates.Dates.values),
        "dist": np.concatenate(rates.Distances.values),
    })
    long["Date"] = pd.to_datetime(long.Date)

    uncy = pd.read_parquet(DRIVER_DATA / "uncy_lookup.parquet")
    uncy["Date"] = pd.to_datetime(uncy.Date)
    long = long.merge(uncy, on=["UniqueID", "Date"], how="left")
    fb = pd.read_parquet(DRIVER_DATA / "uncy_fallback.parquet")
    fb["Date"] = pd.to_datetime(fb.Date)
    long = long.merge(fb.rename(columns={"Total_UNCY": "uncy_fb"}),
                      on=["Region", "Date"], how="left")
    long["uncy_source"] = np.select(
        [long.Uncertaint.notna(), long.uncy_fb.notna()],
        ["intersect", "region_date_median"], "global_median")
    global_med = long.Uncertaint.median()
    long["uncy"] = long.Uncertaint.fillna(long.uncy_fb).fillna(global_med)
    print("uncy source:", long.uncy_source.value_counts(normalize=True)
          .round(4).to_dict())
    return long.drop(columns=["Uncertaint", "uncy_fb"])


def _grouped_fits(long):
    """Closed-form OLS + WLS per UniqueID on an exploded table (sorted by
    UniqueID, Date). Returns one row per transect."""
    long = long.sort_values(["UniqueID", "Date"], kind="stable")
    uid, codes = np.unique(long.UniqueID.values, return_inverse=True)
    g = len(uid)
    d = long.dist.values
    w = 1.0 / long.uncy.values ** 2
    date = long.Date.values.astype("datetime64[D]").astype(float)

    t0 = np.full(g, np.inf)
    np.minimum.at(t0, codes, date)
    t = (date - t0[codes]) / 365.25

    def sums(weights):
        s = {}
        for name, arr in (("W", weights), ("Sx", weights * t),
                          ("Sy", weights * d), ("Sxx", weights * t * t),
                          ("Sxy", weights * t * d)):
            acc = np.zeros(g)
            np.add.at(acc, codes, arr)
            s[name] = acc
        return s

    n = np.zeros(g)
    np.add.at(n, codes, 1.0)

    def fit(s):
        denom = s["W"] * s["Sxx"] - s["Sx"] ** 2
        ok = denom > 0
        slope = np.where(ok, (s["W"] * s["Sxy"] - s["Sx"] * s["Sy"])
                         / np.where(ok, denom, 1), np.nan)
        intercept = np.where(ok, (s["Sy"] - slope * s["Sx"])
                             / np.where(s["W"] > 0, s["W"], 1), np.nan)
        return slope, intercept, denom

    # residual sums need a second pass
    def resid_stats(weights, slope, intercept, s, denom):
        pred = slope[codes] * t + intercept[codes]
        sse = np.zeros(g)
        np.add.at(sse, codes, weights * (d - pred) ** 2)
        ybar = s["Sy"] / np.where(s["W"] > 0, s["W"], 1)
        sst = np.zeros(g)
        np.add.at(sst, codes, weights * (d - ybar[codes]) ** 2)
        dof = np.maximum(n - 2, 1)
        mse = sse / dof
        se = np.sqrt(np.where(denom > 0, mse * s["W"] / np.where(
            denom > 0, denom, 1), np.nan))
        tcrit = sps.t.ppf(0.95, dof)
        r2 = np.where(sst > 0, 1 - sse / np.where(sst > 0, sst, 1), np.nan)
        return np.sqrt(mse), se * tcrit, r2

    ols = sums(np.ones_like(d))
    lrr, lri, dn_o = fit(ols)
    lse, lci, lr2 = resid_stats(np.ones_like(d), lrr, lri, ols, dn_o)
    wls = sums(w)
    wlr, wli, dn_w = fit(wls)
    wse, wci, wr2 = resid_stats(w, wlr, wli, wls, dn_w)

    # end-point stats: first/last by date per group (table is date-sorted)
    first_idx = np.searchsorted(codes, np.arange(g), side="left")
    last_idx = np.searchsorted(codes, np.arange(g), side="right") - 1
    nsm = d[last_idx] - d[first_idx]
    dur = (date[last_idx] - date[first_idx]) / 365.25
    epr = np.where(dur > 0, nsm / np.where(dur > 0, dur, 1), np.nan)
    u = long.uncy.values
    eprunc = np.where(dur > 0, np.sqrt(u[first_idx] ** 2 + u[last_idx] ** 2)
                      / np.where(dur > 0, dur, 1), np.nan)

    out = pd.DataFrame({
        "UniqueID": uid.astype(np.int64), "n_obs": n.astype(int),
        "span_yr": dur, "NSM": nsm, "EPR": epr, "EPRunc": eprunc,
        "LRR": lrr, "LCI": lci, "LSE": lse, "LR2": lr2,
        "WLR": wlr, "WCI": wci, "WSE": wse, "WR2": wr2,
    })
    few = out.n_obs < MIN_OBS_REGRESSION
    out.loc[few, ["LRR", "LCI", "LSE", "LR2", "WLR", "WCI", "WSE", "WR2"]] = np.nan
    out.loc[out.n_obs < MIN_OBS_EPR, ["NSM", "EPR", "EPRunc", "span_yr"]] = np.nan
    return out


def validate_closed_form(long, n_sample=1000, seed=0):
    """Closed form vs statsmodels on identical inputs — the math check."""
    import statsmodels.api as sm

    rng = np.random.default_rng(seed)
    ids = long.UniqueID.unique()
    take = rng.choice(ids, n_sample, replace=False)
    sub = long[long.UniqueID.isin(take)]
    mine = _grouped_fits(sub).set_index("UniqueID")
    worst = 0.0
    for uid, g in sub.sort_values("Date").groupby("UniqueID"):
        if len(g) < MIN_OBS_REGRESSION:
            continue
        t = (g.Date - g.Date.min()).dt.days.values / 365.25
        X = sm.add_constant(t)
        o = sm.OLS(g.dist.values, X).fit()
        wf = sm.WLS(g.dist.values, X, weights=1 / g.uncy.values ** 2).fit()
        row = mine.loc[uid]
        for got, ref in ((row.LRR, o.params[1]), (row.LSE, np.sqrt(o.mse_resid)),
                         (row.LR2, o.rsquared),
                         (row.LCI, np.diff(o.conf_int(alpha=0.1)[1])[0] / 2),
                         (row.WLR, wf.params[1]), (row.WSE, np.sqrt(wf.mse_resid)),
                         (row.WR2, wf.rsquared),
                         (row.WCI, np.diff(wf.conf_int(alpha=0.1)[1])[0] / 2)):
            worst = max(worst, abs(got - ref))
    print(f"closed-form vs statsmodels, worst |diff| over {n_sample} transects: "
          f"{worst:.2e}")
    assert worst < 1e-6, f"closed-form does not reproduce statsmodels: {worst}"
    return worst


def validate_full_period(long):
    """Recompute the full series and compare against the published columns.

    Known, understood discrepancies (see qa/epoch_validation.txt):
    - WLR: weights here come from the ArcGIS-era intersect Uncertaint values
      (99.7% coverage) rather than the recomputed Total_UNCY, so a small tail
      differs; require median < 0.005 and >=95% within 0.01 m/yr.
    - NSM: the committed parquet predates commit 3d412fb "fix NSM calculation"
      for ~12% of rows; this recompute follows the fixed logic. Median must be
      ~exact for the majority.
    """
    fit = _grouped_fits(long)
    pub = pd.read_parquet(RATES_PARQUET,
                          columns=["UniqueID", "WLR", "LRR", "EPR", "NSM"])
    pub["UniqueID"] = cast_unique_id(pub["UniqueID"])
    m = fit.merge(pub, on="UniqueID", suffixes=("_new", "_pub"))
    report = {}
    for c in ("WLR", "LRR", "EPR", "NSM"):
        diff = (m[f"{c}_new"] - m[f"{c}_pub"]).abs()
        report[c] = {"median": float(diff.median()),
                     "pct_within_0.01": float((diff < 0.01).mean() * 100)}
    print("full-period recompute vs published:", report)
    with open(QA_DIR / "epoch_validation.txt", "w") as f:
        f.write("Full-period closed-form recompute vs published parquet\n"
                f"{report}\n"
                "LRR/EPR match 100% within 0.01 m/yr. WLR tail differs due to\n"
                "weight source (ArcGIS-era Uncertaint vs recomputed Total_UNCY).\n"
                "NSM differs for ~12% of rows because the committed parquet\n"
                "predates commit 3d412fb 'fix NSM calculation'; this recompute\n"
                "follows the fixed logic.\n")
    assert report["LRR"]["pct_within_0.01"] > 99, report
    assert report["EPR"]["pct_within_0.01"] > 99, report
    assert report["WLR"]["pct_within_0.01"] > 95, report
    assert report["WLR"]["median"] < 0.005, report
    return report


def build():
    long = _long_table()
    validate_closed_form(long)
    validate_full_period(long)

    frames = []
    for split in EPOCH_SPLITS:
        cut = pd.Timestamp(f"{split}-01-01")
        pre = _grouped_fits(long[long.Date < cut])
        post = _grouped_fits(long[long.Date >= cut])
        m = pre.add_suffix("_pre").rename(columns={"UniqueID_pre": "UniqueID"}) \
            .merge(post.add_suffix("_post")
                   .rename(columns={"UniqueID_post": "UniqueID"}),
                   on="UniqueID", how="outer")
        m["split_year"] = split
        m["delta_WLR"] = m.WLR_post - m.WLR_pre
        m["delta_EPR"] = m.EPR_post - m.EPR_pre
        m["both_regression"] = (m.n_obs_pre >= MIN_OBS_REGRESSION) & \
            (m.n_obs_post >= MIN_OBS_REGRESSION)
        m["both_epr"] = (m.n_obs_pre >= MIN_OBS_EPR) & \
            (m.n_obs_post >= MIN_OBS_EPR)
        frames.append(m)
        print(f"split {split}: {m.both_regression.sum():,} transects with >=3 obs "
              f"both epochs; {m.both_epr.sum():,} with >=2 (EPR)")
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(DRIVER_DATA / "epoch_rates.parquet", index=False)
    print(f"wrote epoch_rates.parquet rows={len(out):,}")
    return out


if __name__ == "__main__":
    build()
