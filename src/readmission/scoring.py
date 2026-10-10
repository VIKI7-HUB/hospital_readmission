"""Scoring helpers for raw model predictions and encounter frames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml

from readmission.features import MODEL_FEATURES, build_features

ROOT = Path(__file__).resolve().parents[2]


def _config() -> dict[str, Any]:
    with (ROOT / "configs" / "config.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def frame_for_encounters(encounter_ids: list[int] | np.ndarray) -> pd.DataFrame:
    """Build model input rows for encounter IDs from cleaned data."""
    config = _config()
    clean_path = ROOT / config["paths"]["cleaned_data"]
    enc_list = [int(i) for i in encounter_ids]
    clean_df = pd.read_parquet(
        clean_path,
        filters=[("encounter_id", "in", enc_list)],
    )
    if clean_df.empty:
        raise ValueError("No encounters found for the provided IDs.")
    clean_df = (
        clean_df.set_index("encounter_id")
        .reindex(enc_list)
        .dropna(subset=["patient_nbr"])
        .reset_index()
    )
    feature_config = json.loads(
        (ROOT / "artifacts" / "feature_config.json").read_text(encoding="utf-8")
    )
    features = build_features(clean_df, feature_config)
    features["encounter_id"] = clean_df["encounter_id"].to_numpy()
    features["patient_nbr"] = clean_df["patient_nbr"].to_numpy()
    features["y_true"] = clean_df["readmit_30"].astype(int).to_numpy()
    features.index = pd.Index(clean_df["encounter_id"], name="encounter_id")
    return features


def predict_raw(model_name: str, frame: pd.DataFrame) -> np.ndarray:
    """Predict raw probabilities using the fitted model for model_name."""
    model_path = ROOT / "artifacts" / "models" / f"{model_name}.joblib"
    model = joblib.load(model_path)
    feature_cols = [c for c in MODEL_FEATURES if c in frame.columns]
    return model.predict_proba(frame[feature_cols])[:, 1]


def save_scores(model_name: str, split: str, df: pd.DataFrame) -> None:
    """Save score table to artifacts/scores/{model_name}__{split}.parquet."""
    out_dir = ROOT / "artifacts" / "scores"
    out_dir.mkdir(parents=True, exist_ok=True)
    df[["encounter_id", "patient_nbr", "y_true", "p_raw"]].to_parquet(
        out_dir / f"{model_name}__{split}.parquet", index=False
    )


def load_scores(model_name: str, split: str) -> pd.DataFrame:
    """Load score table from artifacts/scores/{model_name}__{split}.parquet."""
    path = ROOT / "artifacts" / "scores" / f"{model_name}__{split}.parquet"
    return pd.read_parquet(path)
