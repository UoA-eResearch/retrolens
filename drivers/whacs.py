"""Stream the WHACS hourly hindcast (1979-2023) into per-seapoint climatology.

No open_mfdataset: the grid is unstructured (17,422 seapoints) and 45 years of
hourly files are read once with fixed-size numpy accumulators. Epochs 1979-89
and 1990-2023 are accumulated separately (a calendar year is entirely in one
epoch) and the full period is their merge.

Run:  python3 -m drivers.whacs
Out:  driver_data/whacs_seapoint_climatology.parquet  (17,422 rows)
"""

from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from tqdm.contrib.concurrent import process_map

from .common import DRIVER_DATA, WHACS_DIR

VARS = ("hs", "dir", "cge", "t01")
N_SEA = 17422
HS_BINS = 1000          # 0..25 m at 2.5 cm
HS_BIN_W = 25.0 / HS_BINS
STORM_HS = 4.0
EPOCH_SPLIT = 1990      # years < split -> "7989", >= split -> "9023"
YEARS = range(1979, 2024)


def _files(var, year):
    return sorted(glob(
        f"{WHACS_DIR}/{var}_NZ/{var}_WHACS_hindcast_WHACS_ERA5_1hr_{year}*.nc"))


def _empty_acc():
    z = lambda: np.zeros(N_SEA)
    return {
        "hs_sum": z(), "hs_sumsq": z(), "hs_max": z(), "hs_n": z(),
        "hs_hist": np.zeros((N_SEA, HS_BINS), dtype=np.int64),
        "storm_hrs": z(),
        "dir_sin": z(), "dir_cos": z(), "dir_n": z(),
        "dir_esin": z(), "dir_ecos": z(), "dir_e_n": z(),
        "cge_sum": z(), "cge_n": z(),
        "t01_sum": z(), "t01_n": z(),
        "hours": 0.0,
    }


def _merge(a, b):
    for k in a:
        if k == "hs_max":
            a[k] = np.maximum(a[k], b[k])
        else:
            a[k] = a[k] + b[k]
    return a


def process_year(year):
    """Return (epoch_key, accumulators, lon, lat) for one calendar year."""
    acc = _empty_acc()
    lon = lat = None
    hs_files = _files("hs", year)
    assert len(hs_files) == 12, f"{year}: expected 12 hs files, got {len(hs_files)}"
    for hs_f in hs_files:
        month_tag = hs_f.split("_1hr_")[1]
        with xr.open_dataset(hs_f) as ds:
            hs = ds.hs.values                       # (time, seapoint)
            if lon is None:
                lon = ds.longitude.values.astype(float)
                lat = ds.latitude.values.astype(float)
            assert hs.shape[1] == N_SEA, f"{hs_f}: seapoint dim {hs.shape[1]}"
        ok = np.isfinite(hs)
        hs0 = np.where(ok, hs, 0.0)
        acc["hs_sum"] += hs0.sum(0)
        acc["hs_sumsq"] += (hs0 ** 2).sum(0)
        acc["hs_max"] = np.maximum(acc["hs_max"], np.where(ok, hs, -1).max(0))
        acc["hs_n"] += ok.sum(0)
        acc["storm_hrs"] += ((hs > STORM_HS) & ok).sum(0)
        binned = np.clip((hs0 / HS_BIN_W).astype(np.int64), 0, HS_BINS - 1)
        sp = np.broadcast_to(np.arange(N_SEA), hs.shape)
        flat = np.bincount((sp * HS_BINS + binned)[ok].ravel(),
                           minlength=N_SEA * HS_BINS)
        acc["hs_hist"] += flat.reshape(N_SEA, HS_BINS)
        acc["hours"] += hs.shape[0]

        for var in ("dir", "cge", "t01"):
            f = f"{WHACS_DIR}/{var}_NZ/{var}_WHACS_hindcast_WHACS_ERA5_1hr_{month_tag}"
            with xr.open_dataset(f) as ds:
                v = ds[var].values
            vok = np.isfinite(v)
            if var == "dir":
                rad = np.radians(np.where(vok, v, 0.0))
                acc["dir_sin"] += (np.sin(rad) * vok).sum(0)
                acc["dir_cos"] += (np.cos(rad) * vok).sum(0)
                acc["dir_n"] += vok.sum(0)
                w = hs0 ** 2 * vok * ok
                acc["dir_esin"] += (np.sin(rad) * w).sum(0)
                acc["dir_ecos"] += (np.cos(rad) * w).sum(0)
                acc["dir_e_n"] += w.sum(0)
            else:
                acc[f"{var}_sum"] += np.where(vok, v, 0.0).sum(0)
                acc[f"{var}_n"] += vok.sum(0)
    epoch = "7989" if year < EPOCH_SPLIT else "9023"
    return epoch, acc, lon, lat


def _stats(acc, suffix):
    n = np.maximum(acc["hs_n"], 1)
    years = acc["hours"] / (365.25 * 24)
    cum = acc["hs_hist"].cumsum(1) / n[:, None]
    edges = (np.arange(HS_BINS) + 0.5) * HS_BIN_W

    def pct(q):
        idx = (cum >= q).argmax(1)
        return edges[idx]

    mean = acc["hs_sum"] / n
    var = np.maximum(acc["hs_sumsq"] / n - mean ** 2, 0)
    out = {
        f"hs_mean{suffix}": mean,
        f"hs_std{suffix}": np.sqrt(var),
        f"hs_p50{suffix}": pct(0.50),
        f"hs_p90{suffix}": pct(0.90),
        f"hs_p99{suffix}": pct(0.99),
        f"hs_max{suffix}": acc["hs_max"],
        f"storm_hrs_gt4m_yr{suffix}": acc["storm_hrs"] / years,
        f"dir_mean{suffix}": np.degrees(
            np.arctan2(acc["dir_sin"], acc["dir_cos"])) % 360,
        f"dir_energy_mean{suffix}": np.degrees(
            np.arctan2(acc["dir_esin"], acc["dir_ecos"])) % 360,
        f"cge_mean{suffix}": acc["cge_sum"] / np.maximum(acc["cge_n"], 1),
        f"t01_mean{suffix}": acc["t01_sum"] / np.maximum(acc["t01_n"], 1),
    }
    return out


def build(max_workers=10):
    results = process_map(process_year, list(YEARS),
                          max_workers=max_workers, chunksize=1)
    epochs = {"7989": _empty_acc(), "9023": _empty_acc()}
    lon = lat = None
    for epoch, acc, ln, lt in results:
        _merge(epochs[epoch], acc)
        lon, lat = ln, lt

    full = _merge(_empty_acc(), epochs["7989"])
    full = _merge(full, epochs["9023"])

    cols = {"seapoint": np.arange(N_SEA), "lon": lon, "lat": lat}
    cols.update(_stats(full, ""))
    cols.update(_stats(epochs["7989"], "_7989"))
    cols.update(_stats(epochs["9023"], "_9023"))
    df = pd.DataFrame(cols)
    out = DRIVER_DATA / "whacs_seapoint_climatology.parquet"
    df.to_parquet(out, index=False)
    print(f"wrote {out} rows={len(df)}")
    print(df[["hs_mean", "hs_p99", "storm_hrs_gt4m_yr", "cge_mean"]].describe())
    return df


if __name__ == "__main__":
    build()
