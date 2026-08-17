import os
import json
import logging
import io
import urllib.request
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("dataset_builder")
logging.basicConfig(level=logging.INFO)

DATA_DIR = "data/ml"
RAW_DATA_DIR = "data/raw"

SEASONS = {
    "2022-23": "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2022-23/gws/merged_gw.csv",
    "2023-24": "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2023-24/gws/merged_gw.csv",
    "2024-25": "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2024-25/gws/merged_gw.csv",
    "2025-26": "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2025-26/gws/merged_gw.csv"
}

SPLIT_MAP = {
    "2022-23": "train",
    "2023-24": "train",
    "2024-25": "validation",
    "2025-26": "test"
}

POS_NORMALIZE = {
    "GK": "GKP", "GKP": "GKP",
    "DEF": "DEF",
    "MID": "MID", "AM": "MID",
    "FWD": "FWD"
}

class HistoricalDatasetBuilder:
    """
    Constructs a clean, leak-free, pre-deadline historical dataset across 2022/23 - 2025/26
    for training FPL expected-minutes machine learning models.
    """
    def __init__(self, output_dir: str = DATA_DIR, raw_dir: str = RAW_DATA_DIR):
        self.output_dir = output_dir
        self.raw_dir = raw_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)

    def fetch_raw_season_data(self, season: str, url: str) -> pd.DataFrame:
        """Fetch season CSV from raw cache or vaastav GitHub repository."""
        cache_path = os.path.join(self.raw_dir, f"merged_gw_{season}.csv")
        if os.path.exists(cache_path):
            logger.info(f"Loading raw data for season {season} from local cache: {cache_path}")
            return pd.read_csv(cache_path, low_memory=False)

        logger.info(f"Downloading raw data for season {season} from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            with open(cache_path, "wb") as f:
                f.write(content)
            df = pd.read_csv(io.BytesIO(content), low_memory=False)
            logger.info(f"Successfully downloaded and cached season {season} ({len(df)} rows).")
            return df

    def _compute_historical_team_ratings(self, df_season: pd.DataFrame) -> Dict[Tuple[int, str], Dict[str, float]]:
        """
        Calculates leak-free team ratings for each (gameweek, team) pair using ONLY matches strictly before GW.
        Baseline: 1000.0. Clamped to [600.0, 1600.0].
        """
        gws = sorted(df_season['GW'].unique())
        teams = df_season['team'].unique()
        
        ratings = {}

        for gw in gws:
            prior_df = df_season[df_season['GW'] < gw]
            
            if len(prior_df) == 0:
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
        """Process a single season into leak-free features and targets using fast gameweek aggregation."""
        logger.info(f"Processing season {season} ({len(df)} raw rows)...")

        df = df.copy()
        if 'GW' in df.columns:
            df['gameweek'] = df['GW']

        df['kickoff_dt'] = pd.to_datetime(df['kickoff_time'], errors='coerce')
        df['starts_col'] = df['starts'] if 'starts' in df.columns else (df['minutes'] >= 60).astype(int)

        # Build opponent team map from opponent_team (id) -> team (name)
        opp_map = {}
        if 'opponent_team' in df.columns and 'team' in df.columns:
            for _, row in df[['fixture', 'team', 'opponent_team', 'was_home']].drop_duplicates().iterrows():
                opp_id = row['opponent_team']
                opp_map[opp_id] = row['team']

        # Compute leak-free historical team ratings
        team_ratings = self._compute_historical_team_ratings(df)

        # Aggregate raw fixture rows to 1 row per (element, gameweek) for pre-deadline snapshot
        df = df.sort_values(by=['element', 'kickoff_dt', 'gameweek']).reset_index(drop=True)

        agg_dict = {
            'name': 'first',
            'team': 'first',
            'position': 'first',
            'value': 'first',
            'opponent_team': 'first',
            'was_home': 'first',
            'kickoff_dt': 'min',
            'minutes': 'sum',
            'starts_col': 'max'
        }

        gw_df = df.groupby(['element', 'gameweek'], as_index=False).agg(agg_dict)
        gw_df = gw_df.sort_values(by=['element', 'gameweek']).reset_index(drop=True)

        # Vectorized player rolling statistics across prior gameweeks (STRICTLY GW < current_gw)
        gw_df['is_app'] = (gw_df['minutes'] > 0).astype(int)
        gw_df['is_bench'] = ((gw_df['minutes'] > 0) & (gw_df['starts_col'] == 0)).astype(int)
        gw_df['is_unused'] = (gw_df['minutes'] == 0).astype(int)

        gw_df['minutes_shift'] = gw_df.groupby('element')['minutes'].shift(1).fillna(0)
        gw_df['starts_shift'] = gw_df.groupby('element')['starts_col'].shift(1).fillna(0)
        gw_df['app_shift'] = gw_df.groupby('element')['is_app'].shift(1).fillna(0)
        gw_df['bench_shift'] = gw_df.groupby('element')['is_bench'].shift(1).fillna(0)
        gw_df['unused_shift'] = gw_df.groupby('element')['is_unused'].shift(1).fillna(0)

        gw_df['minutes_last_1'] = gw_df['minutes_shift'].astype(int)
        gw_df['starts_last_1'] = gw_df['starts_shift'].astype(int)

        gw_df['minutes_last_3'] = gw_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(int)
        gw_df['minutes_last_5'] = gw_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        gw_df['minutes_last_10'] = gw_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(int)

        gw_df['starts_last_3'] = gw_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype(int)
        gw_df['starts_last_5'] = gw_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        gw_df['starts_last_10'] = gw_df.groupby('element')['starts_shift'].transform(lambda s: s.rolling(10, min_periods=1).sum()).astype(int)

        gw_df['appearances_last_5'] = gw_df.groupby('element')['app_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        gw_df['bench_appearances_last_5'] = gw_df.groupby('element')['bench_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)
        gw_df['unused_substitute_last_5'] = gw_df.groupby('element')['unused_shift'].transform(lambda s: s.rolling(5, min_periods=1).sum()).astype(int)

        gw_df['average_minutes_last_5'] = gw_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(5, min_periods=1).mean()).fillna(0.0).round(1)
        gw_df['average_minutes_last_10'] = gw_df.groupby('element')['minutes_shift'].transform(lambda s: s.rolling(10, min_periods=1).mean()).fillna(0.0).round(1)

        # Team schedule & rest days vectorization
        team_kickoffs = gw_df[['team', 'gameweek', 'kickoff_dt']].drop_duplicates().sort_values(by=['team', 'kickoff_dt']).dropna(subset=['kickoff_dt']).reset_index(drop=True)
        team_kickoffs['prior_kickoff'] = team_kickoffs.groupby('team')['kickoff_dt'].shift(1)
        team_kickoffs['days_since_last_match'] = (team_kickoffs['kickoff_dt'] - team_kickoffs['prior_kickoff']).dt.total_seconds() / 86400.0
        team_kickoffs['days_since_last_match'] = team_kickoffs['days_since_last_match'].fillna(14.0).round(1)

        m_14_list = []
        m_21_list = []
        for idx, row in team_kickoffs.iterrows():
            t_dt = row['kickoff_dt']
            t_name = row['team']
            t_df = team_kickoffs[(team_kickoffs['team'] == t_name) & (team_kickoffs['kickoff_dt'] < t_dt)]
            m14 = len(t_df[t_df['kickoff_dt'] >= (t_dt - pd.Timedelta(days=14))])
            m21 = len(t_df[t_df['kickoff_dt'] >= (t_dt - pd.Timedelta(days=21))])
            m_14_list.append(m14)
            m_21_list.append(m21)

        team_kickoffs['matches_in_previous_14_days'] = m_14_list
        team_kickoffs['matches_in_previous_21_days'] = m_21_list
        team_kickoffs['fixture_congestion'] = (team_kickoffs['matches_in_previous_14_days'] >= 3).astype(int)

        gw_df = gw_df.merge(
            team_kickoffs[['team', 'gameweek', 'days_since_last_match', 'matches_in_previous_14_days', 'matches_in_previous_21_days', 'fixture_congestion']],
            on=['team', 'gameweek'],
            how='left'
        )

        gw_df['days_since_last_match'] = gw_df['days_since_last_match'].fillna(14.0)
        gw_df['matches_in_previous_14_days'] = gw_df['matches_in_previous_14_days'].fillna(0).astype(int)
        gw_df['matches_in_previous_21_days'] = gw_df['matches_in_previous_21_days'].fillna(0).astype(int)
        gw_df['fixture_congestion'] = gw_df['fixture_congestion'].fillna(0).astype(int)

        processed_rows = []
        for idx, row in gw_df.iterrows():
            gw = int(row['gameweek'])
            p_id = int(row['element'])
            p_name = str(row['name'])
            raw_pos = str(row.get('position', 'MID'))
            pos = POS_NORMALIZE.get(raw_pos, "MID")

            t_name = str(row['team'])
            opp_id = int(row.get('opponent_team', 0))
            opp_name = opp_map.get(opp_id, f"Team_{opp_id}")
            was_home = bool(row.get('was_home', True))
            price = float(row.get('value', 50)) / 10.0

            t_rat = team_ratings.get((gw, t_name), {"att_h": 1050.0, "att_a": 950.0, "def_h": 1050.0, "def_a": 950.0})
            opp_rat = team_ratings.get((gw, opp_name), {"att_h": 1050.0, "att_a": 950.0, "def_h": 1050.0, "def_a": 950.0})

            team_att = t_rat["att_h"] if was_home else t_rat["att_a"]
            team_def = t_rat["def_h"] if was_home else t_rat["def_a"]
            opp_att = opp_rat["att_a"] if was_home else opp_rat["att_h"]
            opp_def = opp_rat["def_a"] if was_home else opp_rat["def_h"]

            raw_diff = round(max(1.0, min(5.0, 3.0 + (opp_def - 1000.0) / 200.0)), 1)

            act_mins = int(row['minutes'])
            act_starts = int(row['starts_col'])

            target_started = 1 if act_starts >= 1 else 0
            target_minutes = act_mins
            target_60_plus = 1 if act_mins >= 60 else 0
            target_zero_minutes = 1 if act_mins == 0 else 0

            processed_rows.append({
                "season": season,
                "gameweek": gw,
                "player_id": p_id,
                "player_name": p_name,
                "team": t_name,
                "position": pos,
                "price": price,
                "opponent": opp_name,
                "opponent_id": opp_id,
                "home_away": "H" if was_home else "A",
                "fixture_difficulty": raw_diff,
                "team_attack_rating": team_att,
                "team_defence_rating": team_def,
                "opponent_attack_rating": opp_att,
                "opponent_defence_rating": opp_def,
                "minutes_last_1": int(row['minutes_last_1']),
                "minutes_last_3": int(row['minutes_last_3']),
                "minutes_last_5": int(row['minutes_last_5']),
                "minutes_last_10": int(row['minutes_last_10']),
                "starts_last_1": int(row['starts_last_1']),
                "starts_last_3": int(row['starts_last_3']),
                "starts_last_5": int(row['starts_last_5']),
                "starts_last_10": int(row['starts_last_10']),
                "appearances_last_5": int(row['appearances_last_5']),
                "bench_appearances_last_5": int(row['bench_appearances_last_5']),
                "unused_substitute_last_5": int(row['unused_substitute_last_5']),
                "average_minutes_last_5": float(row['average_minutes_last_5']),
                "average_minutes_last_10": float(row['average_minutes_last_10']),
                "days_since_last_match": float(row['days_since_last_match']),
                "matches_in_previous_14_days": int(row['matches_in_previous_14_days']),
                "matches_in_previous_21_days": int(row['matches_in_previous_21_days']),
                "fixture_congestion": int(row['fixture_congestion']),
                "injury_status": "unknown_historical",
                "feature_as_of": f"{season}_GW{gw}_pre_deadline",
                "split": SPLIT_MAP.get(season, "train"),
                "target_started": target_started,
                "target_minutes": target_minutes,
                "target_60_plus": target_60_plus,
                "target_zero_minutes": target_zero_minutes
            })

        res_df = pd.DataFrame(processed_rows)
        logger.info(f"Processed {len(res_df)} rows for season {season}.")
        return res_df

    def build_dataset(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Download, process, validate, and save the full 4-season historical dataset."""
        logger.info("Starting historical ML dataset construction pipeline across 4 seasons...")
        
        all_season_dfs = []
        for season, url in SEASONS.items():
            raw_df = self.fetch_raw_season_data(season, url)
            proc_df = self.process_season(season, raw_df)
            all_season_dfs.append(proc_df)

        full_df = pd.concat(all_season_dfs, ignore_index=True)
        
        full_df = full_df.sort_values(by=['season', 'gameweek', 'player_id']).reset_index(drop=True)

        metrics = self.validate_and_summarize(full_df)

        csv_path = os.path.join(self.output_dir, "historical_minutes_dataset.csv")
        full_df.to_csv(csv_path, index=False)
        logger.info(f"Saved full dataset to {csv_path} ({len(full_df)} rows).")

        meta_path = os.path.join(self.output_dir, "dataset_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Saved dataset metadata to {meta_path}.")

        return full_df, metrics

    def validate_and_summarize(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform data quality checks, temporal leakage verification, and statistical summary."""
        logger.info("Executing Quality & Temporal Leakage Validation Checks...")

        dup_count = int(df.duplicated(subset=['season', 'gameweek', 'player_id']).sum())
        missing_player_ids = int(df['player_id'].isnull().sum())
        invalid_minutes = int(((df['target_minutes'] < 0) | (df['target_minutes'] > 240)).sum())
        invalid_positions = int((~df['position'].isin(['GKP', 'DEF', 'MID', 'FWD'])).sum())

        bad_60_plus = int(((df['target_minutes'] >= 60) & (df['target_60_plus'] != 1)).sum())
        bad_zero_mins = int(((df['target_minutes'] == 0) & (df['target_zero_minutes'] != 1)).sum())

        gw1_df = df[df['gameweek'] == 1]
        gw1_mins_leak = int((gw1_df['minutes_last_1'] != 0).sum())

        target_cols = ['target_started', 'target_minutes', 'target_60_plus', 'target_zero_minutes']
        feature_cols = [c for c in df.columns if c not in target_cols + ['season', 'feature_as_of', 'split']]

        seasons_included = list(df['season'].unique())
        gw_range = [int(df['gameweek'].min()), int(df['gameweek'].max())]
        unique_players = int(df['player_id'].nunique())
        unique_teams = int(df['team'].nunique())
        total_rows = len(df)

        split_counts = df['split'].value_counts().to_dict()
        
        starting_apps = int(df['target_started'].sum())
        apps_60_plus = int(df['target_60_plus'].sum())
        zero_mins_apps = int(df['target_zero_minutes'].sum())

        missing_stats = df[feature_cols].isnull().sum().to_dict()

        summary = {
            "created_at": datetime.utcnow().isoformat(),
            "dataset_version": "1.0.0",
            "seasons_included": seasons_included,
            "gameweek_range": gw_range,
            "total_rows": total_rows,
            "unique_players": unique_players,
            "unique_teams": unique_teams,
            "feature_count": len(feature_cols),
            "target_distribution": {
                "total_starts": starting_apps,
                "starts_percent": round(starting_apps / total_rows * 100, 2),
                "total_60_plus": apps_60_plus,
                "60_plus_percent": round(apps_60_plus / total_rows * 100, 2),
                "total_zero_minutes": zero_mins_apps,
                "zero_minutes_percent": round(zero_mins_apps / total_rows * 100, 2)
            },
            "splits": split_counts,
            "quality_audit": {
                "duplicates": dup_count,
                "missing_player_ids": missing_player_ids,
                "invalid_minutes_range": invalid_minutes,
                "invalid_positions": invalid_positions,
                "logical_target_mismatches_60_plus": bad_60_plus,
                "logical_target_mismatches_zero_mins": bad_zero_mins,
                "gw1_minutes_last_1_leakage": gw1_mins_leak,
                "passed_all_quality_checks": (
                    dup_count == 0 and missing_player_ids == 0 and invalid_minutes == 0 and 
                    invalid_positions == 0 and bad_60_plus == 0 and bad_zero_mins == 0 and 
                    gw1_mins_leak == 0
                )
            },
            "missing_values": missing_stats
        }

        return summary

if __name__ == "__main__":
    builder = HistoricalDatasetBuilder()
    builder.build_dataset()
