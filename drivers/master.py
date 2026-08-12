"""Stage 20: join all driver tables onto the base, add derived cross-driver
variables, emit drivers_master.parquet + aggregated variants + coverage matrix.

Run:  python3 -m drivers.master
"""

import numpy as np
import pandas as pd
import shapely

from .common import DRIVER_DATA, QA_DIR, load_base
from .base_build import load_transect_lines

DRIVER_TABLES = [
    "d01_waves", "d02_slope", "d03_vlm", "d04_elevation", "d05_tides",
    "d06_rivers", "d07_typology", "d08_geology", "d09_quakes",
]

# headline numeric driver per table, for the coverage matrix
KEY_VARS = {
    "d01_waves": "hs_mean", "d02_slope": "beach_slope_face",
    "d03_vlm": "vlm_mm_yr", "d04_elevation": "backshore_mean",
    "d05_tides": "spring_range_m", "d06_rivers": "dist_mouth_km",
    "d07_typology": "Typology", "d08_geology": "lith_class",
    "d09_quakes": "shaking_idx",
}


def wave_incidence(master):
    """|angle| between energy-mean wave-from direction and the seaward
    shore-normal; 0 = head-on, 90 = shore-parallel."""
    lines = load_transect_lines()
    geo = lines.reindex(master.UniqueID).geometry
    first = shapely.get_point(geo.values, 0)
    last = shapely.get_point(geo.values, -1)
    fx, fy = shapely.get_x(first), shapely.get_y(first)
    lx, ly = shapely.get_x(last), shapely.get_y(last)
    land_last = (master.landward_side == "last").values
    # seaward vector: from the landward end to the seaward end
    dx = np.where(land_last, fx - lx, lx - fx)
    dy = np.where(land_last, fy - ly, ly - fy)
    seaward_az = (np.degrees(np.arctan2(dx, dy))) % 360
    inc = (master.dir_energy_mean.values - seaward_az + 180) % 360 - 180
    out = np.abs(inc)
    out[~np.isfinite(master.dir_energy_mean.values)] = np.nan
    return out, seaward_az


def build():
    base = load_base()
    n0 = len(base)
    master = base
    for name in DRIVER_TABLES:
        path = DRIVER_DATA / f"{name}.parquet"
        if not path.exists():
            print(f"!! missing {name}, skipping")
            continue
        d = pd.read_parquet(path)
        dup = [c for c in d.columns if c in master.columns and c != "UniqueID"]
        if dup:
            d = d.drop(columns=dup)
            print(f"{name}: dropped duplicate cols {dup}")
        master = master.merge(d, on="UniqueID", how="left")
        assert len(master) == n0, f"{name} join changed row count"
        print(f"joined {name}: +{len(d.columns) - 1} cols")

    if {"dir_energy_mean", "landward_side"} <= set(master.columns):
        master["wave_incidence_deg"], master["seaward_az_deg"] = \
            wave_incidence(master)

    master.to_parquet(DRIVER_DATA / "drivers_master.parquet", index=False)
    print(f"wrote drivers_master.parquet rows={len(master)} "
          f"cols={len(master.columns)}")

    # coverage matrix: % non-null of each headline variable, by region
    cov = {}
    for name, var in KEY_VARS.items():
        if var in master.columns:
            cov[name] = master.groupby("Region")[var].apply(
                lambda s: 100 * s.notna().mean())
    cov_df = pd.DataFrame(cov).round(1)
    cov_df.loc["ALL"] = [100 * master[v].notna().mean()
                         for n, v in KEY_VARS.items() if v in master.columns]
    cov_df.to_csv(QA_DIR / "coverage_matrix.csv")
    print(cov_df.to_string())

    _aggregates(master)
    _web_export(master)
    return master


WEB_COLS = ["UniqueID", "Region", "lat", "lon", "WLR", "WCI", "NSM", "SCE",
            "EPR", "ShrCount", "Duration", "hs_mean", "hs_p99",
            "storm_hrs_gt4m_yr", "cge_mean", "wave_incidence_deg",
            "beach_slope_face", "tanbeta_nearshore", "vlm_mm_yr",
            "backshore_mean", "backshore_max", "spring_range_m",
            "dist_mouth_km", "river_supply_idx", "rain_mm_yr", "shaking_idx",
            "lith_class", "erodibility_ord", "geol_age_ma", "Typology",
            "SHORE_TYPE", "EXPOSURE"]


def _web_export(master):
    """Slim float32 table for the drivers.html Leaflet map."""
    cols = [c for c in WEB_COLS if c in master.columns]
    web = master[cols].copy()
    for c in web.select_dtypes(include=["float64"]).columns:
        web[c] = web[c].astype("float32")
    web.to_parquet(DRIVER_DATA / "drivers_map.parquet", index=False)
    print(f"wrote drivers_map.parquet cols={len(cols)} "
          f"({(DRIVER_DATA / 'drivers_map.parquet').stat().st_size / 1e6:.1f} MB)")


def _cat_mode(s):
    m = s.mode()
    return m.iloc[0] if len(m) else np.nan


def _aggregates(master):
    num = master.select_dtypes(include=[np.number]).columns.difference(
        ["UniqueID", "block_id"])
    cat = [c for c in ("Typology", "SubTypolog", "SHORE_TYPE", "EXPOSURE",
                       "HINTERLAND", "lith_class", "erodibility_ord",
                       "landward_side", "Region") if c in master.columns]

    km = master.assign(km_id=master.island * 10**7
                       + (master.chain_m // 1000).astype(int))
    agg = km.groupby("km_id").agg(
        {**{c: "median" for c in num}, **{c: _cat_mode for c in cat},
         "UniqueID": "count"}).rename(columns={"UniqueID": "n_transects"})
    agg.to_parquet(DRIVER_DATA / "master_1km.parquet")
    print(f"wrote master_1km.parquet rows={len(agg)}")

    if "Typology" in master.columns:
        m = master.sort_values(["island", "chain_m"]).copy()
        typ = m.Typology.fillna("NA")
        new_run = (typ != typ.shift()) | (m.island != m.island.shift()) | \
            (m.chain_m.diff() > 500)
        m["site_id"] = new_run.cumsum()
        agg2 = m.groupby("site_id").agg(
            {**{c: "median" for c in num}, **{c: _cat_mode for c in cat},
             "UniqueID": "count"}).rename(columns={"UniqueID": "n_transects"})
        agg2 = agg2[agg2.n_transects >= 5]
        agg2.to_parquet(DRIVER_DATA / "master_site.parquet")
        print(f"wrote master_site.parquet rows={len(agg2)} "
              f"(runs of same Typology, >=5 transects)")


if __name__ == "__main__":
    build()
