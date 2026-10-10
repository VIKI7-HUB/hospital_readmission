"""Patient-clustered bootstrap confidence intervals and paired differences."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from readmission.calibrate import apply_calibrator
from readmission.metrics import (
    difference_summary,
    interval,
    paired_bootstrap,
    patient_bootstrap,
    ranking_metrics,
    threshold_metrics,
)

ROOT = Path(__file__).resolve().parents[2]


def run_bootstrap(n_boot: int = 1000, seed: int = 42) -> None:
    """Run patient-clustered bootstrap on test scores and write summary tables."""
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    clean = pd.read_parquet(
        ROOT / "artifacts" / "clean.parquet",
        columns=["encounter_id", "patient_nbr", "readmit_30"],
    )
    test_df = clean[clean["encounter_id"].isin(test_ids)].sort_values("encounter_id").reset_index(drop=True)
    y_true = test_df["readmit_30"].astype(int).to_numpy()
    patient_nbr = test_df["patient_nbr"].to_numpy()

    calibrators = joblib.load(ROOT / "artifacts" / "calibrators.joblib")
    thresholds = json.loads((ROOT / "artifacts" / "thresholds.json").read_text(encoding="utf-8"))["models"]
    models = ["logistic_regression", "random_forest", "lightgbm", "xgboost", "catboost"]

    p_cal_dict = {}
    for m in models:
        scores = pd.read_parquet(ROOT / "artifacts" / "scores" / f"{m}__test.parquet")
        scores = scores.sort_values("encounter_id").reset_index(drop=True)
        p_cal_dict[m] = apply_calibrator(calibrators[m], scores["p_raw"].to_numpy())

    bootstrap_rows = []
    for m in models:
        t = float(thresholds[m]["operating"]["threshold"])
        p_cal = p_cal_dict[m]

        def stat(y, p, w, thresh=t):
            return {
                **ranking_metrics(y, p, w),
                "recall": threshold_metrics(y, p, thresh, w)["recall"],
                "precision": threshold_metrics(y, p, thresh, w)["precision"],
            }


        draws = patient_bootstrap(y_true, p_cal, patient_nbr, stat, n_boot=n_boot, seed=seed)
        iv = interval(draws)
        for metric_name, row in iv.iterrows():
            bootstrap_rows.append(
                {
                    "model": m,
                    "metric": str(metric_name),
                    "mean": float(row["mean"]),
                    "lower": float(row["lower"]),
                    "upper": float(row["upper"]),
                }
            )

    pd.DataFrame(bootstrap_rows).to_csv(ROOT / "artifacts" / "bootstrap.csv", index=False)

    def stat_ranking(y, p, w):
        return {
            "roc_auc": ranking_metrics(y, p, w)["roc_auc"],
            "pr_auc": ranking_metrics(y, p, w)["pr_auc"],
        }

    p_cal_logistic = p_cal_dict["logistic_regression"]
    paired_rows = []
    for m in models:
        if m == "logistic_regression":
            continue
        paired = paired_bootstrap(
            y_true, p_cal_dict[m], p_cal_logistic, patient_nbr, stat_ranking, n_boot=n_boot, seed=seed
        )
        summary = difference_summary(paired)
        for metric_name, row in summary.iterrows():
            paired_rows.append(
                {
                    "model": m,
                    "metric": str(metric_name),
                    "mean_diff": float(row["mean"]),
                    "lower": float(row["lower"]),
                    "upper": float(row["upper"]),
                    "share_better": float(row["share_a_better"]),
                }
            )

    pd.DataFrame(paired_rows).to_csv(
        ROOT / "artifacts" / "bootstrap_vs_baseline.csv", index=False
    )
