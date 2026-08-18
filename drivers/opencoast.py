"""Open-coast length for NZ from the LINZ 1:50k MHW coastline.

Definition (morphological): a point on the coast is *open coast* if a disc of
radius R can sit in the water tangent to it and that water is connected to
the open ocean through passages wider than 2R. Harbours, estuaries and fiords
with entrances narrower than 2R are therefore *enclosed*, regardless of how
wide they are inside; open embayments wider than 2R stay open. Computed on a
100 m raster from the coastline geometry alone (no land polygons needed — the
LINZ MHW lines do not close into rings):

  1. rasterise MHW lines -> coast mask; d = distance-to-coast (EDT)
  2. eroded = d >= R; keep the connected component touching the raster border
     (the ocean); land interiors and closed harbours are other components
  3. open_ocean = cells within R of that component
  4. a 100 m coast segment is open if its midpoint is within TOL of open_ocean

R in {1, 2, 3, 5} km for sensitivity. Geometry alone cannot see shelter by
offshore islands or a huge-mouthed harbour (Kaipara), so the headline
definition adds wave exposure: **open coast = geometrically open at R = 1 km
AND WHACS mean Hs >= 0.75 m at the nearest seapoint**. Calibrated against the
NZCCD's expert EXPOSURE field: 100% of 'S' (sheltered) and 82% of 'E'
(exposed) transects are recovered (balanced accuracy 91%; pure geometry
peaks at 56%). Sensitivity table over R x Hs threshold is written too.

Also attaches: NZ mainland/island membership (Natural Earth 10 m), NZCCD
Region (nearest transect), NZCCD + CoastSat coverage, LINZ coast category,
NZCCD WLR sign for eroding/accreting length.

Run:  python3 -m drivers.opencoast
Out:  driver_data/opencoast_points.parquet, driver_data/stats/opencoast_lengths.csv
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
from rasterio import features
from rasterio.transform import from_origin
from scipy import ndimage
from scipy.spatial import cKDTree

from .common import DRIVER_DATA, TRANSECTS_EXTENDED, load_base

MHW = "/mnt/Bruunrule_Yaxiong/input/coastline/nz-coastline-mean-high-water.shp"
STATS = DRIVER_DATA / "stats"
RES = 100.0                 # m
RADII_KM = (1, 2, 3, 5)
TOL_M = 200.0               # coast midpoint must be within TOL of open ocean
SEG_M = 100.0               # coastline discretisation
HEADLINE_R = 2


def coast_segments():
    mhw = gpd.read_file(MHW)[["id", "coast_cate", "geometry"]].to_crs(2193)
    mhw = mhw.explode(index_parts=False, ignore_index=True)
    lengths = mhw.length.values
    n_seg = np.maximum(np.ceil(lengths / SEG_M).astype(int), 1)
    line_idx = np.repeat(np.arange(len(mhw)), n_seg)
    seg_i = np.concatenate([np.arange(k) for k in n_seg])
    seg_len = np.minimum(SEG_M, lengths[line_idx] - seg_i * SEG_M)
    mid = seg_i * SEG_M + seg_len / 2
    pts = shapely.line_interpolate_point(mhw.geometry.values[line_idx], mid)
    df = pd.DataFrame({
        "line_id": mhw.id.values[line_idx],
        "coast_cate": mhw.coast_cate.values[line_idx],
        "seg_len_m": seg_len,
        "x": shapely.get_x(pts), "y": shapely.get_y(pts),
    })
    print(f"{len(mhw):,} MHW lines -> {len(df):,} segments, "
          f"total {df.seg_len_m.sum() / 1000:,.0f} km")
    return mhw, df


def open_coast_flags(mhw, df):
    pad = max(RADII_KM) * 1000 + 2000
    minx, miny, maxx, maxy = mhw.total_bounds
    minx, miny = minx - pad, miny - pad
    maxx, maxy = maxx + pad, maxy + pad
    W, H = int(np.ceil((maxx - minx) / RES)), int(np.ceil((maxy - miny) / RES))
    tf = from_origin(minx, maxy, RES, RES)
    print(f"raster {W} x {H} = {W * H / 1e6:.0f} M cells @ {RES:.0f} m")
    coast = features.rasterize(
        ((g, 1) for g in mhw.geometry.values), out_shape=(H, W),
        transform=tf, fill=0, dtype="uint8", all_touched=True).astype(bool)
    print("  rasterised; EDT ...", flush=True)
    d_coast = ndimage.distance_transform_edt(~coast, sampling=RES)
    col = ((df.x.values - minx) / RES).astype(int)
    row = ((maxy - df.y.values) / RES).astype(int)

    flags = {}
    for R_km in RADII_KM:
        R = R_km * 1000
        eroded = d_coast >= R
        lab, n = ndimage.label(eroded)
        border = np.unique(np.concatenate(
            [lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        border = border[border > 0]
        ocean_core = np.isin(lab, border)
        d_open = ndimage.distance_transform_edt(~ocean_core, sampling=RES)
        open_ocean = d_open <= R
        d_to_open = ndimage.distance_transform_edt(~open_ocean, sampling=RES)
        flags[f"open_R{R_km}km"] = d_to_open[row, col] <= TOL_M
        flags[f"dist_open_R{R_km}km_m"] = d_to_open[row, col]
        print(f"  R={R_km} km: {n} components, ocean core = {len(border)}; "
              f"open segments {flags[f'open_R{R_km}km'].mean() * 100:.1f}%",
              flush=True)
        del lab, eroded, ocean_core, d_open, open_ocean, d_to_open
    return pd.DataFrame(flags, index=df.index)


def island_membership(mhw, df):
    """Mainland (NI / SI / Stewart) vs other islands from coastline
    connectivity: MHW lines within 500 m of each other form one landmass
    (bridges river-mouth gaps; islands < 500 m off the mainland are lumped)."""
    comps = shapely.get_parts(shapely.unary_union(
        shapely.buffer(mhw.geometry.values, 250, quad_segs=2)))
    tree = shapely.STRtree(comps)
    pts = shapely.points(df.x.values, df.y.values)
    idx = tree.nearest(pts)
    length = pd.Series(df.seg_len_m.values).groupby(idx).sum()
    top = length.sort_values(ascending=False)
    cy = {k: comps[k].centroid.y for k in top.index[:3]}
    a, b = top.index[0], top.index[1]
    names = {a: "North Island" if cy[a] > cy[b] else "South Island",
             b: "South Island" if cy[a] > cy[b] else "North Island"}
    # Stewart Island: largest component south of 4,830,000 N
    for k in top.index[2:20]:
        if comps[k].centroid.y < 4_830_000:
            names[k] = "Stewart Island"
            break
    isl = np.array([names.get(k, "Other islands") for k in idx])
    print("island km:", pd.Series(df.seg_len_m.values / 1000).groupby(isl)
          .sum().round(0).to_dict())
    return pd.Series(isl, index=df.index, name="island")


def wave_exposure(df):
    clim = pd.read_parquet(DRIVER_DATA / "whacs_seapoint_climatology.parquet",
                           columns=["lon", "lat", "hs_mean", "hs_p99"])
    sp = gpd.GeoSeries.from_xy(clim.lon, clim.lat, crs=4326).to_crs(2193)
    tree = cKDTree(np.c_[sp.x, sp.y])
    d, i = tree.query(np.c_[df.x, df.y], k=1)
    return pd.DataFrame({"hs_mean": clim.hs_mean.values[i],
                         "hs_p99": clim.hs_p99.values[i],
                         "wave_dist_m": d}, index=df.index)


HS_MIN = 0.75
GEOM_R = 1


def calibrate(df, m):
    """Sensitivity + validation table vs NZCCD EXPOSURE (E/S)."""
    tree = cKDTree(np.c_[m.x2193, m.y2193])
    d, i = tree.query(np.c_[df.x, df.y])
    v = df.assign(EXPOSURE=np.where(d <= 100, m.EXPOSURE.values[i], None))
    v = v[v.EXPOSURE.isin(["E", "S"])]
    rows = []
    for r in RADII_KM:
        for hs_t in (0, 0.5, 0.75, 1.0, 1.25):
            flag = v[f"open_R{r}km"] & (v.hs_mean >= hs_t)
            sens = flag[v.EXPOSURE == "E"].mean()
            spec = 1 - flag[v.EXPOSURE == "S"].mean()
            rows.append(dict(R_km=r, hs_min=hs_t, n_E=(v.EXPOSURE == "E").sum(),
                             n_S=(v.EXPOSURE == "S").sum(),
                             E_open_pct=100 * sens, S_enclosed_pct=100 * spec,
                             balanced_acc=50 * (sens + spec),
                             open_km=df.loc[df[f"open_R{r}km"]
                                            & (df.hs_mean >= hs_t),
                                            "seg_len_m"].sum() / 1000))
    out = pd.DataFrame(rows).round(1)
    out.to_csv(STATS / "opencoast_sensitivity.csv", index=False)
    print(out.sort_values("balanced_acc", ascending=False).head(5)
          .to_string(index=False))
    return out


def coverage_and_region(df):
    base = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet",
                           columns=["UniqueID", "Region", "x2193", "y2193",
                                    "WLR", "EXPOSURE"])
    tree = cKDTree(np.c_[base.x2193, base.y2193])
    d, i = tree.query(np.c_[df.x, df.y], k=1)
    out = pd.DataFrame(index=df.index)
    out["nzccd_dist_m"] = d
    out["nzccd_WLR"] = np.where(d <= 250, base.WLR.values[i], np.nan)
    out["Region"] = np.where(d <= 30_000, base.Region.values[i], "Offshore/other")
    cs = pyogrio.read_dataframe(TRANSECTS_EXTENDED, where="site_id LIKE 'nzd%'",
                                columns=["id"]).to_crs(2193)
    tree_cs = shapely.STRtree(cs.geometry.values)
    pts = shapely.points(df.x.values, df.y.values)
    near = tree_cs.query_nearest(pts, max_distance=250, return_distance=True,
                                 all_matches=False)
    cs_dist = np.full(len(df), np.inf)
    cs_dist[near[0][0]] = near[1]
    out["coastsat_dist_m"] = cs_dist
    return out, base


def summarise(df):
    rows = []
    def add(scope, name, sub):
        rec = {"scope": scope, "name": name,
               "total_km": sub.seg_len_m.sum() / 1000,
               "open_km": sub.loc[sub.open_coast, "seg_len_m"].sum() / 1000}
        rec["open_pct"] = 100 * rec["open_km"] / max(rec["total_km"], 1e-9)
        for r in RADII_KM:
            rec[f"geom_open_km_R{r}"] = sub.loc[sub[f"open_R{r}km"], "seg_len_m"].sum() / 1000
        rec["open_km_R2_hs075"] = sub.loc[sub.open_R2km & (sub.hs_mean >= HS_MIN),
                                          "seg_len_m"].sum() / 1000
        op = sub[sub.open_coast]
        rec["open_nzccd_cov_km"] = op.loc[op.nzccd_dist_m <= 250, "seg_len_m"].sum() / 1000
        rec["open_coastsat_cov_km"] = op.loc[op.coastsat_dist_m <= 250, "seg_len_m"].sum() / 1000
        rec["open_eroding_km"] = op.loc[op.nzccd_WLR < -0.1, "seg_len_m"].sum() / 1000
        rec["open_accreting_km"] = op.loc[op.nzccd_WLR > 0.1, "seg_len_m"].sum() / 1000
        rec["open_stable_km"] = op.loc[op.nzccd_WLR.abs() <= 0.1, "seg_len_m"].sum() / 1000
        rows.append(rec)
    add("all", "New Zealand (LINZ MHW extent)", df)
    for isl, g in df.groupby("island"):
        add("island", isl, g)
    for reg, g in df.groupby("Region"):
        add("region", reg, g)
    for cc, g in df.groupby("coast_cate"):
        add("coast_cate", cc, g)
    return pd.DataFrame(rows).round(1)


def build(reuse_flags=True):
    STATS.mkdir(exist_ok=True)
    mhw, df = coast_segments()
    cache = DRIVER_DATA / "opencoast_points.parquet"
    flag_cols = [f"open_R{r}km" for r in RADII_KM] + \
        [f"dist_open_R{r}km_m" for r in RADII_KM]
    if reuse_flags and cache.exists() and \
            set(flag_cols) <= set(pd.read_parquet(cache).columns):
        old = pd.read_parquet(cache, columns=flag_cols)
        assert len(old) == len(df), "segmentation changed; rerun flags"
        flags = old.set_index(df.index)
        print("reused geometric flags from cache")
    else:
        flags = open_coast_flags(mhw, df)
    df = pd.concat([df, flags], axis=1)
    df["island"] = island_membership(mhw, df)
    df = pd.concat([df, wave_exposure(df)], axis=1)
    cov, base = coverage_and_region(df)
    df = pd.concat([df, cov], axis=1)
    calibrate(df, base)
    df["open_coast"] = df[f"open_R{GEOM_R}km"] & (df.hs_mean >= HS_MIN)
    df.to_parquet(cache, index=False)
    summ = summarise(df)
    summ.to_csv(STATS / "opencoast_lengths.csv", index=False)
    print(summ[summ.scope.isin(["all", "island"])]
          [["name", "total_km", "open_km", "open_pct", "geom_open_km_R1",
            "geom_open_km_R2", "open_nzccd_cov_km", "open_coastsat_cov_km",
            "open_eroding_km", "open_accreting_km", "open_stable_km"]]
          .to_string(index=False))
    return df, summ


if __name__ == "__main__":
    build()
