"""Feature selection evidence calculation fit on training data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = 42


def _evidence_matrix(
    frame: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str], list[pd.Series]]:
    matrix_columns: list[np.ndarray] = []
    discrete: list[bool] = []
    feature_names = list(frame.columns)
    values_by_feature: list[pd.Series] = []
    for name in feature_names:
        values = frame[name]
        values_by_feature.append(values)
        if pd.api.types.is_numeric_dtype(values):
            numeric = pd.to_numeric(values, errors="coerce")
            median = numeric.median()
            matrix_columns.append(numeric.fillna(median).to_numpy(dtype=float))
            discrete.append(False)
        else:
            labels = values.fillna("Unknown").astype(str)
            codes, _ = pd.factorize(labels, sort=True)
            matrix_columns.append(codes.astype(float))
            discrete.append(True)
    return np.column_stack(matrix_columns), np.asarray(discrete), feature_names, values_by_feature


def selection_evidence(
    train_df: pd.DataFrame,
    feature_config: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Write training-only feature metrics and return the evidence table."""
    from readmission.features import (
        FEATURE_RATIONALE,
        ORAL_MEDICATION_COLUMNS,
        build_fairness_attributes,
        build_features,
        fit_feature_config,
    )

    config = feature_config or fit_feature_config(train_df)
    features = build_features(train_df, config)
    fairness = build_fairness_attributes(train_df)
    evidence_values = pd.concat(
        [features, fairness, train_df[list(ORAL_MEDICATION_COLUMNS)]], axis=1
    )
    if any("readmit" in name.casefold() for name in evidence_values.columns):
        raise ValueError("Target-derived columns cannot appear in feature evidence.")
    if "readmit_30" in train_df:
        target = train_df["readmit_30"].astype(int)
    else:
        target = train_df["readmitted"].eq("<30").astype(int)
    if target.nunique() < 2:
        raise ValueError("Feature evidence needs both target classes in training rows.")

    matrix, discrete, names, values_by_feature = _evidence_matrix(evidence_values)
    information = mutual_info_classif(
        matrix,
        target.to_numpy(),
        discrete_features=discrete,
        random_state=DEFAULT_SEED,
    )
    dropped_medications = set(ORAL_MEDICATION_COLUMNS)
    rows: list[dict[str, Any]] = []
    for position, (name, values) in enumerate(zip(names, values_by_feature, strict=True)):
        feature_type = "numeric" if not discrete[position] else "categorical"
        row: dict[str, Any] = {
            "feature": name,
            "type": feature_type,
            "percent_missing": round(float(values.isna().mean() * 100), 4),
            "number_of_levels": int(values.nunique(dropna=True)),
            "mutual_information": float(information[position]),
            "univariate_auc": None,
            "max_readmission_rate": None,
            "min_readmission_rate": None,
        }
        if feature_type == "numeric":
            numeric = pd.to_numeric(values, errors="coerce")
            numeric = numeric.fillna(numeric.median())
            row["univariate_auc"] = (
                float(roc_auc_score(target, numeric)) if numeric.nunique() > 1 else 0.5
            )
        else:
            rates = target.groupby(values.fillna("Unknown").astype(str)).mean()
            row["max_readmission_rate"] = float(rates.max())
            row["min_readmission_rate"] = float(rates.min())

        if name == "age_band":
            row["decision"] = "dropped"
            row["reason"] = "Retained separately for fairness reporting."
        elif name in dropped_medications:
            row["decision"] = "dropped"
            row["reason"] = "Summarized by n_meds_changed and n_meds_active."
        else:
            row["decision"] = "kept"
            row["reason"] = FEATURE_RATIONALE[name]
        rows.append(row)

    evidence = pd.DataFrame(rows)
    destination = (
        Path(output_path)
        if output_path is not None
        else ROOT / "artifacts" / "feature_evidence.csv"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(destination, index=False)
    return evidence
