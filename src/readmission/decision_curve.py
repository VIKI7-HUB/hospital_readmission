"""Decision curve analysis and net benefit computation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from readmission.baselines import lace_score
from readmission.metrics import net_benefit

ROOT = Path(__file__).resolve().parents[2]


def run_decision_curve() -> pd.DataFrame:
    """Compute net benefit curve for champion model and calibrated LACE baseline."""
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    val_ids = set(split.get("val") or split.get("validation", []))
    test_ids = set(split["test"])


    cols = [
        "encounter_id",
        "patient_nbr",
        "readmit_30",
        "time_in_hospital",
        "admission_type_id",
        "diag_1",
        "diag_2",
        "diag_3",
        "number_emergency",
    ]
    clean = pd.read_parquet(ROOT / "artifacts" / "clean.parquet", columns=cols)

    val_df = clean[clean["encounter_id"].isin(val_ids)].copy()
    val_y = val_df["readmit_30"].astype(int).to_numpy()
    val_lace = lace_score(val_df, emergency_type_value=1).to_numpy().reshape(-1, 1)

    test_df = clean[clean["encounter_id"].isin(test_ids)].copy()
    test_y = test_df["readmit_30"].astype(int).to_numpy()
    test_lace = lace_score(test_df, emergency_type_value=1).to_numpy().reshape(-1, 1)

    lr = LogisticRegression(solver="lbfgs")
    lr.fit(val_lace, val_y)
    lace_p = lr.predict_proba(test_lace)[:, 1]

    test_preds = pd.read_parquet(ROOT / "artifacts" / "test_predictions.parquet")
    p_col = "p_cal" if "p_cal" in test_preds.columns else "probability_calibrated"
    champ_p = test_preds[p_col].to_numpy()

    thresholds = np.round(np.arange(0.02, 0.40 + 1e-9, 0.01), 2)
    nb_champ = net_benefit(test_y, champ_p, thresholds)
    nb_lace = net_benefit(test_y, lace_p, thresholds)

    df_out = pd.DataFrame(
        {
            "threshold": thresholds,
            "champion": nb_champ["model"],
            "lace": nb_lace["model"],
            "treat_all": nb_champ["treat_all"],
            "treat_none": nb_champ["treat_none"],
        }
    )
    out_parquet = ROOT / "artifacts" / "decision_curve.parquet"
    if out_parquet.exists():
        out_parquet.unlink()
    df_out.to_parquet(out_parquet, index=False)
    return df_out
