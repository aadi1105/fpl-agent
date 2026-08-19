import pandas as pd
import sqlite3

df_xg = pd.read_csv("data/ml/historical_xg_dataset.csv", nrows=5)
print("--- xG Dataset Columns ---")
print(df_xg.columns.tolist())

df_mins = pd.read_csv("data/ml/historical_minutes_dataset.csv", nrows=5)
print("\n--- Minutes Dataset Columns ---")
print(df_mins.columns.tolist())

conn = sqlite3.connect("data/fpl_database.db")
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("\n--- DB Tables ---")
print(tables)

conn.close()
