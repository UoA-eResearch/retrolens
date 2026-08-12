"""Stage 41: correlate pre/post-1990 rate changes with drivers.

Uses the 1990-split epoch rates (>=3 obs in both epochs for regression rates).
Key hypothesis tests: did wave-climate change (hs_mean_delta etc.) or VLM
pattern the change in shoreline behaviour between epochs?

Outputs (driver_data/stats/): epoch_summary.csv, epoch_correlations.csv,
epoch_rates_joined.parquet (for figures).

Run:  python3 -m drivers.epoch_corr
"""

import numpy as np
import pandas as pd

from .common import DRIVER_DATA
from .correlations import NUMERIC_DRIVERS, STATS_DIR
from .stats import block_bootstrap_corr

EPOCH_DRIVERS = ["hs_mean_delta", "hs_p99_delta", "storm_hrs_delta",
                 "vlm_mm_yr", "shaking_idx"]
SPLIT = 1990


def run():
    STATS_DIR.mkdir(exist_ok=True)
    ep = pd.read_parquet(DRIVER_DATA / "epoch_rates.parquet")
    ep = ep[(ep.split_year == SPLIT) & ep.both_regression].copy()
    m = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet")
    df = ep.merge(m, on="UniqueID", how="inner", suffixes=("", "_full"))
    print(f"{len(df):,} transects with regression rates in both epochs")

    # national summary
    summ = []
    for scope, g in [("ALL", df)] + list(df.groupby("Region")):
        summ.append(dict(
            scope=scope, n=len(g),
            WLR_pre_median=g.WLR_pre.median(), WLR_post_median=g.WLR_post.median(),
            delta_median=g.delta_WLR.median(),
            pct_eroding_pre=100 * (g.WLR_pre < 0).mean(),
            pct_eroding_post=100 * (g.WLR_post < 0).mean(),
            corr_pre_post=g.WLR_pre.corr(g.WLR_post, method="spearman")))
    pd.DataFrame(summ).to_csv(STATS_DIR / "epoch_summary.csv", index=False)
    print(pd.DataFrame(summ).head(1).to_string())

    blocks = df.block_id.values
    rows = []
    drivers = EPOCH_DRIVERS + [c for c in NUMERIC_DRIVERS if c in df.columns]
    seen = set()
    for drv in drivers:
        if drv in seen or drv not in df.columns:
            continue
        seen.add(drv)
        for resp in ("delta_WLR", "WLR_pre", "WLR_post"):
            r = block_bootstrap_corr(df[drv], df[resp], blocks, n_boot=500)
            rows.append(dict(driver=drv, response=resp, **r))
    pd.DataFrame(rows).to_csv(STATS_DIR / "epoch_correlations.csv", index=False)

    keep = ["UniqueID", "Region", "island", "chain_m", "x2193", "y2193",
            "lat", "lon", "WLR_pre", "WLR_post", "delta_WLR", "n_obs_pre",
            "n_obs_post", "span_yr_pre", "span_yr_post", "WCI_pre", "WCI_post"]
    df[[c for c in keep if c in df.columns]].to_parquet(
        STATS_DIR / "epoch_rates_joined.parquet", index=False)
    print("wrote epoch join + correlations")


if __name__ == "__main__":
    run()
