"""Driver 08: QMAP geology (GNS 1:250k Geological Map 2023).

Source driver_data/qmap/qmap_geology.gpkg layer 'qmap_geological_units'
(55,211 MultiPolygons, EPSG:2193). Base transect points are joined into the
polygons directly (sjoin, 'intersects'); points that miss every polygon
(offshore/beach edge) fall back to sjoin_nearest with max_distance=1000 m,
with the join distance recorded in geol_dist_m (0 for direct hits).

Lithology is condensed to an 8-class `lith_class` plus an ordinal hardness
`erodibility_ord` (1 = hardest .. 5 = loose sand). QMAP's `rockgroup` alone
is NOT sufficient: Holocene dune/beach sand is mapped with rockgroup
'sandstone' (mainrock 'sand'), and Quaternary gravels appear under several
rockgroups. Empirically (see qa/d08_lith_mapping.csv) QMAP `simplename`
ending in 'deposits' exactly separates unconsolidated surficial units
(rockclass 'clastic sediment'/'anthropic' only) from lithified '... rocks' /
'Basement ...' units, so classification is hierarchical:

1. surficial '... deposits'  -> unconsolidated_sand where mainrock/rockgroup
   is sand or peat, else alluvium_gravel (gravel, till, mud/silt/loess,
   lahar breccia/agglomerate, human-made fill);
2. 'Basement ...' clastic sediment (greywacke terranes: Torlesse, Murihiku,
   Pahau...) -> hard_sedimentary regardless of rockgroup;
3. otherwise a rockgroup dict, with rockclass fallbacks for stragglers.

Documented judgement calls: melange (tectonic, sheared mudstone matrix of
the East Coast/Northland allochthon) -> soft_sedimentary; the only matched
ignimbrite is unwelded pyroclastic (mainrock 'ignimbrite', lithology
'pyroclastic rock, ...') -> volcanic_soft; lahar 'deposits' (breccia/
agglomerate rockgroups, Taranaki ring plain) -> alluvium_gravel;
quartzite -> metamorphic.

Caveat: the join is point-in-polygon at the MHW transect point, so cliffed
shores fronted by a mapped Holocene beach strip (1:250k) classify as the
fringe deposit, not the backing cliff rock - d07 SHORE_TYPE 'r'/'cp'
transects (n=1,526, Waikato/West Coast) land on Holocene shoreline
conglomerate/sand with median join distance ~7 m. Interpret lith_class as
"material the shoreline is currently cut in".

Run:  python3 -m drivers.d08_geology
Out:  driver_data/d08_geology.parquet  (228,538 rows, one per base UniqueID)
QA:   driver_data/qa/d08_*.csv / .png
"""

import geopandas as gpd
import numpy as np
import pandas as pd

from .common import DRIVER_DATA, QA_DIR, base_gdf, qa_join, write_driver

QMAP_GPKG = DRIVER_DATA / "qmap" / "qmap_geology.gpkg"
QMAP_LAYER = "qmap_geological_units"
MAX_NEAREST_M = 1000.0

SRC_COLS = [
    "rockgroup", "rockclass", "mainrock", "simplename",
    "absmin_ma", "absmax_ma",
]

