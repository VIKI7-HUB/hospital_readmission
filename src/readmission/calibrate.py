"""Choose calibration, champion, and thresholds from validation data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold

from readmission.features import build_features

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"
MODEL_ORDER = (
    "logistic_regression",
    "random_forest",
    "lightgbm",
    "xgboost",
    "catboost",
)


def _config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _new_calibrator(method: str) -> Any:
    if method == "sigmoid":
        return LogisticRegression(solver="lbfgs", max_iter=1000)
    if method == "isotonic":
        return IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    raise ValueError(f"Unknown calibration method: {method}")


def _fit_calibrator(calibrator: Any, method: str, scores: np.ndarray, target: np.ndarray) -> Any:
    values = scores.reshape(-1, 1) if method == "sigmoid" else scores
    return calibrator.fit(values, target)


class ModelCalibrator:
    """Wrapper for calibrated probability predictions."""

    def __init__(self, method: str, estimator: Any) -> None:
        self.method = method
        self.estimator = estimator

    def predict(self, scores: np.ndarray) -> np.ndarray:
        values = np.asarray(scores, dtype=float)
        reshaped = values.reshape(-1, 1) if self.method == "sigmoid" else values
        if self.method == "sigmoid":
            return self.estimator.predict_proba(reshaped)[:, 1]
        return np.asarray(self.estimator.predict(reshaped), dtype=float)


def apply_calibrator(calibrator: dict[str, Any] | ModelCalibrator, scores: np.ndarray) -> np.ndarray:
    """Apply a fitted sigmoid or isotonic calibrator to model scores."""
    if isinstance(calibrator, ModelCalibrator):
        return calibrator.predict(scores)
    method = calibrator["method"]
    estimator = calibrator["estimator"]
    values = scores.reshape(-1, 1) if method == "sigmoid" else scores
    if method == "sigmoid":
        return estimator.predict_proba(values)[:, 1]
    return np.asarray(estimator.predict(values), dtype=float)


def fit_calibrators(
    raw_probabilities: dict[str, np.ndarray],
    target: pd.Series,
    groups: pd.Series,
    seed: int,
    folds: int = 5,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, float | str]]]:
    """Compare grouped cross-validated Brier scores and fit the selected calibrators."""
    labels = target.to_numpy(dtype=int)
    group_values = groups.to_numpy()
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    split_positions = list(splitter.split(np.zeros(len(labels)), labels, group_values))
    fitted: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, float | str]] = {}

    for name, raw_scores in raw_probabilities.items():
        scores = np.asarray(raw_scores, dtype=float)
        if len(scores) != len(labels):
            raise ValueError(f"Validation scores do not align for {name}.")
        cv_scores: dict[str, float] = {}
        for method in ("sigmoid", "isotonic"):
            predicted = np.full(len(labels), np.nan)
            for train_positions, valid_positions in split_positions:
                calibrator = _fit_calibrator(
                    _new_calibrator(method),
                    method,
                    scores[train_positions],
                    labels[train_positions],
                )
                predicted[valid_positions] = apply_calibrator(
                    {"method": method, "estimator": calibrator},
                    scores[valid_positions],
                )
            cv_scores[method] = float(brier_score_loss(labels, predicted))

        method = "sigmoid" if cv_scores["sigmoid"] <= cv_scores["isotonic"] else "isotonic"
        estimator = _fit_calibrator(_new_calibrator(method), method, scores, labels)
        fitted[name] = {"method": method, "estimator": estimator}
        evidence[name] = {
            "sigmoid_cv_brier": cv_scores["sigmoid"],
            "isotonic_cv_brier": cv_scores["isotonic"],
            "selected": method,
        }
    return fitted, evidence


def select_operating_threshold(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    recall_target: float,
) -> dict[str, float | bool]:
    """Select a validation threshold maximizing precision at the requested recall."""
    labels = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if labels.shape != scores.shape or not np.isfinite(scores).all():
        raise ValueError("Threshold labels and probabilities must align and be finite.")
    if not 0 < recall_target <= 1:
        raise ValueError("recall_target must be in (0, 1].")

    candidates: list[dict[str, float]] = []
    for threshold in np.unique(scores):
        predicted = scores >= threshold
        tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
        recall = float(tp / (tp + fn)) if tp + fn else 0.0
        precision = float(tp / (tp + fp)) if tp + fp else 0.0
        candidates.append(
            {"threshold": float(threshold), "precision": precision, "recall": recall}
        )
    feasible = [row for row in candidates if row["recall"] >= recall_target]
    if feasible:
        selected = max(feasible, key=lambda row: (row["precision"], row["threshold"]))
        target_met = True
    else:
        selected = max(
            candidates,
            key=lambda row: (row["recall"], row["precision"], row["threshold"]),
        )
        target_met = False
    return {**selected, "recall_target_met": target_met}


def select_cost_threshold(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    false_negative_cost: float,
    false_positive_cost: float,
) -> dict[str, float | int]:
    """Minimize assumed validation misclassification cost."""
    labels = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if labels.shape != scores.shape or not np.isfinite(scores).all():
        raise ValueError("Threshold labels and probabilities must align and be finite.")
    candidates = np.unique(
        np.concatenate(([0.0], scores, [np.nextafter(scores.max(), np.inf)]))
    )
    choices: list[dict[str, float | int]] = []
    for threshold in candidates:
        predicted = scores >= threshold
        tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
        cost = int(fn * false_negative_cost + fp * false_positive_cost)
        choices.append(
            {
                "threshold": float(threshold),
                "cost": cost,
                "false_positives": int(fp),
                "false_negatives": int(fn),
            }
        )
    return min(choices, key=lambda row: (row["cost"], -row["threshold"]))


def choose_champion(validation_average_precision: dict[str, float]) -> dict[str, Any]:
    """Choose the best validation PR-AUC, preferring simpler models within 0.005."""
    best_score = max(validation_average_precision.values())
    eligible = [
        name
        for name in MODEL_ORDER
        if name in validation_average_precision
        and best_score - validation_average_precision[name] <= 0.005
    ]
    champion = eligible[0]
    reason = (
        f"Selected {champion} by the simpler-model rule within 0.005 of the best "
        "validation average precision."
        if validation_average_precision[champion] != best_score
        else f"Selected {champion}, which had the best validation average precision."
    )
    return {
        "model": champion,
        "validation_average_precision": validation_average_precision[champion],
        "best_validation_average_precision": best_score,
        "simpler_model_order": list(MODEL_ORDER),
        "reason": reason,
    }


def run_calibration() -> dict[str, Any]:
    """Fit validation-only calibrators and save thresholds and champion metadata."""
    config = _config()
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    feature_config = json.loads(
        (ROOT / "artifacts" / "feature_config.json").read_text(encoding="utf-8")
    )
    validation_ids = split["validation"]
    frame = pd.read_parquet(
        ROOT / config["paths"]["cleaned_data"],
        filters=[("encounter_id", "in", validation_ids)],
    )
    if len(frame) != len(validation_ids):
        raise ValueError("Validation encounter IDs do not match the cleaned dataset.")
    features = build_features(frame, feature_config)
    target = frame["readmit_30"].astype(int)
    groups = frame["patient_nbr"]
    raw_probabilities: dict[str, np.ndarray] = {}
    for name in MODEL_ORDER:
        model = joblib.load(ROOT / "artifacts" / "models" / f"{name}.joblib")
        raw_probabilities[name] = model.predict_proba(features)[:, 1]

    calibration, evidence = fit_calibrators(
        raw_probabilities,
        target,
        groups,
        seed=int(config["models"]["seed"]),
        folds=int(config["evaluation"]["calibration_folds"]),
    )
    calibrated = {
        name: apply_calibrator(calibration[name], scores)
        for name, scores in raw_probabilities.items()
    }
    best_params = json.loads(
        (ROOT / "artifacts" / "best_params.json").read_text(encoding="utf-8")
    )
    validation_ap = {
        name: float(best_params[name]["validation_average_precision"])
        for name in MODEL_ORDER
    }
    champion = choose_champion(validation_ap)
    evaluation_config = config["evaluation"]
    thresholds: dict[str, Any] = {}
    recall_target = float(evaluation_config["recall_target"])
    fn_cost = float(evaluation_config["false_negative_cost"])
    fp_cost = float(evaluation_config["false_positive_cost"])
    for name in MODEL_ORDER:
        probabilities = calibrated[name]
        thresholds[name] = {
            "operating": select_operating_threshold(
                target, probabilities, recall_target
            ),
            "cost_optimal": select_cost_threshold(
                target, probabilities, fn_cost, fp_cost
            ),
        }
    champion_scores = calibrated[champion["model"]]
    operating = float(thresholds[champion["model"]]["operating"]["threshold"])
    high = float(
        np.percentile(champion_scores, float(evaluation_config["high_risk_percentile"]))
    )
    tiers = {
        "model": champion["model"],
        "low_below": operating,
        "high_at_or_above": high,
        "elevated_from": operating,
        "elevated_below": high,
        "percentile": float(evaluation_config["high_risk_percentile"]),
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    joblib.dump(calibration, ROOT / "artifacts" / "calibrators.joblib", compress=3)
    (ROOT / "artifacts" / "calibration.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "artifacts" / "champion.json").write_text(
        json.dumps(champion, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "artifacts" / "thresholds.json").write_text(
        json.dumps(
            {
                "recall_target": recall_target,
                "cost_assumptions": {
                    "false_negative_cost": fn_cost,
                    "false_positive_cost": fp_cost,
                    "label": "Assumed relative misclassification costs.",
                },
                "models": thresholds,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (ROOT / "artifacts" / "tiers.json").write_text(
        json.dumps(tiers, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"calibration": evidence, "champion": champion}, indent=2))
    return {
        "calibrators": calibration,
        "calibration_evidence": evidence,
        "champion": champion,
        "thresholds": thresholds,
        "tiers": tiers,
        "validation_target": target,
        "validation_calibrated": calibrated,
    }


def main() -> None:
    run_calibration()


if __name__ == "__main__":
    main()
