"""Tune, fit, and save the project model comparison."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from readmission.features import build_features
from readmission.model_registry import (
    MODEL_REGISTRY,
    FittedReadmissionModel,
    ModelSpec,
    catboost_frame,
    lightgbm_average_precision,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"
FEATURE_CONFIG_PATH = ROOT / "artifacts" / "feature_config.json"


def _load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _prepare_fold(
    spec: ModelSpec, train_x: pd.DataFrame, valid_x: pd.DataFrame
) -> tuple[Any, Any, list[str]]:
    if spec.preprocessor is None:
        train_values, categories = catboost_frame(train_x)
        valid_values, _ = catboost_frame(valid_x)
        return train_values, valid_values, categories
    preprocessor = spec.preprocessor()
    train_values = preprocessor.fit_transform(train_x)
    valid_values = preprocessor.transform(valid_x)
    return train_values, valid_values, []


def _grouped_folds(
    x: pd.DataFrame, y: pd.Series, groups: pd.Series, seed: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
    return list(splitter.split(x, y, groups))


def _cross_validated_average_precision(
    name: str,
    params: dict[str, Any],
    x: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    seed: int,
    config: dict[str, Any],
    trial: optuna.Trial | None = None,
) -> float:
    spec = MODEL_REGISTRY[name]
    scores: list[float] = []
    for fold, (train_positions, valid_positions) in enumerate(
        _grouped_folds(x, y, groups, seed)
    ):
        train_x, valid_x = x.iloc[train_positions], x.iloc[valid_positions]
        train_y, valid_y = y.iloc[train_positions], y.iloc[valid_positions]
        train_values, valid_values, categories = _prepare_fold(spec, train_x, valid_x)
        estimator = spec.factory(params, seed, train_y, config, False)
        fit_kwargs: dict[str, Any] = {"verbose": False} if name == "catboost" else {}
        if categories:
            fit_kwargs["cat_features"] = categories
        estimator.fit(train_values, train_y, **fit_kwargs)
        probabilities = estimator.predict_proba(valid_values)[:, 1]
        scores.append(float(average_precision_score(valid_y, probabilities)))
        if trial is not None:
            trial.report(float(np.mean(scores)), step=fold)
            if trial.should_prune():
                raise optuna.TrialPruned()
    return float(np.mean(scores))


def _tune_model(
    name: str,
    x: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    config: dict[str, Any],
    fast: bool,
) -> tuple[dict[str, Any], float]:
    model_config = config["models"]
    tuning = model_config["tuning"]
    seed = int(model_config["seed"])
    spec = MODEL_REGISTRY[name]
    if name == "logistic_regression":
        values = tuning["logistic_c"]
        scores = [
            _cross_validated_average_precision(
                name, {"C": value}, x, y, groups, seed, config
            )
            for value in values
        ]
        best_index = int(np.argmax(scores))
        return {"C": values[best_index]}, scores[best_index]

    sampler = optuna.samplers.TPESampler(seed=seed)
    pruner = optuna.pruners.MedianPruner(
        n_startup_trials=int(tuning["pruner"]["startup_trials"]),
        n_warmup_steps=int(tuning["pruner"]["warmup_folds"]),
    )
    study = optuna.create_study(direction="maximize", sampler=sampler, pruner=pruner)
    mode = "fast" if fast else "normal"
    trial_count = (
        int(tuning["trials"][mode])
        if fast
        else int(tuning["trials"]["normal"][spec.trials_key])
    )
    timeout = int(tuning["timeout_seconds"][mode])

    def objective(trial: optuna.Trial) -> float:
        params = spec.search(trial, config)
        trial.set_user_attr("model_parameters", params)
        return _cross_validated_average_precision(
            name, params, x, y, groups, seed, config, trial
        )

    study.optimize(
        objective,
        n_trials=trial_count,
        timeout=timeout,
        gc_after_trial=True,
        show_progress_bar=False,
    )
    best = study.best_trial
    return dict(best.user_attrs["model_parameters"]), float(best.value)


def _fit_validation_model(
    name: str,
    params: dict[str, Any],
    train_x: pd.DataFrame,
    train_y: pd.Series,
    valid_x: pd.DataFrame,
    valid_y: pd.Series,
    config: dict[str, Any],
) -> FittedReadmissionModel:
    spec = MODEL_REGISTRY[name]
    model_config = config["models"]
    if spec.preprocessor is None:
        train_values, categories = catboost_frame(train_x)
        valid_values, _ = catboost_frame(valid_x)
        preprocessor = None
    else:
        preprocessor = spec.preprocessor()
        train_values = preprocessor.fit_transform(train_x)
        valid_values = preprocessor.transform(valid_x)
        categories = []
    estimator = spec.factory(params, int(model_config["seed"]), train_y, config, True)
    early_stopping = int(model_config["early_stopping_rounds"])
    if name == "catboost":
        fit_kwargs = {
            "cat_features": categories,
            "eval_set": (valid_values, valid_y),
            "early_stopping_rounds": early_stopping,
            "verbose": False,
        }
    elif name == "xgboost":
        fit_kwargs = {"eval_set": [(valid_values, valid_y)], "verbose": False}
    elif name == "lightgbm":
        fit_kwargs = {
            "eval_X": valid_values,
            "eval_y": valid_y,
            "eval_metric": lightgbm_average_precision,
            "callbacks": [lgb.early_stopping(early_stopping, verbose=False)],
        }
    else:
        fit_kwargs = {}
    estimator.fit(train_values, train_y, **fit_kwargs)
    return FittedReadmissionModel(estimator, preprocessor, name == "catboost")


def _rows_for_ids(frame: pd.DataFrame, ids: list[int]) -> pd.DataFrame:
    result = frame.loc[frame["encounter_id"].isin(ids)].copy()
    if len(result) != len(ids):
        raise ValueError("Split encounter IDs do not match the cleaned dataset.")
    return result


def train_all(fast: bool = False) -> pd.DataFrame:
    """Tune five models on grouped training folds and score validation rows."""
    config = _load_config()
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    feature_config = json.loads(FEATURE_CONFIG_PATH.read_text(encoding="utf-8"))
    frame = pd.read_parquet(ROOT / config["paths"]["cleaned_data"])
    train = _rows_for_ids(frame, split["train"])
    valid = _rows_for_ids(frame, split["validation"])
    train_x = build_features(train, feature_config)
    valid_x = build_features(valid, feature_config)
    train_y = train["readmit_30"].astype(int)
    valid_y = valid["readmit_30"].astype(int)
    groups = train["patient_nbr"]
    model_dir = ROOT / "artifacts" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    best_params: dict[str, Any] = {}

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    for name in MODEL_REGISTRY:
        started = time.perf_counter()
        params, cv_ap = _tune_model(name, train_x, train_y, groups, config, fast)
        model = _fit_validation_model(
            name, params, train_x, train_y, valid_x, valid_y, config
        )
        probabilities = model.predict_proba(valid_x)[:, 1]
        elapsed = time.perf_counter() - started
        joblib.dump(model, model_dir / f"{name}.joblib", compress=3)
        best_params[name] = {
            "parameters": params,
            "cv_average_precision": cv_ap,
            "validation_roc_auc": float(roc_auc_score(valid_y, probabilities)),
            "validation_average_precision": float(
                average_precision_score(valid_y, probabilities)
            ),
            "training_time_seconds": round(elapsed, 3),
        }
        records.append(
            {
                "model": name,
                "validation_roc_auc": best_params[name]["validation_roc_auc"],
                "validation_average_precision": best_params[name][
                    "validation_average_precision"
                ],
                "training_time_seconds": best_params[name]["training_time_seconds"],
            }
        )
        (ROOT / "artifacts" / "best_params.json").write_text(
            json.dumps(best_params, indent=2) + "\n", encoding="utf-8"
        )

    table = pd.DataFrame(records)
    print(table.to_string(index=False))
    return table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    train_all(fast=parser.parse_args().fast)


if __name__ == "__main__":
    main()
