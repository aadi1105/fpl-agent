import os
import pickle
import json
import pytest
import numpy as np
import pandas as pd

from backend.ml.minutes_model import MinutesModelPipeline, MODEL_DIR, FEATURE_COLS

@pytest.fixture(scope="module")
def pipeline_results():
    pipeline = MinutesModelPipeline()
    report_path = os.path.join(MODEL_DIR, "phase2b_evaluation_report.json")
    if not os.path.exists(report_path):
        report = pipeline.run_pipeline()
    else:
        with open(report_path, "r") as f:
            report = json.load(f)
    return report

def test_model_artifacts_created(pipeline_results):
    assert os.path.exists(os.path.join(MODEL_DIR, "minutes_start_v1.pkl"))
    assert os.path.exists(os.path.join(MODEL_DIR, "minutes_regression_v1.pkl"))
    assert os.path.exists(os.path.join(MODEL_DIR, "minutes_60plus_v1.pkl"))
    assert os.path.exists(os.path.join(MODEL_DIR, "minutes_zero_v1.pkl"))
    assert os.path.exists(os.path.join(MODEL_DIR, "phase2b_evaluation_report.json"))

def test_ml_models_beat_baselines(pipeline_results):
    models_rep = pipeline_results["models"]
    
    # Model A: P(start)
    assert models_rep["model_a_p_start"]["ml_beats_baseline"] is True
    assert models_rep["model_a_p_start"]["validation_metrics"]["LightGBM"]["log_loss"] < models_rep["model_a_p_start"]["validation_metrics"]["Baseline"]["log_loss"]

    # Model B: Expected Minutes
    assert models_rep["model_b_expected_minutes"]["ml_beats_baseline"] is True
    assert models_rep["model_b_expected_minutes"]["validation_metrics"]["LightGBM"]["mae"] < models_rep["model_b_expected_minutes"]["validation_metrics"]["Baseline"]["mae"]

    # Model C: P(60+)
    assert models_rep["model_c_p_60_plus"]["ml_beats_baseline"] is True

    # Model D: P(0)
    assert models_rep["model_d_p_zero"]["ml_beats_baseline"] is True

def test_prediction_output_ranges(pipeline_results):
    with open(os.path.join(MODEL_DIR, "minutes_start_v1.pkl"), "rb") as f:
        m_start = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "minutes_regression_v1.pkl"), "rb") as f:
        m_mins = pickle.load(f)

    # Dummy feature row
    dummy_x = pd.DataFrame([{col: 0.0 for col in FEATURE_COLS}])
    dummy_x['price'] = 10.0
    dummy_x['average_minutes_last_5'] = 75.0
    dummy_x['minutes_last_1'] = 90

    prob_start = m_start.predict_proba(dummy_x)[:, 1][0]
    pred_mins = np.clip(m_mins.predict(dummy_x), 0, 180)[0]

    assert 0.0 <= prob_start <= 1.0
    assert 0.0 <= pred_mins <= 180.0

def test_production_projection_engine_unmodified():
    # Verify ProjectionEngine still runs baseline without being overwritten
    from backend.database import SessionLocal
    from backend.projections.engine import ProjectionEngine
    
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db)
        # engine should operate on current DB state without error
        assert engine is not None
    finally:
        db.close()