# rockgroup -> lith_class for lithified ('... rocks') units. Surficial
# '... deposits' and Basement clastics are classified upstream of this dict.
ROCKGROUP_MAP = {
    # unconsolidated (only reached if a unit is not '... deposits'; kept for
    # completeness/robustness)
    "sand": "unconsolidated_sand",
    "peat": "unconsolidated_sand",
    "gravel": "alluvium_gravel",
    "till": "alluvium_gravel",
    "silt": "alluvium_gravel",
    "mud": "alluvium_gravel",
    "loess": "alluvium_gravel",
    "fill": "alluvium_gravel",
    # soft sedimentary rock
    "mudstone": "soft_sedimentary",
    "siltstone": "soft_sedimentary",
    "sandstone": "soft_sedimentary",
    "shale": "soft_sedimentary",
    "marl": "soft_sedimentary",
    "conglomerate": "soft_sedimentary",
    "alternating sandstone/mudstone": "soft_sedimentary",
    "alternating sandstone/siltstone": "soft_sedimentary",
    "melange": "soft_sedimentary",
    # hard / indurated sedimentary
    "greywacke": "hard_sedimentary",
    "argillite": "hard_sedimentary",
    "limestone": "hard_sedimentary",
    "chert": "hard_sedimentary",
    "dolomite": "hard_sedimentary",
    # pyroclastic / weak volcanic
    "tuff": "volcanic_soft",
    "scoria": "volcanic_soft",
    "ignimbrite": "volcanic_soft",   # matched units are unwelded pyroclastics
    "agglomerate": "volcanic_soft",
    # coherent volcanic
    "basalt": "volcanic_hard",
    "andesite": "volcanic_hard",
    "dacite": "volcanic_hard",
    "rhyolite": "volcanic_hard",
    "trachyte": "volcanic_hard",
    "dolerite": "volcanic_hard",
    # plutonic
    "granite": "plutonic",
    "granodiorite": "plutonic",
    "tonalite": "plutonic",
    "diorite": "plutonic",
    "monzonite": "plutonic",
    "monzodiorite": "plutonic",
    "syenite": "plutonic",
    "gabbro": "plutonic",
    "gabbronorite": "plutonic",
    "peridotite": "plutonic",
    "pyroxenite": "plutonic",
    "hornblendite": "plutonic",
    "serpentinite": "plutonic",
    # metamorphic
    "schist": "metamorphic",
    "semischist": "metamorphic",
    "greenschist": "metamorphic",
    "gneiss": "metamorphic",
    "orthogneiss": "metamorphic",
    "paragneiss": "metamorphic",
    "hornfels": "metamorphic",
    "marble": "metamorphic",
    "amphibolite": "metamorphic",
    "quartzite": "metamorphic",
    "metasediment": "metamorphic",
    "metavolcanic": "metamorphic",
    "metaplutonic": "metamorphic",
    "migmatite": "metamorphic",
    "mylonite": "metamorphic",
    "cataclasite": "metamorphic",
}

# rockclass fallback for rockgroups missing from the dict
ROCKCLASS_FALLBACK = {
    "felsic intrusive": "plutonic",
    "intermediate intrusive": "plutonic",
    "mafic intrusive": "plutonic",
    "ultramafic intrusive": "plutonic",
    "felsic igneous": "volcanic_hard",
    "mafic igneous": "volcanic_hard",
    "felsic extrusive": "volcanic_hard",
    "intermediate extrusive": "volcanic_hard",
    "mafic extrusive": "volcanic_hard",
    "volcanic": "volcanic_hard",
    "schist": "metamorphic",
    "gneiss": "metamorphic",
    "metamorphic": "metamorphic",
}

ERODIBILITY = {
    "plutonic": 1,
    "metamorphic": 1,
    "volcanic_hard": 1,
    "hard_sedimentary": 2,
    "soft_sedimentary": 3,
    "volcanic_soft": 3,
    "alluvium_gravel": 4,
    "unconsolidated_sand": 5,
}


def classify(df):
    """Vectorised lith_class + the rule that fired, from QMAP attributes."""
    rockgroup = df["rockgroup"].fillna("")
    rockclass = df["rockclass"].fillna("")
    mainrock = df["mainrock"].fillna("")
    simplename = df["simplename"].fillna("")

    lith = pd.Series("other", index=df.index, dtype="object")
    rule = pd.Series("unmapped", index=df.index, dtype="object")

    # 3) rockgroup dict, then rockclass fallback (lowest precedence)
    by_group = rockgroup.map(ROCKGROUP_MAP)
    by_class = rockclass.map(ROCKCLASS_FALLBACK)
    use_class = by_group.isna() & by_class.notna()
    lith[by_group.notna()] = by_group[by_group.notna()]
    rule[by_group.notna()] = "rockgroup_dict"
    lith[use_class] = by_class[use_class]
    rule[use_class] = "rockclass_fallback"

    # volcanic (extrusive-class) breccia is fragmental, not coherent lava
    volc_breccia = (rockgroup == "breccia") & rockclass.str.endswith("extrusive")
    lith[volc_breccia] = "volcanic_soft"
    rule[volc_breccia] = "breccia_volcanic"
    sed_breccia = (rockgroup == "breccia") & ~volc_breccia
    lith[sed_breccia] = "soft_sedimentary"
    rule[sed_breccia] = "breccia_sedimentary"

    # 2) basement clastics are indurated (greywacke terranes) whatever the
    # rockgroup says (basement sandstone/mudstone/conglomerate -> hard)
    basement = (simplename.str.startswith("Basement")
                & rockclass.isin(["clastic sediment", "chemical sediment",
                                  "sediment"]))
    lith[basement] = "hard_sedimentary"
    rule[basement] = "basement_override"

    # 1) surficial unconsolidated deposits (highest precedence). Verified:
    # simplename '... deposits' <=> rockclass clastic sediment/anthropic.
    surficial = simplename.str.endswith("deposits")
    sandy = surficial & (mainrock.isin(["sand", "peat"])
                         | rockgroup.isin(["sand", "peat"]))
    loose = surficial & ~sandy
    lith[sandy] = "unconsolidated_sand"
    rule[sandy] = "surficial_sand"
    lith[loose] = "alluvium_gravel"
    rule[loose] = "surficial_alluvium"

    return lith, rule


