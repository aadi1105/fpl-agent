import os
import pickle
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime

from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    log_loss, brier_score_loss, roc_auc_score, average_precision_score,
    mean_absolute_error, root_mean_squared_error, median_absolute_error
)
import lightgbm as lgb
import xgboost as xgb

logger = logging.getLogger("minutes_model")
logging.basicConfig(level=logging.INFO)

DATA_PATH = "data/ml/historical_minutes_dataset.csv"
MODEL_DIR = "models"

FEATURE_COLS = [
    'price', 'fixture_difficulty',
    'team_attack_rating', 'team_defence_rating',
    'opponent_attack_rating', 'opponent_defence_rating',
    'home_away_is_home',
    'minutes_last_1', 'minutes_last_3', 'minutes_last_5', 'minutes_last_10',
    'starts_last_1', 'starts_last_3', 'starts_last_5', 'starts_last_10',
    'appearances_last_5', 'bench_appearances_last_5', 'unused_substitute_last_5',
    'average_minutes_last_5', 'average_minutes_last_10',
    'days_since_last_match', 'matches_in_previous_14_days', 'matches_in_previous_21_days',
    'fixture_congestion',
    'pos_DEF', 'pos_MID', 'pos_FWD'
]

class MinutesModelPipeline:
    """
    Phase 2B: Expected Minutes ML Pipeline.
    Trains, evaluates, and backtests Model A (P(start)), Model B (Expected Minutes),
    Model C (P(60+)), and Model D (P(0)) against deterministic baselines.
    """
    def __init__(self, data_path: str = DATA_PATH, model_dir: str = MODEL_DIR):
        self.data_path = data_path
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def prepare_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load dataset and perform feature encoding & chronological train/val/test split."""
        logger.info(f"Loading dataset from {self.data_path}...")
        df = pd.read_csv(self.data_path)

        df['home_away_is_home'] = (df['home_away'] == 'H').astype(int)

        # One-hot encode position
        df['pos_DEF'] = (df['position'] == 'DEF').astype(int)
        df['pos_MID'] = (df['position'] == 'MID').astype(int)
        df['pos_FWD'] = (df['position'] == 'FWD').astype(int)

        train_df = df[df['split'] == 'train'].reset_index(drop=True)
        val_df = df[df['split'] == 'validation'].reset_index(drop=True)
        test_df = df[df['split'] == 'test'].reset_index(drop=True)

        logger.info(f"Splits prepared: Train={len(train_df)} rows, Val={len(val_df)} rows, Test={len(test_df)} rows.")
        return train_df, val_df, test_df

    def compute_baseline_predictions(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Calculate deterministic baseline heuristics for all four targets."""
        p_start_base = np.clip(df['starts_last_5'] / 5.0, 0.05, 0.95).values
        exp_mins_base = df['average_minutes_last_5'].values
        
        # P(60+) baseline: starts/appearances >= 60 mins frequency
        starts_app_last_5 = np.maximum(0, df['appearances_last_5'] - df['bench_appearances_last_5'])
        p_60_base = np.clip(starts_app_last_5 / 5.0, 0.05, 0.95).values
        
        # P(0) baseline: unused substitute frequency
        p_0_base = np.clip(df['unused_substitute_last_5'] / 5.0, 0.05, 0.95).values

        return {
            "p_start": p_start_base,
            "exp_mins": exp_mins_base,
            "p_60_plus": p_60_base,
            "p_zero": p_0_base
        }

    def evaluate_classifier(self, y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
        """Compute Log Loss, Brier Score, ROC-AUC, PR-AUC, and calibration error for classifiers."""
        eps = 1e-15
        y_prob_c = np.clip(y_prob, eps, 1.0 - eps)
        
        loss = float(log_loss(y_true, y_prob_c))
        brier = float(brier_score_loss(y_true, y_prob_c))
        roc_auc = float(roc_auc_score(y_true, y_prob_c))
        pr_auc = float(average_precision_score(y_true, y_prob_c))

        # Reliability calibration error (Expected Calibration Error - ECE)
        bins = np.linspace(0.0, 1.0, 11)
        binids = np.digitize(y_prob_c, bins) - 1
        ece = 0.0
        for i in range(10):
            mask = binids == i
            if np.sum(mask) > 0:
                bin_acc = np.mean(y_true[mask])
                bin_conf = np.mean(y_prob_c[mask])
                ece += np.abs(bin_acc - bin_conf) * (np.sum(mask) / len(y_true))

        return {
            "log_loss": round(loss, 4),
            "brier_score": round(brier, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "ece": round(float(ece), 4)
        }

    def evaluate_regressor(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute MAE, RMSE, and Median Absolute Error for regression models."""
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(root_mean_squared_error(y_true, y_pred))
        med_ae = float(median_absolute_error(y_true, y_pred))
        
        return {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "median_ae": round(med_ae, 3)
        }

    def run_pipeline(self) -> Dict[str, Any]:
        """Train models, perform validation model selection, and evaluate untouched test set once."""
        train_df, val_df, test_df = self.prepare_data()

        X_train = train_df[FEATURE_COLS]
        X_val = val_df[FEATURE_COLS]
        X_test = test_df[FEATURE_COLS]

        # Extract Targets
        y_start_tr, y_start_val, y_start_te = train_df['target_started'].values, val_df['target_started'].values, test_df['target_started'].values
        y_mins_tr, y_mins_val, y_mins_te = train_df['target_minutes'].values, val_df['target_minutes'].values, test_df['target_minutes'].values
        y_60_tr, y_60_val, y_60_te = train_df['target_60_plus'].values, val_df['target_60_plus'].values, test_df['target_60_plus'].values
        y_0_tr, y_0_val, y_0_te = train_df['target_zero_minutes'].values, val_df['target_zero_minutes'].values, test_df['target_zero_minutes'].values

        # Compute Deterministic Baselines
        base_val = self.compute_baseline_predictions(val_df)
        base_te = self.compute_baseline_predictions(test_df)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_version": "1.0.0",
            "features_used": FEATURE_COLS,
            "models": {}
        }

        # -------------------------------------------------------------
        # MODEL A: P(start) Classifier
        # -------------------------------------------------------------
        logger.info("Training Model A: P(start)...")
        # 1. Baseline
        val_start_base = self.evaluate_classifier(y_start_val, base_val["p_start"])
        te_start_base = self.evaluate_classifier(y_start_te, base_te["p_start"])

        # 2. Logistic Regression
        lr_start = LogisticRegression(max_iter=1000, random_state=42)
        lr_start.fit(X_train, y_start_tr)
        val_start_lr = self.evaluate_classifier(y_start_val, lr_start.predict_proba(X_val)[:, 1])

        # 3. LightGBM
        lgb_start = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.03, max_depth=5, random_state=42, verbose=-1)
        lgb_start.fit(X_train, y_start_tr)
        val_start_lgb = self.evaluate_classifier(y_start_val, lgb_start.predict_proba(X_val)[:, 1])

        # Model Selection on Validation set based on Log Loss
        models_a_val = {
            "Baseline": val_start_base,
            "LogisticRegression": val_start_lr,
            "LightGBM": val_start_lgb
        }
        best_a_name = min(models_a_val, key=lambda k: models_a_val[k]["log_loss"])
        best_a_obj = lgb_start if best_a_name == "LightGBM" else (lr_start if best_a_name == "LogisticRegression" else None)
        
        # Test Set Single Evaluation
        if best_a_obj:
            te_start_best = self.evaluate_classifier(y_start_te, best_a_obj.predict_proba(X_test)[:, 1])
        else:
            te_start_best = te_start_base

        report["models"]["model_a_p_start"] = {
            "target": "target_started",
            "selected_model": best_a_name,
            "validation_metrics": models_a_val,
            "test_metrics": {
                "Baseline": te_start_base,
                "Selected_ML": te_start_best
            },
            "ml_beats_baseline": models_a_val[best_a_name]["log_loss"] < val_start_base["log_loss"]
        }

        # Save Model A artifact
        with open(os.path.join(self.model_dir, "minutes_start_v1.pkl"), "wb") as f:
            pickle.dump(best_a_obj if best_a_obj else lgb_start, f)

        # -------------------------------------------------------------
        # MODEL B: Expected Minutes Regressor
        # -------------------------------------------------------------
        logger.info("Training Model B: Expected Minutes Regressor...")
        val_mins_base = self.evaluate_regressor(y_mins_val, base_val["exp_mins"])
        te_mins_base = self.evaluate_regressor(y_mins_te, base_te["exp_mins"])

        ridge_mins = Ridge(alpha=10.0, random_state=42)
        ridge_mins.fit(X_train, y_mins_tr)
        val_mins_ridge = self.evaluate_regressor(y_mins_val, np.clip(ridge_mins.predict(X_val), 0, 180))

        lgb_mins = lgb.LGBMRegressor(n_estimators=150, learning_rate=0.03, max_depth=5, random_state=42, verbose=-1)
        lgb_mins.fit(X_train, y_mins_tr)
        val_mins_lgb = self.evaluate_regressor(y_mins_val, np.clip(lgb_mins.predict(X_val), 0, 180))

        models_b_val = {
            "Baseline": val_mins_base,
            "RidgeRegression": val_mins_ridge,
            "LightGBM": val_mins_lgb
        }
        best_b_name = min(models_b_val, key=lambda k: models_b_val[k]["mae"])
        best_b_obj = lgb_mins if best_b_name == "LightGBM" else (ridge_mins if best_b_name == "RidgeRegression" else None)

        te_mins_best = self.evaluate_regressor(y_mins_te, np.clip(best_b_obj.predict(X_test), 0, 180)) if best_b_obj else te_mins_base

        # Subgroup & Sample Size Error Analysis on Test set
        test_preds = np.clip(best_b_obj.predict(X_test), 0, 180) if best_b_obj else base_te["exp_mins"]
        test_df_copy = test_df.copy()
        test_df_copy['pred_mins'] = test_preds
        test_df_copy['abs_err'] = np.abs(test_df_copy['target_minutes'] - test_df_copy['pred_mins'])

        subgroup_mae = {
            "starters": round(float(test_df_copy[test_df_copy['target_started'] == 1]['abs_err'].mean()), 2),
            "substitutes": round(float(test_df_copy[test_df_copy['target_started'] == 0]['abs_err'].mean()), 2),
            "GKP": round(float(test_df_copy[test_df_copy['position'] == 'GKP']['abs_err'].mean()), 2),
            "DEF": round(float(test_df_copy[test_df_copy['position'] == 'DEF']['abs_err'].mean()), 2),
            "MID": round(float(test_df_copy[test_df_copy['position'] == 'MID']['abs_err'].mean()), 2),
            "FWD": round(float(test_df_copy[test_df_copy['position'] == 'FWD']['abs_err'].mean()), 2)
        }

        report["models"]["model_b_expected_minutes"] = {
            "target": "target_minutes",
            "selected_model": best_b_name,
            "validation_metrics": models_b_val,
            "test_metrics": {
                "Baseline": te_mins_base,
                "Selected_ML": te_mins_best
            },
            "subgroup_test_mae": subgroup_mae,
            "ml_beats_baseline": models_b_val[best_b_name]["mae"] < val_mins_base["mae"]
        }

        with open(os.path.join(self.model_dir, "minutes_regression_v1.pkl"), "wb") as f:
            pickle.dump(best_b_obj if best_b_obj else lgb_mins, f)

        # -------------------------------------------------------------
        # MODEL C: P(60+) Classifier
        # -------------------------------------------------------------
        logger.info("Training Model C: P(60+)...")
        val_60_base = self.evaluate_classifier(y_60_val, base_val["p_60_plus"])
        te_60_base = self.evaluate_classifier(y_60_te, base_te["p_60_plus"])

        lgb_60 = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.03, max_depth=5, random_state=42, verbose=-1)
        lgb_60.fit(X_train, y_60_tr)
        val_60_lgb = self.evaluate_classifier(y_60_val, lgb_60.predict_proba(X_val)[:, 1])

        report["models"]["model_c_p_60_plus"] = {
            "target": "target_60_plus",
            "selected_model": "LightGBM",
            "validation_metrics": {"Baseline": val_60_base, "LightGBM": val_60_lgb},
            "test_metrics": {
                "Baseline": te_60_base,
                "LightGBM": self.evaluate_classifier(y_60_te, lgb_60.predict_proba(X_test)[:, 1])
            },
            "ml_beats_baseline": val_60_lgb["log_loss"] < val_60_base["log_loss"]
        }

        with open(os.path.join(self.model_dir, "minutes_60plus_v1.pkl"), "wb") as f:
            pickle.dump(lgb_60, f)

        # -------------------------------------------------------------
        # MODEL D: P(0) Classifier
        # -------------------------------------------------------------
        logger.info("Training Model D: P(0)...")
        val_0_base = self.evaluate_classifier(y_0_val, base_val["p_zero"])
        te_0_base = self.evaluate_classifier(y_0_te, base_te["p_zero"])

        lgb_0 = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.03, max_depth=5, random_state=42, verbose=-1)
        lgb_0.fit(X_train, y_0_tr)
        val_0_lgb = self.evaluate_classifier(y_0_val, lgb_0.predict_proba(X_val)[:, 1])

        report["models"]["model_d_p_zero"] = {
            "target": "target_zero_minutes",
            "selected_model": "LightGBM",
            "validation_metrics": {"Baseline": val_0_base, "LightGBM": val_0_lgb},
            "test_metrics": {
                "Baseline": te_0_base,
                "LightGBM": self.evaluate_classifier(y_0_te, lgb_0.predict_proba(X_test)[:, 1])
            },
            "ml_beats_baseline": val_0_lgb["log_loss"] < val_0_base["log_loss"]
        }

        with open(os.path.join(self.model_dir, "minutes_zero_v1.pkl"), "wb") as f:
            pickle.dump(lgb_0, f)

        # Feature Importance Analysis (LightGBM Regressor & Classifier)
        feature_importances = dict(zip(FEATURE_COLS, [round(float(v), 2) for v in lgb_mins.feature_importances_]))
        sorted_fi = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))
        report["feature_importances_xg_mins"] = sorted_fi

        # Save Report JSON
        report_path = os.path.join(self.model_dir, "phase2b_evaluation_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved Phase 2B evaluation report to {report_path}.")

        return report

if __name__ == "__main__":
    pipeline = MinutesModelPipeline()
    pipeline.run_pipeline()
