"""Driver 01: WHACS wave climatology joined to NZCCD transects.

Primary join reuses the line-of-sight-filtered Unique_ID -> wave point mapping
built by the Bruun-rule pipeline (wave_lat/wave_lon columns); transects absent
from that mapping fall back to nearest seapoint. Run after drivers.whacs.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .common import (BRUUN_WAVE_CSV, DRIVER_DATA, cast_unique_id, load_base,
                     qa_join, write_driver)


def build():
    clim = pd.read_parquet(DRIVER_DATA / "whacs_seapoint_climatology.parquet")
    base = load_base(["UniqueID", "x2193", "y2193", "lat", "lon"])

    # seapoints in NZTM for metric distances
    sp = gpd.GeoSeries.from_xy(clim.lon, clim.lat, crs=4326).to_crs(2193)
    sp_xy = np.c_[sp.x.values, sp.y.values]
    tree = cKDTree(sp_xy)

    # primary: LOS-filtered mapping (coordinate-keyed to the WHACS grid)
    bruun = pd.read_csv(BRUUN_WAVE_CSV,
                        usecols=["Unique_ID", "wave_lat", "wave_lon"])
    bruun["UniqueID"] = cast_unique_id(bruun["Unique_ID"])
    bruun = bruun.drop_duplicates("UniqueID")
    key = lambda lat, lon: (np.round(lat, 4) * 10**4).astype(np.int64) * 10**8 \
        + (np.round(lon, 4) * 10**4).astype(np.int64)
    clim_key = pd.Series(np.arange(len(clim)), index=key(clim.lat, clim.lon))
    bruun["sp_idx"] = clim_key.reindex(key(bruun.wave_lat, bruun.wave_lon)).values

    df = base.merge(bruun[["UniqueID", "sp_idx"]], on="UniqueID", how="left")
    matched = df.sp_idx.notna()
    print(f"LOS mapping: {matched.sum():,}/{len(df):,} transects "
          f"({df.sp_idx.isna().sum():,} to nearest-fallback)")

    # fallback: nearest seapoint
    need = ~matched
    _, idx = tree.query(np.c_[df.loc[need, "x2193"], df.loc[need, "y2193"]], k=1)
    df.loc[need, "sp_idx"] = idx
    df["sp_idx"] = df.sp_idx.astype(int)
    df["wave_join_method"] = np.where(matched, "los_mapped", "nearest")
    dx = sp_xy[df.sp_idx, 0] - df.x2193.values
    dy = sp_xy[df.sp_idx, 1] - df.y2193.values
    df["wave_dist_m"] = np.hypot(dx, dy)

    wave_cols = [c for c in clim.columns if c not in ("seapoint", "lon", "lat")]
    out = pd.concat(
        [df[["UniqueID", "wave_join_method", "wave_dist_m"]].reset_index(drop=True),
         clim.iloc[df.sp_idx][wave_cols].reset_index(drop=True)], axis=1)
    # epoch deltas for the epoch-correlation stage
    out["hs_mean_delta"] = out.hs_mean_9023 - out.hs_mean_7989
    out["hs_p99_delta"] = out.hs_p99_9023 - out.hs_p99_7989
    out["storm_hrs_delta"] = out.storm_hrs_gt4m_yr_9023 - out.storm_hrs_gt4m_yr_7989

    qa_join(out.wave_dist_m, "d01_waves", 10_000)
    write_driver(out, "d01_waves")
    reg = base.merge(out[["UniqueID", "hs_mean", "wave_dist_m"]], on="UniqueID")
    print(reg.groupby(reg.UniqueID // 10**9).agg(
        hs_mean=("hs_mean", "mean"), med_dist_km=("wave_dist_m",
                                                  lambda d: d.median() / 1000)))
    return out


if __name__ == "__main__":
    build()
