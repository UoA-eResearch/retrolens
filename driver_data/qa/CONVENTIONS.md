# NZCCD conventions (empirically verified 2026-08-07)

- **Sign**: positive WLR/NSM/EPR/LRR = accretion (seaward movement); negative =
  erosion. Verified by mapping earliest-shoreline positions back onto transect
  geometry: NSM > +50 m transects have their earliest shoreline on land today
  (median elev +5.05 m, 92% > 2 m); NSM < −50 m transects at sea level
  (median −0.16 m, 11% > 2 m). n=300 each.
- **Distance origin**: DSAS.ipynb measures Distance from `shapely.get_point(t, -1)`
  (last vertex). Transect vertex order is NOT uniform nationally: the robust
  per-transect determination in d04 (valid-DEM fraction + mean elevation of the
  two sides adjacent to the latest shoreline) finds the LAST vertex landward for
  86% of transects and the FIRST for 14%. Never assume a fixed landward end.
  (A naive endpoint-validity test misleads because some LiDAR surveys map water
  as valid ~0 m elevation.)
- **Alongshore axis**: published `TCD` resets per mapped section (max ~67 km).
  The national alongshore ordering is embedded in UniqueID: first 3 digits =
  island code (100 NI, 101 Waiheke, 102 Matakana, 200 SI, 201 Jackett,
  202 Moturoa/Rabbit, 203 Rakiura), last 9 digits = route chainage in cm
  (`chain_m = (UniqueID % 1e9)/100`, median step 10.01 m). Bootstrap blocks =
  `island * 1e7 + chain_m // 2000`.
- **CoastSat-intersects parquet** uses the OPPOSITE sign convention (origin at
  first vertex) — reconcile before any comparison.
