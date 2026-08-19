import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
import numpy as np
from scratch.run_phase3c7_temporal_audit import construct_leak_free_temporal_dataset, load_data

df_temporal = construct_leak_free_temporal_dataset(load_data())

target_names = ["Omar Marmoush", "Dominic Calvert-Lewin", "Taiwo Awoniyi", "William Osula", "Beto"]

print("=== CASE STUDY PLAYER TEMPORAL SNAPSHOTS ===")
for name in target_names:
    matches = df_temporal[df_temporal['player_name'].str.contains(name, case=False, na=False)].copy()
    if len(matches) > 0:
        latest = matches.iloc[-1]
        print(f"\n--- {latest['player_name']} (Total Career Mins in DB: {latest['tot_mins_prior']:.0f}) ---")
        print(f"Season/GW: {latest['season']} GW{latest['gameweek']} | Team: {latest['team']}")
        print(f"Career xG/90: {latest['xg_90_career']:.3f} | Career xA/90: {latest['xa_90_career']:.3f}")
        print(f"xG/90 Last 3: {latest['xg_90_3']:.3f} | xG/90 Last 5: {latest['xg_90_5']:.3f} | xG/90 Last 10: {latest['xg_90_10']:.3f}")
        print(f"xA/90 Last 3: {latest['xa_90_3']:.3f} | xA/90 Last 5: {latest['xa_90_5']:.3f} | xA/90 Last 10: {latest['xa_90_10']:.3f}")
        print(f"Mins Last 3: {latest['mins_last_3']:.0f} | Mins Last 5: {latest['mins_last_5']:.0f} | Mins Last 10: {latest['mins_last_10']:.0f}")
        print(f"Starts Last 5: {latest['starts_last_5']:.0f} | Current Club Mins: {latest['curr_club_mins']:.0f}")
