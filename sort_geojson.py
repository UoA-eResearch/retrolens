#!/usr/bin/env python3

import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

data["features"] = sorted(data["features"], key=lambda f: f["properties"]["Date"])

with open(sys.argv[1], "w") as f:
    json.dump(data, f)