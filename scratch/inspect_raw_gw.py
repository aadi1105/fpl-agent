import pandas as pd

df = pd.read_csv("data/raw/merged_gw_2022-23.csv")
print("--- Raw Merged GW Columns ---")
print(df.columns.tolist())
print(f"Total rows in 2022-23: {len(df)}")
print(df.head(2))
