from __future__ import annotations

import pandas as pd

CHARLSON_RULES = [
    (1, "myocardial_infarction", [(410, 410), (412, 412)], []),
    (1, "heart_failure", [(428, 428)], []),
    (1, "peripheral_vascular", [(440, 443)], ["785.4"]),
    (1, "cerebrovascular", [(430, 438)], []),
    (1, "dementia", [(290, 290)], []),
    (1, "chronic_pulmonary", [(490, 496), (500, 505)], ["506.4"]),
    (1, "rheumatic", [(725, 725)], ["710.0", "710.1", "710.4", "714.0", "714.1", "714.2", "714.8"]),
    (1, "peptic_ulcer", [(531, 534)], []),
    (1, "mild_liver", [], ["571.2", "571.4", "571.5", "571.6"]),
    (2, "diabetes_complications", [], ["250.4", "250.5", "250.6", "250.7"]),
    (2, "hemiplegia", [(342, 342)], ["344.1"]),
    (2, "renal", [(582, 582), (585, 586), (588, 588)], ["583.0", "583.1", "583.2", "583.3", "583.4", "583.5", "583.6", "583.7"]),
    (2, "malignancy", [(140, 172), (174, 195), (200, 208)], []),
    (3, "severe_liver", [], ["456.0", "456.1", "456.2", "572.2", "572.3", "572.4", "572.5", "572.6", "572.7", "572.8"]),
    (6, "metastatic", [(196, 199)], []),
]


def _int_part(code: str) -> int | None:
    head = str(code).split(".")[0]
    return int(head) if head.isdigit() else None


def conditions_for_code(code: str) -> set[str]:
    code = str(code)
    n = _int_part(code)
    found = set()
    for _, name, ranges, prefixes in CHARLSON_RULES:
        if n is not None and any(lo <= n <= hi for lo, hi in ranges):
            found.add(name)
        if any(code.startswith(p) for p in prefixes):
            found.add(name)
    return found


def charlson_points(codes) -> int:
    points = {name: pts for pts, name, _, _ in CHARLSON_RULES}
    seen = set()
    for c in codes:
        seen |= conditions_for_code(c)
    return int(sum(points[n] for n in seen))


def _los_points(days: float) -> int:
    for upper, points in ((1, 0), (2, 1), (3, 2), (4, 3), (7, 4), (14, 5)):
        if days < upper:
            return points
    return 7


def lace_score(
    df: pd.DataFrame,
    los_col="time_in_hospital",
    type_col="admission_type_id",
    diag_cols=("diag_1", "diag_2", "diag_3"),
    ed_col="number_emergency",
    emergency_type_value=1,
) -> pd.Series:
    """Approximate LACE index using simplified Charlson and prior-year ED counts."""
    length = df[los_col].map(_los_points)
    acuity = (df[type_col].astype(int) == emergency_type_value).astype(int) * 3
    charlson = df[list(diag_cols)].apply(lambda row: charlson_points(row.tolist()), axis=1)
    comorbidity = charlson.map(lambda v: 5 if v >= 4 else v)
    emergency = df[ed_col].clip(upper=4).astype(int)
    return (length + acuity + comorbidity + emergency).astype(int)


def stage_lace() -> dict:
    """Evaluate approximate LACE index on test split."""
    import json
    from pathlib import Path

    import numpy as np
    from sklearn.metrics import average_precision_score, roc_auc_score

    from readmission.metrics import threshold_metrics

    root = Path(__file__).resolve().parents[2]
    split = json.loads((root / "artifacts" / "split.json").read_text(encoding="utf-8"))
    champ_data = json.loads((root / "artifacts" / "champion.json").read_text(encoding="utf-8"))
    champ = champ_data.get("model") or champ_data.get("champion")
    mc = pd.read_csv(root / "artifacts" / "model_comparison.csv")
    champ_row = mc[mc["model"] == champ].iloc[0]
    total_enc = champ_row["tp"] + champ_row["fp"] + champ_row["tn"] + champ_row["fn"]
    flag_rate = float((champ_row["tp"] + champ_row["fp"]) / total_enc)

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
    clean = pd.read_parquet(root / "artifacts" / "clean.parquet", columns=cols)
    test_ids = set(split["test"])
    test_df = clean[clean["encounter_id"].isin(test_ids)].copy()
    y_test = test_df["readmit_30"].astype(int).to_numpy()

    test_score = lace_score(test_df, emergency_type_value=1).to_numpy()
    roc_auc = float(roc_auc_score(y_test, test_score))
    pr_auc = float(average_precision_score(y_test, test_score))

    cutoff = float(np.quantile(test_score, 1 - flag_rate))
    flagged = (test_score >= cutoff).astype(int)
    tm = threshold_metrics(y_test, flagged, 0.5)

    result = {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "cutoff": cutoff,
        "flag_rate": tm["flag_rate"],
        "recall": tm["recall"],
        "precision": tm["precision"],
        "note": (
            "Approximate LACE: simplified Charlson mapping; "
            "emergency visits cover the previous year in this data, not six months."
        ),
    }
    (root / "artifacts" / "lace.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result

