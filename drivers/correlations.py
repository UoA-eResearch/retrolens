"""Stage 30: driver-vs-rate correlations with spatially honest uncertainty.

Outputs (driver_data/stats/):
  correlogram_WLR.csv          alongshore autocorrelation of WLR + block choice
  corr_numeric.csv             Spearman+Pearson rho [block-bootstrap CI] per
                               driver x response, at 3 block lengths (L/2,L,2L)
  corr_numeric_by_typology.csv Spearman per driver x WLR within Typology class
  corr_numeric_by_region.csv   Spearman per driver x WLR within Region
  categorical_effects.csv      Kruskal-Wallis epsilon^2 per categorical driver
  group_medians_<cat>.csv      per-class WLR medians with CIs
  collinearity_spearman.csv    driver-driver Spearman matrix
  aggregation_sensitivity.csv  rho at transect vs 1km vs site aggregation
  morans_i.csv                 Moran's I of WLR and residual structure

Run:  python3 -m drivers.correlations
"""

import numpy as np
import pandas as pd

from .common import DRIVER_DATA, load_base
from .stats import (alongshore_correlogram, block_bootstrap_corr,
                    decorrelation_length, effective_n, group_median_ci,
                    kruskal_epsilon_sq, morans_i)

STATS_DIR = DRIVER_DATA / "stats"

RESPONSES = ["WLR", "NSM", "SCE", "EPR"]

NUMERIC_DRIVERS = [
    "hs_mean", "hs_p99", "storm_hrs_gt4m_yr", "cge_mean", "t01_mean",
    "wave_incidence_deg", "beach_slope_face", "tanbeta_nearshore",
    "closure_depth_m", "vlm_mm_yr", "backshore_mean", "backshore_max",
    "hinterland_slope", "spring_range_m", "form_factor", "dist_mouth_km",
    "river_supply_idx", "rain_mm_yr", "rainstorm_days", "geol_age_ma",
    "erodibility_ord", "shaking_idx", "n_M5_50km", "dist_M65_km",
]

CATEGORICAL_DRIVERS = ["Typology", "SubTypolog", "SHORE_TYPE", "EXPOSURE",
                       "HINTERLAND", "lith_class", "erodibility"]


def run():
    STATS_DIR.mkdir(exist_ok=True)
    m = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet")
    numeric = [c for c in NUMERIC_DRIVERS if c in m.columns]
    cats = [c for c in CATEGORICAL_DRIVERS if c in m.columns]
    print(f"{len(numeric)} numeric drivers, {len(cats)} categorical")

    # ---- block length from the WLR correlogram
    cg = alongshore_correlogram(m.WLR, m.island, m.chain_m)
    L = decorrelation_length(cg)
    cg.to_csv(STATS_DIR / "correlogram_WLR.csv", index=False)
    n_eff, r1 = effective_n(m.WLR, m.island, m.chain_m)
    print(f"decorrelation length ~{L:.0f} m; lag-10m r1={r1:.3f}; "
          f"effective n ~{n_eff:,.0f} of {m.WLR.notna().sum():,}")
    block_lens = [max(int(L), 500), max(int(2 * L), 1000), max(int(4 * L), 2000)]
    pd.DataFrame([{"decorrelation_m": L, "r1_lag10m": r1, "n_eff": n_eff,
                   "block_lens_m": str(block_lens)}]).to_csv(
        STATS_DIR / "block_choice.csv", index=False)

    def blocks_for(length_m):
        return (m.island * 10**7 + (m.chain_m // length_m)).astype("int64").values

    # ---- numeric drivers x responses
    rows = []
    main_L = block_lens[1]
    for drv in numeric:
        for resp in RESPONSES:
            for bl in block_lens:
                if bl != main_L and resp != "WLR":
                    continue  # sensitivity lengths on the primary response only
                for meth in ("spearman", "pearson"):
                    if meth == "pearson" and bl != main_L:
                        continue
                    r = block_bootstrap_corr(m[drv], m[resp], blocks_for(bl),
                                             n_boot=1000, method=meth)
                    rows.append(dict(driver=drv, response=resp, method=meth,
                                     block_len_m=bl, **r))
        print(f"  corr done: {drv}")
    corr = pd.DataFrame(rows)
    corr.to_csv(STATS_DIR / "corr_numeric.csv", index=False)

    # ---- stratified (Spearman, WLR, main block length)
    strat_rows = []
    for strat_col, fname in (("Typology", "corr_numeric_by_typology.csv"),
                             ("Region", "corr_numeric_by_region.csv")):
        if strat_col not in m.columns:
            continue
        for level, g in m.groupby(strat_col, observed=True):
            if len(g) < 2000:
                continue
            gb = (g.island * 10**7 + (g.chain_m // main_L)).astype("int64").values
            for drv in numeric:
                r = block_bootstrap_corr(g[drv], g.WLR, gb, n_boot=500)
                strat_rows.append(dict(stratum=level, driver=drv, **r))
        pd.DataFrame([r for r in strat_rows]).to_csv(STATS_DIR / fname,
                                                     index=False)
        strat_rows = []
        print(f"  stratified by {strat_col} done")

    # ---- categorical drivers
    cat_rows = []
    for cat in cats:
        for resp in ("WLR", "SCE"):
            e = kruskal_epsilon_sq(m[resp], m[cat])
            cat_rows.append(dict(driver=cat, response=resp, **e))
        gm = group_median_ci(m.WLR, m[cat], m.block_id.values)
        gm.to_csv(STATS_DIR / f"group_medians_{cat}.csv", index=False)
    pd.DataFrame(cat_rows).to_csv(STATS_DIR / "categorical_effects.csv",
                                  index=False)
    print("  categorical done")

    # ---- driver-driver collinearity
    m[numeric].corr(method="spearman").round(3).to_csv(
        STATS_DIR / "collinearity_spearman.csv")

    # ---- aggregation sensitivity
    agg_rows = []
    for level, df in (("transect", m),
                      ("1km", pd.read_parquet(DRIVER_DATA / "master_1km.parquet")),
                      ("site", pd.read_parquet(DRIVER_DATA / "master_site.parquet"))):
        if level == "transect":
            gb = blocks_for(main_L)
        else:
            gb = (df.island * 10**7 + (df.chain_m // main_L)).astype("int64").values
        for drv in numeric:
            if drv not in df.columns:
                continue
            r = block_bootstrap_corr(df[drv], df.WLR, gb, n_boot=500)
            agg_rows.append(dict(level=level, driver=drv, **r))
    pd.DataFrame(agg_rows).to_csv(STATS_DIR / "aggregation_sensitivity.csv",
                                  index=False)
    print("  aggregation sensitivity done")

    # ---- spatial structure of WLR itself (subsampled for tractability)
    sub = m.dropna(subset=["WLR"]).sample(min(50_000, m.WLR.notna().sum()),
                                          random_state=0)
    mi = morans_i(sub.WLR, sub.x2193, sub.y2193)
    pd.DataFrame([dict(variable="WLR", **mi)]).to_csv(
        STATS_DIR / "morans_i.csv", index=False)
    print(f"Moran's I (WLR, 50k sample): {mi['I']:.3f}")


if __name__ == "__main__":
    run()
