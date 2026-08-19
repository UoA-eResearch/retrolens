# retrolens
An alternative, Leaflet based web interface for retrolens (http://retrolens.nz/)

## Quick start

New to coding, VS Code, or Git? Start with [GETTING_STARTED.md](GETTING_STARTED.md), which covers installing everything, setting up the environment, creating your own branch, running the workflow, and pushing your work.

The shoreline update workflow lives on the `nzccdv2` branch. After cloning, run `git checkout nzccdv2`, then create your own branch from there (`git checkout -b yourname`). Nobody works directly on `main` or `nzccdv2`.

To add newly detected shorelines into the NZCCD workflow:

1. Open [new_transects.ipynb](new_transects.ipynb) and run the notebook to discover new shoreline files, resolve AOIs and baselines, and generate transects.
2. Open [new_uncy.ipynb](new_uncy.ipynb) and run it with the same shoreline selection settings to calculate uncertainty values.
3. Open [new_DSAS.ipynb](new_DSAS.ipynb) and run it to build the updated NZCCD dataset and produce DSAS outputs.

Expected outputs are written to `DataUpdatev2/<RUN_OWNER>/`, including transects, row-level uncertainty reports, and DSAS result layers. Set `RUN_OWNER` to your own name in all three notebooks so that runs of the same area by different people can't overwrite each other. Output filenames are also tagged with the area/date you selected, and are **not** committed to Git. The maintainer combines everyone's folders with [NZCCDv2_merge.ipynb](NZCCDv2_merge.ipynb).

## New shoreline update workflow

The new shoreline workflow adds recently detected shoreline shapefiles into the NZCCDv1-based processing chain by running three notebooks in sequence:

- [new_transects.ipynb](new_transects.ipynb) to discover new shoreline files, resolve AOI and baseline inputs, and generate transects.
- [new_uncy.ipynb](new_uncy.ipynb) to calculate uncertainty values for the same shoreline set.
- [new_DSAS.ipynb](new_DSAS.ipynb) to update the NZCCDv1 dataset, append new shoreline features, and run DSAS-style rate calculations.

### Goal

This workflow is used when new shoreline shapefiles have been produced for one or more AOIs and need to be incorporated into the NZCCD workflow. The process:

1. Finds shoreline files in the expected folder structure under the configured search roots.
2. Matches each shoreline to its AOI polygon and baseline coverage.
3. Builds transects for the AOIs that have valid baselines.
4. Calculates uncertainty values for the selected shorelines.
5. Appends the new shoreline data into an updated NZCCD dataset and runs DSAS calculations.

### Inputs and assumptions

The notebooks assume the following data are available:

- Shoreline shapefiles stored under `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Shorelines\*.shp` or `Z:\Retrolens\<Region>\<AOI>\Shorelines\*.shp`.
- Maxar mosaics are under `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Stack\`; Retrolens mosaics are under `Z:\Retrolens\<Region>\<AOI>\Stack\`. Their `.jp2.aux.xml` sidecars provide pixel resolution.
- AOI polygon shapefiles stored under Z:\MaxarImagery\HighFreq\AOI.
- Baseline shapefiles stored under Z:\DSAS\BaselineTemplate\Baselines.
- Route shapefiles stored under Z:\DSAS\BaselineTemplate\Routes or the local test data folder.
- A base dataset file such as Data for testing/NZCCDv1.shp, which is used as the starting point for the DSAS update.

The search logic is controlled by the same parameters in the first notebook cells of all three workflows:

- cutoff_date
- search_roots
- search_mode
- target_aoi
- target_region

Use the same values across the notebooks so the set of selected shoreline files is consistent. `target_aoi` and `target_region` may be strings or lists. Matching is case- and punctuation-insensitive and checks both the AOI folder and the AOI part of the shoreline filename. The cutoff filters file modification time; it is not the shoreline observation date.

### Recommended run order

1. Run [new_transects.ipynb](new_transects.ipynb)
   - Review the matched shoreline files.
   - Confirm AOI polygons are found.
   - Confirm each AOI has baseline overlap.
   - Generate transects and save the output to DataUpdatev2/new_transects.shp.
   - Check that Unique_ID values are unique and that required columns are present.

2. Run [new_uncy.ipynb](new_uncy.ipynb)
   - Reuse the same shoreline selection logic.
   - Calculate uncertainty values for the selected shoreline files.
   - Review `new_uncy_row_report.csv` and `new_uncy_row_missing.csv`. This notebook writes CSV reports only; it does not modify source shoreline shapefiles.

3. Run [new_DSAS.ipynb](new_DSAS.ipynb)
   - The notebook cuts NZCCDv1 down to the AOIs matched by the current selection, dropping everything outside the run.
   - It adds the newly selected shoreline features.
   - It uses the generated transects and the uncertainty summary to run DSAS calculations.
   - Outputs are written to `DataUpdatev2/<RUN_OWNER>/` and tagged with the selection that produced them, so neither two people nor two areas ever write to the same file:
     - `NZCCDv2_<tag>.shp`
     - `ratesv2_<tag>.shp`
     - `intersectsv2_<tag>.shp`
     - `new_dsas_exclusions_<tag>.csv`

### Output naming

The tag comes from the selection settings used to find the new shorelines:

| search_mode | Tag | Example filename |
| --- | --- | --- |
| `date` | `since<YYYYMMDD>` | `NZCCDv2_since20240718.shp` |
| `aoi` | AOI name | `NZCCDv2_MedlandsBeach.shp` |
| `aoi_in_date_range` | AOI name + date | `NZCCDv2_MedlandsBeach_since20240718.shp` |
| `region` | region name | `NZCCDv2_Auckland.shp` |
| `region_in_date_range` | region name + date | `NZCCDv2_Auckland_since20240718.shp` |

### Expected outputs

After the full workflow completes, the updated outputs should include:

- A new transect layer describing the AOI-specific transects, including fields such as region, AOI, route name, MEAS, DIST, and Unique_ID.
- `new_uncy_row_report.csv`, with one uncertainty record per shoreline feature and provenance for every assigned value.
- `new_uncy_row_missing.csv`, listing rows that could not be resolved.
- An NZCCDv2-style shoreline dataset covering only the AOIs in this run: the newly added shoreline features alongside the NZCCDv1 rows for those same AOIs. Coastline outside the run is deliberately dropped so per-area outputs can be recombined later without conflicting.
- An intersects layer, where each record is a shoreline-transect intersection point. These points are attached to the transect by Unique_ID and carry the shoreline geometry and the associated timing/position information needed for later analysis.
- A rates layer, where each record is a transect-level DSAS result. This layer stores the calculated shoreline change rates and related statistics attached to each transect, so users can query change-rate values by transect rather than by shoreline feature alone.
- A CSV report listing shoreline files excluded from DSAS for reasons such as missing data, poor overlap, or no successful transect intersections.

### Quality checks

The notebooks include several checks to catch common issues before the workflow proceeds:

- Missing AOI polygons or missing baseline overlap.
- No transects generated for an AOI.
- Duplicate Unique_ID values.
- Missing required transect columns such as MEAS, DIST, and Unique_ID.
- Shorelines that are not eligible for DSAS due to missing uncertainty or date values.

### Combining everyone's work

Shapefiles are binary, so Git cannot merge them: if two branches both change the same shapefile, one side's work is lost at merge time. Per-area outputs are therefore kept out of Git (`DataUpdatev2/` is ignored) and recombined with geopandas instead.

[NZCCDv2_merge.ipynb](NZCCDv2_merge.ipynb) collects the tagged `NZCCDv2_*`, `ratesv2_*` and `intersectsv2_*` files from one or more folders, stitches them back onto NZCCDv1, de-duplicates, and writes a single national dataset. It is run by the project maintainer, not by individual contributors.

### Practical notes

- Keep the search mode and AOI/region filters consistent between the notebooks.
- If an AOI is unresolved, inspect the AOI path matching logic before continuing.
- If no baseline overlap is found for an AOI, the transect generation step will skip it.
- Review the exclusion files after DSAS runs so that any missing or problematic shoreline inputs are easy to identify.

## Pipeline reference

### Source files and locations

The notebooks read source data from the mapped `Z:` drive and write derived run products under `DataUpdatev2/<RUN_OWNER>/`.

| Input | Location and use |
| --- | --- |
| Shoreline features | `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Shorelines\*.shp` and `Z:\Retrolens\<Region>\<AOI>\Shorelines\*.shp` |
| Maxar imagery | `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Stack\*.jp2`/`*.tif` plus `.aux.xml` metadata |
| Retrolens imagery | `Z:\Retrolens\<Region>\<AOI>\Stack\*.jp2`/`*.tif` plus `.aux.xml` metadata |
| AOI polygons | `Z:\MaxarImagery\HighFreq\AOI\` |
| Baselines | `Z:\DSAS\BaselineTemplate\Baselines\` |
| Routes | `Z:\DSAS\BaselineTemplate\Routes\` or `Data for testing/Routes/` |
| NZCCDv1 baseline | `Data for testing/NZCCDv1.shp` and its companion files |

The notebooks do not copy source shapefiles or imagery into the repository. A shapefile is a group of companion files (`.shp`, `.dbf`, `.shx`, `.prj`, and sometimes `.cpg`/`.xml`) that must remain together.

### Target search

All three notebooks share `cutoff_date`, `search_roots`, `search_mode`, `target_aoi`, `target_region`, and `RUN_OWNER`. The five modes are `date`, `aoi`, `aoi_in_date_range`, `region`, and `region_in_date_range`. AOI and region settings may be lists. Matching is normalized for case and punctuation and checks the AOI folder plus the filename's AOI stem. The cutoff is based on the shapefile modification time; the shoreline observation date is resolved separately from its attributes.

### Transects and Unique_ID

`new_transects.ipynb` resolves each selected AOI polygon, finds the regional baseline, filters the baseline to the AOI, selects the route with the greatest AOI overlap, and generates transects at 10 m spacing. It writes `DataUpdatev2/<RUN_OWNER>/new_transects.shp` and the run report `new_transects.csv`.

Each transect ID is 12 digits:

```text
3-digit route code + 9-digit rounded centimetres along route
```

The route codes are `100` North Island, `101` Waiheke Island, `102` Matakana Island, `200` South Island, `201` Jackett Island, `202` Moturoa/Rabbit Island, and `203` Rakiura/Stewart Island. `MEAS` is distance along the route in metres; `DIST` is `round(MEAS * 100)` in centimetres. If projected transects collapse to the same centimetre, duplicate distances are nudged upward, first within an AOI and then between AOIs sharing a route. Adjustments are logged in `new_transects.csv`; QA checks require unique 12-digit IDs.

### Uncertainty rules

`new_uncy.ipynb` processes every shoreline feature row, including rows from merged multi-date shapefiles. It writes reports only; it does not write uncertainty fields back to source shoreline shapefiles.

For each row, date precedence is `DSAS_Date` attribute, then `Date` attribute, then filename fallback. Source precedence is the `Source` attribute, normalized so `LZ`/`LINZ` become `LDS`, `MAXAR` becomes `MAX`, and Retrolens aliases become `RL`. If there is no source attribute and the date year is a configured LDS survey year, the row is treated as LDS. Folder location is only the final source fallback.

`Pixel_ER` precedence is:

1. `Pixel_ER`, `Pixel_Er`, or `pixel_er` in the row attribute table.
2. For `MAX`, exact-date mosaic in the Maxar `Stack` folder.
3. For `RL`, exact-date mosaic in the Retrolens `Stack` folder; if none exists, nearest dated Retrolens mosaic within 92 days.
4. Pixel size from `.jp2.aux.xml` GML metadata, with JP2 header/rasterio fallbacks and degree-to-metre conversion.
5. For `LDS`/`LZ`, no mosaic is expected: 1999/2000/2003 use `2.5 m`, 2012 uses `0.5 m`, 2017/2020/2022/2024 use `0.075 m`, otherwise the configured LDS default is used.

`Georef_ER` uses the row attribute first. If absent, RL gets photoscale from the AOI CSV beside the Stack/Shorelines folder and assigns `2.09`, `2.43`, or `2.90` by scale; MAX is `1.17`; LDS/LZ is `0`. `CPS` maps to `Dig_ER` as `{1: 0.43, 2: 0.73, 3: 0.97, 4: 2.07, 5: 8.59}`. Missing or invalid CPS defaults to `1`.

The total is:

```text
Total_UNCY = sqrt(Pixel_ER^2 + Georef_ER^2 + Dig_ER^2)
```

`new_uncy_row_report.csv` contains date/source provenance, all three components, total uncertainty, and ready/flagged status. `new_uncy_row_missing.csv` contains unresolved rows. The older `new_uncy_summary.csv` and `new_uncy_missing.csv` are legacy file-level reports and are not the authoritative row-level input.

### DSAS calculations

`new_DSAS.ipynb` repeats the target search, loads `new_transects.shp`, and applies `new_uncy_row_report.csv` by source file and geometry to build a memory-bounded shoreline table. It retains each row's `DSAS_Date`/`Date`, so merged files are not reduced to one file-level date.

For each transect, it intersects all dated shoreline rows, selects one intersection point per shoreline, sorts points by date, and requires at least three observations. It calculates `NSM` (first-to-last movement), `SCE` (maximum separation), `EPR` (NSM divided by elapsed years), `LRR` (ordinary least-squares rate with confidence interval, standard error and R-squared), `EPRunc` (endpoint uncertainty over duration), and `WLR` (weighted least-squares using `1 / Total_UNCY^2` when every observation has uncertainty). Missing dates exclude rows; missing uncertainty prevents weighted statistics but does not prevent unweighted rates.

The rates layer is transect-level. The intersections layer is one point per transect/shoreline observation and retains its date, distance, uncertainty, and rate fields. The exclusions CSV records files or observations that could not be used.
