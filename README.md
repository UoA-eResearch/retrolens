# retrolens
An alternative, Leaflet based web interface for retrolens (http://retrolens.nz/)

## Quick start

New to coding, VS Code, or Git? Start with [GETTING_STARTED.md](GETTING_STARTED.md), which covers installing everything, setting up the environment, creating your own branch, running the workflow, and pushing your work.

The shoreline update workflow lives on the `nzccdv2` branch. After cloning, run `git checkout nzccdv2`, then create your own branch from there (`git checkout -b yourname`). Nobody works directly on `main` or `nzccdv2`.

To add newly detected shorelines into the NZCCD workflow:

1. Open [new_transects.ipynb](new_transects.ipynb) and run the notebook to discover new shoreline files, resolve AOIs and baselines, and generate transects.
2. Open [new_uncy.ipynb](new_uncy.ipynb) and run it with the same shoreline selection settings to calculate uncertainty values.
3. Open [new_DSAS.ipynb](new_DSAS.ipynb) and run it to build the updated NZCCD dataset and produce DSAS outputs.

Expected outputs are written to `DataUpdatev2/<RUN_OWNER>/`, including transects, an uncertainty summary, and DSAS result layers. Set `RUN_OWNER` to your own name in all three notebooks so that runs of the same area by different people can't overwrite each other. Output filenames are also tagged with the area/date you selected, and are **not** committed to Git. The maintainer combines everyone's folders with [NZCCDv2_merge.ipynb](NZCCDv2_merge.ipynb).

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

- Shoreline shapefiles stored under folders such as Z:\MaxarImagery\HighFreq or Z:\Retrolens, following a structure like Region/AOI/Shorelines/*.shp.
- AOI polygon shapefiles stored under Z:\MaxarImagery\HighFreq\AOI.
- Baseline shapefiles stored under Z:\DSAS\BaselineTemplate\Baselines.
- Route shapefiles stored under Z:\DSAS\BaselineTemplate\Routes or the local test data folder.
- A base dataset file such as Data for testing/NZCCDv1.shp, which is used as the starting point for the DSAS update.

The search logic is controlled by the same parameters in the first notebook cells of the transect and uncertainty workflows:

- cutoff_date
- search_roots
- search_mode
- target_aoi
- target_region

Use the same values across the notebooks so the set of selected shoreline files is consistent.

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
   - Review the summary output and save the uncertainty summary to DataUpdatev2/new_uncy_summary.csv.

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
- An uncertainty summary for the newly processed shorelines, with the calculated uncertainty values and the source information used for each shoreline.
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
