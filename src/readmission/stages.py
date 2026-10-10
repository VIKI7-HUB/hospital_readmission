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


def stage_fairness_audit() -> None:
    """Audit the champion's test predictions across age band, gender, and race."""
    from sklearn.metrics import roc_auc_score

    from readmission.fair_stats import (
        disparity_summary,
        gap_interval,
        group_table,
    )

    pred_path = ROOT / "artifacts" / "test_predictions.parquet"
    df = pd.read_parquet(pred_path)
    if "p_cal" not in df.columns and "probability_calibrated" in df.columns:
        df["p_cal"] = df["probability_calibrated"]
    if "patient_nbr" not in df.columns:
        clean_df = pd.read_parquet(
            ROOT / "artifacts" / "clean.parquet",
            columns=["encounter_id", "patient_nbr"],
        )
        df = df.merge(clean_df, on="encounter_id", how="left")

    th_path = ROOT / "artifacts" / "threshold.json"
    if th_path.exists():
        t = float(json.loads(th_path.read_text(encoding="utf-8"))["primary"]["threshold"])
    else:
        th_all = json.loads((ROOT / "artifacts" / "thresholds.json").read_text(encoding="utf-8"))
        champ = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))[
            "model"
        ]
        t = float(th_all["models"][champ]["operating"]["threshold"])

    all_tables: list[pd.DataFrame] = []
    all_gaps: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"threshold": t}

    for attribute in ("age_band", "gender", "race"):
        sub_df = df.copy()
        if attribute == "gender":
            sub_df = sub_df[sub_df["gender"].isin(["Male", "Female"])]
        elif attribute == "race":
            sub_df["race"] = sub_df["race"].fillna("Unknown")

        table = group_table(sub_df, attribute, t)
        table["attribute"] = attribute

        roc_aucs: list[float] = []
        for _, row in table.iterrows():
            grp_data = sub_df[sub_df[attribute] == row["group"]]
            y_grp = grp_data["y_true"].to_numpy().astype(int)
            if len(np.unique(y_grp)) == 2:
                score = float(roc_auc_score(y_grp, grp_data["p_cal"].to_numpy()))
            else:
                score = float("nan")
            roc_aucs.append(score)
        table["roc_auc"] = roc_aucs
        all_tables.append(table)

        reference = table.iloc[0]["group"]
        for _, row in table.iterrows():
            grp = row["group"]
            if grp == reference or row["underpowered"]:
                continue
            for kind in ("tpr", "fpr"):
                gap_row = gap_interval(sub_df, attribute, grp, reference, t, kind=kind, n_boot=1000)
                gap_row["attribute"] = attribute
                all_gaps.append(gap_row)

        summary[attribute] = disparity_summary(table)

    stacked_table = pd.concat(all_tables, ignore_index=True)
    gaps_table = pd.DataFrame(all_gaps)

    artifacts_dir = ROOT / "artifacts"
    stacked_table.to_csv(artifacts_dir / "fairness_audit.csv", index=False)
    gaps_table.to_csv(artifacts_dir / "fairness_gaps.csv", index=False)
    (artifacts_dir / "fairness_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print("Fairness Audit Summary (TPR and FPR per group):")
    print(
        stacked_table[
            ["attribute", "group", "n", "positives", "tpr", "fpr", "roc_auc", "underpowered"]
        ].to_string(index=False)
    )
