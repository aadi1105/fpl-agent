import os
import glob
import logging
import json
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor

logger = logging.getLogger("xa_dataset_builder")
logging.basicConfig(level=logging.INFO)

RAW_DATA_DIR = "data/raw"
OUTPUT_DIR = "data/ml"

SPLIT_MAP = {
    "2022-23": "train",
    "2023-24": "train",
    "2024-25": "validation",
    "2025-26": "test"
}

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]

POS_NORMALIZE = {
    'GK': 'GKP', 'GKP': 'GKP',
    'DEF': 'DEF',
    'MID': 'MID', 'AM': 'MID',
    'FWD': 'FWD'
}

class HistoricalXADatasetBuilder:
    def __init__(self, raw_dir: str = RAW_DATA_DIR, output_dir: str = OUTPUT_DIR):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.minutes_predictor = MinutesPredictor()
        self.xg_predictor = XGPredictor()

    def _compute_historical_team_ratings(self, df: pd.DataFrame) -> Dict[Tuple[int, str], Dict[str, float]]:
        """Calculate leak-free historical team attacking and defensive ratings for GW N using matches in GW < N."""
        ratings = {}
        teams = df['team'].unique()
        gameweeks = sorted(df['gameweek'].unique())

        for gw in gameweeks:
            prior_df = df[df['gameweek'] < gw]
            if prior_df.empty:
                for t in teams:
                    ratings[(gw, t)] = {
                        "att_h": 1050.0, "att_a": 950.0,
                        "def_h": 1050.0, "def_a": 950.0
                    }
                continue

            t_xg = prior_df.groupby('team')['expected_goals'].sum() if 'expected_goals' in prior_df.columns else prior_df.groupby('team')['goals_scored'].sum() * 0.8
            t_xga = prior_df.groupby('team')['expected_goals_conceded'].sum() if 'expected_goals_conceded' in prior_df.columns else prior_df.groupby('team')['goals_conceded'].sum() * 1.1
            t_mins = prior_df.groupby('team')['minutes'].sum()

            league_xg_sum = 0.0
            league_xga_sum = 0.0
            valid_teams = 0

            team_stats = {}
            for t in teams:
                mins = t_mins.get(t, 0)
                games = max(0.0, mins / 990.0)
                if games >= 1.0:
                    xg_pg = t_xg.get(t, 0.0) / games
                    xga_pg = (t_xga.get(t, 0.0) / 11.0) / games
                    team_stats[t] = (games, xg_pg, xga_pg)
                    league_xg_sum += xg_pg
                    league_xga_sum += xga_pg
                    valid_teams += 1

            avg_league_xg = (league_xg_sum / valid_teams) if valid_teams > 0 else 1.35
            avg_league_xga = (league_xga_sum / valid_teams) if valid_teams > 0 else 1.35

            for t in teams:
                if t in team_stats:
                    games, xg_pg, xga_pg = team_stats[t]
                    obs_att = 1000.0 * (xg_pg / max(0.5, avg_league_xg))
                    obs_def = 1000.0 * (max(0.5, avg_league_xga) / max(0.3, xga_pg))

                    w = games / (games + 5.0)
                    base_att = (w * obs_att) + ((1.0 - w) * 1000.0)
                    base_def = (w * obs_def) + ((1.0 - w) * 1000.0)

                    att_h = round(min(1600.0, max(600.0, base_att * 1.05)), 1)
                    att_a = round(min(1600.0, max(600.0, base_att * 0.95)), 1)
                    def_h = round(min(1600.0, max(600.0, base_def * 1.05)), 1)
                    def_a = round(min(1600.0, max(600.0, base_def * 0.95)), 1)
                else:
                    att_h, att_a, def_h, def_a = 1050.0, 950.0, 1050.0, 950.0

                ratings[(gw, t)] = {
                    "att_h": att_h, "att_a": att_a,
                    "def_h": def_h, "def_a": def_a
                }

        return ratings

    def process_season(self, season: str, df: pd.DataFrame) -> pd.DataFrame:
        """Process a single season into per-fixture leak-free xA features and target_assists."""
        logger.info(f"Processing season {season} ({len(df)} raw rows) for xA dataset...")

        df = df.copy()
        if 'GW' in df.columns:
            df['gameweek'] = df['GW']

        df['kickoff_dt'] = pd.to_datetime(df['kickoff_time'], errors='coerce')
        df['starts_col'] = df['starts'] if 'starts' in df.columns else (df['minutes'] >= 60).astype(int)

        opp_map = {}
        if 'opponent_team' in df.columns and 'team' in df.columns:
            for _, row in df[['fixture', 'team', 'opponent_team', 'was_home']].drop_duplicates().iterrows():
                opp_id = row['opponent_team']
                opp_map[opp_id] = row['team']

        team_ratings = self._compute_historical_team_ratings(df)

        fix_df = df.sort_values(by=['element', 'kickoff_dt', 'fixture']).reset_index(drop=True)

        fix_df['is_app'] = (fix_df['minutes'] > 0).astype(int)
        fix_df['is_bench'] = ((fix_df['minutes'] > 0) & (fix_df['starts_col'] == 0)).astype(int)
        fix_df['is_unused'] = (fix_df['minutes'] == 0).astype(int)

        fix_df['minutes_shift'] = fix_df.groupby('element')['minutes'].shift(1).fillna(0)
        fix_df['starts_shift'] = fix_df.groupby('element')['starts_col'].shift(1).fillna(0)

        # Creative features shift (assists, expected_assists, creativity, threat, goals)
        fix_df['assists_shift'] = fix_df.groupby('element')['assists'].shift(1).fillna(0.0)
        
        if 'expected_assists' in fix_df.columns:
            fix_df['xa_shift'] = fix_df.groupby('element')['expected_assists'].shift(1).fillna(0.0)
        else:
            fix_df['xa_shift'] = fix_df['assists_shift'] * 0.75

        if 'creativity' in fix_df.columns:
            fix_df['creativity_shift'] = fix_df.groupby('element')['creativity'].transform(lambda s: pd.to_numeric(s, errors='coerce').fillna(0.0)).groupby(fix_df['element']).shift(1).fillna(0.0)
        else:
            fix_df['creativity_shift'] = fix_df['xa_shift'] * 100.0

        if 'threat' in fix_df.columns:
            fix_df['threat_shift'] = fix_df.groupby('element')['threat'].transform(lambda s: pd.to_numeric(s, errors='coerce').fillna(0.0)).groupby(fix_df['element']).shift(1).fillna(0.0)
        else:
            fix_df['threat_shift'] = 0.0

        if 'goals_scored' in fix_df.columns:
            fix_df['goals_shift'] = fix_df.groupby('element')['goals_scored'].shift(1).fillna(0.0)
        else:
            fix_df['goals_shift'] = 0.0

        if 'expected_goals' in fix_df.columns:
            fix_df['xg_shift'] = fix_df.groupby('element')['expected_goals'].shift(1).fillna(0.0)
        else:
            fix_df['xg_shift'] = 0.0

        # Rolling minutes & starts
        fix_df['minutes_last_1'] = fix_df['minutes_shift'].astype(int)
        fix_df['minutes_last_3'] = fix_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(int)
        fix_df['minutes_last_5'] = fix_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        fix_df['minutes_last_10'] = fix_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(int)

        fix_df['starts_last_1'] = fix_df['starts_shift'].astype(int)
        fix_df['starts_last_3'] = fix_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(int)
        fix_df['starts_last_5'] = fix_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        fix_df['starts_last_10'] = fix_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(int)

        # Rolling Assists
        fix_df['assists_last_1'] = fix_df['assists_shift'].astype(float)
        fix_df['assists_last_3'] = fix_df.groupby('element')['assists_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(float)
        fix_df['assists_last_5'] = fix_df.groupby('element')['assists_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float)
        fix_df['assists_last_10'] = fix_df.groupby('element')['assists_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(float)

        # Rolling xA
        fix_df['xa_last_1'] = fix_df['xa_shift'].astype(float).round(3)
        fix_df['xa_last_3'] = fix_df.groupby('element')['xa_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(float).round(3)
        fix_df['xa_last_5'] = fix_df.groupby('element')['xa_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float).round(3)
        fix_df['xa_last_10'] = fix_df.groupby('element')['xa_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(float).round(3)

        # Rolling Creativity & Threat
        fix_df['creativity_last_5'] = fix_df.groupby('element')['creativity_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float).round(1)
        fix_df['creativity_last_10'] = fix_df.groupby('element')['creativity_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(float).round(1)
        fix_df['threat_last_5'] = fix_df.groupby('element')['threat_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float).round(1)

        # Rolling Goals & xG
        fix_df['goals_last_5'] = fix_df.groupby('element')['goals_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float)
        fix_df['xg_last_5'] = fix_df.groupby('element')['xg_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(float).round(3)

        # Per 90 rates over last 5 matches
        mins_5 = fix_df['minutes_last_5'].replace(0, np.nan)
        fix_df['assists_per_90_last_5'] = ((fix_df['assists_last_5'] / mins_5) * 90.0).fillna(0.0).round(3)
        fix_df['xa_per_90_last_5'] = ((fix_df['xa_last_5'] / mins_5) * 90.0).fillna(0.0).round(3)
        fix_df['creativity_per_90_last_5'] = ((fix_df['creativity_last_5'] / mins_5) * 90.0).fillna(0.0).round(1)

        # Force GW1 prior rolling stats to 0 (zero prior season leakage)
        gw1_mask = (fix_df['gameweek'] == 1)
        rolling_cols = [
            'minutes_last_1', 'minutes_last_3', 'minutes_last_5', 'minutes_last_10',
            'starts_last_1', 'starts_last_3', 'starts_last_5', 'starts_last_10',
            'assists_last_1', 'assists_last_3', 'assists_last_5', 'assists_last_10',
            'xa_last_1', 'xa_last_3', 'xa_last_5', 'xa_last_10',
            'creativity_last_5', 'creativity_last_10', 'threat_last_5',
            'goals_last_5', 'xg_last_5',
            'assists_per_90_last_5', 'xa_per_90_last_5', 'creativity_per_90_last_5'
        ]
        for c in rolling_cols:
            fix_df.loc[gw1_mask, c] = 0.0 if 'per_90' in c or 'xa' in c or 'creativity' in c or 'threat' in c or 'xg' in c else 0

        # Vectorized team context
        fix_df['price'] = fix_df['value'].astype(float) / 10.0
        fix_df['position'] = fix_df['position'].map(POS_NORMALIZE).fillna('MID')
        fix_df['home_away'] = np.where(fix_df['was_home'], 'H', 'A')

        team_att_list, team_def_list = [], []
        opp_att_list, opp_def_list = [], []

        for idx, row in fix_df.iterrows():
            gw = int(row['gameweek'])
            t_name = str(row['team'])
            opp_id = int(row.get('opponent_team', 0))
            opp_name = opp_map.get(opp_id, f"Team_{opp_id}")
            was_home = bool(row.get('was_home', True))

            t_rat = team_ratings.get((gw, t_name), {"att_h": 1050.0, "att_a": 950.0, "def_h": 1050.0, "def_a": 950.0})
            opp_rat = team_ratings.get((gw, opp_name), {"att_h": 1050.0, "att_a": 950.0, "def_h": 1050.0, "def_a": 950.0})

            team_att_list.append(t_rat["att_h"] if was_home else t_rat["att_a"])
            team_def_list.append(t_rat["def_h"] if was_home else t_rat["def_a"])
            opp_att_list.append(opp_rat["att_a"] if was_home else opp_rat["att_h"])
            opp_def_list.append(opp_rat["def_a"] if was_home else opp_rat["def_h"])

        fix_df['team_attack_rating'] = team_att_list
        fix_df['team_defence_rating'] = team_def_list
        fix_df['opponent_attack_rating'] = opp_att_list
        fix_df['opponent_defence_rating'] = opp_def_list

        if 'fixture_difficulty' in fix_df.columns:
            fix_df['fixture_difficulty'] = fix_df['fixture_difficulty'].fillna(3).astype(int)
        else:
            fix_df['fixture_difficulty'] = 3

        # Batch predict expected minutes
        fix_df = self.minutes_predictor.predict_batch(fix_df)

        # Batch predict pre-fixture xG using xg_v1_lgbm predictor for xG ablation study
        fix_df = self.xg_predictor.predict_batch(fix_df)

        fix_df['season'] = season
        fix_df['fixture_id'] = fix_df.get('fixture', 0).astype(int)
        fix_df['player_id'] = fix_df['element'].astype(int)
        fix_df['player_name'] = fix_df['name'].astype(str)
        fix_df['opponent'] = fix_df['opponent_team'].map(opp_map).fillna('Opponent')
        fix_df['opponent_id'] = fix_df['opponent_team'].astype(int)
        fix_df['target_assists'] = fix_df['assists'].astype(int)
        fix_df['actual_xa'] = fix_df.get('expected_assists', fix_df['assists'] * 0.75).astype(float).round(3)
        fix_df['split'] = SPLIT_MAP.get(season, "train")

        out_cols = [
            "season", "gameweek", "fixture_id", "player_id", "player_name",
            "team", "position", "opponent", "opponent_id", "home_away", "fixture_difficulty",
            "team_attack_rating", "team_defence_rating", "opponent_attack_rating", "opponent_defence_rating", "price",
            "expected_minutes_v1", "p_start", "p_60_plus", "p_zero", "xg_v1_lgbm_pred",
            "minutes_last_1", "minutes_last_5", "starts_last_5",
            "assists_last_1", "assists_last_3", "assists_last_5", "assists_last_10",
            "xa_last_1", "xa_last_3", "xa_last_5", "xa_last_10",
            "creativity_last_5", "creativity_last_10", "threat_last_5",
            "assists_per_90_last_5", "xa_per_90_last_5", "creativity_per_90_last_5",
            "target_assists", "actual_xa", "split"
        ]

        res_df = fix_df[out_cols].copy()
        logger.info(f"Completed season {season}: {len(res_df)} fixture rows created for xA dataset.")
        return res_df

    def build_dataset(self) -> str:
        """Build complete historical xA dataset across all seasons."""
        all_dfs = []
        for season in SEASONS:
            fpath = os.path.join(self.raw_dir, f"merged_gw_{season}.csv")
            if os.path.exists(fpath):
                raw_df = pd.read_csv(fpath, low_memory=False)
                proc_df = self.process_season(season, raw_df)
                all_dfs.append(proc_df)
            else:
                logger.warning(f"Raw file {fpath} not found!")

        full_df = pd.concat(all_dfs, ignore_index=True)

        out_csv = os.path.join(self.output_dir, "historical_xa_dataset.csv")
        full_df.to_csv(out_csv, index=False)
        logger.info(f"Saved historical xA dataset to {out_csv} ({len(full_df)} total fixture rows).")

        meta = {
            "total_records": len(full_df),
            "seasons": SEASONS,
            "splits": {
                "train": len(full_df[full_df['split'] == 'train']),
                "validation": len(full_df[full_df['split'] == 'validation']),
                "test": len(full_df[full_df['split'] == 'test'])
            },
            "columns": list(full_df.columns),
            "leak_audit": "VERIFIED (All rolling stats shifted by 1, GW1 reset to 0, per-fixture target_assists)"
        }

        meta_path = os.path.join(self.output_dir, "xa_dataset_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return out_csv

if __name__ == "__main__":
    builder = HistoricalXADatasetBuilder()
    builder.build_dataset()
