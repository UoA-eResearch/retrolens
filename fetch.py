#!/usr/bin/env python3

import pandas as pd
import requests
import os
from tqdm.auto import tqdm # Progress bar

df = pd.read_csv("TZ_trial.csv")

for i,row in tqdm(df.iterrows(), total=df.shape[0]):
    url = f"https://files.interpret.co.nz/Retrolens/Imagery/SN{row.Survey}/{row.Released_F}/High.jpg"
    folder = f"{row.Region_1}/{row.Site}/{row.Date[-4:]}"
    os.makedirs(folder, exist_ok=True)
    filename = f"{folder}/{row.Released_F}.jpg"
    if os.path.exists(filename):
        print(f"{filename} exists, skipping")
        continue
    print(f"Fetching {url}")
    r = requests.get(url)
    print(f"Writing to {filename}")
    with open(filename, "wb") as f:
        f.write(r.content)