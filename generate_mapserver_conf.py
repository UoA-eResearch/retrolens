#!/usr/bin/env python3

from glob import glob
from os.path import basename, splitext
files = sorted(glob("/mnt/coastal/*/*.tif"))

print("""MAP
    PROJECTION
        "init=epsg:3857" # Output projection
    END""")

for filepath in files:
    name = splitext(basename(filepath))[0]
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
