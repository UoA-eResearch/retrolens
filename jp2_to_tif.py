#!/usr/bin/env python3

from glob import glob
import os
import re
from tqdm import tqdm
from osgeo import gdal

files = glob("/mnt/coastal_raw/Stack/*.jp2")
sites = set()
for f in files:
    match = re.search('(\w+?)_(\d|LDS)', f)
    sites.add(match.group(1))
sites = sorted(sites)
print(f"Found {len(sites)} sites: {sites}")

for site in tqdm(sites):
    os.makedirs(f"/mnt/coastal/{site}", exist_ok=True)
    files_for_site = [f for f in files if f"/{site}_" in f]
    for f in tqdm(files_for_site):
        ds = gdal.Open(f)
        outfile = f"/mnt/coastal/{site}/{os.path.splitext(os.path.basename(f))[0]}.tif"
        ds = gdal.Translate(outfile, ds)
        ds = None