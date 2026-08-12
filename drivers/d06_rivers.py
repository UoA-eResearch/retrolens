"""Driver 06: river mouths + precipitation from REC2 v5.

Terminal network segments (NextDownID == -1 sentinel; verified equal to the
"NextDownID not in HydroID" set) located within 1,500 m of the LINZ MHW
coastline are treated as coastal river mouths.

Discharge proxy: Q_m3s = us_ro * us_catarea / 1e9, i.e. `us_ro` is upstream
mean specific runoff in L/s/km2 and `us_catarea` is upstream catchment area in
m2. Verified empirically against gauged mean flows: Waikato (us_catarea
1.447e10 m2 = 14,473 km2, Q 381 m3/s, gauged ~340-400), Waitaki (337, gauged
~360), Buller (348, gauged ~430), Grey (297, gauged ~350), Waiau-Southland
(439, natural ~430-500).  The alternative reading of us_ro as mm/yr gives a
max national Q of 14 m3/s, which is physically absurd.

REC2 v5 appends 21 pseudo-outlet segments (Clutha among them) whose
downcoordX/Y are 0 and whose rain/runoff attributes are null; their mouth
coordinates are recovered from the line geometry (endpoint nearer the
coastline) and their Q / us_rain / us_catarea by walking upstream to the first
attribute-valid segments and summing across those cut points.  This restores
the Clutha at Q ~ 502 m3/s, the largest river in the country.

Run:  python3 -m drivers.d06_rivers
Out:  driver_data/d06_rivers.parquet  (228,538 rows, one per UniqueID)
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from scipy.spatial import cKDTree

from .common import QA_DIR, REC2_GDB, base_gdf, qa_join, write_driver

COASTLINE_SHP = "/mnt/Bruunrule_Yaxiong/input/coastline/nz-coastline-mean-high-water.shp"
COAST_MAX_M = 1500.0        # terminal segment -> coastline distance cut
BIG_Q_M3S = 10.0            # "big mouth" threshold
SUPPLY_RADIUS_KM = 150.0    # supply index truncation
SUPPLY_SCALES_KM = {"river_supply_idx_L10": 10.0,
                    "river_supply_idx": 20.0,
                    "river_supply_idx_L50": 50.0}
# nzsegment -> name, for the QA top-Q table only (identified during unit checks)
KNOWN_MOUTHS = {14330003: "Clutha", 15308908: "Waiau (Southland)",
                3050201: "Waikato", 12035600: "Buller", 13212900: "Waitaki",
                12073872: "Grey"}


def _load_rec2():
    rl = pyogrio.read_dataframe(
        REC2_GDB, layer="riverlines", read_geometry=False,
        columns=["nzsegment", "HydroID", "NextDownID", "CUM_AREA",
                 "StreamOrde", "downcoordX", "downcoordY"])
    rr = pyogrio.read_dataframe(
        REC2_GDB, layer="rec2_rain_runoff_V5", read_geometry=False,
        columns=["nzsegment", "seg_rain", "us_rain", "us_ro", "us_catarea"])
    return rl.merge(rr, on="nzsegment", how="left")


def _patch_degenerate_coords(term, coast):
    """Recover mouth xy for terminals whose downcoordX/Y are 0/NaN.

    Both line endpoints are candidates; keep the one nearer the coastline.
    """
    bad = term[(term.mouth_x == 0) | (term.mouth_y == 0)
               | term.mouth_x.isna() | term.mouth_y.isna()]
    if not len(bad):
        return term
    ids = ", ".join(str(int(s)) for s in bad.nzsegment)
    geoms = pyogrio.read_dataframe(
        REC2_GDB, layer="riverlines", columns=["nzsegment"],
        where=f"nzsegment IN ({ids})")
    cands = []
    for seg, geom in zip(geoms.nzsegment, geoms.geometry):
        parts = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
        for xy in (parts[0].coords[0], parts[-1].coords[-1]):
            cands.append((seg, xy[0], xy[1]))
    cand = gpd.GeoDataFrame(
        pd.DataFrame(cands, columns=["nzsegment", "x", "y"]),
        geometry=gpd.points_from_xy([c[1] for c in cands],
                                    [c[2] for c in cands]), crs=2193)
    near = gpd.sjoin_nearest(cand, coast[["geometry"]], how="left",
                             distance_col="d")
    near = near[~near.index.duplicated()]
    pick = near.sort_values("d").drop_duplicates("nzsegment")
    lut = pick.set_index("nzsegment")[["x", "y"]]
    fix = term.nzsegment.map(lut.x)
    term.loc[bad.index, "mouth_x"] = fix[bad.index]
    term.loc[bad.index, "mouth_y"] = term.nzsegment.map(lut.y)[bad.index]
    print(f"patched mouth coords for {len(bad)} degenerate terminals "
          f"(incl. Clutha nzsegment 14330003)")
    return term


def _fill_null_terminals(term, net):
    """BFS upstream from attribute-null terminals to the first valid segments;
    sum Q and area, area-weight us_rain, across those cut points."""
    children = {}
    for h, nd in zip(net.HydroID.values, net.NextDownID.values):
        children.setdefault(nd, []).append(h)
    byhyd = net.set_index("HydroID")
    null_rows = term[term.Q_m3s.isna()]
    for i, row in null_rows.iterrows():
        q = area = rain_w = 0.0
        stack = [row.HydroID]
        while stack:
            for c in children.get(stack.pop(), []):
                r = byhyd.loc[c]
                if pd.notna(r.us_ro) and pd.notna(r.us_catarea):
                    q += r.us_ro * r.us_catarea / 1e9
                    area += r.us_catarea
                    rain_w += (r.us_rain if pd.notna(r.us_rain) else 0.0) * r.us_catarea
                else:
                    stack.append(c)
        if area > 0:
            term.loc[i, ["Q_m3s", "us_catarea", "us_rain"]] = (
                q, area, rain_w / area)
    n_fixed = term.loc[null_rows.index, "Q_m3s"].notna().sum()
    print(f"filled Q/us_rain via upstream BFS for {n_fixed}/{len(null_rows)} "
          f"attribute-null terminals")
    return term


def build():
    net = _load_rec2()
    print(f"riverlines: {len(net)} segments")
    print("NextDownID value_counts head:\n",
          net.NextDownID.value_counts().head(3).to_string())
    term = net[~net.NextDownID.isin(set(net.HydroID.values))].copy()
    assert (term.NextDownID == -1).all(), "unexpected terminal sentinel"
    print(f"terminal segments (sentinel -1): {len(term)}")

    coast = gpd.read_file(COASTLINE_SHP)[["geometry"]]
    assert coast.crs.to_epsg() == 2193, f"coastline CRS {coast.crs}"

    term["mouth_x"] = term.downcoordX
    term["mouth_y"] = term.downcoordY
    term["Q_m3s"] = term.us_ro * term.us_catarea / 1e9   # L/s/km2 * m2 -> m3/s
    term = _patch_degenerate_coords(term, coast)
    term = _fill_null_terminals(term, net)

    pts = gpd.GeoDataFrame(
        term, geometry=gpd.points_from_xy(term.mouth_x, term.mouth_y), crs=2193)
    near = gpd.sjoin_nearest(pts, coast, how="left", distance_col="coast_dist_m")
    near = near[~near.index.duplicated()]
    mouths = near[near.coast_dist_m <= COAST_MAX_M].copy()
    big = mouths[mouths.Q_m3s > BIG_Q_M3S]
    print(f"coastal mouths (<= {COAST_MAX_M:.0f} m of MHW): {len(mouths)}; "
          f"big mouths Q > {BIG_Q_M3S} m3/s: {len(big)}; "
          f"null-Q coastal mouths: {mouths.Q_m3s.isna().sum()}")

    top5 = mouths.nlargest(5, "Q_m3s")[
        ["nzsegment", "mouth_x", "mouth_y", "us_catarea", "us_rain", "Q_m3s"]]
    top5["name"] = top5.nzsegment.map(KNOWN_MOUTHS).fillna("")
    top5["us_catarea_km2"] = top5.us_catarea / 1e6
    top5 = top5.drop(columns="us_catarea")
    top5.to_csv(QA_DIR / "d06_rivers_top5_Q.csv", index=False)
    print("top-5 Q mouths:\n", top5.to_string(index=False))
    pd.DataFrame([{
        "n_terminal": len(term), "n_coastal_mouths": len(mouths),
        "n_big_mouths": len(big),
        "n_nullQ_coastal": int(mouths.Q_m3s.isna().sum()),
        "coast_max_m": COAST_MAX_M, "big_q_m3s": BIG_Q_M3S,
    }]).to_csv(QA_DIR / "d06_rivers_mouth_counts.csv", index=False)

    base = base_gdf(columns=["UniqueID", "Region", "x2193", "y2193"])
    bxy = np.c_[base.x2193.values, base.y2193.values]
    out = pd.DataFrame({"UniqueID": base.UniqueID.values})

    mxy = np.c_[mouths.mouth_x.values, mouths.mouth_y.values]
    d, i = cKDTree(mxy).query(bxy, k=1)
    out["dist_mouth_km"] = d / 1000.0
    out["nearest_mouth_Q_m3s"] = mouths.Q_m3s.values[i]
    d_big, _ = cKDTree(np.c_[big.mouth_x.values, big.mouth_y.values]).query(bxy, k=1)
    out["dist_bigmouth_km"] = d_big / 1000.0

    # supply index: sum_j Q_j * exp(-d_ij / L) for mouths within 150 km
    q = np.nan_to_num(mouths.Q_m3s.values, nan=0.0)
    sums = {k: np.zeros(len(base)) for k in SUPPLY_SCALES_KM}
    for lo in range(0, len(base), 8192):
        hi = min(lo + 8192, len(base))
        dk = np.sqrt(((bxy[lo:hi, None, :] - mxy[None, :, :]) ** 2)
                     .sum(-1)) / 1000.0
        w = dk <= SUPPLY_RADIUS_KM
        for col, L in SUPPLY_SCALES_KM.items():
            sums[col][lo:hi] = (q * np.exp(-dk / L) * w).sum(1)
    for col in SUPPLY_SCALES_KM:
        out[col] = sums[col]

    # precipitation at the coast: nearest river segment (any), downcoord points
    util = pyogrio.read_dataframe(
        REC2_GDB, layer="rec2_utility_variables_V5", read_geometry=False,
        columns=["nzsegment", "loc_rd25"])
    seg = net[(net.downcoordX > 0) & (net.downcoordY > 0)
              & net.seg_rain.notna()].merge(util, on="nzsegment", how="left")
    d_seg, j = cKDTree(np.c_[seg.downcoordX.values,
                             seg.downcoordY.values]).query(bxy, k=1)
    out["rain_mm_yr"] = seg.seg_rain.values[j]
    out["rainstorm_days"] = seg.loc_rd25.values[j]
    out["rain_seg_dist_m"] = d_seg
    out["catchment_rain_mm_yr"] = mouths.us_rain.values[i]
    qa_join(d_seg, "d06_rivers_rain_seg", 10_000)

    by_region = (out.assign(Region=base.Region.values)
                 .groupby("Region")["rain_mm_yr"].mean().sort_values(
                     ascending=False))
    by_region.to_csv(QA_DIR / "d06_rivers_rain_by_region.csv")
    print("mean rain_mm_yr by Region:\n", by_region.to_string())
    wc, east = by_region["West Coast"], by_region[["Canterbury", "Otago"]].mean()
    print(f"sanity: West Coast {wc:.0f} mm vs Canterbury/Otago {east:.0f} mm "
          f"-> ratio {wc / east:.1f}x")
    assert wc > 2 * east, "West Coast rain not >> east coast"

    cols = ["UniqueID", "dist_mouth_km", "dist_bigmouth_km",
            "river_supply_idx", "river_supply_idx_L10", "river_supply_idx_L50",
            "nearest_mouth_Q_m3s", "rain_mm_yr", "rainstorm_days",
            "catchment_rain_mm_yr", "rain_seg_dist_m"]
    write_driver(out[cols], "d06_rivers")
    return out


if __name__ == "__main__":
    build()
