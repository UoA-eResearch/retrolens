"""Stage 32: paper-grade figures from cached stats (driver_data/stats/).

Conventions from the dataviz method: diverging blue<->red only for signed
quantities (WLR polarity: red = erosion, blue = accretion, neutral gray at 0);
single-hue sequential ramps for magnitudes; categorical identity only where an
axis label can't carry it; thin marks, recessive chrome, no dual axes.

Run:  python3 -m drivers.figures        -> figures/*.png (300 dpi) + .pdf
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from .common import DRIVER_DATA, REPO

STATS = DRIVER_DATA / "stats"
FIGS = REPO / "figures"

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"
RED = "#e34948"
NEUTRAL = "#f0efec"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95",
       "#0d366b"]

DIV = LinearSegmentedColormap.from_list("erode_accrete", [RED, NEUTRAL, BLUE])
SEQC = LinearSegmentedColormap.from_list("seq_blue", SEQ)

DRIVER_LABELS = {
    "hs_mean": "Mean Hs (m)", "hs_p99": "Hs p99 (m)",
    "storm_hrs_gt4m_yr": "Storm hours >4 m (h/yr)",
    "cge_mean": "Wave energy flux (kW/m)", "t01_mean": "Mean period T01 (s)",
    "wave_incidence_deg": "Wave incidence (deg)",
    "beach_slope_face": "Beach-face slope (tan b)",
    "tanbeta_nearshore": "Nearshore slope (tan b)",
    "closure_depth_m": "Closure depth (m)", "vlm_mm_yr": "VLM (mm/yr, +up)",
    "backshore_mean": "Backshore mean elev (m)",
    "backshore_max": "Backshore max elev (m)",
    "hinterland_slope": "Hinterland slope", "spring_range_m": "Spring tide range (m)",
    "form_factor": "Tidal form factor", "dist_mouth_km": "Distance to river mouth (km)",
    "river_supply_idx": "River supply index", "rain_mm_yr": "Rainfall (mm/yr)",
    "rainstorm_days": "Rain days >25 mm (d/yr)", "geol_age_ma": "Rock age (Ma)",
    "erodibility_ord": "Lithologic erodibility (1-5)",
    "shaking_idx": "Seismic shaking index", "n_M5_50km": "M>=5 quakes <50 km",
    "dist_M65_km": "Distance to M>=6.5 (km)",
    "hs_mean_delta": "Change in mean Hs, post-pre (m)",
    "hs_p99_delta": "Change in Hs p99, post-pre (m)",
    "storm_hrs_delta": "Change in storm hours (h/yr)",
    "hs_mean": "Mean Hs (m)",
}


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "font.family": "sans-serif",
        "font.size": 9, "axes.edgecolor": BASE, "axes.linewidth": 0.8,
        "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 10, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "figure.dpi": 120,
    })


def save(fig, name):
    FIGS.mkdir(exist_ok=True)
    fig.savefig(FIGS / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved figures/{name}.png")


def _map_axes(ax, m):
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(m.x2193.min() - 3e4, m.x2193.max() + 3e4)
    ax.set_ylim(m.y2193.min() - 3e4, m.y2193.max() + 3e4)


def f1_national_maps(m):
    fig = plt.figure(figsize=(12, 8.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.5, 1, 1])
    axw = fig.add_subplot(gs[:, 0])
    lim = np.nanpercentile(np.abs(m.WLR), 98)
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    sc = axw.scatter(m.x2193, m.y2193, c=m.WLR, s=0.5, cmap=DIV, norm=norm,
                     rasterized=True, linewidths=0)
    _map_axes(axw, m)
    axw.set_title("Shoreline change rate WLR (m/yr)\n"
                  "red = erosion, blue = accretion", fontsize=10)
    cb = fig.colorbar(sc, ax=axw, fraction=0.045, pad=0.02, shrink=0.7,
                      format="%.1f")
    cb.set_label("WLR (m/yr)", color=INK2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8)

    panels = [("hs_mean", "Mean Hs (m)"), ("spring_range_m", "Spring range (m)"),
              ("vlm_mm_yr", "VLM (mm/yr, +up)"), ("beach_slope_face",
                                                  "Beach-face slope")]
    for i, (col, title) in enumerate(panels):
        ax = fig.add_subplot(gs[i // 2, 1 + i % 2])
        v = m[col]
        if col == "vlm_mm_yr":
            lim2 = np.nanpercentile(np.abs(v), 98)
            sc = ax.scatter(m.x2193, m.y2193, c=v, s=0.4, cmap=DIV,
                            norm=TwoSlopeNorm(vmin=-lim2, vcenter=0,
                                              vmax=lim2),
                            rasterized=True, linewidths=0)
        else:
            vmin, vmax = np.nanpercentile(v, [2, 98])
            sc = ax.scatter(m.x2193, m.y2193, c=v, s=0.4, cmap=SEQC,
                            vmin=vmin, vmax=vmax, rasterized=True,
                            linewidths=0)
        _map_axes(ax, m)
        ax.set_title(title, fontsize=9)
        cb = fig.colorbar(sc, ax=ax, fraction=0.05, pad=0.02, shrink=0.85,
                          format="%.2f" if col == "beach_slope_face" else "%.1f")
        cb.outline.set_visible(False)
        cb.ax.tick_params(labelsize=7)
    save(fig, "F1_national_maps")


def f2_scatter_grid(m, corr):
    c = corr[(corr.response == "WLR") & (corr.method == "spearman")]
    main_L = c.block_len_m.median()
    c = c[c.block_len_m == main_L].set_index("driver")
    top = c.rho.abs().sort_values(ascending=False).head(8).index
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.5), constrained_layout=True)
    for ax, drv in zip(axes.ravel(), top):
        d = m[[drv, "WLR"]].dropna()
        ylim = np.nanpercentile(np.abs(d.WLR), 99)
        xlo, xhi = np.nanpercentile(d[drv], [0.5, 99.5])
        hb = ax.hexbin(d[drv], d.WLR, gridsize=45, bins="log", cmap=SEQC,
                       extent=(xlo, xhi, -ylim, ylim), linewidths=0)
        ax.axhline(0, color=BASE, lw=0.8)
        r = c.loc[drv]
        ax.set_title(f"{DRIVER_LABELS.get(drv, drv)}\n"
                     rf"$\rho$={r.rho:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}]",
                     fontsize=8.5)
        ax.set_xlabel("")
        ax.set_ylabel("WLR (m/yr)" if ax in axes[:, 0] else "")
    fig.suptitle("Drivers vs shoreline change rate (hexbin density, log scale; "
                 "Spearman with 95% block-bootstrap CI)", color=INK)
    save(fig, "F2_scatter_grid")


def f3_heatmaps(corr, coll):
    piv = corr[(corr.method == "spearman")
               & (corr.block_len_m == corr.block_len_m.median())]
    piv = piv.pivot_table(index="driver", columns="response", values="rho")
    piv = piv.loc[piv.WLR.abs().sort_values(ascending=False).index,
                  ["WLR", "EPR", "NSM", "SCE"]]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(13, 0.32 * len(piv) + 2),
        gridspec_kw={"width_ratios": [1, 2.2]}, constrained_layout=True)
    im = ax1.imshow(piv.values, cmap=DIV, vmin=-0.6, vmax=0.6, aspect="auto")
    ax1.set_xticks(range(len(piv.columns)), piv.columns)
    ax1.set_yticks(range(len(piv)),
                   [DRIVER_LABELS.get(i, i) for i in piv.index], fontsize=8)
    ax1.grid(False)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if np.isfinite(v):
                ax1.text(j, i, f"{v:+.2f}", ha="center", va="center",
                         fontsize=7, color=INK if abs(v) < 0.4 else SURFACE)
    ax1.set_title("Driver x response (Spearman)")
    fig.colorbar(im, ax=ax1, fraction=0.03).outline.set_visible(False)

    cl = coll.loc[[i for i in piv.index if i in coll.index],
                  [i for i in piv.index if i in coll.columns]]
    mask = np.triu(np.ones_like(cl.values, bool))
    vals = np.where(mask, np.nan, cl.values)
    im2 = ax2.imshow(vals, cmap=DIV, vmin=-1, vmax=1, aspect="auto")
    ax2.set_xticks(range(len(cl.columns)),
                   [DRIVER_LABELS.get(i, i) for i in cl.columns],
                   rotation=90, fontsize=7)
    ax2.set_yticks(range(len(cl)),
                   [DRIVER_LABELS.get(i, i) for i in cl.index], fontsize=7)
    ax2.grid(False)
    ax2.set_title("Driver x driver collinearity (Spearman)")
    fig.colorbar(im2, ax=ax2, fraction=0.03).outline.set_visible(False)
    save(fig, "F3_correlation_heatmaps")


def f4_categorical(m, effects):
    cats = [("SHORE_TYPE", 10), ("lith_class", 12), ("EXPOSURE", 6),
            ("HINTERLAND", 8)]
    fig, axes = plt.subplots(1, 4, figsize=(13.5, 4.2),
                             constrained_layout=True,
                             gridspec_kw={"width_ratios": [1.2, 1, 0.7, 1]})
    lim = np.nanpercentile(np.abs(m.WLR), 98)
    for ax, (cat, topn) in zip(axes, cats):
        if cat not in m.columns:
            ax.axis("off")
            continue
        counts = m[cat].value_counts().head(topn)
        order = (m[m[cat].isin(counts.index)].groupby(cat, observed=True)
                 .WLR.median().sort_values().index)
        data = [m.loc[m[cat] == g, "WLR"].dropna().clip(-lim, lim)
                for g in order]
        bp = ax.boxplot(data, vert=False, showfliers=False, patch_artist=True,
                        widths=0.62, medianprops=dict(color=INK, lw=1.4),
                        boxprops=dict(facecolor=SEQ[1], edgecolor=BASE, lw=0.7),
                        whiskerprops=dict(color=BASE), capprops=dict(color=BASE))
        ax.set_yticks(range(1, len(order) + 1),
                      [f"{g} ({counts[g]:,})" for g in order], fontsize=7.5)
        ax.axvline(0, color=RED, lw=0.8, ls="--", alpha=0.6)
        e = effects[(effects.driver == cat) & (effects.response == "WLR")]
        eps = e.eps2.iloc[0] if len(e) else np.nan
        ax.set_title(f"{cat}   " + rf"$\epsilon^2$={eps:.3f}", fontsize=9)
        ax.set_xlabel("WLR (m/yr)")
    save(fig, "F4_categorical")


def f5_model(imp):
    top = imp.sort_values("mean_importance", ascending=False).head(12)
    fig = plt.figure(figsize=(13, 4.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 4, width_ratios=[1.6, 1, 1, 1])
    ax1 = fig.add_subplot(gs[:, 0])
    y = np.arange(len(top))[::-1]
    ax1.barh(y, top.mean_importance, xerr=top.std_across_regions, height=0.62,
             color=BLUE, error_kw=dict(ecolor=MUTED, lw=0.9))
    ax1.set_yticks(y, [DRIVER_LABELS.get(i, i) for i in top.index], fontsize=8)
    ax1.set_xlabel("Permutation importance\n(held-out, mean over regions)")
    ax1.set_title("What the model uses")

    pdps = []
    for p in sorted(STATS.glob("pdp_*.csv")):
        d = pd.read_csv(p)
        d["grid"] = pd.to_numeric(d.grid, errors="coerce")
        d = d.dropna()
        if len(d) >= 3:
            pdps.append((p.stem.replace("pdp_", ""), d))
    for i, (feat, d) in enumerate(pdps[:6]):
        ax = fig.add_subplot(gs[i // 3, 1 + i % 3])
        yc = d.partial_dependence - d.partial_dependence.mean()
        lo, hi = np.percentile(d.grid, [1, 99])
        ax.plot(d.grid, yc, lw=2, color=BLUE)
        ax.axhline(0, color=BASE, lw=0.7)
        ax.set_xlim(lo, hi)
        ax.set_title(DRIVER_LABELS.get(feat, feat), fontsize=8)
        ax.tick_params(labelsize=7)
        if i % 3 == 0:
            ax.set_ylabel("PD of WLR\n(m/yr, centred)", fontsize=7.5)
    save(fig, "F5_model_importance")


def f6_regions(cv, oof):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4),
                                   constrained_layout=True)
    c = cv[cv.region != "POOLED_OOF"].sort_values("r2")
    y = np.arange(len(c))
    ax1.barh(y, c.r2, color=np.where(c.r2 > 0, BLUE, RED), height=0.62)
    ax1.set_yticks(y, c.region, fontsize=8)
    ax1.axvline(0, color=BASE, lw=0.8)
    pooled = cv[cv.region == "POOLED_OOF"].r2.iloc[0]
    ax1.set_xlabel("Held-out R^2 (leave-one-region-out)")
    ax1.set_title(f"Regional generalisation (pooled OOF R^2 = {pooled:.2f})")

    lim = np.nanpercentile(np.abs(oof.WLR), 99)
    ax2.hexbin(oof.WLR, oof.WLR_pred_oof, gridsize=60, bins="log", cmap=SEQC,
               extent=(-lim, lim, -lim, lim), linewidths=0)
    ax2.plot([-lim, lim], [-lim, lim], color=RED, lw=0.9, ls="--")
    ax2.set_xlabel("Observed WLR (m/yr)")
    ax2.set_ylabel("Predicted WLR (m/yr, out-of-fold)")
    ax2.set_title("Observed vs predicted")
    ax2.set_aspect("equal")
    save(fig, "F6_regional_model")


def f7_epochs(ej, ec):
    fig = plt.figure(figsize=(14, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1, 1.2])
    ax1 = fig.add_subplot(gs[0])
    lim = np.nanpercentile(np.abs(ej.delta_WLR), 95)
    sc = ax1.scatter(ej.x2193, ej.y2193, c=ej.delta_WLR, s=0.6, cmap=DIV,
                     norm=TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim),
                     rasterized=True, linewidths=0)
    _map_axes(ax1, ej)
    ax1.set_title(f"Change in rate, post-1990 minus pre-1990\n"
                  f"(n={len(ej):,} transects, >=3 shorelines both epochs)",
                  fontsize=9.5)
    cb = fig.colorbar(sc, ax=ax1, fraction=0.05, pad=0.02, shrink=0.65,
                      format="%.0f")
    cb.set_label(r"$\Delta$WLR (m/yr)", color=INK2, fontsize=8)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8)

    ax2 = fig.add_subplot(gs[1])
    lim2 = np.nanpercentile(np.abs(ej[["WLR_pre", "WLR_post"]]), 98)
    ax2.hexbin(ej.WLR_pre, ej.WLR_post, gridsize=55, bins="log", cmap=SEQC,
               extent=(-lim2, lim2, -lim2, lim2), linewidths=0)
    ax2.plot([-lim2, lim2], [-lim2, lim2], color=RED, lw=0.9, ls="--")
    rho = ej.WLR_pre.corr(ej.WLR_post, method="spearman")
    ax2.set_xlabel("WLR pre-1990 (m/yr)")
    ax2.set_ylabel("WLR post-1990 (m/yr)")
    ax2.set_title(rf"Epoch persistence  $\rho$={rho:.2f}")
    ax2.set_aspect("equal")

    ax3 = fig.add_subplot(gs[2])
    d = ec[ec.response == "delta_WLR"].set_index("driver")
    d = d.loc[d.rho.abs().sort_values(ascending=False).head(10).index[::-1]]
    y = np.arange(len(d))
    ax3.barh(y, d.rho, xerr=[d.rho - d.lo, d.hi - d.rho], height=0.6,
             color=np.where(d.rho > 0, BLUE, RED),
             error_kw=dict(ecolor=MUTED, lw=0.9))
    ax3.set_yticks(y, [DRIVER_LABELS.get(i, i) for i in d.index], fontsize=8)
    ax3.axvline(0, color=BASE, lw=0.8)
    ax3.set_xlabel(r"Spearman $\rho$ with $\Delta$WLR [95% CI]")
    ax3.set_title("What correlates with the change")
    save(fig, "F7_epochs")


def s1_correlogram(cg, block_choice):
    fig, ax = plt.subplots(figsize=(7, 3.8), constrained_layout=True)
    ax.plot(cg.lag_m / 1000, cg.r, color=BLUE, lw=2)
    ax.axhline(1 / np.e, color=MUTED, lw=0.8, ls="--")
    L = block_choice.decorrelation_m.iloc[0]
    ax.axvline(L / 1000, color=RED, lw=0.9, ls="--")
    ax.annotate(f"decorrelation ~{L/1000:.1f} km", (L / 1000, 1 / np.e),
                textcoords="offset points", xytext=(8, 8), color=INK2,
                fontsize=8)
    ax.set_xlabel("Alongshore lag (km)")
    ax.set_ylabel("Autocorrelation of WLR")
    ax.set_title("Alongshore autocorrelation and bootstrap block choice")
    save(fig, "S1_correlogram")


def run():
    style()
    m = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet")
    corr = pd.read_csv(STATS / "corr_numeric.csv")
    coll = pd.read_csv(STATS / "collinearity_spearman.csv", index_col=0)
    effects = pd.read_csv(STATS / "categorical_effects.csv")
    f1_national_maps(m)
    f2_scatter_grid(m, corr)
    f3_heatmaps(corr, coll)
    f4_categorical(m, effects)
    imp = pd.read_csv(STATS / "permutation_importance.csv", index_col=0)
    f5_model(imp)
    cv = pd.read_csv(STATS / "cv_scores.csv")
    oof = pd.read_parquet(STATS / "oof_predictions.parquet")
    f6_regions(cv, oof)
    ej = pd.read_parquet(STATS / "epoch_rates_joined.parquet")
    ec = pd.read_csv(STATS / "epoch_correlations.csv")
    f7_epochs(ej, ec)
    s1_correlogram(pd.read_csv(STATS / "correlogram_WLR.csv"),
                   pd.read_csv(STATS / "block_choice.csv"))
    print("all figures done")


if __name__ == "__main__":
    run()
