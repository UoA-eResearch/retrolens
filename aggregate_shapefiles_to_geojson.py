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

import platform
if platform.system() == "Windows":
  prefix = "Z:/"
else:
  prefix = "ressci201900060-RNC2-Coastal/"

# A complete filelist of the MaxarImagery & Retrolens folders, generated with the unix command:
# find MaxarImagery/ Retrolens/ > ressci201900060-RNC2-Coastal_MaxarImagery_Retrolens_filelist.txt
filelist = pd.read_csv(prefix + "/Nick/ressci201900060-RNC2-Coastal_MaxarImagery_Retrolens_filelist.txt", header=None).iloc[:,0]
df = filelist[filelist.apply(check_filename)].to_frame(name="filename")

def read(filename):
    df = gpd.read_file(prefix + filename)
    df["filename"] = filename
    return df

df = gpd.GeoDataFrame(pd.concat(thread_map(read, df.filename))).to_crs(epsg=4326)
df.to_file("shorelines.geojson")