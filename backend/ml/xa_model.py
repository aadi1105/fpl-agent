import os
import json
import logging
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, Any, Tuple
from scipy.stats import spearmanr, pearsonr

logger = logging.getLogger("xa_model")
logging.basicConfig(level=logging.INFO)

DATA_PATH = "data/ml/historical_xa_dataset.csv"
MODEL_DIR = "models"

FEATURE_COLS_WITHOUT_XG = [
    "price", "fixture_difficulty",
    "team_attack_rating", "team_defence_rating",
    "opponent_attack_rating", "opponent_defence_rating",
    "expected_minutes_v1", "p_start", "p_60_plus", "p_zero",
    "minutes_last_1", "minutes_last_5", "starts_last_5",
    "assists_last_1", "assists_last_3", "assists_last_5", "assists_last_10",
    "xa_last_1", "xa_last_3", "xa_last_5", "xa_last_10",
    "creativity_last_5", "creativity_last_10", "threat_last_5",
    "assists_per_90_last_5", "xa_per_90_last_5", "creativity_per_90_last_5",
    "pos_GKP", "pos_DEF", "pos_MID", "pos_FWD",
    "home_away_is_home"
]

FEATURE_COLS_WITH_XG = FEATURE_COLS_WITHOUT_XG + ["xg_v1_lgbm_pred"]

POSITION_BASELINE_XA90 = {
    "GKP": 0.0,
    "DEF": 0.05,
    "MID": 0.18,
    "FWD": 0.15
}

def calculate_deterministic_baseline_xa(df: pd.DataFrame) -> np.ndarray:
    """Compute current deterministic xA baseline predictions for a DataFrame of fixtures."""
    baseline_preds = []
    for idx, row in df.iterrows():
        pos = str(row['position'])
        price = float(row['price'])
        x_mins = float(row['expected_minutes_v1'])
        mins_ratio = min(1.0, max(0.0, x_mins / 90.0))

        # Position + Price Tier Baseline xA per 90
        base_xa90 = POSITION_BASELINE_XA90.get(pos, 0.12)
        if pos == "MID":
            if price >= 9.0: base_xa90 = 0.32
            elif price >= 6.5: base_xa90 = 0.20
            else: base_xa90 = 0.10
        elif pos == "FWD":
            if price >= 9.0: base_xa90 = 0.22
            elif price >= 6.5: base_xa90 = 0.15
            else: base_xa90 = 0.08
        elif pos == "DEF":
            if price >= 6.0: base_xa90 = 0.15
            elif price >= 5.0: base_xa90 = 0.08
            else: base_xa90 = 0.03

        opp_def = float(row['opponent_defence_rating'])
        is_home = (row['home_away'] == 'H')
        home_factor = 1.05 if is_home else 0.95
        att_multiplier = min(1.50, max(0.60, (1000.0 / max(300.0, opp_def)) * home_factor))

        baseline_xa = base_xa90 * mins_ratio * att_multiplier
        baseline_preds.append(max(0.0, baseline_xa))

    return np.array(baseline_preds)

