"""Blend of all models via meta logistic regression."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from readmission.calibrate import apply_calibrator
from readmission.metrics import threshold_metrics

ROOT = Path(__file__).resolve().parents[2]


def run_blend() -> dict:
    """Train and evaluate 5-model meta logistic regression blend."""
    calibrators = joblib.load(ROOT / "artifacts" / "calibrators.joblib")
    models = ["logistic_regression", "random_forest", "lightgbm", "xgboost", "catboost"]

    val_dfs = {}
    for m in models:
        df = pd.read_parquet(ROOT / "artifacts" / "scores" / f"{m}__val.parquet")
        df = df.sort_values("encounter_id").reset_index(drop=True)
        val_dfs[m] = df

    y_val = val_dfs[models[0]]["y_true"].astype(int).to_numpy()
    patient_val = val_dfs[models[0]]["patient_nbr"].to_numpy()

    eps = 1e-6
    X_val = np.column_stack(
        [
            logit(
                np.clip(
                    apply_calibrator(calibrators[m], val_dfs[m]["p_raw"].to_numpy()),
                    eps,
                    1 - eps,
                )
            )
            for m in models
        ]
    )

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    oof_preds = np.zeros(len(y_val))

    for train_idx, val_idx in sgkf.split(X_val, y_val, groups=patient_val):
        meta = LogisticRegression(C=1.0)
        meta.fit(X_val[train_idx], y_val[train_idx])
        oof_preds[val_idx] = meta.predict_proba(X_val[val_idx])[:, 1]

    val_pr_auc_oof = float(average_precision_score(y_val, oof_preds))

    target_recall = 0.60
    candidates = np.linspace(0.01, 0.99, 99)
    best_t = 0.5
    best_prec = -1.0
    for cand in candidates:
        tm = threshold_metrics(y_val, oof_preds, cand)
        if tm["recall"] >= target_recall and tm["precision"] > best_prec:
            best_prec = tm["precision"]
            best_t = cand

    meta_full = LogisticRegression(C=1.0)
    meta_full.fit(X_val, y_val)

    test_dfs = {}
    for m in models:
        df = pd.read_parquet(ROOT / "artifacts" / "scores" / f"{m}__test.parquet")
        df = df.sort_values("encounter_id").reset_index(drop=True)
        test_dfs[m] = df

    y_test = test_dfs[models[0]]["y_true"].astype(int).to_numpy()
    X_test = np.column_stack(
        [
            logit(
                np.clip(
                    apply_calibrator(calibrators[m], test_dfs[m]["p_raw"].to_numpy()),
                    eps,
                    1 - eps,
                )
            )
            for m in models
        ]
    )
    test_preds = meta_full.predict_proba(X_test)[:, 1]

    test_roc_auc = float(roc_auc_score(y_test, test_preds))
    test_pr_auc = float(average_precision_score(y_test, test_preds))
    test_tm = threshold_metrics(y_test, test_preds, best_t)

    result = {
        "val_pr_auc_oof": val_pr_auc_oof,
        "threshold": float(best_t),
        "test": {
            "roc_auc": test_roc_auc,
            "pr_auc": test_pr_auc,
            "recall": test_tm["recall"],
            "precision": test_tm["precision"],
            "accuracy": test_tm["accuracy"],
            "f1": test_tm["f1"],
            "f2": test_tm["f2"],
            "flag_rate": test_tm["flag_rate"],
        },
        "eligible_for_champion": False,
        "reason": "no per-feature explanation is available for a blend",
    }

    (ROOT / "artifacts" / "blend.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
