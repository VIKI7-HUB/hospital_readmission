"""Split encounters by patient and fit training-only outlier caps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"
DEFAULT_SEED = 42
UTILIZATION_COLUMNS = (
    "number_inpatient",
    "number_outpatient",
    "number_emergency",
    "time_in_hospital",
    "num_lab_procedures",
    "num_medications",
    "num_procedures",
    "number_diagnoses",
)


def _config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _fold_count(share: float) -> int:
    folds = round(1 / share)
    if folds < 2:
        raise ValueError("Each holdout share must be greater than zero and less than one half.")
    return folds


def _select_holdout(
    frame: pd.DataFrame,
    target: str,
    groups_column: str,
    share: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = StratifiedGroupKFold(n_splits=_fold_count(share), shuffle=True, random_state=seed)
    labels = frame[target].to_numpy()
    groups = frame[groups_column].to_numpy()
    desired_rows = len(frame) * share
    overall_rate = float(np.mean(labels))
    candidates = list(splitter.split(np.zeros(len(frame)), labels, groups))
    return min(
        candidates,
        key=lambda split: (
            abs(len(split[1]) - desired_rows),
            abs(float(np.mean(labels[split[1]])) - overall_rate),
        ),
    )


def patient_split(
    df: pd.DataFrame,
    seed: int,
    ratios: tuple[float, float, float] = (0.70, 0.10, 0.20),
) -> tuple[pd.Index, pd.Index, pd.Index]:
    """Return train, validation, and test row indexes without patient overlap."""
    if len(ratios) != 3 or any(ratio <= 0 for ratio in ratios):
        raise ValueError("ratios must contain three positive values.")
    if not np.isclose(sum(ratios), 1.0):
        raise ValueError("ratios must sum to 1.")
    train_ratio, validation_ratio, test_ratio = ratios
    if not df.index.is_unique:
        raise ValueError("df must have a unique index so split indexes identify rows.")
    for column in ("patient_nbr", "readmit_30"):
        if column not in df:
            raise KeyError(f"Required split column is missing: {column}")

    remaining_positions, test_positions = _select_holdout(
        df,
        "readmit_30",
        "patient_nbr",
        test_ratio,
        seed,
    )
    remaining = df.iloc[remaining_positions]
    validation_share = validation_ratio / (train_ratio + validation_ratio)
    relative_train, relative_validation = _select_holdout(
        remaining,
        "readmit_30",
        "patient_nbr",
        validation_share,
        seed,
    )
    train_positions = remaining_positions[relative_train]
    validation_positions = remaining_positions[relative_validation]

    train_index = df.index.take(train_positions)
    validation_index = df.index.take(validation_positions)
    test_index = df.index.take(test_positions)
    assert_no_overlap(df, train_index, validation_index, test_index)

    for name, index in (
        ("train", train_index),
        ("validation", validation_index),
        ("test", test_index),
    ):
        subset = df.loc[index]
        print(
            f"{name}: {len(subset) / len(df):.2%} of rows "
            f"({len(subset):,}); positive rate {subset['readmit_30'].mean():.2%}"
        )
    all_split_positions = np.concatenate((train_positions, validation_positions, test_positions))
    if len(all_split_positions) != len(df) or len(np.unique(all_split_positions)) != len(df):
        raise AssertionError("The split indexes do not form a complete, disjoint partition.")
    return train_index, validation_index, test_index


def assert_no_overlap(
    df: pd.DataFrame,
    train_index: pd.Index,
    validation_index: pd.Index,
    test_index: pd.Index,
) -> None:
    """Raise an assertion error if a patient appears in more than one split."""
    patient_sets = {
        name: set(df.loc[index, "patient_nbr"])
        for name, index in (
            ("train", train_index),
            ("validation", validation_index),
            ("test", test_index),
        )
    }
    split_names = tuple(patient_sets)
    for left_position, left_name in enumerate(split_names):
        for right_name in split_names[left_position + 1 :]:
            overlap = patient_sets[left_name] & patient_sets[right_name]
            if overlap:
                raise AssertionError(
                    f"Patient overlap between {left_name} and {right_name}: "
                    f"{len(overlap)} patient(s)."
                )


def fit_caps(
    train_df: pd.DataFrame,
    columns: list[str] | tuple[str, ...],
    quantile: float = 0.99,
) -> dict[str, float]:
    """Fit upper quantile caps using only the supplied training rows."""
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one, inclusive.")
    missing = [column for column in columns if column not in train_df]
    if missing:
        raise KeyError(f"Cap columns are missing: {missing}")
    caps: dict[str, float] = {}
    for column in columns:
        if not pd.api.types.is_numeric_dtype(train_df[column]):
            raise TypeError(f"Cap column must be numeric: {column}")
        values = train_df[column].dropna()
        if values.empty:
            raise ValueError(f"Cannot fit a cap without non-missing training values: {column}")
        caps[column] = float(values.quantile(quantile))
    return caps


def apply_caps(df: pd.DataFrame, caps: dict[str, float]) -> pd.DataFrame:
    """Return a copy with each capped column clipped at its fitted upper bound."""
    missing = [column for column in caps if column not in df]
    if missing:
        raise KeyError(f"Cap columns are missing: {missing}")
    capped = df.copy()
    for column, cap in caps.items():
        capped[column] = capped[column].clip(upper=cap)
    return capped


def main() -> None:
    config = _config()
    clean_path = ROOT / config["paths"]["cleaned_data"]
    frame = pd.read_parquet(clean_path)
    seed = DEFAULT_SEED
    train_index, validation_index, test_index = patient_split(frame, seed)
    assert_no_overlap(frame, train_index, validation_index, test_index)

    splits = {
        name: sorted(frame.loc[index, "encounter_id"].tolist())
        for name, index in (
            ("train", train_index),
            ("validation", validation_index),
            ("test", test_index),
        )
    }
    split_path = ROOT / "artifacts" / "split.json"
    caps_path = ROOT / "artifacts" / "caps.json"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_text(json.dumps({"seed": seed, **splits}, indent=2) + "\n", encoding="utf-8")

    train_df = frame.loc[train_index]
    caps = fit_caps(train_df, UTILIZATION_COLUMNS)
    caps_path.write_text(json.dumps(caps, indent=2) + "\n", encoding="utf-8")
    print(f"Split file: {split_path.relative_to(ROOT)}")
    print(f"Caps file: {caps_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
