"""Estimator factories and tuning spaces for the model comparison."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import optuna
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from xgboost import XGBClassifier

from readmission.preprocess import (
    build_linear_preprocessor,
    build_tree_preprocessor,
)


@dataclass(frozen=True)
class ModelSpec:
    factory: Callable[[dict[str, Any], int, pd.Series, dict[str, Any], bool], Any]
    search: Callable[[optuna.Trial, dict[str, Any]], dict[str, Any]]
    preprocessor: Callable[[], Any] | None
    trials_key: str
    boosted: bool = False


def _logistic_factory(
    params: dict[str, Any],
    seed: int,
    y: pd.Series,
    config: dict[str, Any],
    early_stopping: bool,
) -> Any:
    return LogisticRegression(
        C=params["C"],
        class_weight="balanced",
        max_iter=2000,
        random_state=seed,
        solver="lbfgs",
    )


def _forest_factory(
    params: dict[str, Any],
    seed: int,
    y: pd.Series,
    config: dict[str, Any],
    early_stopping: bool,
) -> Any:
    return RandomForestClassifier(
        **params,
        class_weight="balanced_subsample",
        n_jobs=int(config["models"]["n_jobs"]),
        random_state=seed,
    )


def _xgboost_factory(
    params: dict[str, Any],
    seed: int,
    y: pd.Series,
    config: dict[str, Any],
    early_stopping: bool,
) -> Any:
    positive = int(y.sum())
    negative = len(y) - positive
    return XGBClassifier(
        **params,
        eval_metric=_xgboost_average_precision,
        early_stopping_rounds=(
            int(config["models"]["early_stopping_rounds"]) if early_stopping else None
        ),
        n_jobs=int(config["models"]["n_jobs"]),
        objective="binary:logistic",
        random_state=seed,
        scale_pos_weight=negative / max(positive, 1),
        tree_method="hist",
    )


def _lightgbm_factory(
    params: dict[str, Any],
    seed: int,
    y: pd.Series,
    config: dict[str, Any],
    early_stopping: bool,
) -> Any:
    return LGBMClassifier(
        **params,
        class_weight="balanced",
        metric="None",
        n_jobs=int(config["models"]["n_jobs"]),
        random_state=seed,
        verbosity=-1,
    )


def _catboost_factory(
    params: dict[str, Any],
    seed: int,
    y: pd.Series,
    config: dict[str, Any],
    early_stopping: bool,
) -> Any:
    return CatBoostClassifier(
        **params,
        auto_class_weights="Balanced",
        eval_metric=_AveragePrecisionMetric(),
        random_seed=seed,
        thread_count=int(config["models"]["n_jobs"]),
        verbose=False,
        allow_writing_files=False,
    )


def _logistic_search(trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    return {"C": trial.suggest_categorical("C", config["models"]["tuning"]["logistic_c"])}


def _forest_search(trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    ranges = config["models"]["search"]["random_forest"]
    unlimited = trial.suggest_categorical("unlimited_depth", [True, False])
    return {
        "n_estimators": trial.suggest_int("n_estimators", *ranges["n_estimators"]),
        "max_depth": (None if unlimited else trial.suggest_int("max_depth", *ranges["max_depth"])),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", *ranges["min_samples_leaf"]),
        "max_features": trial.suggest_categorical("max_features", ranges["max_features"]),
    }


def _boosted_search(name: str, trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    ranges = config["models"]["search"][name]
    params: dict[str, Any] = {}
    for key, bounds in ranges.items():
        if key in {"learning_rate", "reg_lambda", "l2_leaf_reg"}:
            params[key] = trial.suggest_float(key, *bounds, log=True)
        elif key in {"subsample", "colsample_bytree", "random_strength"}:
            params[key] = trial.suggest_float(key, *bounds)
        else:
            params[key] = trial.suggest_int(key, *bounds)
    if name == "lightgbm":
        params["subsample_freq"] = 1
    return params


def _xgboost_search(trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    return _boosted_search("xgboost", trial, config)


def _lightgbm_search(trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    return _boosted_search("lightgbm", trial, config)


def _catboost_search(trial: optuna.Trial, config: dict[str, Any]) -> dict[str, Any]:
    return _boosted_search("catboost", trial, config)


MODEL_REGISTRY = {
    "logistic_regression": ModelSpec(
        _logistic_factory, _logistic_search, build_linear_preprocessor, "logistic"
    ),
    "random_forest": ModelSpec(
        _forest_factory, _forest_search, build_tree_preprocessor, "random_forest"
    ),
    "xgboost": ModelSpec(
        _xgboost_factory, _xgboost_search, build_tree_preprocessor, "boosted", True
    ),
    "lightgbm": ModelSpec(
        _lightgbm_factory, _lightgbm_search, build_tree_preprocessor, "boosted", True
    ),
    "catboost": ModelSpec(_catboost_factory, _catboost_search, None, "boosted", True),
}


class _AveragePrecisionMetric:
    def is_max_optimal(self) -> bool:
        return True

    def evaluate(
        self,
        approximations: list[list[float]],
        target: list[float],
        weight: list[float] | None,
    ) -> tuple[float, float]:
        values = np.asarray(approximations[0], dtype=float)
        labels = np.asarray(target, dtype=int)
        weights = None if weight is None else np.asarray(weight, dtype=float)
        total_weight = float(len(labels)) if weights is None else float(weights.sum())
        score = average_precision_score(labels, values, sample_weight=weights)
        return float(score * total_weight), total_weight

    def get_final_error(self, error: float, weight: float) -> float:
        return error / weight if weight else 0.0


def _xgboost_average_precision(labels: np.ndarray, predictions: np.ndarray) -> float:
    return float(average_precision_score(labels, predictions))


def lightgbm_average_precision(
    labels: np.ndarray, predictions: np.ndarray
) -> tuple[str, float, bool]:
    return "average_precision", float(average_precision_score(labels, predictions)), True


def catboost_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    values = frame.copy()
    categorical = [name for name in values if not pd.api.types.is_numeric_dtype(values[name])]
    for name in categorical:
        values[name] = values[name].fillna("Unknown").astype(object)
    for name in values.columns.difference(categorical):
        values[name] = pd.to_numeric(values[name], errors="raise").astype(float)
    return values, categorical


@dataclass
class FittedReadmissionModel:
    estimator: Any
    preprocessor: Any | None
    native_categoricals: bool

    def _transform(self, frame: pd.DataFrame) -> Any:
        if self.native_categoricals:
            values, _ = catboost_frame(frame)
            return values
        if self.preprocessor is None:
            return frame
        return self.preprocessor.transform(frame)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict_proba(self._transform(frame))
