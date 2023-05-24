#!/usr/bin/env python3

# This fails due to OOM

import rasterio
rasterio.open("Retrolens/Otago/KatikiBeach/Stack/KatikiBeach_12MAR1979_mosaic.jp2").read()

# This doesn't work either
# gdal_translate -ot Byte Retrolens/Otago/KatikiBeach/Stack/KatikiBeach_12MAR1979_mosaic.jp2 KatikiBeach_12MAR1979_mosaic.jp2