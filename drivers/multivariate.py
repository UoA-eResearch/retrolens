"""Stage 31: multivariate driver model of WLR.

HistGradientBoostingRegressor (native NaN + categorical handling) with
leave-one-region-out CV — the honest generalisation estimate under spatial
autocorrelation. Typology/typology_trend/typology_rate are EXCLUDED as
features: they are derived from the NZCCD rates themselves (target leakage);
SHORE_TYPE/EXPOSURE/HINTERLAND/lith_class are mapped classifications and stay.

Outputs (driver_data/stats/): cv_scores.csv, permutation_importance.csv,
pdp_<feature>.csv, oof_predictions.parquet, morans_residuals.csv,
sign_classification.csv.

Run:  python3 -m drivers.multivariate
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import (HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor)
from sklearn.inspection import partial_dependence, permutation_importance
from sklearn.metrics import balanced_accuracy_score, r2_score
from sklearn.model_selection import GroupKFold

from .common import DRIVER_DATA
from .correlations import NUMERIC_DRIVERS, STATS_DIR
from .stats import morans_i

CAT_FEATURES = ["SHORE_TYPE", "EXPOSURE", "HINTERLAND", "lith_class",
                "erodibility", "landward_side"]
TARGET = "WLR"


def _design(m):
    numeric = [c for c in NUMERIC_DRIVERS if c in m.columns]
    cats = [c for c in CAT_FEATURES if c in m.columns]
    X = m[numeric + cats].copy()
    for c in cats:
        X[c] = X[c].astype("category")
    return X, numeric, cats


def _model():
    return HistGradientBoostingRegressor(
        max_iter=400, learning_rate=0.08, max_leaf_nodes=63,
        categorical_features="from_dtype", random_state=0)


def run():
    STATS_DIR.mkdir(exist_ok=True)
    m = pd.read_parquet(DRIVER_DATA / "drivers_master.parquet")
    m = m.dropna(subset=[TARGET]).reset_index(drop=True)
    X, numeric, cats = _design(m)
    y = m[TARGET].values
    groups = m.Region.values
    print(f"n={len(m):,}; {len(numeric)} numeric + {len(cats)} categorical")

    # ---- leave-one-region-out CV
    gkf = GroupKFold(n_splits=m.Region.nunique())
    oof = np.full(len(m), np.nan)
    scores, imps = [], []
    for k, (tr, te) in enumerate(gkf.split(X, y, groups)):
        mdl = _model().fit(X.iloc[tr], y[tr])
        pred = mdl.predict(X.iloc[te])
        oof[te] = pred
        region = m.Region.iloc[te].iloc[0]
        scores.append(dict(region=region, n_test=len(te),
                           r2=r2_score(y[te], pred),
                           mae=float(np.mean(np.abs(y[te] - pred)))))
        pi = permutation_importance(mdl, X.iloc[te], y[te], n_repeats=5,
                                    random_state=0, n_jobs=8)
        imps.append(pd.Series(pi.importances_mean, index=X.columns,
                              name=region))
        print(f"  fold {k + 1}/{gkf.n_splits} {region}: "
              f"R2={scores[-1]['r2']:.3f}")

    cv = pd.DataFrame(scores)
    cv.loc[len(cv)] = dict(region="POOLED_OOF", n_test=len(m),
                           r2=r2_score(y, oof),
                           mae=float(np.mean(np.abs(y - oof))))
    cv.to_csv(STATS_DIR / "cv_scores.csv", index=False)
    print(cv.tail(3).to_string())

    imp = pd.concat(imps, axis=1)
    imp_out = pd.DataFrame({"mean_importance": imp.mean(1),
                            "std_across_regions": imp.std(1)})
    imp_out.sort_values("mean_importance", ascending=False).to_csv(
        STATS_DIR / "permutation_importance.csv")
    print(imp_out.sort_values("mean_importance", ascending=False)
          .head(10).to_string())

    pd.DataFrame({"UniqueID": m.UniqueID, "Region": m.Region, "WLR": y,
                  "WLR_pred_oof": oof, "x2193": m.x2193, "y2193": m.y2193,
                  }).to_parquet(STATS_DIR / "oof_predictions.parquet",
                                index=False)

    # ---- PDPs for the top features (full-data model, display only)
    full = _model().fit(X, y)
    top = imp_out.mean_importance.sort_values(ascending=False).head(8).index
    for feat in top:
        try:
            pd_res = partial_dependence(full, X, [feat],
                                        grid_resolution=40, kind="average")
            grid = pd_res["grid_values"][0]
            pd.DataFrame({"grid": grid,
                          "partial_dependence": pd_res["average"][0]}).to_csv(
                STATS_DIR / f"pdp_{feat}.csv", index=False)
        except Exception as e:  # categorical PDP quirks
            print(f"  pdp skipped for {feat}: {e}")

    # ---- residual spatial structure vs raw
    sub = np.random.default_rng(0).choice(len(m), 50_000, replace=False)
    mi_raw = morans_i(y[sub], m.x2193.values[sub], m.y2193.values[sub])
    resid = y - oof
    mi_res = morans_i(resid[sub], m.x2193.values[sub], m.y2193.values[sub])
    pd.DataFrame([dict(variable="WLR", **mi_raw),
                  dict(variable="WLR_oof_residual", **mi_res)]).to_csv(
        STATS_DIR / "morans_residuals.csv", index=False)
    print(f"Moran's I: raw {mi_raw['I']:.3f} -> residual {mi_res['I']:.3f}")

    # ---- robustness: erosion/accretion sign classification
    ysign = (y > 0).astype(int)
    sign_scores = []
    for tr, te in gkf.split(X, ysign, groups):
        clf = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, max_leaf_nodes=63,
            categorical_features="from_dtype", random_state=0)
        clf.fit(X.iloc[tr], ysign[tr])
        sign_scores.append(dict(
            region=m.Region.iloc[te].iloc[0],
            balanced_acc=balanced_accuracy_score(ysign[te],
                                                 clf.predict(X.iloc[te]))))
    pd.DataFrame(sign_scores).to_csv(STATS_DIR / "sign_classification.csv",
                                     index=False)
    print("sign classification balanced acc:",
          round(np.mean([s["balanced_acc"] for s in sign_scores]), 3))


if __name__ == "__main__":
    run()
