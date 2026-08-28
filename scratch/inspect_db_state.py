import sqlite3
import pandas as pd

print("=== fpl_engine.db tables ===")
con1 = sqlite3.connect("fpl_engine.db")
tables1 = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con1)
print(tables1)

print("\n=== data/fpl_database.db tables ===")
con2 = sqlite3.connect("data/fpl_database.db")
tables2 = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con2)
print(tables2)

print("\n=== raw merged_gw_2024-25.csv columns ===")
df_raw = pd.read_csv("data/raw/merged_gw_2024-25.csv", nrows=5)
print(list(df_raw.columns))

print("\n=== historical_xg_dataset.csv columns ===")
df_xg = pd.read_csv("data/ml/historical_xg_dataset.csv", nrows=5)
print(list(df_xg.columns))
