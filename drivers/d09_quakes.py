"""Driver 09: earthquake exposure metrics at every NZCCD transect.

Source: driver_data/geonet_quakes_M4.csv — GeoNet catalogue, 25,554 events
1901-2026, M 4.0-7.82. Rows whose eventtype is neither 'earthquake' nor
blank/NaN (e.g. 'other', 'outside of network interest', 'not locatable') are
dropped and reported.

Method: metrics are computed once per 2-km alongshore block (mean x2193/y2193
of the block's transects — a <=2 km positional error, negligible against the
50-300 km scales below) and broadcast to all 228,538 transects via block_id.
Distances are planar EPSG:2193 (events beyond the NZTM domain keep
approximately correct distances at these scales).

Per-block metrics:
  n_M4_50km     events (all kept, M>=4) within 50 km
  n_M5_50km     M>=5.0 events within 50 km
  n_M6_100km    M>=6.0 events within 100 km
  dist_M65_km   distance to the nearest M>=6.5 event
  shaking_idx   log10( sum over ALL events of
                       10^(1.5*M) / (d_km^2 + depth_km^2 + 100) )
                — an energy-weighted proximity index; the +100 regularizes
                the near-field.
  coseismic_flag  within 50 km of any M>=7.0 event with depth<=40 km and
                  year>=1938 (the NZCCD record period). NOTE: the 1931
                  Hawke's Bay (Napier) M7.4 IS in the catalogue but predates
                  1938, and Edgecumbe 1987 is M6.5 (below M7.0), so neither
                  raises the flag; see the printed report.

Run:  python3 -m drivers.d09_quakes
Out:  driver_data/d09_quakes.parquet (228,538 rows, one per UniqueID)
QA:   driver_data/qa/d09_shaking_map.png, d09_quakes_region_means.csv
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .common import DRIVER_DATA, QA_DIR, load_base, write_driver

QUAKES_CSV = DRIVER_DATA / "geonet_quakes_M4.csv"
RECORD_START_YEAR = 1938   # NZCCD record period for the coseismic flag
COSEISMIC_MAG = 7.0
COSEISMIC_MAX_DEPTH_KM = 40.0
COSEISMIC_RADIUS_M = 50_000.0
BLOCK_CHUNK = 512

# Single-hue sequential blue ramp (light -> dark), steps 100..700.
SEQ_BLUES = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
             "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281",
             "#0d366b"]
CRITICAL_RED = "#d03b3b"


def load_quakes():
    """Kept GeoNet events with year and EPSG:2193 coordinates."""
    df = pd.read_csv(QUAKES_CSV, usecols=["publicid", "eventtype", "origintime",
                                          "longitude", "latitude", "magnitude",
                                          "depth"])
    n_raw = len(df)
    keep = df["eventtype"].isna() | (df["eventtype"] == "earthquake")
    dropped = df.loc[~keep, "eventtype"].value_counts()
    print(f"catalogue: {n_raw} rows; kept {int(keep.sum())} "
          f"('earthquake' or blank eventtype), dropped {int((~keep).sum())}:")
    print(dropped.to_string())
    df = df[keep].copy()

    df["year"] = pd.to_datetime(df["origintime"], utc=True,
                                format="ISO8601").dt.year
    assert df[["longitude", "latitude", "magnitude", "depth", "year"]] \
        .notna().all().all(), "unexpected NaNs in kept events"
    assert (df["magnitude"] >= 4.0).all()

    pts = gpd.GeoSeries(gpd.points_from_xy(df.longitude, df.latitude),
                        crs=4326).to_crs(2193)
    df["x2193"], df["y2193"] = pts.x.values, pts.y.values
    print(f"events: {len(df)} kept, years {df.year.min()}-{df.year.max()}, "
          f"M {df.magnitude.min():.2f}-{df.magnitude.max():.2f}")
    return df.reset_index(drop=True)


def report_catalogue_notes(ev):
    """Print the known edge cases the coseismic filter is sensitive to."""
    napier = ev[(ev.year == 1931) & (ev.magnitude >= 7.0)]
    if len(napier):
        rows = napier[["origintime", "longitude", "latitude", "magnitude",
                       "depth"]].to_string(index=False)
        print("note: 1931 Hawke's Bay (Napier) M>=7 IS in the catalogue but "
              f"predates year>={RECORD_START_YEAR}, so it does NOT raise "
              f"coseismic_flag:\n{rows}")
    else:
        print("note: no 1931 M>=7 (Napier) event found in the catalogue.")
    edge = ev[(ev.year == 1987) & (ev.magnitude >= 6.0) &
              ev.longitude.between(176.3, 177.3) & ev.latitude.between(-38.3, -37.7)]
    if len(edge):
        m = edge.magnitude.max()
        print(f"note: Edgecumbe 1987 present at M{m:.2f} — below the "
              f"M>={COSEISMIC_MAG} coseismic threshold, so it does not raise "
              "coseismic_flag (it does contribute to n_M6_100km/shaking_idx).")
    else:
        print("note: Edgecumbe 1987 not found in the catalogue.")


def block_metrics(blocks, ev):
    """All per-block metrics; `blocks` has block_id/x2193/y2193."""
    bxy = np.c_[blocks.x2193.values, blocks.y2193.values]
    exy = np.c_[ev.x2193.values, ev.y2193.values]

    def count_within(sub, radius_m):
        tree = cKDTree(np.c_[sub.x2193.values, sub.y2193.values])
        return tree.query_ball_point(bxy, r=radius_m, return_length=True,
                                     workers=-1).astype("int32")

    blocks = blocks.copy()
    blocks["n_M4_50km"] = count_within(ev, 50_000.0)
    blocks["n_M5_50km"] = count_within(ev[ev.magnitude >= 5.0], 50_000.0)
    blocks["n_M6_100km"] = count_within(ev[ev.magnitude >= 6.0], 100_000.0)

    m65 = ev[ev.magnitude >= 6.5]
    print(f"M>=6.5 events: {len(m65)}; M>=5 events: "
          f"{int((ev.magnitude >= 5).sum())}; M>=6: "
          f"{int((ev.magnitude >= 6).sum())}")
    dist, _ = cKDTree(np.c_[m65.x2193.values, m65.y2193.values]).query(bxy, k=1)
    blocks["dist_M65_km"] = dist / 1000.0

    # shaking_idx: energy-weighted sum over ALL events, chunked over blocks.
    w = 10.0 ** (1.5 * ev.magnitude.values)
    depth2 = ev.depth.values ** 2
    acc = np.empty(len(blocks))
    for i in range(0, len(blocks), BLOCK_CHUNK):
        dx = (bxy[i:i + BLOCK_CHUNK, 0:1] - exy[None, :, 0].reshape(1, -1)) / 1000.0
        dy = (bxy[i:i + BLOCK_CHUNK, 1:2] - exy[None, :, 1].reshape(1, -1)) / 1000.0
        acc[i:i + BLOCK_CHUNK] = (w / (dx * dx + dy * dy + depth2 + 100.0)).sum(axis=1)
    blocks["shaking_idx"] = np.log10(acc)

    cos = ev[(ev.magnitude >= COSEISMIC_MAG) &
             (ev.depth <= COSEISMIC_MAX_DEPTH_KM) &
             (ev.year >= RECORD_START_YEAR)]
    print(f"coseismic events (M>={COSEISMIC_MAG}, depth<="
          f"{COSEISMIC_MAX_DEPTH_KM:.0f} km, year>={RECORD_START_YEAR}): "
          f"{len(cos)}")
    print(cos[["origintime", "longitude", "latitude", "magnitude",
               "depth"]].to_string(index=False))
    cdist, _ = cKDTree(np.c_[cos.x2193.values, cos.y2193.values]).query(bxy, k=1)
    blocks["coseismic_flag"] = cdist <= COSEISMIC_RADIUS_M

    # Which coseismic events actually reach the coast (blocks within 50 km)?
    ctree = cKDTree(bxy)
    hits = ctree.query_ball_point(np.c_[cos.x2193.values, cos.y2193.values],
                                  r=COSEISMIC_RADIUS_M, return_length=True)
    rep = cos[["origintime", "magnitude"]].copy()
    rep["blocks_within_50km"] = hits
    print("coseismic events -> coastal blocks within 50 km:")
    print(rep.to_string(index=False))
    return blocks, cos


def qa_map(base, cos):
    """National scatter coloured by shaking_idx + coseismic epicentres."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUES)
    fig, ax = plt.subplots(figsize=(7.5, 9), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    order = np.argsort(base["shaking_idx"].values)  # darkest drawn last
    sc = ax.scatter(base["x2193"].values[order], base["y2193"].values[order],
                    c=base["shaking_idx"].values[order], cmap=cmap, s=1.2,
                    linewidths=0, rasterized=True)
    ax.scatter(cos.x2193, cos.y2193, s=55, marker="o", facecolors="none",
               edgecolors=CRITICAL_RED, linewidths=1.6,
               label="M$\\geq$7.0 shallow ($\\leq$40 km) epicentre, 1938+")
    ax.set_aspect("equal")
    ax.set_xlabel("NZTM easting (m)", color="#52514e")
    ax.set_ylabel("NZTM northing (m)", color="#52514e")
    ax.tick_params(colors="#52514e", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#c9c8c2")
    ax.set_title("d09 earthquakes: shaking_idx at NZCCD transects",
                 color="#0b0b0b")
    cb = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("shaking_idx  (log10 energy-weighted proximity)",
                 color="#52514e")
    cb.ax.tick_params(colors="#52514e", labelsize=8)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(QA_DIR / "d09_shaking_map.png", dpi=150)
    plt.close(fig)
    print(f"wrote {QA_DIR / 'd09_shaking_map.png'}")


def build():
    ev = load_quakes()
    report_catalogue_notes(ev)

    base = load_base(columns=["UniqueID", "Region", "block_id",
                              "x2193", "y2193"])
    blocks = base.groupby("block_id", as_index=False)[["x2193", "y2193"]].mean()
    print(f"blocks: {len(blocks)} centroids from {len(base)} transects")

    blocks, cos = block_metrics(blocks, ev)

    metric_cols = ["n_M4_50km", "n_M5_50km", "n_M6_100km", "dist_M65_km",
                   "shaking_idx", "coseismic_flag"]
    out = base.merge(blocks[["block_id"] + metric_cols], on="block_id",
                     how="left", validate="many_to_one")
    assert len(out) == len(base) == 228538
    assert out[metric_cols].notna().all().all(), "broadcast left NaNs"

    region = (out.groupby("Region")
              .agg(n=("UniqueID", "size"),
                   shaking_idx_mean=("shaking_idx", "mean"),
                   n_M4_50km_mean=("n_M4_50km", "mean"),
                   n_M6_100km_mean=("n_M6_100km", "mean"),
                   dist_M65_km_median=("dist_M65_km", "median"),
                   coseismic_pct=("coseismic_flag", "mean"))
              .assign(coseismic_pct=lambda d: d.coseismic_pct * 100)
              .round(3).sort_values("shaking_idx_mean", ascending=False))
    region.to_csv(QA_DIR / "d09_quakes_region_means.csv")
    print("mean shaking_idx by region (descending):")
    print(region.to_string())

    top3 = set(region.index[:3])
    lows = set(region.index[-4:])
    print(f"sanity: top-3 shaking regions {sorted(top3)}; "
          f"lowest-4 {sorted(lows)}")
    print("coseismic_flag by region (transect counts):")
    print(out[out.coseismic_flag].groupby("Region").size()
          .sort_values(ascending=False).to_string())

    qa_map(out, cos)
    return write_driver(out[["UniqueID"] + metric_cols], "d09_quakes")


if __name__ == "__main__":
    build()
