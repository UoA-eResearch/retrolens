#!/usr/bin/env python3

from glob import glob
import os
import re
from tqdm import tqdm
from osgeo import gdal

options = gdal.TranslateOptions(
    format = 'GTiff',
    creationOptions = ['TILED=YES', 'COMPRESS=LZW']
)

for filename in tqdm(glob("/mnt/coastal_raw/*.jp2")):
    f = filename.replace("1TorrentBay", "TorrentBay").replace("TaieriBech_Mouth", "TaieriBeach_Mouth")
    site = re.search('(\w+?)_(\d|LDS)', f).group(1)
    os.makedirs(f"/mnt/coastal/{site}", exist_ok=True)
    f = os.path.splitext(os.path.basename(f))[0]
    outfile = f"/mnt/coastal/{site}/{f}.tif"
    print(f"{filename} -> {outfile}")
    if os.path.isfile(outfile):
        print(f"{outfile} exists, skipping")
        continue
    ds = gdal.Open(filename)
    ds = gdal.Translate(outfile, ds, options=options)
    ds = None