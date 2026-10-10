"""Pipeline stage entry points."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from readmission.explain import contributions_matrix
from readmission.features import MODEL_FEATURES
from readmission.scoring import frame_for_encounters

ROOT = Path(__file__).resolve().parents[2]


def _config() -> dict[str, Any]:
    with (ROOT / "configs" / "config.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def stage_data() -> None:
    from readmission.data import main

    main()


def stage_split() -> None:
    from readmission.split import main

    main()


def stage_features() -> None:
    from readmission.features import main

    main()


def stage_train() -> None:
    from readmission.models import train_all

    train_all()


def stage_calibrate() -> None:
    from readmission.calibrate import run_calibration

    run_calibration()


def stage_evaluate() -> None:
    from readmission.evaluate import run_evaluation

    run_evaluation()


def stage_explain_global() -> None:
    """Compute global SHAP contributions for champion model on sample of test encounters."""
    config = _config()
    champion_info = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))
    champion_name = champion_info["model"]

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    test_ids = split["test"]

    sample_size = int(config.get("explain", {}).get("sample_size", 3000))
    seed = int(config.get("explain", {}).get("seed", 42))

    clean_path = ROOT / config["paths"]["cleaned_data"]
    clean_test = pd.read_parquet(
        clean_path,
        columns=["encounter_id", "readmit_30"],
        filters=[("encounter_id", "in", test_ids)],
    )

    pos_df = clean_test[clean_test["readmit_30"] == 1]
    neg_df = clean_test[clean_test["readmit_30"] == 0]
    pos_rate = len(pos_df) / len(clean_test)
    n_pos = int(round(sample_size * pos_rate))
    n_neg = sample_size - n_pos

    sampled_pos = pos_df.sample(n=n_pos, random_state=seed)
    sampled_neg = neg_df.sample(n=n_neg, random_state=seed)
    sample_encounters = (
        pd.concat([sampled_pos, sampled_neg])
        .sample(frac=1.0, random_state=seed)["encounter_id"]
        .tolist()
    )

    frame = frame_for_encounters(sample_encounters)
    contribs, base, margin = contributions_matrix(champion_name, frame)

    artifacts_dir = ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    contribs.to_parquet(artifacts_dir / "shap_values.parquet")

    feature_cols = [c for c in MODEL_FEATURES if c in frame.columns]
    raw_vals = frame[feature_cols].copy()
    for col in raw_vals.select_dtypes(include=["object", "category", "string"]).columns:
        raw_vals[col] = raw_vals[col].astype(str)
    raw_vals.to_parquet(artifacts_dir / "shap_feature_values.parquet")

    base_scalar = float(np.mean(base))
    (artifacts_dir / "shap_base.json").write_text(
        json.dumps({"base_value": base_scalar}, indent=2) + "\n",
        encoding="utf-8",
    )

    mean_abs = contribs.abs().mean(axis=0)
    importance_df = (
        pd.DataFrame({"feature": mean_abs.index, "mean_abs_shap": mean_abs.values})
        .sort_values(by="mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    importance_df["rank"] = np.arange(1, len(importance_df) + 1)
    importance_df.to_csv(artifacts_dir / "shap_importance.csv", index=False)

    print("Top 10 features by SHAP importance:")
    print(importance_df.head(10).to_string(index=False))
