"""Evaluate calibrated models once on the held-out test split."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from readmission.calibrate import apply_calibrator, run_calibration
from readmission.features import build_fairness_attributes, build_features

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"


def _config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _metrics(target: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(target, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(target, predicted)),
        "precision": float(precision_score(target, predicted, zero_division=0)),
        "recall": float(recall_score(target, predicted, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "npv": float(tn / (tn + fn)) if tn + fn else 0.0,
        "f1": float(f1_score(target, predicted, zero_division=0)),
        "f2": float(fbeta_score(target, predicted, beta=2, zero_division=0)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "pr_auc": float(average_precision_score(target, probabilities)),
        "brier_score": float(brier_score_loss(target, probabilities)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def _points(values: np.ndarray) -> list[float | None]:
    return [float(value) if np.isfinite(value) else None for value in values]


def _curves(target: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    fpr, tpr, roc_thresholds = roc_curve(target, probabilities)
    precision, recall, pr_thresholds = precision_recall_curve(target, probabilities)
    observed, predicted = calibration_curve(target, probabilities, n_bins=10, strategy="uniform")
    return {
        "roc": {
            "false_positive_rate": _points(fpr),
            "true_positive_rate": _points(tpr),
            "thresholds": _points(roc_thresholds),
        },
        "precision_recall": {
            "precision": _points(precision),
            "recall": _points(recall),
            "thresholds": _points(pr_thresholds),
        },
        "reliability": {
            "observed_rate": _points(observed),
            "mean_predicted_probability": _points(predicted),
        },
    }


def _threshold_sweep(target: np.ndarray, probabilities: np.ndarray) -> list[dict[str, int | float]]:
    rows: list[dict[str, int | float]] = []
    for threshold in np.round(np.arange(2, 61) / 100, 2):
        predicted = probabilities >= threshold
        tn, fp, fn, tp = confusion_matrix(target, predicted, labels=[0, 1]).ravel()
        rows.append(
            {
                "threshold": float(threshold),
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
            }
        )
    return rows


def _risk_tier(probability: np.ndarray, tiers: dict[str, Any]) -> np.ndarray:
    low = float(tiers["low_below"])
    high = float(tiers["high_at_or_above"])
    return np.select(
        [probability < low, probability >= high],
        ["Low", "High"],
        default="Elevated",
    )


def evaluate_test_set(
    models: dict[str, Any],
    calibrators: dict[str, dict[str, Any]],
    thresholds: dict[str, Any],
    champion: dict[str, Any],
    tiers: dict[str, Any],
    split: dict[str, Any],
    config: dict[str, Any],
    feature_config: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Read test rows once, score them, and write evaluation artifacts."""
    test_ids = split["test"]
    test = pd.read_parquet(
        ROOT / config["paths"]["cleaned_data"],
        filters=[("encounter_id", "in", test_ids)],
    )
    if len(test) != len(test_ids):
        raise ValueError("Test encounter IDs do not match the cleaned dataset.")
    features = build_features(test, feature_config)
    target = test["readmit_30"].astype(int).to_numpy()
    raw: dict[str, np.ndarray] = {}
    calibrated: dict[str, np.ndarray] = {}
    for name, model in models.items():
        raw[name] = model.predict_proba(features)[:, 1]
        calibrated[name] = apply_calibrator(calibrators[name], raw[name])

    metrics: dict[str, Any] = {}
    comparison: list[dict[str, Any]] = []
    for name in models:
        threshold = float(thresholds[name]["operating"]["threshold"])
        model_metrics = _metrics(target, calibrated[name], threshold)
        model_metrics["curves"] = _curves(target, calibrated[name])
        model_metrics["threshold_sweep"] = _threshold_sweep(target, calibrated[name])
        metrics[name] = model_metrics
        table_metrics = {
            key: value
            for key, value in model_metrics.items()
            if key not in {"curves", "threshold_sweep"}
        }
        comparison.append({"model": name, **table_metrics})

    champion_name = str(champion["model"])
    champion_probability = calibrated[champion_name]
    feature_frame = features
    fairness = build_fairness_attributes(test)
    predictions = pd.DataFrame(
        {
            "encounter_id": test["encounter_id"].to_numpy(),
            "y_true": target,
            "probability_raw": raw[champion_name],
            "probability_calibrated": champion_probability,
            "tier": _risk_tier(champion_probability, tiers),
            "age_band": fairness["age_band"].astype(str).to_numpy(),
            "gender": test["gender"].astype(str).to_numpy(),
            "race": test["race"].astype(str).to_numpy(),
            "discharge_group": feature_frame["discharge_group"].astype(str).to_numpy(),
            "diag_1_category": feature_frame["diag_1_category"].astype(str).to_numpy(),
            "number_inpatient": feature_frame["number_inpatient"].to_numpy(),
        }
    )
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "metrics.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    pd.DataFrame(comparison).to_csv(ROOT / "artifacts" / "model_comparison.csv", index=False)
    predictions.to_parquet(ROOT / "artifacts" / "test_predictions.parquet", index=False)
    return metrics, pd.DataFrame(comparison)


def run_evaluation() -> pd.DataFrame:
    """Calibrate on validation rows, then evaluate the test split once."""
    config = _config()
    calibration = run_calibration()
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    feature_config = json.loads(
        (ROOT / "artifacts" / "feature_config.json").read_text(encoding="utf-8")
    )
    champion = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))
    thresholds = json.loads((ROOT / "artifacts" / "thresholds.json").read_text(encoding="utf-8"))[
        "models"
    ]
    tiers = json.loads((ROOT / "artifacts" / "tiers.json").read_text(encoding="utf-8"))
    models = {
        name: joblib.load(ROOT / "artifacts" / "models" / f"{name}.joblib")
        for name in calibration["calibrators"]
    }
    metrics, comparison = evaluate_test_set(
        models,
        calibration["calibrators"],
        thresholds,
        champion,
        tiers,
        split,
        config,
        feature_config,
    )
    champion_recall = float(metrics[champion["model"]]["recall"])
    target = float(config["evaluation"]["recall_target"])
    if abs(champion_recall - target) > 0.05:
        print(
            f"Warning: champion test recall {champion_recall:.3f} differs from "
            f"the validation target {target:.3f} by more than 0.05."
        )
    print(comparison.to_string(index=False))
    return comparison


def main() -> None:
    run_evaluation()


if __name__ == "__main__":
    main()
