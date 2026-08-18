import os
import json
import logging
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, Any, Tuple
from scipy.stats import spearmanr, pearsonr

logger = logging.getLogger("xg_model")
logging.basicConfig(level=logging.INFO)

DATA_PATH = "data/ml/historical_xg_dataset.csv"
MODEL_DIR = "models"

FEATURE_COLS = [
    "price", "fixture_difficulty",
    "team_attack_rating", "team_defence_rating",
    "opponent_attack_rating", "opponent_defence_rating",
    "expected_minutes_v1", "p_start", "p_60_plus", "p_zero",
    "minutes_last_1", "minutes_last_5", "starts_last_5",
    "goals_last_1", "goals_last_3", "goals_last_5", "goals_last_10",
    "xg_last_1", "xg_last_3", "xg_last_5", "xg_last_10",
    "threat_last_5", "threat_last_10", "creativity_last_5",
    "goals_per_90_last_5", "xg_per_90_last_5", "threat_per_90_last_5",
    "pos_GKP", "pos_DEF", "pos_MID", "pos_FWD",
    "home_away_is_home"
]

POSITION_BASELINE_XG90 = {
    "GKP": 0.0,
    "DEF": 0.04,
    "MID": 0.22,
    "FWD": 0.40
}

def calculate_deterministic_baseline_xg(df: pd.DataFrame) -> np.ndarray:
    """Compute current deterministic xG baseline predictions for a DataFrame of fixtures."""
    baseline_preds = []
    for idx, row in df.iterrows():
        pos = str(row['position'])
        price = float(row['price'])
        x_mins = float(row['expected_minutes_v1'])
        mins_ratio = min(1.0, max(0.0, x_mins / 90.0))
        
        # Position + Price Tier Baseline xG per 90
        base_xg90 = POSITION_BASELINE_XG90.get(pos, 0.20)
        if pos == "FWD":
            if price >= 9.0: base_xg90 = 0.55
            elif price >= 7.0: base_xg90 = 0.40
            else: base_xg90 = 0.25
        elif pos == "MID":
            if price >= 9.0: base_xg90 = 0.45
            elif price >= 7.0: base_xg90 = 0.30
            else: base_xg90 = 0.15
        elif pos == "DEF":
            if price >= 6.0: base_xg90 = 0.08
            else: base_xg90 = 0.04

        # Opponent defence & team attack multiplier
        opp_def = float(row['opponent_defence_rating'])
        is_home = (row['home_away'] == 'H')
        home_factor = 1.05 if is_home else 0.95
        att_multiplier = min(1.50, max(0.60, (1000.0 / max(300.0, opp_def)) * home_factor))
        
        baseline_xg = base_xg90 * mins_ratio * att_multiplier
        baseline_preds.append(max(0.0, baseline_xg))
        
    return np.array(baseline_preds)

