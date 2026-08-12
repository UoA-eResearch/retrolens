# retrolens

An alternative, Leaflet based web interface for retrolens (http://retrolens.nz/),
plus the NZCCD (NZ Coastal Change Dataset) rates pipeline and analyses.

## Drivers of coastal change

`drivers/` + `Drivers_*.ipynb` implement the national correlation analysis
between NZCCD change metrics (WLR/NSM/SCE at 228,538 transects) and candidate
drivers: WHACS wave climate, CoastSat beach slope, NZ SeaRise VLM, LiDAR
backshore elevation, FES2022b tidal range, REC2 rivers/rainfall, NZCCD coastal
typology, QMAP 1:250k geology and GeoNet earthquakes — with a pre/post-1990
epoch module.

- Run order: `Drivers_00` → `01`–`09` (any order) → `20` → `30`/`31`/`40` →
  `41`/`32`. Every notebook is cache-aware: it loads
  `driver_data/*.parquet` when present and only recomputes when missing.
- Heavy steps: `python3 -m drivers.whacs` (~6 min, 32 cores) and
  `python3 -m drivers.elevation` (~25 min) — both cached.
- Data conventions (sign, alongshore axis, transect orientation):
  `driver_data/qa/CONVENTIONS.md`. Per-stage QA lands in `driver_data/qa/`,
  statistics in `driver_data/stats/`, figures in `figures/`.
- Interactive map: `drivers.html` (Leaflet + glify, reads
  `driver_data/drivers_map.parquet` client-side; pick a variable to colour by).

External inputs live on the data mounts (`/mnt/WHACS`, `/mnt/CoastSat`,
`/mnt/rivers`, `/mnt/Bruunrule_Yaxiong`); QMAP + GeoNet are fetched into
`driver_data/` by the `Drivers_08`/`09` stages.
