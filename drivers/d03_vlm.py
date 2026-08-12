"""Driver 03: vertical land motion (VLM) at every NZCCD transect.

Source: NZ_VLM_final_May24.csv — 8,173 coastal sites (InSAR-derived VLM,
Hamling et al.-style product). Sites are projected to EPSG:2193 and joined to
the 228,538 base transect points by nearest neighbour (no max distance: VLM
fields are smooth at the multi-km scale, so every transect gets a value).

Sign convention (verified empirically 2026-08-07): POSITIVE = UPLIFT.
  - Matata (BOP) magmatic uplift dome (documented ~+10 mm/yr uplift):
    raw rates +6..+9.4 mm/yr, and the 'BOP corrected' column removes exactly
    this transient (corrected values drop to ~0-4 mm/yr there).
  - Wellington (documented subsidence): -2.9 mm/yr.
  - South Wairarapa coast (documented interseismic subduction subsidence):
    -7..-8.3 mm/yr.
  Note the Kaikoura coast reads -2.3 mm/yr: this product's epoch is
  post-2016, so it records POST-seismic relaxation (subsidence) after the
  coseismic uplift, not the quake itself.

Derived relative sea-level rise:
  rslr_mm_yr = 1.8 - vlm_mm_yr
where 1.8 mm/yr is the NZ 20th-century absolute (geocentric) sea-level rise
(Hannah & Bell 2012). Land going up (vlm > 0) reduces the sea-level rise felt
locally; subsidence (vlm < 0) adds to it.

Run:  python3 -m drivers.d03_vlm
Out:  driver_data/d03_vlm.parquet (228,538 rows, one per UniqueID)
"""

import geopandas as gpd
import pandas as pd

from .common import (QA_DIR, VLM_CSV, load_base, nearest_join, qa_join,
                     write_driver)

NZ_ABS_SLR_MM_YR = 1.8  # NZ 20th-century absolute SLR (Hannah & Bell 2012)

COLMAP = {
    "Vertical Rate - BOP corrected (mm/yr)": "vlm_mm_yr",
    "Vertical Rate (mm/yr)": "vlm_raw_mm_yr",
    "1-sigma uncertainty (mm/yr)": "vlm_sigma",
    "Quality Factor": "vlm_quality",
    "Number of obs": "vlm_nobs",
}


def load_vlm_sites():
    """VLM sites with EPSG:2193 coords; drops the CSV's trailing empty cols."""
    df = pd.read_csv(VLM_CSV)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.rename(columns=COLMAP)
    assert len(df) == 8173, f"expected 8,173 VLM sites, got {len(df)}"
    assert not df[list(COLMAP.values())].isna().any().any()
    pts = gpd.GeoSeries(gpd.points_from_xy(df.Lon, df.Lat), crs=4326).to_crs(2193)
    df["x2193"], df["y2193"] = pts.x.values, pts.y.values
    return df


def build():
    sites = load_vlm_sites()

    # Empirical sign check at documented anomalies (positive = uplift).
    for label, (lat0, lat1, lon0, lon1) in {
        "Matata dome (uplift, raw)": (-37.95, -37.75, 176.6, 176.9),
        "Tauranga / BOP": (-37.9, -37.5, 175.9, 176.5),
        "Wellington (subsiding)": (-41.4, -41.2, 174.7, 174.95),
        "Kaikoura (post-seismic)": (-42.6, -42.2, 173.4, 174.0),
    }.items():
        sub = sites[sites.Lat.between(lat0, lat1) & sites.Lon.between(lon0, lon1)]
        print(f"sign check {label:28s} n={len(sub):4d} "
              f"raw={sub.vlm_raw_mm_yr.mean():+.2f} "
              f"corr={sub.vlm_mm_yr.mean():+.2f} mm/yr")

    base = load_base(columns=["UniqueID", "Region", "x2193", "y2193"])
    cols = ["vlm_mm_yr", "vlm_raw_mm_yr", "vlm_sigma", "vlm_quality", "vlm_nobs"]
    out = nearest_join(base, sites, cols, name="vlm", max_dist=None)
    out["rslr_mm_yr"] = NZ_ABS_SLR_MM_YR - out["vlm_mm_yr"]
    assert len(out) == len(base) == 228538

    qa_join(out["vlm_dist_m"], "d03_vlm", threshold_m=2000)

    region = (out.assign(Region=base["Region"].values)
              .groupby("Region")
              .agg(n=("vlm_mm_yr", "size"),
                   vlm_mean_mm_yr=("vlm_mm_yr", "mean"),
                   vlm_median_mm_yr=("vlm_mm_yr", "median"),
                   rslr_mean_mm_yr=("rslr_mm_yr", "mean"),
                   join_dist_median_m=("vlm_dist_m", "median"))
              .round(3).sort_values("vlm_mean_mm_yr"))
    region.to_csv(QA_DIR / "d03_vlm_region_means.csv")
    print(region.to_string())

    in_band = out["vlm_mm_yr"].between(-5, 5).mean() * 100
    print(f"vlm in [-5, +5] mm/yr: {in_band:.2f}% "
          f"(range {out.vlm_mm_yr.min():+.2f}..{out.vlm_mm_yr.max():+.2f})")

    return write_driver(out, "d03_vlm")


if __name__ == "__main__":
    build()