def mean_poisson_deviance(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute mean Poisson deviance."""
    eps = 1e-9
    y_pred = np.clip(y_pred, eps, None)
    # Poisson deviance formula: 2 * (y * log(y / y_pred) - (y - y_pred))
    # Where y == 0: 2 * y_pred
    dev = np.where(y_true > 0, 2 * (y_true * np.log(np.maximum(eps, y_true) / y_pred) - (y_true - y_pred)), 2 * y_pred)
    return float(np.mean(dev))

def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract and encode feature columns for ML modeling."""
    feat_df = df.copy()
    feat_df['home_away_is_home'] = (feat_df['home_away'] == 'H').astype(float)
    feat_df['pos_GKP'] = (feat_df['position'] == 'GKP').astype(float)
    feat_df['pos_DEF'] = (feat_df['position'] == 'DEF').astype(float)
    feat_df['pos_MID'] = (feat_df['position'] == 'MID').astype(float)
    feat_df['pos_FWD'] = (feat_df['position'] == 'FWD').astype(float)
    
    return feat_df[FEATURE_COLS].astype(float)

class XGModelPipeline:
    def __init__(self, data_path: str = DATA_PATH, model_dir: str = MODEL_DIR):
        self.data_path = data_path
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load leak-free xG dataset and partition into Train, Validation, and Test sets."""
        df = pd.read_csv(self.data_path, low_memory=False)
        train_df = df[df['split'] == 'train'].reset_index(drop=True)
        val_df = df[df['split'] == 'validation'].reset_index(drop=True)
        test_df = df[df['split'] == 'test'].reset_index(drop=True)
        
        logger.info(f"Loaded dataset: Train={len(train_df)} rows, Val={len(val_df)} rows, Test={len(test_df)} rows.")
        return train_df, val_df, test_df

    def train_and_evaluate(self) -> Dict[str, Any]:
        train_df, val_df, test_df = self.load_data()

        X_train = prepare_features(train_df)
        y_train = train_df['target_goals'].values.astype(float)

        X_val = prepare_features(val_df)
        y_val = val_df['target_goals'].values.astype(float)

        X_test = prepare_features(test_df)
        y_test = test_df['target_goals'].values.astype(float)

        # Baselines
        base_val_preds = calculate_deterministic_baseline_xg(val_df)
        base_test_preds = calculate_deterministic_baseline_xg(test_df)

        base_val_mae = float(np.mean(np.abs(base_val_preds - y_val)))
        base_val_rmse = float(np.sqrt(np.mean((base_val_preds - y_val)**2)))
        base_val_pdev = mean_poisson_deviance(y_val, base_val_preds)

        base_test_mae = float(np.mean(np.abs(base_test_preds - y_test)))
        base_test_rmse = float(np.sqrt(np.mean((base_test_preds - y_test)**2)))
        base_test_pdev = mean_poisson_deviance(y_test, base_test_preds)

        logger.info(f"Deterministic Baseline Val: MAE={base_val_mae:.4f}, RMSE={base_val_rmse:.4f}, PoissonDev={base_val_pdev:.4f}")
        logger.info(f"Deterministic Baseline Test: MAE={base_test_mae:.4f}, RMSE={base_test_rmse:.4f}, PoissonDev={base_test_pdev:.4f}")

        # Formulations to test on Validation Set
        candidates = {
            "poisson": {
                "objective": "poisson",
                "learning_rate": 0.03,
                "num_leaves": 31,
                "min_child_samples": 25,
                "n_estimators": 350,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42
            },
            "tweedie": {
                "objective": "tweedie",
                "tweedie_variance_power": 1.5,
                "learning_rate": 0.03,
                "num_leaves": 31,
                "min_child_samples": 25,
                "n_estimators": 350,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42
            },
            "regression": {
                "objective": "regression",
                "learning_rate": 0.03,
                "num_leaves": 31,
                "min_child_samples": 25,
                "n_estimators": 350,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42
            }
        }

        val_results = {}
        models = {}

        for name, params in candidates.items():
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train)
            val_preds = np.clip(model.predict(X_val), 0.0, None)
            
            val_mae = float(np.mean(np.abs(val_preds - y_val)))
            val_rmse = float(np.sqrt(np.mean((val_preds - y_val)**2)))
            val_pdev = mean_poisson_deviance(y_val, val_preds)
            val_calib = float(np.sum(val_preds) / max(1e-5, np.sum(y_val)))

            val_results[name] = {
                "mae": round(val_mae, 4),
                "rmse": round(val_rmse, 4),
                "poisson_deviance": round(val_pdev, 4),
                "calibration_ratio": round(val_calib, 4)
            }
            models[name] = model
            logger.info(f"Candidate '{name}' Val: MAE={val_mae:.4f}, RMSE={val_rmse:.4f}, PoissonDev={val_pdev:.4f}, Calib={val_calib:.4f}")

        # Select best formulation based on Validation Set Poisson Deviance
        best_name = min(val_results.keys(), key=lambda k: val_results[k]["poisson_deviance"])
        best_model = models[best_name]
        logger.info(f"Selected Best Model Formulation on Validation Set: '{best_name}' (PoissonDev={val_results[best_name]['poisson_deviance']})")

        # FROZEN EVALUATION ON UNTOUCHED 2025/26 TEST SET
        test_preds = np.clip(best_model.predict(X_test), 0.0, None)
        test_mae = float(np.mean(np.abs(test_preds - y_test)))
        test_rmse = float(np.sqrt(np.mean((test_preds - y_test)**2)))
        test_pdev = mean_poisson_deviance(y_test, test_preds)
        test_calib = float(np.sum(test_preds) / max(1e-5, np.sum(y_test)))
        spear_corr, _ = spearmanr(test_preds, y_test)
        pears_corr, _ = pearsonr(test_preds, y_test)

        logger.info("=== UNTOUCHED 2025/26 TEST SET FINAL EVALUATION ===")
        logger.info(f"Deterministic Baseline Test: MAE={base_test_mae:.4f}, RMSE={base_test_rmse:.4f}, PoissonDev={base_test_pdev:.4f}")
        logger.info(f"Selected ML ({best_name}) Test: MAE={test_mae:.4f}, RMSE={test_rmse:.4f}, PoissonDev={test_pdev:.4f}")

        mae_impr_pct = round(((base_test_mae - test_mae) / base_test_mae) * 100.0, 2)
        rmse_impr_pct = round(((base_test_rmse - test_rmse) / base_test_rmse) * 100.0, 2)
        pdev_impr_pct = round(((base_test_pdev - test_pdev) / base_test_pdev) * 100.0, 2)

        logger.info(f"Out-of-Sample MAE Improvement: {mae_impr_pct}%")
        logger.info(f"Out-of-Sample RMSE Improvement: {rmse_impr_pct}%")
        logger.info(f"Out-of-Sample Poisson Deviance Improvement: {pdev_impr_pct}%")

        # Feature Importance
        imp_df = pd.DataFrame({
            "feature": FEATURE_COLS,
            "importance": best_model.feature_importances_
        }).sort_values(by="importance", ascending=False).reset_index(drop=True)

        # Save Best Model Artifact
        best_path = os.path.join(self.model_dir, "xg_v1_lgbm.pkl")
        with open(best_path, "wb") as f:
            pickle.dump(best_model, f)
        logger.info(f"Saved best model artifact to {best_path}.")

        # Save Evaluation Report JSON
        report = {
            "model_version": "xg_v1_lgbm",
            "selected_formulation": best_name,
            "training_seasons": ["2022-23", "2023-24"],
            "validation_season": "2024-25",
            "test_season": "2025-26",
            "validation_candidate_results": val_results,
            "test_evaluation": {
                "baseline_mae": round(base_test_mae, 4),
                "ml_mae": round(test_mae, 4),
                "mae_improvement_pct": mae_impr_pct,
                "baseline_rmse": round(base_test_rmse, 4),
                "ml_rmse": round(test_rmse, 4),
                "rmse_improvement_pct": rmse_impr_pct,
                "baseline_poisson_deviance": round(base_test_pdev, 4),
                "ml_poisson_deviance": round(test_pdev, 4),
                "poisson_deviance_improvement_pct": pdev_impr_pct,
                "calibration_ratio": round(test_calib, 4),
                "spearman_correlation": round(float(spear_corr), 4),
                "pearson_correlation": round(float(pears_corr), 4)
            },
            "top_10_features": imp_df.head(10).to_dict(orient="records"),
            "deployment_recommendation": "APPROVED" if (test_pdev < base_test_pdev and test_mae <= base_test_mae) else "REJECTED"
        }

        report_path = os.path.join(self.model_dir, "phase3a_evaluation_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved evaluation report to {report_path}.")

        return report

if __name__ == "__main__":
    pipeline = XGModelPipeline()
    pipeline.train_and_evaluate()
