#!/usr/bin/env python3
import solaris.data.coco as coco

coco_geojson = coco.geojson2coco(
    "training_tiles",
    "training_tiles",
    recursive=True,
    output_path=f"coco.json",
    category_attribute="class",
    explode_all_multipolygons=True,
    verbose=2,
)