"""Driver 04: LiDAR elevation along each transect's landward side.

Samples the 92 GB national 1 m coastal DEM at 81 evenly spaced positions per
transect (~5 m spacing on 400 m transects). Because transect vertex order is
not uniform nationally (see qa/CONVENTIONS.md), the landward side is chosen
per transect: the side of the latest-shoreline position with the higher
valid-DEM fraction (ties: higher mean elevation). Ocean is NoData in the
coastal-strip DEM, so validity is a reliable land indicator.

Run:  python3 -m drivers.elevation
Out:  driver_data/d04_elevation.parquet
"""

import numpy as np
import pandas as pd
import rasterio
import shapely
from tqdm.contrib.concurrent import process_map

from .common import COASTAL_DEM, DRIVER_DATA, RATES_PARQUET, cast_unique_id
from .base_build import load_transect_lines

N_SAMP = 81           # per transect; ~5 m spacing on 400 m transects
NEAR_M = 200.0        # backshore window landward of the latest shoreline
CHUNK = 2000

_src = None           # per-worker raster handle (not fork-safe to share)


def _prep():
    """(UniqueID, transect wkb, latest-shoreline distance-from-last-vertex)."""
    rates = pd.read_parquet(RATES_PARQUET, columns=["UniqueID", "Distances"])
    rates["UniqueID"] = cast_unique_id(rates["UniqueID"])
    rates["d_last"] = rates.Distances.map(lambda d: d[-1])
    lines = load_transect_lines()
    df = rates[["UniqueID", "d_last"]].join(lines, on="UniqueID", how="inner")
    df["wkb"] = shapely.to_wkb(df.geometry.values)
    # sort along-coast for raster block locality
    df["island"] = df.UniqueID // 10**9
    df["chain"] = df.UniqueID % 10**9
    df = df.sort_values(["island", "chain"])
    return df[["UniqueID", "d_last", "wkb"]].reset_index(drop=True)


def _process_chunk(chunk_df):
    global _src
    if _src is None:
        _src = rasterio.open(COASTAL_DEM)
    nodata = _src.nodata
    coords, meta = [], []
    for uid, d_last, wkb in chunk_df.itertuples(index=False):
        line = shapely.from_wkb(wkb)
        length = line.length
        ts = np.linspace(0, length, N_SAMP)
        pts = [line.interpolate(t) for t in ts]
        coords.extend((p.x, p.y) for p in pts)
        # latest shoreline: Distance measured from the LAST vertex
        shore_t = np.clip(length - d_last, 0, length)
        meta.append((uid, length, shore_t))
    vals = np.array([v[0] for v in _src.sample(coords, masked=False)],
                    dtype=np.float64).reshape(len(meta), N_SAMP)
    vals[(vals == nodata) | (vals < -50) | (vals > 3000)] = np.nan

    out = []
    for i, (uid, length, shore_t) in enumerate(meta):
        ts = np.linspace(0, length, N_SAMP)
        v = vals[i]
        near = np.abs(ts - shore_t) <= NEAR_M
        # side of the shoreline position toward the FIRST vertex vs the LAST
        side_first = near & (ts < shore_t)
        side_last = near & (ts > shore_t)

        def score(mask):
            vv = v[mask]
            frac = np.isfinite(vv).mean() if len(vv) else 0.0
            mean = np.nanmean(vv) if np.isfinite(vv).any() else -np.inf
            return frac, mean

        f_first, m_first = score(side_first)
        f_last, m_last = score(side_last)
        if (f_first, m_first) >= (f_last, m_last):
            land, land_side = side_first, "first"
        else:
            land, land_side = side_last, "last"
        lv = v[land]
        lts = ts[land]
        finite = np.isfinite(lv)
        rec = {"UniqueID": uid, "landward_side": land_side,
               "transect_len": length,
               "elev_frac_valid": float(finite.mean()) if len(lv) else 0.0,
               "elev_shore": v[np.abs(ts - shore_t).argmin()]}
        if finite.sum() >= 0.6 * max(len(lv), 1) and finite.sum() >= 5:
            rec["backshore_mean"] = float(np.nanmean(lv))
            rec["backshore_max"] = float(np.nanmax(lv))
            rec["backshore_min"] = float(np.nanmin(lv))
            # slope over the 100 m nearest the shoreline
            near100 = finite & (np.abs(lts - shore_t) <= 100)
            if near100.sum() >= 4:
                dist_from_shore = np.abs(lts[near100] - shore_t)
                rec["hinterland_slope"] = float(np.polyfit(
                    dist_from_shore, lv[near100], 1)[0])
        out.append(rec)
    return pd.DataFrame(out)


def build(max_workers=10):
    df = _prep()
    chunks = [df.iloc[i:i + CHUNK] for i in range(0, len(df), CHUNK)]
    print(f"{len(df):,} transects in {len(chunks)} chunks")
    parts = process_map(_process_chunk, chunks,
                        max_workers=max_workers, chunksize=1)
    result = pd.concat(parts, ignore_index=True)
    out = DRIVER_DATA / "d04_elevation.parquet"
    result.to_parquet(out, index=False)
    print(f"wrote {out} rows={len(result):,}")
    print(result[["elev_frac_valid", "backshore_mean", "backshore_max",
                  "hinterland_slope"]].describe())
    print("landward_side:", result.landward_side.value_counts().to_dict())
    return result


if __name__ == "__main__":
    build()
