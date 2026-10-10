"""HbA1c testing and readmission risk analysis."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from readmission.eda import rate_table
from readmission.features import DISCHARGE_GROUP_IDS, _diagnosis_category

ROOT = Path(__file__).resolve().parents[2]


def run_hba1c() -> dict:
    """Analyze crude readmission rates and cluster-adjusted odds ratios by HbA1c testing status."""
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    train_ids = set(split["train"])
    caps = json.loads((ROOT / "artifacts" / "caps.json").read_text(encoding="utf-8"))

    clean = pd.read_parquet(ROOT / "artifacts" / "clean.parquet")
    train = clean[clean["encounter_id"].isin(train_ids)].copy()

    def get_a1c_group(row) -> str:
        a1c = str(row["A1Cresult"])
        ch = str(row["change"])
        if a1c in ["Not tested", "None"]:
            return "Not tested"
        if a1c == "Norm":
            return "Normal"
        if a1c in [">7", ">8"]:
            return "High, therapy changed" if ch == "Ch" else "High, no change"
        return "Not tested"

    train["a1c_group"] = train.apply(get_a1c_group, axis=1)
    train["age_band"] = train["age"].astype(str)
    train["diag_1_cat"] = train["diag_1"].map(_diagnosis_category)

    def get_discharge_group(disp_id) -> str:
        for grp, ids in DISCHARGE_GROUP_IDS.items():
            if disp_id in ids:
                return grp
        return "other"

    train["discharge_group"] = train["discharge_disposition_id"].map(get_discharge_group)
    train["time_in_hospital"] = train["time_in_hospital"].clip(upper=caps.get("time_in_hospital", 13.0))
    train["number_inpatient"] = train["number_inpatient"].clip(upper=caps.get("number_inpatient", 6.0))

    crude = rate_table(train, "a1c_group")
    crude_records = []
    for _, r in crude.iterrows():
        crude_records.append(
            {
                "group": str(r["a1c_group"]),
                "n": int(r["n"]),
                "positives": int(r["positives"]),
                "rate": float(r["rate"]),
                "lo": float(r["lo"]),
                "hi": float(r["hi"]),
            }
        )

    formula = (
        "readmit_30 ~ C(a1c_group, Treatment('Not tested')) + C(age_band) + "
        "time_in_hospital + number_inpatient + C(diag_1_cat) + C(discharge_group)"
    )
    model = smf.logit(formula, data=train).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": train["patient_nbr"]}
    )

    adjusted_records = []
    prefix = "C(a1c_group, Treatment('Not tested'))[T."
    for param, pval in model.pvalues.items():
        if param.startswith(prefix):
            grp_name = param[len(prefix) : -1]
            coef = float(model.params[param])
            ci = model.conf_int().loc[param]
            adjusted_records.append(
                {
                    "group": grp_name,
                    "or": float(np.exp(coef)),
                    "lower": float(np.exp(ci[0])),
                    "upper": float(np.exp(ci[1])),
                    "p_value": float(pval),
                }
            )

    result = {
        "crude": crude_records,
        "adjusted": adjusted_records,
    }
    (ROOT / "artifacts" / "hba1c.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
