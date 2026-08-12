"""Driver 07: coastal typology from the Bruun-rule proxy table.

Source /mnt/Bruunrule_Yaxiong/code/nzccd_rates_proxy.parquet (224,583 rows)
carries the national coastal typology classification (Typology/SubTypolog,
SHORE_TYPE, EXPOSURE, HINTERLAND, FS, CSI indices) keyed by NZCCD UniqueID.
Join is by ID, not geometry, so the QA centres on ID integrity: the source's
`Rate` column is compared against the base table's WLR/EPR/LRR to prove both
files key the same transects.

Run:  python3 -m drivers.d07_typology
Out:  driver_data/d07_typology.parquet  (228,538 rows, one per base UniqueID)
QA:   driver_data/qa/d07_typology_*.csv / .png
"""

import numpy as np
import pandas as pd

from .common import QA_DIR, TYPOLOGY_PARQUET, cast_unique_id, load_base, write_driver

SRC_COLS = [
    "UniqueID", "Typology", "SubTypolog", "SHORE_TYPE", "EXPOSURE",
    "HINTERLAND", "FS", "CSI_in", "CSI_cc", "Trend", "Confidence", "Rate",
]
RENAME = {
    "Trend": "typology_trend",
    "Confidence": "typology_confidence",
    "Rate": "typology_rate",
}


def _rate_identity_qa(src, base):
    """Prove the source's Rate column is the base's WLR (ID integrity check)."""
    m = base.merge(
        src[["UniqueID", "Rate", "EPR", "LRR"]], on="UniqueID",
        how="inner", suffixes=("", "_src"))
    rows = []
    for col in ("WLR", "EPR", "LRR"):
        x = m[[col, "Rate"]].dropna()
        diff = (x["Rate"] - x[col]).abs()
        rows.append({
            "base_col": col,
            "n_matched": len(x),
            "pearson_corr": x["Rate"].corr(x[col]),
            "median_abs_diff": diff.median(),
            "pct_abs_diff_lt_0p01": diff.lt(0.01).mean() * 100,
        })
    qa = pd.DataFrame(rows).sort_values("pct_abs_diff_lt_0p01", ascending=False)

    # The residual disagreement is a rates-vintage issue, not an ID issue:
    # split on whether the source row's own EPR equals the base EPR.
    d = (m["Rate"] - m["WLR"]).abs()
    same_run = (m["EPR_src"] - m["EPR"]).abs() < 0.005
    vintage = pd.DataFrame([{
        "subset": "src EPR == base EPR (same DSAS vintage)",
        "n": int(same_run.sum()),
        "rate_eq_wlr_pct": d[same_run].lt(0.01).mean() * 100,
        "pearson_corr_rate_wlr": m.loc[same_run, "Rate"].corr(m.loc[same_run, "WLR"]),
    }, {
        "subset": "src EPR != base EPR (older vintage)",
        "n": int((~same_run).sum()),
        "rate_eq_wlr_pct": d[~same_run].lt(0.01).mean() * 100,
        "pearson_corr_rate_wlr": m.loc[~same_run, "Rate"].corr(m.loc[~same_run, "WLR"]),
    }])

    qa.to_csv(QA_DIR / "d07_typology_rate_identity.csv", index=False)
    vintage.to_csv(QA_DIR / "d07_typology_rate_vintage.csv", index=False)
    print("rate identity check (Rate vs base columns):")
    print(qa.to_string(index=False))
    print("vintage split (why Rate!=WLR on a minority of rows):")
    print(vintage.to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.hexbin(m["WLR"], m["Rate"], gridsize=80, bins="log",
              extent=(-5, 5, -5, 5), cmap="viridis")
    ax.plot([-5, 5], [-5, 5], color="crimson", lw=0.8, ls="--")
    best = qa.iloc[0]
    ax.set_xlabel("base WLR (m/yr)")
    ax.set_ylabel("source Rate (m/yr)")
    ax.set_title(
        f"d07 ID integrity: Rate vs WLR, n={best.n_matched:,}\n"
        f"corr={best.pearson_corr:.4f}, "
        f"{best.pct_abs_diff_lt_0p01:.1f}% within 0.01 m/yr")
    fig.tight_layout()
    fig.savefig(QA_DIR / "d07_typology_rate_vs_wlr.png", dpi=120)
    plt.close(fig)
    return qa


def build():
    src = pd.read_parquet(TYPOLOGY_PARQUET)
    src["UniqueID"] = cast_unique_id(src["UniqueID"])
    n_dup = int(src["UniqueID"].duplicated().sum())
    print(f"source rows={len(src)} duplicate UniqueIDs dropped={n_dup}")
    if n_dup:
        src = src.drop_duplicates("UniqueID", keep="first")

    base = load_base(columns=["UniqueID", "Region", "WLR", "EPR", "LRR"])
    assert len(base) == 228538, f"unexpected base row count {len(base)}"

    _rate_identity_qa(src, base)

    driver = src[SRC_COLS].rename(columns=RENAME)
    out = base[["UniqueID"]].merge(driver, on="UniqueID", how="left")
    assert len(out) == len(base)
    for col in ("CSI_in", "CSI_cc"):
        out[col] = out[col].astype("Int32")

    # Categorical QA. Distinguish "matched but blank in source" from
    # "base transect absent from the source file" — both are null in the
    # parquet, but they mean different things.
    matched = out["Typology"].notna() | out["UniqueID"].isin(driver["UniqueID"])

    def counts(col):
        lab = out[col].astype("object").where(
            out[col].notna(),
            np.where(matched, "(missing in source)", "(no source row)"))
        return lab.value_counts().rename_axis(col).rename("n")

    typ_counts = counts("Typology")
    typ_counts.to_csv(QA_DIR / "d07_typology_typology_counts.csv")
    exp_counts = counts("EXPOSURE")
    exp_counts.to_csv(QA_DIR / "d07_typology_exposure_counts.csv")
    xtab = pd.crosstab(
        out["Typology"].astype("object").where(
            out["Typology"].notna(),
            np.where(matched, "(missing in source)", "(no source row)")),
        base["Region"])
    xtab.to_csv(QA_DIR / "d07_typology_typology_x_region.csv")

    pct_typ = out["Typology"].notna().mean() * 100
    print(f"base transects with non-null Typology: {pct_typ:.2f}% (expect ~98%)")
    print("Typology counts:")
    print(typ_counts.to_string())
    print("EXPOSURE counts:")
    print(exp_counts.to_string())

    return write_driver(out, "d07_typology")


if __name__ == "__main__":
    build()
