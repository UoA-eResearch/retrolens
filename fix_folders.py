#!/usr/bin/env python3

from glob import glob
import os

with open("stack_files_clipped.txt") as f:
    original_filenames = f.readlines()
print(original_filenames)

files = glob("/mnt/coastal/*/*.*")
print(files)

for f in files:
    print(f)
    try:
        o = [o for o in original_filenames if os.path.basename(f).split(".")[0] in o][0]
    except:
        pass
    bits = o.split("/")
    region = bits[3]
    name = bits[4]
    print(region, name)
    os.makedirs(f"/mnt/coastal/{region}/{name}/", exist_ok=True)
    new_filename = f"/mnt/coastal/{region}/{name}/{os.path.basename(f)}"
    print(f"{f} -> {new_filename}")
    os.rename(f, new_filename)