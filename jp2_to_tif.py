#!/usr/bin/env python3

from glob import glob
import os
import re
from tqdm import tqdm
import shutil
import rasterio as rio

for filename in tqdm(glob("/mnt/coastal_raw/**/*.jp?", recursive=True)):
    f = filename.replace("1TorrentBay", "TorrentBay").replace("TaieriBech_Mouth", "TaieriBeach_Mouth").replace("/Stack", "").replace("coastal_raw", "coastal")
    dirname = os.path.dirname(f)
    os.makedirs(dirname, exist_ok=True)
    f = os.path.splitext(os.path.basename(f))[0]
    outfile = f"{dirname}/{f}.tif"
    print(f"{filename} -> {outfile}")
    if os.path.isfile(outfile):
        print(f"{outfile} exists, skipping")
        continue
    src = rio.open(filename)
    kwargs = {**src.profile, **{"driver": "GTiff", "compress": "LZW", "tiled": True}}
    try:
        with rio.open(outfile, "w", **kwargs) as dst:
            dst.write(src.read())
    except Exception as e:
        print(e)

for filename in tqdm(glob("/mnt/coastal_raw/**/*.tif", recursive=True)):
    outfile = filename.replace("/Stack", "").replace("coastal_raw", "coastal")
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    print(f"{filename} -> {outfile}")
    if os.path.isfile(outfile):
        print(f"{outfile} exists, skipping")
        continue
    shutil.copy(filename, outfile)
