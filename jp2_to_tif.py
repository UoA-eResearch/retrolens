#!/usr/bin/env python3

from glob import glob
import os
import re
from tqdm import tqdm
import rasterio as rio

for filename in tqdm(glob("/mnt/coastal_raw/*.jp2")):
    f = filename.replace("1TorrentBay", "TorrentBay").replace("TaieriBech_Mouth", "TaieriBeach_Mouth")
    site = re.search('(\w+?)_(\d|LDS)', f).group(1)
    os.makedirs(f"/mnt/coastal/{site}", exist_ok=True)
    f = os.path.basename(f).replace(".jp2", "")
    outfile = f"/mnt/coastal/{site}/{f}.tif"
    print(f"{filename} -> {outfile}")
    if os.path.isfile(outfile):
        print(f"{outfile} exists, skipping")
        continue
    src = rio.open(filename)
    kwargs = {**src.profile, **{"driver": "GTiff", "compress": "LZW", "tiled": True}}
    with rio.open(outfile, "w", **kwargs) as dst:
        dst.write(src.read())