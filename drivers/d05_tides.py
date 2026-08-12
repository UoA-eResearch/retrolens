"""Driver 05: tidal range at each NZCCD transect from FES2022b constituents.

Loads M2/S2/K1/O1 amplitude grids (global 1/30 deg, amplitude in cm,
lon 0-360), subsets to the NZ window BEFORE building any tree, and joins
each base transect to the nearest wet (finite-amplitude) cell with a
haversine BallTree.

Outputs (driver_data/d05_tides.parquet, one row per base transect):
  spring_range_m  = 2 * (amp_M2 + amp_S2) / 100     mean spring tidal range
  m2_amp_m        = amp_M2 / 100
  form_factor     = (amp_K1 + amp_O1) / (amp_M2 + amp_S2)
  tide_dist_km    join distance to nearest wet FES cell
  tide_quality    'ok' (<= 15 km) or 'far' (fjord/harbour interiors where
                  the FES open-ocean solution is unreliable)

Run:  python3 -m drivers.d05_tides
"""

from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

from .common import (CSV_RUN7, FES2022_DIR, QA_DIR, haversine_join, load_base,
                     qa_join, write_driver)

NAME = "d05_tides"
CONSTITUENTS = ("m2", "s2", "k1", "o1")
# NZ window (FES lon is 0..360; NZ sits entirely in 165..180 E for this base)
LAT_MIN, LAT_MAX = -48.5, -33.5
LON_MIN, LON_MAX = 165.0, 180.0
FAR_KM = 15.0


def load_constituent(name):
    """Return (lat_sub, lon_sub, amp_cm) for one constituent, NZ window only."""
    path = Path(FES2022_DIR) / f"{name}_fes2022.nc"
    with netCDF4.Dataset(path) as ds:
        lat = ds.variables["lat"][:].filled(np.nan)
        lon = ds.variables["lon"][:].filled(np.nan)
        i0, i1 = np.searchsorted(lat, [LAT_MIN, LAT_MAX])
        j0, j1 = np.searchsorted(lon, [LON_MIN, LON_MAX])
        amp = ds.variables["amplitude"][i0:i1, j0:j1]
    return lat[i0:i1], lon[j0:j1], np.ma.filled(amp.astype("float64"), np.nan)


def load_wet_cells():
    """Amplitudes (cm) of every cell wet in all four constituents.

    Returns dict with lat, lon (1-D arrays over wet cells) and one amplitude
    array per constituent.
    """
    amps, lat, lon = {}, None, None
    for c in CONSTITUENTS:
        clat, clon, amp = load_constituent(c)
        if lat is None:
            lat, lon = clat, clon
        else:
            assert np.array_equal(lat, clat) and np.array_equal(lon, clon), \
                f"{c}: grid mismatch"
        amps[c] = amp
    wet = np.logical_and.reduce([np.isfinite(a) for a in amps.values()])
    long, latg = np.meshgrid(lon, lat)
    out = {"lat": latg[wet], "lon": long[wet]}
    out.update({c: amps[c][wet] for c in CONSTITUENTS})
    print(f"FES NZ window: {wet.shape[0]}x{wet.shape[1]} cells, "
          f"{wet.sum()} wet ({wet.mean() * 100:.1f}%)")
    return out


