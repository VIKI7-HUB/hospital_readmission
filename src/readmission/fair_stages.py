"""Fairness audit and mitigation stage implementations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from readmission.calibrate import apply_calibrator
from readmission.fair_stats import (
    MIN_POSITIVES,
    apply_group_thresholds,
    disparity_summary,
    gap_interval,
    group_table,
    group_thresholds,
)
from readmission.features import build_fairness_attributes
from readmission.scoring import frame_for_encounters, predict_raw

ROOT = Path(__file__).resolve().parents[2]


def stage_fairness_audit() -> None:
    """Audit the champion's test predictions across age band, gender, and race."""
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


def stage_fairness_mitigation() -> pd.DataFrame:
    """Compare base model against group-threshold equal opportunity mitigation."""
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
    return mitigation_df
