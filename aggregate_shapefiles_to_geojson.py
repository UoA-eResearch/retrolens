#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
import glob
from tqdm import tqdm
import os
import re

def check_filename(filename):
    filename = os.path.splitext(os.path.basename(filename))[0]
    return re.search(r'\d\w+\d{4}', filename)

files = []
for file in glob.iglob("/mnt/research/ressci201900060-RNC2-Coastal/Retrolens/**/Shorelines/*.shp", recursive=True):
    print(file)
    if check_filename(file):
        df = gpd.read_file(file)
        df["filename"] = file.replace("/mnt/research/ressci201900060-RNC2-Coastal/", "")
        files.append(df)

for file in glob.iglob("/mnt/research/ressci201900060-RNC2-Coastal/MaxarImagery/HighFreq/**/Shorelines/*.shp", recursive=True):
    print(file)
    if check_filename(file):
        df = gpd.read_file(file)
        df["filename"] = file.replace("/mnt/research/ressci201900060-RNC2-Coastal/", "")
        files.append(df)

df = gpd.GeoDataFrame(pd.concat(files)).to_crs(epsg=4326)
df.to_file("shorelines.geojson")