def qa_map(df, base):
    """Map-style scatter of spring_range_m over x2193/y2193."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # single-hue sequential (light -> dark blue), truncated so the low end
    # stays visible on a white surface
    cmap = LinearSegmentedColormap.from_list(
        "blues_trunc", plt.get_cmap("Blues")(np.linspace(0.25, 1.0, 256)))
    fig, ax = plt.subplots(figsize=(7, 8.5))
    sc = ax.scatter(base["x2193"], base["y2193"], c=df["spring_range_m"],
                    s=1.5, cmap=cmap, linewidths=0, rasterized=True)
    cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("spring range 2(M2+S2) (m)")
    ax.set_aspect("equal")
    ax.set_xlabel("x (NZTM2000, m)")
    ax.set_ylabel("y (NZTM2000, m)")
    ax.set_title(
        f"{NAME}: FES2022b spring tidal range\n"
        f"min {df.spring_range_m.min():.2f}  median "
        f"{df.spring_range_m.median():.2f}  max {df.spring_range_m.max():.2f} m")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(QA_DIR / f"{NAME}_spring_range_map.png", dpi=130)
    plt.close(fig)


def coastsat_crosscheck(df, base, n_sites=10):
    """Compare spring_range_m against observed FES tide-level records at
    CoastSat nzd sites: max-min of the record should be comparable to
    (slightly larger than) the mean spring range at the nearest transect."""
    run7 = Path(CSV_RUN7)
    sites = sorted(p.parent.name for p in run7.glob("nzd*/tide_levels_fes2022.csv"))
    picks = [sites[i] for i in
             np.linspace(0, len(sites) - 1, n_sites).round().astype(int)]

    joined = base[["UniqueID", "lat", "lon"]].merge(df, on="UniqueID")
    rows = []
    for site in picks:
        tides = pd.read_csv(run7 / site / "tide_levels_fes2022.csv")
        coords = pd.read_csv(
            run7 / site / "transect_coordinates_and_beach_slopes.csv")
        site_lat = coords["Latitude - Origin"].mean()
        site_lon = coords["Longitude - Origin"].mean()
        d_km, idx = haversine_join(
            np.c_[[site_lat], [site_lon % 360]],
            np.c_[joined["lat"].values, joined["lon"].values % 360])
        t = joined.iloc[idx[0]]
        obs = tides["tide levels"].max() - tides["tide levels"].min()
        rows.append({
            "site": site, "site_lat": site_lat, "site_lon": site_lon,
            "nearest_UniqueID": t["UniqueID"], "transect_dist_km": d_km[0],
            "obs_range_m": obs, "spring_range_m": t["spring_range_m"],
            "obs_over_spring": obs / t["spring_range_m"],
            "n_tide_obs": len(tides),
        })
    table = pd.DataFrame(rows)
    table.to_csv(QA_DIR / f"{NAME}_coastsat_check.csv", index=False)
    print("\nCoastSat cross-check (observed record range vs FES spring range):")
    print(table[["site", "transect_dist_km", "obs_range_m", "spring_range_m",
                 "obs_over_spring"]].to_string(index=False,
                                               float_format="%.2f"))
    return table


def sanity_check(df, base):
    """West-coast North Island spring range must clearly exceed east-coast."""
    j = base[["UniqueID", "Region"]].merge(df, on="UniqueID")
    means = j.groupby("Region")["spring_range_m"].mean().sort_values()
    means.to_csv(QA_DIR / f"{NAME}_region_spring_range.csv")
    print("\nmean spring range by region (m):")
    print(means.to_string(float_format="%.2f"))
    west = j.loc[j.Region == "Taranaki", "spring_range_m"].mean()
    east = j.loc[j.Region.isin(["Hawkes Bay", "Gisborne"]),
                 "spring_range_m"].mean()
    msg = (f"west-coast NI (Taranaki) {west:.2f} m vs "
           f"east-coast NI (Hawkes Bay+Gisborne) {east:.2f} m")
    print(f"sanity: {msg}")
    assert west > east + 1.0, f"sanity FAILED: {msg}"
    return msg


def build():
    wet = load_wet_cells()
    base = load_base(["UniqueID", "Region", "lat", "lon", "x2193", "y2193"])

    dist_km, idx = haversine_join(
        np.c_[base["lat"].values, base["lon"].values % 360],
        np.c_[wet["lat"], wet["lon"]])

    m2, s2 = wet["m2"][idx], wet["s2"][idx]
    k1, o1 = wet["k1"][idx], wet["o1"][idx]
    df = pd.DataFrame({
        "UniqueID": base["UniqueID"].values,
        "spring_range_m": 2.0 * (m2 + s2) / 100.0,
        "m2_amp_m": m2 / 100.0,
        "form_factor": (k1 + o1) / (m2 + s2),
        "tide_dist_km": dist_km,
    })
    df["tide_quality"] = np.where(df["tide_dist_km"] <= FAR_KM, "ok", "far")

    qa_join(dist_km * 1000.0, NAME, FAR_KM * 1000.0)
    qa_map(df, base)
    coastsat_crosscheck(df, base)
    sanity = sanity_check(df, base)
    write_driver(df, NAME)
    print(df.drop(columns="UniqueID").describe().to_string(float_format="%.3f"))
    print(df["tide_quality"].value_counts().to_string())
    return df, sanity


if __name__ == "__main__":
    build()
