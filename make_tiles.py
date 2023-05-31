#!/usr/bin/env python3

import geopandas as gpd # Geospatial data operations
import rasterio as rio # Geospatial imagery manipulation
import pandas as pd # Tabular data
import os
from tqdm.auto import tqdm # Progress bars
import shapely # Polygon operations
import solaris.tile as tile # Tile splitting
import solaris.data.coco as coco
import contextlib
import io
import traceback
from termcolor import cprint
from tqdm.contrib.concurrent import thread_map, process_map
tqdm.pandas()

def line_to_split_bbox(geo):
    """ Take a polyline, gets its bounding box as a rectangular polygon, and splits the polygon by the polyline """
    bounding_box = geo.envelope
    split_bbox = shapely.ops.split(bounding_box, geo)
    return split_bbox

def match_to_tiles(match):
    """ Takes a match between a shapefile and image, and tiles it """
    try:
        name = os.path.splitext(os.path.basename(match.filename))[0]
        image_filename = match.matched_image
        folder = "training_tiles/" + os.path.splitext(match.filename)[0].replace("Retrolens", "LDS").replace("Shorelines/", "")
        
        match_gdf = gpd.read_file(match.filename)
        if not len(match_gdf):
            return
        split_bboxes = match_gdf.geometry.explode(index_parts=True).apply(line_to_split_bbox).explode(index_parts=True).reset_index()
        split_bboxes["area"] = split_bboxes.area
        split_bboxes = split_bboxes[split_bboxes.area > 1e5]
        if not len(split_bboxes):
            return
        relevant_coastline = coastline.clip(split_bboxes.total_bounds)
        split_bboxes["area_inland"] = split_bboxes.clip(relevant_coastline).area
        split_bboxes["fraction_inland"] = split_bboxes.area_inland / split_bboxes.area
        split_bboxes["class"] = split_bboxes.fraction_inland.apply(lambda f: "land" if f > .5 else "sea")
        
        geojson_filename = f"polygon_annotations/{name}.geojson"
        split_bboxes.to_file(geojson_filename, driver='GeoJSON')

        image = rio.open(image_filename)
        # Fix for files missing CRS (instead using GCP CRS)
        # See https://github.com/rasterio/rasterio/issues/1916
        if not image.crs and image.gcps:
            print(image_filename)
            image_filename = "temp/" + os.path.basename(image_filename)
            with rio.open(image_filename, "w", **image.profile) as dst:
                dst.write(image.read())
                dst.transform = rio.transform.from_gcps(image.gcps[0])
                dst.crs = image.gcps[1]
                cprint(f"Wrote to {image_filename} with corrected CRS", "magenta")

        for bounding_box in tqdm(split_bboxes.envelope):
            with contextlib.redirect_stdout(io.StringIO()):
                raster_tiler = tile.raster_tile.RasterTiler(
                    dest_dir=folder,  # the directory to save images to
                    src_tile_size=(800, 800),  # the size of the output chips
                    verbose=False,
                    aoi_boundary=bounding_box,
                )
                raster_bounds_crs = raster_tiler.tile(
                    image_filename,
                    restrict_to_aoi=True,
                    nodata_threshold=.5,
                    dest_fname_base=name
                )
                vector_tiler = tile.vector_tile.VectorTiler(
                    dest_dir=folder,
                    verbose=False
                )
                vector_tiler.tile(
                    geojson_filename,
                    tile_bounds=raster_tiler.tile_bounds,
                    tile_bounds_crs=raster_bounds_crs,
                    dest_fname_base=name,
                )
    except Exception as e:
        cprint(f"ERROR: {e} for {image_filename}", "red", attrs=["blink"])
        cprint(traceback.format_exc(), "red")

def check_folder(filename):
    folder = "training_tiles/" + os.path.splitext(filename)[0].replace("Retrolens", "LDS").replace("Shorelines/", "")
    print(folder)
    return os.path.isdir(folder) and len(os.listdir(folder)) > 0

coastline = gpd.read_file("lds-nz-coastlines-and-islands-polygons-topo-150k-FGDB.zip!nz-coastlines-and-islands-polygons-topo-150k.gdb")

df = pd.read_csv("LDS_matches.csv")
#df = df[df.match_score == 100]
df = df[~df.filename.apply(check_folder)]
df.progress_apply(match_to_tiles, axis=1)
# Process things in parallel
#process_map(match_to_tiles, df.itertuples(), max_workers=4, total=len(df))