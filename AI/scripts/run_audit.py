import os
import zipfile
import json
import re
import pandas as pd
import numpy as np
from pathlib import Path

raw_dir = Path("data/raw")
interim_dir = Path("data/interim")

# Detect files
csv_files = list(raw_dir.glob("*.csv"))
zip_files = list(raw_dir.glob("*.zip"))

print(f"Found {len(csv_files)} CSV files and {len(zip_files)} ZIP files.")

for cf in csv_files:
    print(f"\n--- Checking CSV: {cf.name} ---")
    try:
        df = pd.read_csv(cf, nrows=5)
        print(f"Columns ({len(df.columns)}): {list(df.columns)}")
    except Exception as e:
        print(f"Error reading with default utf-8: {e}")
        try:
            df = pd.read_csv(cf, nrows=5, encoding="latin1")
            print(f"Columns (latin1) ({len(df.columns)}): {list(df.columns)}")
        except Exception as e2:
            print(f"Error reading latin1: {e2}")
