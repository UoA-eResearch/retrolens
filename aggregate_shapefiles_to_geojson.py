#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
import glob
from tqdm import tqdm
import os
import re
from tqdm.contrib.concurrent import thread_map, process_map

def check_filename(filename):
    # This regex only matches shapefiles that contain something date-like in their names
    match = re.search(r'/Shorelines/\w+\d\w+\d{4}\w*.shp$', filename)
    return bool(match)

# A complete filelist of the MaxarImagery & Retrolens folders, generated with the unix command:
# find MaxarImagery/ Retrolens/ > ressci201900060-RNC2-Coastal_MaxarImagery_Retrolens_filelist.txt
filelist = pd.read_csv("ressci201900060-RNC2-Coastal/Nick/ressci201900060-RNC2-Coastal_MaxarImagery_Retrolens_filelist.txt", header=None).iloc[:,0]
df = filelist[filelist.apply(check_filename)].to_frame(name="filename")

def read(filename):
    df = gpd.read_file(filename)
    df["filename"] = filename
    return df

df = gpd.GeoDataFrame(pd.concat(process_map(read, df.filename))).to_crs(epsg=4326)
df.to_file("shorelines.geojson")