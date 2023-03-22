#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
import glob
from tqdm import tqdm
import os

def check_filename(filename):
    filename = os.path.splitext(os.path.basename(filename))[0]
    bits = filename.split("_")
    return len(bits) > 1 and len(bits[1]) == len("14MAR1948")

files = []
for file in glob.iglob("/mnt/research/ressci201900060-RNC2-Coastal/Retrolens/**/Shorelines/*.shp", recursive=True):
    print(file)
    if check_filename(file):
        df = gpd.read_file(file)
        df["filename"] = file.replace("/mnt/research/ressci201900060-RNC2-Coastal/Retrolens/", "")
        files.append(df)

df = gpd.GeoDataFrame(pd.concat(files)).to_crs(epsg=4326)
df.to_file("shorelines.geojson")