"""CoastSat (satellite-derived shorelines, 1999-2026) as a second response
dataset for the drivers analysis, plus a NZCCD-vs-CoastSat comparison.

Sign convention verified: CoastSat `trend` and NZCCD WLR are positively
correlated (rho ~ +0.40 overall, +0.52 within 50 m) -> positive = accretion
in both. The NZCCD-on-CoastSat-transects file (rates_with_timeseries_CoastSat_
intersects.parquet) is also positive = accretion (rho +0.41 vs CoastSat).

Design
- transects: 33,422 nzd transects / 604 sites from transects_extended.geojson
  (id, site_id, along_dist, beach_slope, trend + CI, n_points, r2)
- drivers: nearest NZCCD transect (<= 300 m; drivers vary on km scales) except
  beach-face slope, which is CoastSat's own per-transect slope
- comparison layers: NZCCD WLR at the nearest transect (all-period), NZCCD
  rates on the SAME CoastSat transect geometry (intersects file), and a
  post-1999 same-period NZCCD recompute (closed-form OLS from drivers.epochs)
- satellite epochs: per-transect OLS trends 1999-2012 vs 2013-2026 from the
  per-site tidally corrected time series (Landsat 5/7 vs 8/9 era - noted)
- stats: block bootstrap with CoastSat site as the block; like-for-like NZCCD
  correlations computed on the same matched rows

Run:  python3 -m drivers.coastsat
Out:  driver_data/coastsat_master.parquet + driver_data/stats/coastsat_*.csv
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from tqdm.contrib.concurrent import thread_map

from .common import DRIVER_DATA, REPO, TRANSECTS_EXTENDED
from .correlations import CATEGORICAL_DRIVERS, NUMERIC_DRIVERS, STATS_DIR
from .stats import block_bootstrap_corr, kruskal_epsilon_sq

CS_DATA = Path("/mnt/CoastSat/data")
INTERSECTS = REPO / "rates_with_timeseries_CoastSat_intersects.parquet"
EPOCH_SPLIT = "2013-01-01"
MIN_OBS = 30
MATCH_M = 300


def load_transects():
    te = pyogrio.read_dataframe(
        TRANSECTS_EXTENDED, where="site_id LIKE 'nzd%'",
        columns=["id", "site_id", "along_dist", "beach_slope", "trend",
                 "cil", "ciu", "n_points", "r2_score"]).to_crs(2193)
    te = te.rename(columns={"trend": "cs_trend", "cil": "cs_trend_lo",
                            "ciu": "cs_trend_hi", "n_points": "cs_n_obs",
                            "r2_score": "cs_r2",
                            "beach_slope": "beach_slope_face"})
    mid = te.geometry.interpolate(0.5, normalized=True)
    te["x2193"], te["y2193"] = mid.x, mid.y
    te["lon"], te["lat"] = mid.to_crs(4326).x, mid.to_crs(4326).y
    return te


def attach_nzccd(te):
    m = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet")
    keep_resp = ["UniqueID", "Region", "WLR", "NSM", "SCE", "EPR", "WCI"]
    drivers = [c for c in NUMERIC_DRIVERS + CATEGORICAL_DRIVERS
               if c in m.columns and c != "beach_slope_face"]
    pts = gpd.GeoDataFrame(m[keep_resp + drivers + ["x2193", "y2193"]],
                           geometry=gpd.points_from_xy(m.x2193, m.y2193),
                           crs=2193)
    j = gpd.sjoin_nearest(te[["id", "geometry"]], pts, how="left",
                          max_distance=MATCH_M, distance_col="nz_dist_m")
    j = j[~j.index.duplicated()].drop(columns=["geometry", "index_right",
                                                 "x2193", "y2193"])
    j = j.rename(columns={c: f"nz_{c}" for c in keep_resp})
    out = te.merge(j, on="id", how="left")
    print(f"NZCCD within {MATCH_M} m: {out.nz_UniqueID.notna().mean() * 100:.1f}%"
          f" of {len(out):,} CoastSat transects")
    return out


def same_transect_nzccd():
    """NZCCD shorelines intersected on the CoastSat transects themselves."""
    from .epochs import _grouped_fits
    ip = pd.read_parquet(INTERSECTS).dropna(subset=["UniqueID", "WLR"])
    ip = ip.rename(columns={"UniqueID": "id"})
    n = ip.Dates.map(len)
    long = pd.DataFrame({
        "UniqueID": np.repeat(np.arange(len(ip)), n),
        "Date": pd.to_datetime(np.concatenate(ip.Dates.values)),
        "dist": np.concatenate(ip.Distances.values), "uncy": 1.0})
    post = _grouped_fits(long[long.Date >= "1999-01-01"])
    post = post.set_index("UniqueID")
    out = pd.DataFrame({
        "id": ip.id.values,
        "nzst_WLR": ip.WLR.values, "nzst_EPR": ip.EPR.values,
        "nzst_ShrCount": ip.ShrCount.values,
        "nzst_LRR_post1999": post.LRR.reindex(np.arange(len(ip))).values,
        "nzst_n_post1999": post.n_obs.reindex(np.arange(len(ip))).values,
        "nzst_EPR_post1999": post.EPR.reindex(np.arange(len(ip))).values,
    })
    print(f"same-transect NZCCD: {len(out):,} transects; "
          f"{(out.nzst_n_post1999 >= 3).sum():,} with >=3 shorelines post-1999")
    return out


def _site_epochs(site):
    f = CS_DATA / site / "transect_time_series_tidally_corrected.csv"
    if not f.exists():
        return None
    ts = pd.read_csv(f)
    ts["dates"] = pd.to_datetime(ts.dates, utc=True)
    t = (ts.dates - pd.Timestamp("1999-01-01", tz="UTC")).dt.days.values / 365.25
    cut = (pd.Timestamp(EPOCH_SPLIT, tz="UTC") - pd.Timestamp(
        "1999-01-01", tz="UTC")).days / 365.25
    rows = []
    for col in ts.columns:
        if not col.startswith(site):
            continue
        y = ts[col].values.astype(float)
        rec = {"id": col}
        for name, mask in (("full", np.ones_like(t, bool)),
                           ("pre", t < cut), ("post", t >= cut)):
            ok = mask & np.isfinite(y)
            rec[f"cs_n_{name}"] = int(ok.sum())
            if ok.sum() >= MIN_OBS and np.ptp(t[ok]) > 3:
                rec[f"cs_trend_{name}"] = np.polyfit(t[ok], y[ok], 1)[0]
            else:
                rec[f"cs_trend_{name}"] = np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def epoch_trends(sites):
    parts = thread_map(_site_epochs, sites, max_workers=16, chunksize=4)
    ep = pd.concat([p for p in parts if p is not None], ignore_index=True)
    ep["cs_delta_trend"] = ep.cs_trend_post - ep.cs_trend_pre
    print(f"epoch trends for {len(ep):,} transects; both epochs: "
          f"{ep.cs_delta_trend.notna().sum():,}")
    return ep


def build():
    STATS_DIR.mkdir(exist_ok=True)
    te = load_transects()
    df = attach_nzccd(te)
    df = df.merge(same_transect_nzccd(), on="id", how="left")
    df = df.merge(epoch_trends(sorted(df.site_id.unique())), on="id", how="left")
    chk = df[["cs_trend", "cs_trend_full"]].dropna()
    print(f"recomputed full trend vs published: r={chk.cs_trend.corr(chk.cs_trend_full):.3f} "
          f"(n={len(chk):,})")
    df = df.drop(columns=["geometry"])
    df.to_parquet(DRIVER_DATA / "coastsat_master.parquet", index=False)
    print(f"wrote coastsat_master.parquet {df.shape}")
    return df


def run_stats(df=None):
    if df is None:
        df = pd.read_parquet(DRIVER_DATA / "coastsat_master.parquet")
    blocks = df.site_id.astype("category").cat.codes.values
    numeric = [c for c in NUMERIC_DRIVERS if c in df.columns]

    # driver correlations: CoastSat trend vs NZCCD WLR on the same rows
    rows = []
    for drv in numeric:
        r_cs = block_bootstrap_corr(df[drv], df.cs_trend, blocks, n_boot=500)
        r_nz = block_bootstrap_corr(df[drv], df.nz_WLR, blocks, n_boot=500)
        r_st = block_bootstrap_corr(df[drv], df.nzst_WLR, blocks, n_boot=500)
        ok99 = df.nzst_n_post1999 >= 3
        r_99 = block_bootstrap_corr(df.loc[ok99, drv], df.loc[ok99, "nzst_LRR_post1999"],
                                    blocks[ok99.values], n_boot=500)
        r_cs99 = block_bootstrap_corr(df.loc[ok99, drv], df.loc[ok99, "cs_trend"],
                                      blocks[ok99.values], n_boot=500)
        rows.append(dict(driver=drv,
                         rho_coastsat=r_cs["rho"], lo_cs=r_cs["lo"], hi_cs=r_cs["hi"],
                         rho_nzccd_nearest=r_nz["rho"], lo_nz=r_nz["lo"], hi_nz=r_nz["hi"],
                         rho_nzccd_same_transect=r_st["rho"], lo_st=r_st["lo"],
                         hi_st=r_st["hi"],
                         rho_nzccd_post1999=r_99["rho"], lo_99=r_99["lo"], hi_99=r_99["hi"],
                         rho_coastsat_on_post1999_rows=r_cs99["rho"],
                         n_cs=r_cs["n"], n_nz=r_nz["n"], n_st=r_st["n"],
                         n_post1999=r_99["n"], n_sites=r_cs["n_blocks"]))
    corr = pd.DataFrame(rows)
    corr.to_csv(STATS_DIR / "coastsat_correlations.csv", index=False)
    print(corr.sort_values("rho_coastsat", key=abs, ascending=False)
          [["driver", "rho_coastsat", "rho_nzccd_same_transect", "rho_nzccd_post1999",
            "rho_coastsat_on_post1999_rows", "n_post1999"]]
          .head(14).round(3).to_string(index=False))

    cats = []
    for cat in [c for c in CATEGORICAL_DRIVERS if c in df.columns]:
        e_cs = kruskal_epsilon_sq(df.cs_trend, df[cat])
        e_nz = kruskal_epsilon_sq(df.nz_WLR, df[cat])
        cats.append(dict(driver=cat, eps2_coastsat=e_cs["eps2"],
                         eps2_nzccd_matched=e_nz["eps2"], k=e_cs["k"], n=e_cs["n"]))
    pd.DataFrame(cats).to_csv(STATS_DIR / "coastsat_categorical.csv", index=False)

    # NZCCD vs CoastSat agreement
    comp = []
    def agree(scope, a, b, label, min_n=200):
        d = pd.DataFrame({"a": a, "b": b}).dropna()
        if len(d) < min_n:
            return
        comp.append(dict(scope=scope, comparison=label, n=len(d),
                         spearman=d.a.corr(d.b, method="spearman"),
                         pearson=d.a.corr(d.b),
                         sign_agreement=(np.sign(d.a) == np.sign(d.b)).mean(),
                         median_abs_diff=(d.a - d.b).abs().median()))
    near = df.nz_dist_m <= 100
    agree("all", df.cs_trend[near], df.nz_WLR[near],
          "CoastSat 1999-2026 vs NZCCD WLR full period (nearest <=100 m)")
    agree("all", df.cs_trend, df.nzst_WLR,
          "CoastSat 1999-2026 vs NZCCD WLR full period (same transect)")
    ok = df.nzst_n_post1999 >= 3
    agree("all", df.cs_trend[ok], df.nzst_LRR_post1999[ok],
          "CoastSat 1999-2026 vs NZCCD LRR post-1999 (same transect, same period)")
    agree("all", df.cs_trend[df.nzst_n_post1999 >= 2],
          df.nzst_EPR_post1999[df.nzst_n_post1999 >= 2],
          "CoastSat 1999-2026 vs NZCCD EPR post-1999 (same transect, same period)")
    for reg, g in df[near].groupby("nz_Region"):
        agree(reg, g.cs_trend, g.nz_WLR, "CoastSat vs NZCCD WLR (nearest <=100 m)")
    pd.DataFrame(comp).round(3).to_csv(STATS_DIR / "coastsat_comparison.csv",
                                       index=False)
    print(pd.DataFrame(comp).query("scope=='all'")
          [["comparison", "n", "spearman", "sign_agreement"]].round(3)
          .to_string(index=False))

    # satellite-era epochs
    ep = df.dropna(subset=["cs_delta_trend"])
    summ = [dict(scope="ALL", n=len(ep), pre_median=ep.cs_trend_pre.median(),
                 post_median=ep.cs_trend_post.median(),
                 delta_median=ep.cs_delta_trend.median(),
                 pct_eroding_pre=100 * (ep.cs_trend_pre < 0).mean(),
                 pct_eroding_post=100 * (ep.cs_trend_post < 0).mean(),
                 persistence_rho=ep.cs_trend_pre.corr(ep.cs_trend_post,
                                                      method="spearman"))]
    for reg, g in ep.groupby("nz_Region"):
        if len(g) >= 200:
            summ.append(dict(scope=reg, n=len(g), pre_median=g.cs_trend_pre.median(),
                             post_median=g.cs_trend_post.median(),
                             delta_median=g.cs_delta_trend.median(),
                             pct_eroding_pre=100 * (g.cs_trend_pre < 0).mean(),
                             pct_eroding_post=100 * (g.cs_trend_post < 0).mean(),
                             persistence_rho=g.cs_trend_pre.corr(
                                 g.cs_trend_post, method="spearman")))
    pd.DataFrame(summ).round(3).to_csv(STATS_DIR / "coastsat_epoch_summary.csv",
                                       index=False)
    print(pd.DataFrame(summ).head(1).round(3).to_string(index=False))
    eb = ep.site_id.astype("category").cat.codes.values
    erows = [dict(driver=drv, **block_bootstrap_corr(ep[drv], ep.cs_delta_trend,
                                                     eb, n_boot=500))
             for drv in numeric]
    pd.DataFrame(erows).to_csv(STATS_DIR / "coastsat_epoch_correlations.csv",
                               index=False)
    return corr


if __name__ == "__main__":
    df = build()
    run_stats(df)