def mean_poisson_deviance(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute mean Poisson deviance."""
    eps = 1e-9
    y_pred = np.clip(y_pred, eps, None)
    dev = np.where(y_true > 0, 2 * (y_true * np.log(np.maximum(eps, y_true) / y_pred) - (y_true - y_pred)), 2 * y_pred)
    return float(np.mean(dev))

def prepare_features(df: pd.DataFrame, include_xg: bool = True) -> pd.DataFrame:
    """Extract and encode feature columns for ML modeling."""
    feat_df = df.copy()
    feat_df['home_away_is_home'] = (feat_df['home_away'] == 'H').astype(float)
    feat_df['pos_GKP'] = (feat_df['position'] == 'GKP').astype(float)
    feat_df['pos_DEF'] = (feat_df['position'] == 'DEF').astype(float)
    feat_df['pos_MID'] = (feat_df['position'] == 'MID').astype(float)
    feat_df['pos_FWD'] = (feat_df['position'] == 'FWD').astype(float)

    cols = FEATURE_COLS_WITH_XG if include_xg else FEATURE_COLS_WITHOUT_XG
    return feat_df[cols].astype(float)

class XAModelPipeline:
    def __init__(self, data_path: str = DATA_PATH, model_dir: str = MODEL_DIR):
        self.data_path = data_path
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df = pd.read_csv(self.data_path, low_memory=False)
        train_df = df[df['split'] == 'train'].reset_index(drop=True)
        val_df = df[df['split'] == 'validation'].reset_index(drop=True)
        test_df = df[df['split'] == 'test'].reset_index(drop=True)

        logger.info(f"Loaded dataset: Train={len(train_df)} rows, Val={len(val_df)} rows, Test={len(test_df)} rows.")
        return train_df, val_df, test_df

    def train_and_evaluate(self) -> Dict[str, Any]:
        train_df, val_df, test_df = self.load_data()

        y_train = train_df['target_assists'].values.astype(float)
        y_val = val_df['target_assists'].values.astype(float)
        y_test = test_df['target_assists'].values.astype(float)

        # Baseline evaluation
        base_val_preds = calculate_deterministic_baseline_xa(val_df)
        base_test_preds = calculate_deterministic_baseline_xa(test_df)

        base_val_mae = float(np.mean(np.abs(base_val_preds - y_val)))
        base_val_rmse = float(np.sqrt(np.mean((base_val_preds - y_val)**2)))
        base_val_pdev = mean_poisson_deviance(y_val, base_val_preds)

        base_test_mae = float(np.mean(np.abs(base_test_preds - y_test)))
        base_test_rmse = float(np.sqrt(np.mean((base_test_preds - y_test)**2)))
        base_test_pdev = mean_poisson_deviance(y_test, base_test_preds)

        logger.info(f"Deterministic Baseline Val: MAE={base_val_mae:.4f}, RMSE={base_val_rmse:.4f}, PoissonDev={base_val_pdev:.4f}")
        logger.info(f"Deterministic Baseline Test: MAE={base_test_mae:.4f}, RMSE={base_test_rmse:.4f}, PoissonDev={base_test_pdev:.4f}")

        # STEP 1: xG ABLATION TEST ON VALIDATION SET
        logger.info("=== RUNNING xG ABLATION TEST ON VALIDATION SET ===")
        X_train_no_xg = prepare_features(train_df, include_xg=False)
        X_val_no_xg = prepare_features(val_df, include_xg=False)

        X_train_with_xg = prepare_features(train_df, include_xg=True)
        X_val_with_xg = prepare_features(val_df, include_xg=True)

        params = {
            "objective": "poisson",
            "learning_rate": 0.03,
            "num_leaves": 31,
            "min_child_samples": 25,
            "n_estimators": 350,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42
        }

        m_no_xg = lgb.LGBMRegressor(**params)
        m_no_xg.fit(X_train_no_xg, y_train)
        p_val_no_xg = np.clip(m_no_xg.predict(X_val_no_xg), 0.0, None)
        pdev_no_xg = mean_poisson_deviance(y_val, p_val_no_xg)
        mae_no_xg = float(np.mean(np.abs(p_val_no_xg - y_val)))

        m_with_xg = lgb.LGBMRegressor(**params)
        m_with_xg.fit(X_train_with_xg, y_train)
        p_val_with_xg = np.clip(m_with_xg.predict(X_val_with_xg), 0.0, None)
        pdev_with_xg = mean_poisson_deviance(y_val, p_val_with_xg)
        mae_with_xg = float(np.mean(np.abs(p_val_with_xg - y_val)))

        logger.info(f"Model WITHOUT xG Feature Val: MAE={mae_no_xg:.4f}, PoissonDev={pdev_no_xg:.4f}")
        logger.info(f"Model WITH xG Feature Val: MAE={mae_with_xg:.4f}, PoissonDev={pdev_with_xg:.4f}")

        # Decide whether to include xG based on validation deviance
        use_xg_feature = bool(pdev_with_xg < pdev_no_xg)
        logger.info(f"xG Feature Ablation Result: {'KEEP xG FEATURE' if use_xg_feature else 'EXCLUDE xG FEATURE'}")

        # STEP 2: FORMULATION SELECTION ON VALIDATION SET
        feature_cols = FEATURE_COLS_WITH_XG if use_xg_feature else FEATURE_COLS_WITHOUT_XG
        X_train = prepare_features(train_df, include_xg=use_xg_feature)
        X_val = prepare_features(val_df, include_xg=use_xg_feature)
        X_test = prepare_features(test_df, include_xg=use_xg_feature)

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

        for name, p_dict in candidates.items():
            model = lgb.LGBMRegressor(**p_dict)
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

        best_name = min(val_results.keys(), key=lambda k: val_results[k]["poisson_deviance"])
        best_model = models[best_name]
        logger.info(f"Selected Best xA Model Formulation: '{best_name}' (PoissonDev={val_results[best_name]['poisson_deviance']})")

        # STEP 3: FROZEN EVALUATION ON UNTOUCHED 2025/26 TEST SET
        test_preds = np.clip(best_model.predict(X_test), 0.0, None)
        test_mae = float(np.mean(np.abs(test_preds - y_test)))
        test_rmse = float(np.sqrt(np.mean((test_preds - y_test)**2)))
        test_pdev = mean_poisson_deviance(y_test, test_preds)
        test_calib = float(np.sum(test_preds) / max(1e-5, np.sum(y_test)))
        spear_corr, _ = spearmanr(test_preds, y_test)
        pears_corr, _ = pearsonr(test_preds, y_test)

        logger.info("=== UNTOUCHED 2025/26 TEST SET FINAL EVALUATION FOR xA ===")
        logger.info(f"Deterministic Baseline Test: MAE={base_test_mae:.4f}, RMSE={base_test_rmse:.4f}, PoissonDev={base_test_pdev:.4f}")
        logger.info(f"Selected ML ({best_name}) Test: MAE={test_mae:.4f}, RMSE={test_rmse:.4f}, PoissonDev={test_pdev:.4f}")

        mae_impr_pct = round(((base_test_mae - test_mae) / base_test_mae) * 100.0, 2)
        rmse_impr_pct = round(((base_test_rmse - test_rmse) / base_test_rmse) * 100.0, 2)
        pdev_impr_pct = round(((base_test_pdev - test_pdev) / base_test_pdev) * 100.0, 2)

        logger.info(f"Out-of-Sample MAE Improvement: {mae_impr_pct}%")
        logger.info(f"Out-of-Sample RMSE Improvement: {rmse_impr_pct}%")
        logger.info(f"Out-of-Sample Poisson Deviance Improvement: {pdev_impr_pct}%")

        # BUCKET CALIBRATION BREAKDOWN ON TEST SET
        test_df_copy = test_df.copy()
        test_df_copy['pred_xa'] = test_preds

        bins = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 999.0]
        labels = ["0–0.05", "0.05–0.10", "0.10–0.20", "0.20–0.30", "0.30–0.50", "0.50–0.75", "0.75–1.00", "1.00+"]
        test_df_copy['bucket'] = pd.cut(test_df_copy['pred_xa'], bins=bins, labels=labels, right=False, include_lowest=True)

        bucket_breakdown = []
        for l in labels:
            b_df = test_df_copy[test_df_copy['bucket'] == l]
            n_fix = len(b_df)
            if n_fix > 0:
                m_pred = float(b_df['pred_xa'].mean())
                m_act = float(b_df['target_assists'].mean())
                tot_b_pred = float(b_df['pred_xa'].sum())
                tot_b_act = float(b_df['target_assists'].sum())
                ratio = (tot_b_pred / tot_b_act) if tot_b_act > 0 else (m_pred / m_act if m_act > 0 else 0.0)
            else:
                m_pred, m_act, ratio = 0.0, 0.0, 0.0

            bucket_breakdown.append({
                "bucket": l,
                "fixtures": n_fix,
                "mean_pred_xa": round(m_pred, 4),
                "actual_assists_per_fixture": round(m_act, 4),
                "pred_act_ratio": round(ratio, 4)
            })

        # Feature Importance
        imp_df = pd.DataFrame({
            "feature": feature_cols,
            "importance": best_model.feature_importances_
        }).sort_values(by="importance", ascending=False).reset_index(drop=True)

        # Save Model Artifact
        best_path = os.path.join(self.model_dir, "xa_v1_lgbm.pkl")
        with open(best_path, "wb") as f:
            pickle.dump(best_model, f)
        logger.info(f"Saved best xA model artifact to {best_path}.")

        report = {
            "model_version": "xa_v1_lgbm",
            "selected_formulation": best_name,
            "xg_ablation_result": {
                "included_xg_feature": use_xg_feature,
                "val_poisson_dev_without_xg": round(pdev_no_xg, 4),
                "val_poisson_dev_with_xg": round(pdev_with_xg, 4)
            },
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
            "bucket_calibration_breakdown": bucket_breakdown,
            "top_10_features": imp_df.head(10).to_dict(orient="records"),
            "deployment_recommendation": "APPROVED" if (test_pdev < base_test_pdev and test_mae <= base_test_mae) else "REJECTED"
        }

        report_path = os.path.join(self.model_dir, "phase3b_evaluation_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved evaluation report to {report_path}.")

        return report

if __name__ == "__main__":
    pipeline = XAModelPipeline()
    pipeline.train_and_evaluate()
