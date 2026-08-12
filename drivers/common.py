"""Shared data-access, join and QA helpers for the NZCCD drivers analysis.

All metric operations are in EPSG:2193 (NZTM2000); EPSG:4326 lat/lon only for
display and haversine trees, matching the conventions in DSAS.ipynb.
"""

from glob import glob
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from scipy.spatial import cKDTree

REPO = Path("/mnt/retrolens")
DRIVER_DATA = REPO / "driver_data"
QA_DIR = DRIVER_DATA / "qa"

RATES_PARQUET = REPO / "rates_with_timeseries.parquet"
PUBLISHED_ZIP = REPO / "kx-nzccd-coastal-change-rates-SHP.zip"
TRANSECTS_GLOB = str(REPO / "Data for testing/Unique_ID_transects/*.shp")
MHW_ZIP = (
    REPO / "Data for testing/lds-nz-coastline-mean-high-water-GPKG.zip"
    ).as_posix() + "!nz-coastline-mean-high-water.gpkg"
INTERSECTS_GLOB = "/mnt/Bruunrule_Yaxiong/input/Merged Intersects_UniqueID/*.shp"
NZCCD_SHORELINES = REPO / "Data for testing/NZCCDv1.shp"

BRUUN_WAVE_CSV = "/mnt/Bruunrule_Yaxiong/code/bruunrule_JaMoNoRaSoWa_b_10_with_rates.csv"
TYPOLOGY_PARQUET = "/mnt/Bruunrule_Yaxiong/code/nzccd_rates_proxy.parquet"
VLM_CSV = "/mnt/Bruunrule_Yaxiong/input/SLR_OCC/NZ_VLM_final_May24.csv"
COASTAL_DEM = "/mnt/Bruunrule_Yaxiong/input/CoastalLiDAR/NewZealand_Coastal_DEM_Merged_250m.tif"
FES2022_DIR = "/mnt/CoastSat/fes2022b/ocean_tide_20241025"
CSV_RUN7 = "/mnt/CoastSat/csv_run7"
TRANSECTS_EXTENDED = "/mnt/CoastSat/transects_extended.geojson"
REC2_GDB = "/mnt/rivers/nzRec2_v5.gdb"
WHACS_DIR = "/mnt/WHACS"

RESPONSES = ["WLR", "NSM", "SCE", "EPR", "LRR"]


def cast_unique_id(series):
    """NZCCD UniqueID arrives as float64; cast losslessly to int64."""
    uid = pd.to_numeric(series, errors="raise")
    out = uid.round().astype("int64")
    if not np.allclose(uid, out):
        raise ValueError("UniqueID cast is not lossless")
    return out


def load_base(columns=None):
    df = pd.read_parquet(DRIVER_DATA / "base_transects.parquet", columns=columns)
    return df


def base_gdf(columns=None):
    cols = columns or ["UniqueID", "Region", "TCD", "x2193", "y2193"]
    df = load_base(columns=sorted(set(cols) | {"x2193", "y2193"}))
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.x2193, df.y2193), crs=2193)


def load_transect_lines():
    """National transect linestrings keyed by int64 UniqueID (EPSG:2193)."""
    parts = []
    for f in sorted(glob(TRANSECTS_GLOB)):
        gdf = gpd.read_file(f, columns=["Unique_ID"])
        parts.append(gdf)
    lines = pd.concat(parts, ignore_index=True)
    lines["UniqueID"] = cast_unique_id(lines["Unique_ID"])
    lines = lines.drop(columns=["Unique_ID"]).drop_duplicates("UniqueID")
    return lines.set_index("UniqueID")


def nearest_join(base, driver, cols, name, max_dist=None):
    """Attach `cols` from `driver` to `base` by nearest neighbour in EPSG:2193.

    Both frames need x2193/y2193 columns. Adds `{name}_dist_m`; rows beyond
    max_dist get NaN for `cols` but keep the distance for QA.
    """
    tree = cKDTree(np.c_[driver.x2193.values, driver.y2193.values])
    dist, idx = tree.query(np.c_[base.x2193.values, base.y2193.values], k=1)
    out = driver.iloc[idx][cols].reset_index(drop=True)
    out.index = base.index
    out[f"{name}_dist_m"] = dist
    if max_dist is not None:
        out.loc[dist > max_dist, cols] = np.nan
    return pd.concat([base.reset_index(drop=True)[["UniqueID"]],
                      out.reset_index(drop=True)], axis=1)


def haversine_join(base_latlon, driver_latlon):
    """Nearest neighbour on the sphere. Args are (lat, lon) 2-col arrays.

    Returns (dist_km, idx) following matching_points_ball.py.
    """
    from sklearn.neighbors import BallTree
    tree = BallTree(np.radians(driver_latlon), metric="haversine")
    dist, idx = tree.query(np.radians(base_latlon), k=1)
    return dist[:, 0] * 6371.0, idx[:, 0]


def qa_join(dist_m, name, threshold_m):
    """Join-distance histogram + summary row, saved under driver_data/qa/."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dist_m = np.asarray(dist_m, dtype=float)
    dist_m = dist_m[np.isfinite(dist_m)]
    summary = {
        "driver": name,
        "n": len(dist_m),
        "median_m": float(np.median(dist_m)),
        "p95_m": float(np.percentile(dist_m, 95)),
        "max_m": float(dist_m.max()),
        "pct_over_threshold": float((dist_m > threshold_m).mean() * 100),
        "threshold_m": threshold_m,
    }
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(np.clip(dist_m, 0, threshold_m * 3), bins=100)
    ax.axvline(threshold_m, color="crimson", ls="--", lw=1,
               label=f"threshold {threshold_m:,.0f} m "
                     f"({summary['pct_over_threshold']:.1f}% beyond)")
    ax.set_xlabel("join distance (m, clipped at 3x threshold)")
    ax.set_ylabel("transects")
    ax.set_title(f"{name}: join distance (median {summary['median_m']:,.0f} m)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(QA_DIR / f"{name}_join_dist.png", dpi=120)
    plt.close(fig)
    pd.DataFrame([summary]).to_csv(QA_DIR / f"{name}_join_summary.csv", index=False)
    return summary


def write_driver(df, name):
    """Validate and write one driver table keyed by unique int64 UniqueID."""
    assert df["UniqueID"].dtype == np.int64, f"{name}: UniqueID must be int64"
    assert df["UniqueID"].is_unique, f"{name}: UniqueID not unique"
    df = df.drop(columns=[c for c in ("geometry",) if c in df], errors="ignore")
    path = DRIVER_DATA / f"{name}.parquet"
    pd.DataFrame(df).to_parquet(path, index=False)
    nulls = df.isna().mean().sort_values(ascending=False)
    print(f"wrote {path} rows={len(df)} cols={len(df.columns)}")
    print("null fraction (top):")
    print(nulls.head(10).to_string())
    return path