def _sanity_regions(out, region):
    """Printable regional shares for the documented sanity expectations."""
    xtab = pd.crosstab(region, out["lith_class"], normalize="index") * 100
    xtab_n = pd.crosstab(region, out["lith_class"])
    xtab.round(1).to_csv(QA_DIR / "d08_lith_x_region_pct.csv")
    checks = [
        ("Canterbury", ["alluvium_gravel", "unconsolidated_sand"],
         "gravel/alluvium + sand dominate"),
        ("West Coast", ["plutonic", "metamorphic"], "plutonic+metamorphic present"),
        ("Southland", ["plutonic", "metamorphic"], "plutonic+metamorphic (Fiordland)"),
        ("Auckland", ["soft_sedimentary", "volcanic_hard", "volcanic_soft"],
         "soft sedimentary + volcanic"),
        ("Northland", ["soft_sedimentary", "volcanic_hard", "volcanic_soft"],
         "soft sedimentary + volcanic"),
    ]
    print("\nregional sanity (share of region transects, %):")
    for reg, cls, note in checks:
        share = xtab.loc[reg, [c for c in cls if c in xtab.columns]].sum()
        print(f"  {reg:12s} {'+'.join(cls):45s} {share:5.1f}%  ({note})")
    print("\nlith_class x Region counts:")
    print(xtab_n.T.to_string())


