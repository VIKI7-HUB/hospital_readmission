"""Pipeline stage entry points."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from readmission.explain import contributions_matrix
from readmission.fair_stages import (
    stage_fairness_audit,
    stage_fairness_mitigation,
)
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
    import os

    from readmission.models import train_all

    is_fast = os.environ.get("READMISSION_FAST") == "1"
    train_all(fast=is_fast)


def stage_score() -> None:
    """Generate and save raw scores for validation and test splits."""
    from readmission.model_registry import MODEL_REGISTRY
    from readmission.scoring import frame_for_encounters, predict_raw, save_scores

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    for model_name in MODEL_REGISTRY:
        for split_name, ids in [("val", split["validation"]), ("test", split["test"])]:
            frame = frame_for_encounters(ids)
            p_raw = predict_raw(model_name, frame)
            score_df = pd.DataFrame(
                {
                    "encounter_id": frame["encounter_id"].to_numpy(),
                    "patient_nbr": frame["patient_nbr"].to_numpy(),
                    "y_true": frame["y_true"].to_numpy(),
                    "p_raw": p_raw,
                }
            )
            save_scores(model_name, split_name, score_df)


def stage_calibrate() -> None:
    from readmission.calibrate import run_calibration

    run_calibration()


def stage_threshold() -> None:
    from readmission.calibrate import run_calibration

    run_calibration()


def stage_evaluate() -> None:
    from readmission.evaluate import run_evaluation

    run_evaluation()


def stage_bootstrap() -> None:
    from readmission.bootstrap import run_bootstrap

    run_bootstrap()


def stage_lace() -> None:
    from readmission.baselines import stage_lace

    stage_lace()


def stage_decision_curve() -> None:
    from readmission.decision_curve import run_decision_curve

    run_decision_curve()



def stage_explain_global() -> None:
    """Compute global SHAP contributions for champion model on sample of test encounters."""
    config = _config()
    champion_info = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))
    champion_name = champion_info["model"]

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    test_ids = split["test"]

    sample_size = int(config.get("explain", {}).get("sample_size", 3000))
    if os.environ.get("READMISSION_FAST") == "1":
        sample_size = min(sample_size, 50)
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


def stage_odds_ratios() -> pd.DataFrame:
    """Compute and save odds ratios for the baseline model using the training split."""
    from readmission.oddsratio import odds_table

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    train_ids = split["train"]
    train_frame = frame_for_encounters(train_ids)
    y = train_frame["y_true"]
    patient = train_frame["patient_nbr"]

    table = odds_table(train_frame, y, patient)
    out_path = ROOT / "artifacts" / "odds_ratios.csv"
    table.to_csv(out_path, index=False)

    table["abs_log_or"] = np.abs(np.log(table["odds_ratio"]))
    top_10 = table.sort_values(by="abs_log_or", ascending=False).head(10)
    print("Top 10 terms with largest absolute log odds ratio:")
    print(
        top_10[
            [
                "term",
                "source_feature",
                "odds_ratio",
                "lower",
                "upper",
                "p_value",
                "unit",
            ]
        ].to_string(index=False)
    )
    return table


def stage_hba1c() -> None:
    from readmission.hba1c import run_hba1c

    run_hba1c()


def stage_blend() -> None:
    from readmission.blend import run_blend

    run_blend()


__all__ = [

    "stage_data",
    "stage_split",
    "stage_features",
    "stage_train",
    "stage_score",
    "stage_calibrate",
    "stage_threshold",
    "stage_evaluate",
    "stage_bootstrap",
    "stage_lace",
    "stage_decision_curve",
    "stage_explain_global",
    "stage_odds_ratios",
    "stage_hba1c",
    "stage_blend",
    "stage_fairness_audit",
    "stage_fairness_mitigation",
]

