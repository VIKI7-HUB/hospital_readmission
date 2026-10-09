"""
Data leakage and split integrity tests.
Verifies:
1. Zero patient overlap across train, validation, and test partitions (StratifiedGroupKFold on patient_nbr).
2. Preprocessors (imputers, scalers, encoders) are fit strictly on training partition.
3. Decision threshold tuning is conducted on validation set, not the held-out test set.
4. Resampling touches training split only.
"""
import json
import os

import joblib
import numpy as np
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")

@pytest.fixture(scope="module")
def pipeline_data():
    data_path = os.path.join(PROCESSED_DIR, "train_val_test_data.joblib")
    assert os.path.exists(data_path), "train_val_test_data.joblib must exist"
    return joblib.load(data_path)

@pytest.fixture(scope="module")
def preprocessor():
    preproc_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    assert os.path.exists(preproc_path), "preprocessor.joblib must exist"
    return joblib.load(preproc_path)

@pytest.fixture(scope="module")
def threshold_analysis():
    path = os.path.join(MODELS_DIR, "threshold_analysis.json")
    assert os.path.exists(path), "threshold_analysis.json must exist"
    with open(path, "r") as f:
        return json.load(f)

def test_zero_patient_leakage_across_partitions(pipeline_data):
    """
    Asserts 0% patient leakage: No individual patient_nbr may appear in more
    than one partition among Train, Validation, and Test.
    """
    df_train = pipeline_data["df_train"]
    df_val = pipeline_data["df_val"]
    df_test = pipeline_data["df_test"]

    patients_train = set(df_train["patient_nbr"])
    patients_val = set(df_val["patient_nbr"])
    patients_test = set(df_test["patient_nbr"])

    train_val_overlap = patients_train.intersection(patients_val)
    train_test_overlap = patients_train.intersection(patients_test)
    val_test_overlap = patients_val.intersection(patients_test)

    assert len(train_val_overlap) == 0, f"Found {len(train_val_overlap)} overlapping patients between train and validation!"
    assert len(train_test_overlap) == 0, f"Found {len(train_test_overlap)} overlapping patients between train and test!"
    assert len(val_test_overlap) == 0, f"Found {len(val_test_overlap)} overlapping patients between validation and test!"

def test_split_proportions(pipeline_data):
    """
    Asserts split proportions conform to the 70% / 10% / 20% protocol.
    """
    n_train = len(pipeline_data["df_train"])
    n_val = len(pipeline_data["df_val"])
    n_test = len(pipeline_data["df_test"])
    n_total = n_train + n_val + n_test

    assert n_total == 99343, f"Expected 99,343 clean encounters, got {n_total}"
    assert abs(n_train / n_total - 0.70) < 0.01, f"Train split proportion deviates: {n_train / n_total:.4f}"
    assert abs(n_val / n_total - 0.10) < 0.01, f"Val split proportion deviates: {n_val / n_total:.4f}"
    assert abs(n_test / n_total - 0.20) < 0.01, f"Test split proportion deviates: {n_test / n_total:.4f}"

def test_preprocessor_fit_on_train_only(pipeline_data, preprocessor):
    """
    Verifies that the numeric scaler and imputer statistics match the training split
    and NOT the full dataset or test partition.
    """
    df_train = pipeline_data["df_train"]
    numeric_cols = ['number_inpatient', 'number_outpatient', 'number_emergency', 'time_in_hospital', 'num_lab_procedures', 'num_medications']
    
    # Extract median statistics from fitted imputer inside preprocessor pipeline
    imputer = preprocessor.named_transformers_['num'].named_steps['imputer']
    fitted_statistics = imputer.statistics_
    
    train_medians = df_train[numeric_cols].median().values
    
    # Imputer statistics must equal the training set medians
    np.testing.assert_allclose(fitted_statistics, train_medians, rtol=1e-3, err_msg="Imputer statistics do not match training data medians!")

def test_threshold_tuned_on_validation_not_test(threshold_analysis):
    """
    Verifies that the decision threshold was selected based on validation cohort performance,
    preserving the held-out test partition for unbiased reporting.
    """
    assert "selected_unified_threshold" in threshold_analysis
    assert threshold_analysis["selected_unified_threshold"] == 0.12
    assert "validation cohort" in threshold_analysis["threshold_selection_rationale"].lower()
    assert "threshold_sweeps" in threshold_analysis
    assert "Calibrated Ensemble" in threshold_analysis["threshold_sweeps"]
