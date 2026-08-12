"""Driver 02: beach slope for every NZCCD transect.

Three sources, joined onto the 228,538 base transects:

1. CoastSat csv_run7 per-site ``transect_coordinates_and_beach_slopes.csv``
   (560 nzd sites): beach-face slope (tan beta) with lower/upper bounds at the
   transect origin (landward end). Nearest-neighbour join in EPSG:2193,
   max 250 m.
2. ``transects_extended.geojson`` filtered to nzd sites: per-transect
   beach_slope, shoreline trend and ERODIBILITY class, located at the transect
   line midpoint. Nearest-neighbour join in EPSG:2193, max 250 m.
3. Bruun-rule input table: nearshore slope (tanbeta) and closure depth (CD)
   keyed directly on Unique_ID.

Run:  python3 -m drivers.d02_slope
Out:  driver_data/d02_slope.parquet  (one row per base UniqueID)
"""

from glob import glob

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from .common import (BRUUN_WAVE_CSV, CSV_RUN7, QA_DIR, TRANSECTS_EXTENDED,
                     cast_unique_id, load_base, nearest_join, qa_join,
                     write_driver)

NAME = "d02_slope"
MAX_DIST_M = 250.0

OUT_COLS = [
    "UniqueID", "beach_slope_face", "beach_slope_lb", "beach_slope_ub",
    "slope_dist_m", "erodibility", "coastsat_trend", "coastsat_beach_slope",
    "coastsat_dist_m", "tanbeta_nearshore", "closure_depth_m",
]


def _to_2193(df, lon_col, lat_col):
    """Add x2193/y2193 columns projected from lon/lat (EPSG:4326)."""
    pts = gpd.GeoSeries(
        gpd.points_from_xy(df[lon_col], df[lat_col]), crs=4326).to_crs(2193)
    df = df.copy()
    df["x2193"] = pts.x.values
    df["y2193"] = pts.y.values
    return df


def load_site_slopes():
    """Source 1: per-site beach-face slopes at the transect origin."""
    usecols = ["Transect id", "Longitude - Origin", "Latitude - Origin",
               "Beach face slope", "Lower bound", "Upper bound"]
    files = sorted(glob(
        f"{CSV_RUN7}/nzd*/transect_coordinates_and_beach_slopes.csv"))
    df = pd.concat((pd.read_csv(f, usecols=usecols) for f in files),
                   ignore_index=True)
    df = df.dropna(subset=["Beach face slope"]).rename(columns={
        "Beach face slope": "beach_slope_face",
        "Lower bound": "beach_slope_lb",
        "Upper bound": "beach_slope_ub",
    })
    print(f"source 1: {len(files)} site CSVs, {len(df)} transects "
          "with non-null beach-face slope")
    return _to_2193(df, "Longitude - Origin", "Latitude - Origin")


def load_coastsat_extended():
    """Source 2: global CoastSat transects filtered to nzd, at line midpoint."""
    gdf = pyogrio.read_dataframe(
        TRANSECTS_EXTENDED,
        columns=["id", "site_id", "beach_slope", "trend", "ERODIBILITY"],
        where="site_id LIKE 'nzd%'")
    gdf = gdf.to_crs(2193)
    mid = gdf.geometry.interpolate(0.5, normalized=True)
    df = pd.DataFrame({
        "coastsat_beach_slope": gdf["beach_slope"].values,
        "coastsat_trend": gdf["trend"].values,
        "erodibility": gdf["ERODIBILITY"].values,
        "x2193": mid.x.values,
        "y2193": mid.y.values,
    })
    print(f"source 2: {len(df)} nzd transects from transects_extended")
    return df


def load_bruun():
    """Source 3: nearshore slope and closure depth, keyed on Unique_ID."""
    df = pd.read_csv(BRUUN_WAVE_CSV, usecols=["Unique_ID", "tanbeta", "CD"])
    df["UniqueID"] = cast_unique_id(df["Unique_ID"])
    # 59 exact-duplicate rows (identical tanbeta/CD) — keep first.
    df = df.drop_duplicates("UniqueID")
    print(f"source 3: {len(df)} unique Unique_IDs with tanbeta/CD")
    return df.rename(columns={"tanbeta": "tanbeta_nearshore",
                              "CD": "closure_depth_m"})[
        ["UniqueID", "tanbeta_nearshore", "closure_depth_m"]]


