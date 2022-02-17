#!/usr/bin/env python3

from glob import glob
import os
import re
from tqdm import tqdm
import rasterio as rio

for filename in tqdm(glob("/mnt/coastal/*/*.tif")):
    with rio.open(filename) as ds:
        if not {**ds.profile, **{"driver": "GTiff", "tiled": True, "compress": "lzw"}} == ds.profile:
            print(ds.profile)
