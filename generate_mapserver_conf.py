#!/usr/bin/env python3

from glob import glob
from os.path import basename, splitext
files = sorted(glob("/mnt/coastal/**/*.tif", recursive=True))

print("""MAP
    PROJECTION
        "init=epsg:3857" # Output projection
    END""")

for filepath in files:
    name = filepath.replace("/mnt/coastal/", "").replace(".tif", "").replace("/", " - ")
    print(f"""
    LAYER
        NAME "{name}"
        DATA "{filepath}"
        TYPE RASTER
        PROJECTION
            "init=epsg:2193"
        END
        STATUS ON
        OFFSITE 255 255 255
    END""")
print("""
    WEB
        METADATA
            "wms_title" "NZ Coastal Mosaic Server"
            "wms_enable_request"  "*"
        END
    END
END
""")