def _qa_region_coverage(df):
    cov = df.groupby("Region").agg(
        n=("UniqueID", "size"),
        slope_face_pct=("beach_slope_face", lambda s: 100 * s.notna().mean()),
        coastsat_slope_pct=("coastsat_beach_slope",
                            lambda s: 100 * s.notna().mean()),
        tanbeta_pct=("tanbeta_nearshore", lambda s: 100 * s.notna().mean()),
    ).round(2).sort_values("slope_face_pct", ascending=False)
    path = QA_DIR / f"{NAME}_region_coverage.csv"
    cov.to_csv(path)
    print(f"wrote {path}")
    print(cov.to_string())
    return cov


def _qa_scatter(df):
    """Beach-face slope vs nearshore slope (expect weak positive relation)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    both = df[["beach_slope_face", "tanbeta_nearshore"]].dropna()
    r_p = both["beach_slope_face"].corr(both["tanbeta_nearshore"])
    r_s = both["beach_slope_face"].corr(both["tanbeta_nearshore"],
                                        method="spearman")

    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(both["tanbeta_nearshore"], both["beach_slope_face"],
               s=4, alpha=0.08, color="#2a78d6", edgecolors="none",
               rasterized=True)
    ax.set_xlim(0, both["tanbeta_nearshore"].quantile(0.995))
    ax.set_ylim(0, both["beach_slope_face"].quantile(0.995))
    ax.set_xlabel("nearshore slope tanbeta (Bruun-rule input)",
                  color="#404040")
    ax.set_ylabel("beach-face slope tan beta (CoastSat)", color="#404040")
    ax.set_title(f"Beach-face vs nearshore slope  (n={len(both):,})",
                 color="#262626")
    ax.text(0.97, 0.04,
            f"Pearson r = {r_p:.2f}\nSpearman r = {r_s:.2f}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=10, color="#404040")
    ax.grid(True, color="#e6e6e6", lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#bfbfbf")
    ax.tick_params(colors="#666666")
    fig.tight_layout()
    path = QA_DIR / f"{NAME}_face_vs_tanbeta.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path}  pearson={r_p:.3f} spearman={r_s:.3f} n={len(both)}")
    return r_p, r_s


def build():
    base = load_base(columns=["UniqueID", "Region", "x2193", "y2193"])

    slopes = load_site_slopes()
    j1 = nearest_join(
        base, slopes,
        ["beach_slope_face", "beach_slope_lb", "beach_slope_ub"],
        "slope", max_dist=MAX_DIST_M)
    qa_join(j1["slope_dist_m"], NAME, MAX_DIST_M)

    coastsat = load_coastsat_extended()
    j2 = nearest_join(
        base, coastsat,
        ["coastsat_beach_slope", "coastsat_trend", "erodibility"],
        "coastsat", max_dist=MAX_DIST_M)
    qa_join(j2["coastsat_dist_m"], f"{NAME}_coastsat", MAX_DIST_M)

    bruun = load_bruun()

    df = (base[["UniqueID", "Region"]]
          .merge(j1, on="UniqueID", validate="1:1")
          .merge(j2, on="UniqueID", validate="1:1")
          .merge(bruun, on="UniqueID", how="left", validate="1:1"))
    assert len(df) == len(base)

    _qa_region_coverage(df)
    _qa_scatter(df)

    n_face = int(df["beach_slope_face"].notna().sum())
    pct_face = 100 * n_face / len(df)
    med_face = df["beach_slope_face"].median()
    print(f"beach_slope_face non-null: {n_face} / {len(df)} "
          f"({pct_face:.2f}%)  median={med_face:.4f}")
    print(f"coastsat_beach_slope non-null: "
          f"{df['coastsat_beach_slope'].notna().sum()} "
          f"({100 * df['coastsat_beach_slope'].notna().mean():.2f}%)")
    print(f"tanbeta_nearshore non-null: "
          f"{df['tanbeta_nearshore'].notna().sum()} "
          f"({100 * df['tanbeta_nearshore'].notna().mean():.2f}%)")

    write_driver(df[OUT_COLS], NAME)
    return df


if __name__ == "__main__":
    build()