def build():
    print(f"reading {QMAP_GPKG.name}:{QMAP_LAYER} ...")
    geol = gpd.read_file(QMAP_GPKG, layer=QMAP_LAYER, columns=SRC_COLS)
    assert geol.crs.to_epsg() == 2193
    base = base_gdf(columns=["UniqueID", "Region"])
    assert len(base) == 228538, f"unexpected base row count {len(base)}"

    def _one_row_per_point(joined_df, index):
        """Boundary points can hit 2+ polygons; keep the lowest polygon id
        (deterministic), selecting whole rows so attributes never mix."""
        joined_df = joined_df.sort_values("index_right", kind="stable")
        joined_df = joined_df[~joined_df.index.duplicated(keep="first")]
        return joined_df.reindex(index)

    # 1) direct polygon membership
    hit = gpd.sjoin(base, geol, how="left", predicate="intersects")
    hit = _one_row_per_point(hit, base.index)
    direct = hit["index_right"].notna()

    # 2) nearest polygon within 1 km for the misses
    miss = base.loc[~direct]
    near = gpd.sjoin_nearest(miss, geol, how="left",
                             max_distance=MAX_NEAREST_M,
                             distance_col="geol_dist_m")
    near = _one_row_per_point(near, miss.index)
    matched_near = near["index_right"].notna()

    n_direct, n_near = int(direct.sum()), int(matched_near.sum())
    n_unmatched = len(base) - n_direct - n_near
    print(f"direct hits    : {n_direct:7d} ({n_direct / len(base) * 100:.2f}%)")
    print(f"nearest <=1 km : {n_near:7d} ({n_near / len(base) * 100:.2f}%)")
    print(f"unmatched      : {n_unmatched:7d} "
          f"({n_unmatched / len(base) * 100:.2f}%)")

    hit["geol_dist_m"] = 0.0
    joined = pd.concat([hit.loc[direct], near.loc[matched_near]]).reindex(
        base.index)
    joined["UniqueID"] = base["UniqueID"]
    joined.loc[joined["index_right"].isna(), "geol_dist_m"] = np.nan

    # QA: distinct rockgroup x rockclass among matched transects
    rg = (joined.dropna(subset=["index_right"])
          .groupby(["rockgroup", "rockclass"], dropna=False)
          .size().rename("n_transects").reset_index()
          .sort_values("n_transects", ascending=False))
    rg.to_csv(QA_DIR / "d08_rockgroups.csv", index=False)
    print(f"\ndistinct rockgroups among matched: {rg['rockgroup'].nunique()} "
          f"(-> qa/d08_rockgroups.csv)")

    # classify
    lith, rule = classify(joined)
    matched = joined["index_right"].notna()
    lith[~matched] = np.nan
    rule[~matched] = np.nan
    joined["lith_class"] = lith
    joined["erodibility_ord"] = lith.map(ERODIBILITY).astype("Int8")
    joined["geol_age_ma"] = (joined["absmin_ma"] + joined["absmax_ma"]) / 2.0

    # QA: the mapping as actually applied (rockgroup x rule -> class)
    mapping = (joined.loc[matched]
               .assign(rule=rule[matched])
               .groupby(["rockgroup", "rule"])
               .agg(n_transects=("UniqueID", "size"),
                    lith_class=("lith_class", "first"))
               .reset_index()
               .sort_values("n_transects", ascending=False))
    mapping.to_csv(QA_DIR / "d08_lith_mapping.csv", index=False)

    n_other = int((lith[matched] == "other").sum())
    pct_mapped = (lith[matched] != "other").mean() * 100
    print(f"matched transects mapped to a lith_class: {pct_mapped:.3f}% "
          f"(require >=99%); left 'other': {n_other}")
    if n_other:
        print(joined.loc[matched & (lith == "other"),
                         ["rockgroup", "rockclass", "mainrock", "simplename"]]
              .value_counts().to_string())
    assert pct_mapped >= 99.0

    counts = joined["lith_class"].value_counts(dropna=False)
    counts.rename_axis("lith_class").rename("n").to_csv(
        QA_DIR / "d08_lith_class_counts.csv")
    print("\nlith_class counts:")
    print(counts.to_string())

    qa_join(joined["geol_dist_m"], "d08_geology", MAX_NEAREST_M)
    _sanity_regions(joined, base["Region"])

    # optional crosstab against d07 shoreline typology
    d07 = DRIVER_DATA / "d07_typology.parquet"
    if d07.exists():
        st = pd.read_parquet(d07, columns=["UniqueID", "SHORE_TYPE"])
        m = joined.merge(st, on="UniqueID", how="left")
        xt = pd.crosstab(m["lith_class"], m["SHORE_TYPE"].fillna("(null)"))
        xt.to_csv(QA_DIR / "d08_lith_x_shoretype.csv")
        beach = m["SHORE_TYPE"].str.startswith(("b", "fdb", "pb"), na=False)
        rock = m["SHORE_TYPE"].str.startswith(("r", "cp"), na=False)
        soft_cls = m["lith_class"].isin(["unconsolidated_sand",
                                         "alluvium_gravel"])
        hard_cls = m["lith_class"].isin(["hard_sedimentary", "volcanic_hard",
                                         "plutonic", "metamorphic"])
        print("\nlith_class x SHORE_TYPE association "
              "(-> qa/d08_lith_x_shoretype.csv):")
        print(f"  beach shore types (b*/fdb*/pb*, n={int(beach.sum())}) on "
              f"sand/gravel classes: {soft_cls[beach].mean() * 100:.1f}%")
        print(f"  rock/cliff types (r/cp, n={int(rock.sum())}) on hard "
              f"classes: {hard_cls[rock].mean() * 100:.1f}% "
              "(caveat: at MHW these points sit on the mapped Holocene "
              "beach-fringe polygon fronting the cliff)")
    else:
        print("d07_typology.parquet not found - skipping SHORE_TYPE crosstab")

    out_cols = ["UniqueID", "lith_class", "erodibility_ord", "rockgroup",
                "rockclass", "mainrock", "simplename", "geol_age_ma",
                "geol_dist_m"]
    out = pd.DataFrame(joined[out_cols]).reset_index(drop=True)
    assert len(out) == 228538
    return write_driver(out, "d08_geology")


if __name__ == "__main__":
    build()
