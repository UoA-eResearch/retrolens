#!/usr/bin/env python3

import json
from pprint import pprint
import pandas as pd

with open("coco.json") as f:
    data = json.load(f)

df = pd.DataFrame(data["annotations"])
meta = pd.DataFrame()
meta["annotation_categories"] = df.groupby("image_id")["category_id"].apply(list)
meta["n_annotations"] = meta.annotation_categories.str.len()
meta["n_categories"] = meta.annotation_categories.apply(lambda c: len(set(c)))
meta = meta[meta.n_categories == 2]
#print(meta.n_annotations.value_counts())

good_images = meta.index

new_data = {
    "annotations": [d for d in data["annotations"] if d["image_id"] in good_images],
    "categories": data["categories"],
    "images": [d for d in data["images"] if d["id"] in good_images]
}
print(f'Filtered {len(data["annotations"])} annotations to {len(new_data["annotations"])}')
print(f'Filtered {len(data["images"])} images to {len(new_data["images"])}')
with open("coco_filtered.json", "w") as f:
    json.dump(new_data, f)