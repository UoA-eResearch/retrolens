#!/usr/bin/env python3

import pandas as pd
import geopandas as gpd

df = gpd.read_file("shorelines.geojson")
print(df)

def fix_row(row):
    bits = row.filename.split("/")
    if not row.Region:
        row.Region = bits[0]
    if not row.Site:
        row.Site = bits[1]
    if not row.Date or row.Date < "1900-01-01":
        bits = bits[-1].split("_")
        last_fragment = bits[-1].replace(".shp", "")
        if len(bits) > 1 and len(last_fragment) == len("14MAR1948"):
            row.Date = last_fragment
        elif row.Date_:
            row.Date = row.Date_
        elif row.DSASDate:
            row.Date = row.DSASDate
    if row.Date:
        row.Date = str(pd.to_datetime(row.Date).date())
    return row
df = df.apply(fix_row, axis=1)
print(df)

df.to_file("shorelines.geojson")