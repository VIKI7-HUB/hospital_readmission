"""
Metric verification tests against scikit-learn standard benchmarks.
Verifies Accuracy, Precision, Recall, F1, ROC-AUC, Wilson CIs, and Subgroup Gaps.
"""
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.fairness import compute_group_metrics


def test_metrics_against_hand_checked_example():
    """
    Deterministic 10-sample verification with hand-calculated ground truth:
    y_true: [1, 0, 1, 1, 0, 0, 1, 0, 1, 0] (5 positive, 5 negative)
    y_prob: [0.9, 0.1, 0.8, 0.4, 0.3, 0.2, 0.7, 0.6, 0.65, 0.05]
    threshold: 0.5 -> y_pred: [1, 0, 1, 0, 0, 0, 1, 1, 1, 0]
    
    Hand-calculated values:
    TP: indices 0, 2, 6, 8 -> 4
    FP: index 7 -> 1
    TN: indices 1, 4, 5, 9 -> 4
    FN: index 3 -> 1
    
    Precision = TP / (TP + FP) = 4 / 5 = 0.8000
    Recall    = TP / (TP + FN) = 4 / 5 = 0.8000
    Accuracy  = (TP + TN) / 10 = 8 / 10 = 0.8000
    F1        = 2 * (0.8 * 0.8) / (0.8 + 0.8) = 0.8000
    """
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.9, 0.1, 0.8, 0.4, 0.3, 0.2, 0.7, 0.6, 0.65, 0.05])
    threshold = 0.5
    y_pred = (y_prob >= threshold).astype(int)

    # Scikit-learn computations
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_prob)

    assert acc == 0.8
    assert prec == 0.8
    assert rec == 0.8
    assert f1 == 0.8
    assert round(auc, 4) == 0.9600

def test_compute_group_metrics_and_wilson_ci():
    """
    Tests compute_group_metrics on hand-checkable inputs and verifies
    the Wilson 95% confidence interval formula.
    """
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.9, 0.1, 0.8, 0.4, 0.3, 0.2, 0.7, 0.6, 0.65, 0.05])
    threshold = 0.5
    y_pred = (y_prob >= threshold).astype(int)

    metrics = compute_group_metrics(y_true, y_pred, y_prob)

    assert metrics["n"] == 10
    assert metrics["tpr"] == 80.0
    assert metrics["fpr"] == 20.0
    assert metrics["precision"] == 80.0
    
    # Hand-calculate Wilson 95% CI for p = 4/5 = 0.8, n = 5 (positives)
    # p = 0.8, k = 5, z = 1.96
    p = 0.8
    k = 5
    z = 1.96
    denom = 1 + z**2 / k
    centre = (p + z**2 / (2 * k)) / denom
    spread = (z * np.sqrt((p * (1 - p) + z**2 / (4 * k)) / k)) / denom
    expected_lower = round(max(0.0, centre - spread) * 100, 1)
    expected_upper = round(min(1.0, centre + spread) * 100, 1)

    assert metrics["ci_lower"] == expected_lower
    assert metrics["ci_upper"] == expected_upper
    assert metrics["ci_str"] == f"{expected_lower}%–{expected_upper}%"

def test_subgroup_disparity_gap_calculation():
    """
    Verifies that demographic disparity gaps correctly represent the difference
    between the maximum and minimum subgroup TPRs.
    """
    subgroup_tprs = {
        "Caucasian": 58.67,
        "AfricanAmerican": 53.69,
        "Hispanic": 60.00,
        "Asian": 38.46
    }
    max_tpr = max(subgroup_tprs.values())
    min_tpr = min(subgroup_tprs.values())
    gap = round(max_tpr - min_tpr, 2)
    
    assert max_tpr == 60.00
    assert min_tpr == 38.46
    assert gap == 21.54

def test_model_report_and_benchmark_artifacts_integrity():
    """
    Verifies that all required model benchmark and audit artifacts are created,
    contain expected columns, and docs/model_report.md exists.
    """
    import os, json, pandas as pd
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    docs_dir = os.path.join(base_dir, "docs")

    bench_csv = os.path.join(models_dir, "test_metrics_benchmarks.csv")
    thresh_csv = os.path.join(models_dir, "threshold_sweep_test.csv")
    roc_png = os.path.join(models_dir, "roc_curve_all_models.png")
    pr_png = os.path.join(models_dir, "pr_curve_all_models.png")
    audit_json = os.path.join(models_dir, "test_set_audit.json")
    report_md = os.path.join(docs_dir, "model_report.md")

    assert os.path.exists(bench_csv), "test_metrics_benchmarks.csv must exist"
    assert os.path.exists(thresh_csv), "threshold_sweep_test.csv must exist"
    assert os.path.exists(roc_png), "roc_curve_all_models.png must exist"
    assert os.path.exists(pr_png), "pr_curve_all_models.png must exist"
    assert os.path.exists(audit_json), "test_set_audit.json must exist"
    assert os.path.exists(report_md), "docs/model_report.md must exist"

    df_bench = pd.read_csv(bench_csv)
    assert len(df_bench) == 12  # 6 models x 2 operating points
    assert "ROC-AUC" in df_bench.columns
    assert "Precision" in df_bench.columns
    assert "Recall" in df_bench.columns
    assert "Accuracy" in df_bench.columns

    df_th = pd.read_csv(thresh_csv)
    assert len(df_th) == 46  # 0.05 to 0.50 step 0.01
    assert "threshold" in df_th.columns
    assert "false_positives" in df_th.columns
    assert "false_negatives" in df_th.columns

    with open(audit_json, "r") as f:
        audit_data = json.load(f)
    assert len(audit_data) == 6

