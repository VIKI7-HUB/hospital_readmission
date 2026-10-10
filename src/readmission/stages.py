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


def stage_fairness_mitigation() -> pd.DataFrame:
    """Compare base model against group-threshold equal opportunity mitigation."""
    import joblib

    from readmission.calibrate import apply_calibrator
    from readmission.fair_stats import (
        MIN_POSITIVES,
        apply_group_thresholds,
        group_thresholds,
    )
    from readmission.features import build_fairness_attributes
    from readmission.scoring import frame_for_encounters, predict_raw

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    val = frame_for_encounters(split["validation"])
    val_fair = build_fairness_attributes(val)
    val["age_band"] = val_fair["age_band"].astype(str)

    champ = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))["model"]
    calibrators = joblib.load(ROOT / "artifacts" / "calibrators.joblib")
    cal = calibrators[champ]
    val["p_cal"] = apply_calibrator(cal, predict_raw(champ, val))

    th = json.loads((ROOT / "artifacts" / "threshold.json").read_text(encoding="utf-8"))
    primary_t = float(th["primary"]["threshold"])
    target_recall = float(th["primary"]["recall"])

    test = pd.read_parquet(ROOT / "artifacts" / "test_predictions.parquet")
    if "p_cal" not in test.columns and "probability_calibrated" in test.columns:
        test["p_cal"] = test["probability_calibrated"]

    records: list[dict[str, Any]] = []
    thresholds_dict: dict[str, Any] = {}

    for attribute in ("age_band", "gender", "race"):
        val_sub = val.copy()
        test_sub = test.copy()
        if attribute == "gender":
            val_sub = val_sub[val_sub["gender"].isin(["Male", "Female"])]
            test_sub = test_sub[test_sub["gender"].isin(["Male", "Female"])]
        elif attribute == "race":
            val_sub["race"] = val_sub["race"].fillna("Unknown")
            test_sub["race"] = test_sub["race"].fillna("Unknown")

        thr = group_thresholds(val_sub, attribute, target_recall, fallback=primary_t)
        thresholds_dict[attribute] = thr

        base_flag = (test_sub["p_cal"].to_numpy() >= primary_t).astype(int)
        mit_flag = apply_group_thresholds(test_sub, attribute, thr, fallback=primary_t)
        y_test = test_sub["y_true"].to_numpy().astype(int)

        for variant, flags in (("base", base_flag), ("group_threshold", mit_flag)):
            tp = int(((flags == 1) & (y_test == 1)).sum())
            fp = int(((flags == 1) & (y_test == 0)).sum())
            fn = int(((flags == 0) & (y_test == 1)).sum())
            tn = int(((flags == 0) & (y_test == 0)).sum())

            rec = float(tp / (tp + fn)) if (tp + fn) else 0.0
            prec = float(tp / (tp + fp)) if (tp + fp) else 0.0
            fpr = float(fp / (fp + tn)) if (fp + tn) else 0.0
            acc = float((tp + tn) / len(y_test))

            tprs: list[float] = []
            fprs: list[float] = []
            for _, g in test_sub.groupby(attribute, observed=True):
                idx = g.index
                pos = int((g["y_true"] == 1).sum())
                neg = int((g["y_true"] == 0).sum())
                if pos < MIN_POSITIVES:
                    continue
                fl = flags[test_sub.index.get_indexer(idx)]
                g_tp = int(((fl == 1) & (g["y_true"].to_numpy() == 1)).sum())
                g_fp = int(((fl == 1) & (g["y_true"].to_numpy() == 0)).sum())
                tprs.append(g_tp / pos if pos else 0.0)
                fprs.append(g_fp / neg if neg else 0.0)

            tpr_diff = float(max(tprs) - min(tprs)) if len(tprs) >= 2 else 0.0
            fpr_diff = float(max(fprs) - min(fprs)) if len(fprs) >= 2 else 0.0
            eq_odds = float(max(tpr_diff, fpr_diff))

            records.append(
                {
                    "attribute": attribute,
                    "variant": variant,
                    "recall": rec,
                    "precision": prec,
                    "fpr": fpr,
                    "accuracy": acc,
                    "tpr_difference": tpr_diff,
                    "fpr_difference": fpr_diff,
                    "equalized_odds_difference": eq_odds,
                }
            )

    mitigation_df = pd.DataFrame(records)
    artifacts_dir = ROOT / "artifacts"
    mitigation_df.to_csv(artifacts_dir / "fairness_mitigation.csv", index=False)
    (artifacts_dir / "fairness_thresholds.json").write_text(
        json.dumps(thresholds_dict, indent=2) + "\n", encoding="utf-8"
    )

    print("Fairness Mitigation Summary:")
    print(mitigation_df.to_string(index=False))
    return mitigation_df
