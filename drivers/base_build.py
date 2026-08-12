"""Stage 00: build base_transects.parquet and uncy_lookup.parquet."""

from glob import glob

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from .common import (
    COASTAL_DEM, DRIVER_DATA, INTERSECTS_GLOB, NZCCD_SHORELINES,
    PUBLISHED_ZIP, QA_DIR, RATES_PARQUET, cast_unique_id, load_transect_lines,
)

BLOCK_LEN_M = 2000  # default alongshore block for the spatial bootstrap


def build_base():
    rates = pd.read_parquet(RATES_PARQUET)
    rates["UniqueID"] = cast_unique_id(rates["UniqueID"])
    assert rates["UniqueID"].is_unique and len(rates) == 228_538

    pts = gpd.GeoSeries.from_xy(rates.lon, rates.lat, crs=4326).to_crs(2193)
    rates["x2193"], rates["y2193"] = pts.x.values, pts.y.values

    pub = pyogrio.read_dataframe(
        f"zip://{PUBLISHED_ZIP}!nzccd-coastal-change-rates.shp",
        columns=["UniqueID", "TCD"], read_geometry=False)
    pub["UniqueID"] = cast_unique_id(pub["UniqueID"])
    pub = pub.drop_duplicates("UniqueID")

    base = rates.drop(columns=["Dates", "Distances"]).merge(
        pub, on="UniqueID", how="left")
    missing_tcd = base.TCD.isna().sum()
    only_published = set(pub.UniqueID) - set(rates.UniqueID)
    pd.Series(sorted(only_published), name="UniqueID").to_csv(
        QA_DIR / "published_only_ids.csv", index=False)
    print(f"TCD joined; {missing_tcd} base rows without TCD, "
          f"{len(only_published)} published-only points logged")

    # Alongshore axis: TCD resets per mapped section (max ~67 km), so the
    # national ordering comes from the UniqueID itself — last 9 digits are
    # island-route chainage in cm (spec sheet: MEAS*100).
    base["island"] = base.UniqueID // 10**9
    base["chain_m"] = (base.UniqueID % 10**9) / 100.0
    step = (base.sort_values(["island", "chain_m"])
                .groupby("island").chain_m.diff())
    med_step = step.median()
    print(f"median alongshore chain_m step = {med_step:.2f} (expect ~10)")
    assert 5 <= med_step <= 20, "UniqueID chainage does not step at ~10 m"

    # Contiguous alongshore blocks within island, for the spatial bootstrap.
    base["block_id"] = base.island * 10_000_000 + (
        base.chain_m // BLOCK_LEN_M).astype("int64")

    base.to_parquet(DRIVER_DATA / "base_transects.parquet", index=False)
    print(f"wrote base_transects.parquet rows={len(base)} cols={len(base.columns)}")
    return base


def build_uncy_lookup():
    """(UniqueID, Date) -> shoreline-intersect uncertainty, for epoch WLS."""
    parts = []
    for f in sorted(glob(INTERSECTS_GLOB)):
        df = pyogrio.read_dataframe(
            f, columns=["Unique_ID", "Date", "Uncertaint"], read_geometry=False)
        parts.append(df)
        print(f"  {f.split('/')[-1]}: {len(df):,} rows")
    uncy = pd.concat(parts, ignore_index=True)
    uncy["UniqueID"] = cast_unique_id(uncy["Unique_ID"])
    uncy["Date"] = pd.to_datetime(uncy["Date"]).dt.strftime("%Y-%m-%d")
    uncy = (uncy[["UniqueID", "Date", "Uncertaint"]]
            .dropna(subset=["Uncertaint"])
            .drop_duplicates(["UniqueID", "Date"]))
    uncy.to_parquet(DRIVER_DATA / "uncy_lookup.parquet", index=False)
    print(f"wrote uncy_lookup.parquet rows={len(uncy):,}")

    # Region-median Total_UNCY per date, the documented fallback.
    sh = pyogrio.read_dataframe(
        str(NZCCD_SHORELINES), columns=["Date", "Region", "Total_UNCY"],
        read_geometry=False)
    sh["Date"] = pd.to_datetime(sh["Date"]).dt.strftime("%Y-%m-%d")
    fb = (sh.groupby(["Region", "Date"], observed=True)
            .Total_UNCY.median().reset_index())
    fb.to_parquet(DRIVER_DATA / "uncy_fallback.parquet", index=False)
    print(f"wrote uncy_fallback.parquet rows={len(fb):,}")
    return uncy


def check_landward_convention(n_sample=400, seed=0):
    """Which transect end is landward? DSAS.ipynb uses get_point(t, -1) as the
    distance origin. Sample the coastal DEM at both ends: the land end has
    valid elevation far more often (ocean is NoData in the coastal strip)."""
    import rasterio

    lines = load_transect_lines()
    rng = np.random.default_rng(seed)
    sample = lines.iloc[rng.choice(len(lines), n_sample, replace=False)]
    first = shapely.get_point(sample.geometry.values, 0)
    last = shapely.get_point(sample.geometry.values, -1)

    def frac_valid(points):
        with rasterio.open(COASTAL_DEM) as src:
            vals = np.array([v[0] for v in src.sample(
                [(p.x, p.y) for p in points], masked=False)])
        return float(((vals != src.nodata) & (vals > -100) & (vals < 2000)).mean())

    f_first, f_last = frac_valid(first), frac_valid(last)
    landward = "last" if f_last > f_first else "first"
    print(f"valid-DEM fraction: first-vertex={f_first:.2f} last-vertex={f_last:.2f}"
          f" -> landward end = {landward} vertex")
    pd.DataFrame([{"first_valid": f_first, "last_valid": f_last,
                   "landward_end": landward}]).to_csv(
        QA_DIR / "landward_convention.csv", index=False)
    return landward


if __name__ == "__main__":
    build_base()
    build_uncy_lookup()
    check_landward_convention()
