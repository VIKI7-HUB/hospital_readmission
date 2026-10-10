"""Build discharge-time model inputs and training-only feature evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from readmission.evidence import selection_evidence
from readmission.feature_definitions import (
    DISCHARGE_GROUP_IDS,
    FEATURE_RATIONALE,
    MODEL_FEATURES,
    ORAL_MEDICATION_COLUMNS,
    discharge_group_mapping,
    normalize_mapping_label,
    read_id_mappings,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"

_read_id_mappings = read_id_mappings
_normalize_mapping_label = normalize_mapping_label
_discharge_group_mapping = discharge_group_mapping


def _project_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def fit_feature_config(train_df: pd.DataFrame) -> dict[str, Any]:
    """Fit specialty levels on training rows and load source ID descriptions."""
    if "medical_specialty" not in train_df:
        raise KeyError("Required feature column is missing: medical_specialty")
    specialty = train_df["medical_specialty"].fillna("Unknown").astype(str).str.strip()
    specialty = specialty.replace({"Missing": "Unknown", "": "Unknown"})
    counts = specialty.loc[specialty.ne("Unknown")].value_counts()
    top_specialties = sorted(counts.index, key=lambda level: (-int(counts[level]), level))[:10]

    id_mapping_path = ROOT / _project_config()["paths"]["id_mapping"]
    id_mappings = _read_id_mappings(id_mapping_path)
    return {
        "specialty_top_10": top_specialties,
        "admission_type": {
            code: _normalize_mapping_label(label)
            for code, label in id_mappings["admission_type_id"].items()
        },
        "admission_source": {
            code: _normalize_mapping_label(label)
            for code, label in id_mappings["admission_source_id"].items()
        },
        "discharge_group": _discharge_group_mapping(id_mappings["discharge_disposition_id"]),
    }


def _age_midpoint(age: pd.Series) -> pd.Series:
    bounds = age.astype("string").str.extract(r"\[(\d+)-(\d+)\)")
    lower = pd.to_numeric(bounds[0], errors="coerce")
    upper = pd.to_numeric(bounds[1], errors="coerce")
    return (lower + upper).div(2).astype("Float64")


def build_fairness_attributes(df: pd.DataFrame) -> pd.DataFrame:
    """Return the age band used for fairness reporting, separate from model inputs."""
    midpoint = _age_midpoint(df["age"])
    band = pd.Series("<40", index=df.index, dtype="string")
    band.loc[midpoint.ge(40) & midpoint.lt(60)] = "40-59"
    band.loc[midpoint.ge(60) & midpoint.lt(80)] = "60-79"
    band.loc[midpoint.ge(80)] = "80+"
    band.loc[midpoint.isna()] = "Unknown"
    return pd.DataFrame({"age_band": band}, index=df.index)


def _diagnosis_category(value: Any) -> str:
    if pd.isna(value):
        return "other"
    code = str(value).strip().upper()
    if not code or code.startswith(("V", "E")):
        return "other"
    match = re.match(r"^(\d+)", code)
    if match is None:
        return "other"
    number = int(match.group(1))
    if number in (249, 250):
        return "diabetes"
    if 140 <= number <= 239:
        return "neoplasms"
    if 390 <= number <= 459:
        return "circulatory"
    if 460 <= number <= 519:
        return "respiratory"
    if 520 <= number <= 579:
        return "digestive"
    if 580 <= number <= 629:
        return "genitourinary"
    if 710 <= number <= 739:
        return "musculoskeletal"
    if 800 <= number <= 999:
        return "injury"
    return "other"


def _mapped_id(series: pd.Series, mapping: dict[str, str], default: str = "Unknown") -> pd.Series:
    codes = pd.to_numeric(series, errors="coerce").astype("Int64").astype("string")
    return codes.map(mapping).fillna(default).astype("string")


def _specialty_group(series: pd.Series, top_levels: list[str]) -> pd.Series:
    specialty = series.fillna("Unknown").astype("string").str.strip()
    specialty = specialty.replace({"Missing": "Unknown", "": "Unknown"})
    return specialty.where(specialty.eq("Unknown") | specialty.isin(top_levels), "Other")


def _payer_group(series: pd.Series) -> pd.Series:
    payer = series.fillna("Unknown").astype("string").str.strip()
    payer = payer.replace({"Missing": "Unknown", "": "Unknown", "UN": "Unknown"})
    groups = {"MC": "Medicare", "MD": "Medicaid", "SP": "Self-pay"}
    return payer.map(groups).fillna("Commercial/Other").where(payer.ne("Unknown"), "Unknown")


def build_features(df: pd.DataFrame, feature_config: dict[str, Any]) -> pd.DataFrame:
    """Build model input columns without identifiers, target, or fairness-only fields."""
    required = set(ORAL_MEDICATION_COLUMNS) | {
        "age",
        "gender",
        "race",
        "admission_type_id",
        "admission_source_id",
        "discharge_disposition_id",
        "time_in_hospital",
        "num_lab_procedures",
        "num_procedures",
        "num_medications",
        "number_diagnoses",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "diag_1",
        "diag_2",
        "diag_3",
        "A1Cresult",
        "max_glu_serum",
        "insulin",
        "change",
        "diabetesMed",
        "medical_specialty",
        "payer_code",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Required feature columns are missing: {missing}")
    if "specialty_top_10" not in feature_config:
        raise KeyError("feature_config must contain specialty_top_10.")

    features = pd.DataFrame(index=df.index)
    features["age"] = df["age"].astype("string")
    features["age_mid"] = _age_midpoint(df["age"])
    for column in ("gender", "race"):
        features[column] = df[column].fillna("Unknown").astype("string")
    numeric_columns = (
        "time_in_hospital",
        "num_lab_procedures",
        "num_procedures",
        "num_medications",
        "number_diagnoses",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
    )
    for column in numeric_columns:
        features[column] = pd.to_numeric(df[column], errors="raise")
    features["prior_visits_total"] = features[
        ["number_outpatient", "number_emergency", "number_inpatient"]
    ].sum(axis=1)

    for output, source, mapping_name in (
        ("admission_type", "admission_type_id", "admission_type"),
        ("admission_source", "admission_source_id", "admission_source"),
    ):
        features[output] = _mapped_id(df[source], feature_config[mapping_name])
    features["discharge_group"] = _mapped_id(
        df["discharge_disposition_id"], feature_config["discharge_group"], default="other"
    )
    for column in ("diag_1", "diag_2", "diag_3"):
        features[f"{column}_category"] = df[column].map(_diagnosis_category).astype("string")
    for column in ("A1Cresult", "max_glu_serum"):
        values = df[column].fillna("Not tested").astype("string")
        features[column] = values.replace({"None": "Not tested", "Missing": "Not tested"})
    for column in ("insulin", "change", "diabetesMed"):
        features[column] = df[column].fillna("Unknown").astype("string")

    medication_values = df[list(ORAL_MEDICATION_COLUMNS)].fillna("No")
    features["n_meds_changed"] = medication_values.isin(["Up", "Down"]).sum(axis=1)
    features["n_meds_active"] = medication_values.ne("No").sum(axis=1)
    features["medical_specialty"] = _specialty_group(
        df["medical_specialty"], feature_config["specialty_top_10"]
    )
    features["payer_code"] = _payer_group(df["payer_code"])

    extra = feature_config.get("extra", False) or _project_config().get("features", {}).get(
        "extra", False
    )
    if extra:
        diag_cats = features[["diag_1_category", "diag_2_category", "diag_3_category"]]
        features["comorbidity_count"] = diag_cats.apply(
            lambda r: len({x for x in r if x not in {"other", "Unknown"}}), axis=1
        )
        features["has_circulatory"] = (diag_cats == "circulatory").any(axis=1).astype(int)
        features["has_renal"] = diag_cats.isin(["renal", "genitourinary"]).any(axis=1).astype(int)
        features["has_neoplasm"] = (
            diag_cats.isin(["neoplasms", "neoplasm"]).any(axis=1).astype(int)
        )
        features["inpatient_x_home"] = (
            features["number_inpatient"] * (features["discharge_group"] == "home").astype(int)
        )
        features["labs_per_day"] = (
            features["num_lab_procedures"] / features["time_in_hospital"].clip(lower=1)
        )
        features["meds_per_day"] = (
            features["num_medications"] / features["time_in_hospital"].clip(lower=1)
        )
        clean_path = ROOT / "artifacts" / "clean.parquet"
        if clean_path.exists() and "encounter_id" in df.columns:
            clean_df = pd.read_parquet(clean_path, columns=["encounter_id", "patient_nbr"])
            prior_counts = prior_encounter_count(clean_df)
            prior_map = pd.Series(
                prior_counts.to_numpy(), index=clean_df["encounter_id"].to_numpy()
            )
            features["prior_encounters_in_data"] = (
                df["encounter_id"].map(prior_map).fillna(0).astype(int)
            )
        elif "patient_nbr" in df.columns and "encounter_id" in df.columns:
            features["prior_encounters_in_data"] = prior_encounter_count(df).astype(int)
        else:
            features["prior_encounters_in_data"] = 0

    expected = (
        MODEL_FEATURES
        if not extra
        else MODEL_FEATURES
        + (
            "comorbidity_count",
            "has_circulatory",
            "has_renal",
            "has_neoplasm",
            "inpatient_x_home",
            "labs_per_day",
            "meds_per_day",
            "prior_encounters_in_data",
        )
    )
    if tuple(features.columns) != expected:
        raise AssertionError("Built model feature columns do not match the declared feature list.")
    return features


def prior_encounter_count(df: pd.DataFrame) -> pd.Series:
    """Return number of earlier encounters for each patient."""
    order = df.sort_values(["patient_nbr", "encounter_id"])
    return order.groupby("patient_nbr").cumcount().reindex(df.index)


__all__ = [
    "DISCHARGE_GROUP_IDS",
    "FEATURE_RATIONALE",
    "MODEL_FEATURES",
    "ORAL_MEDICATION_COLUMNS",
    "build_fairness_attributes",
    "build_features",
    "fit_feature_config",
    "prior_encounter_count",
    "selection_evidence",
]


def main() -> None:
    project = _project_config()
    split_path = ROOT / "artifacts" / "split.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    frame = pd.read_parquet(ROOT / project["paths"]["cleaned_data"])
    training_ids = set(split["train"])
    train_df = frame.loc[frame["encounter_id"].isin(training_ids)].copy()
    if len(train_df) != len(training_ids):
        raise ValueError("Training encounter IDs do not match the clean dataset.")

    feature_config = fit_feature_config(train_df)
    config_path = ROOT / "artifacts" / "feature_config.json"
    config_path.write_text(json.dumps(feature_config, indent=2) + "\n", encoding="utf-8")
    features = build_features(train_df, feature_config)
    evidence = selection_evidence(train_df, feature_config)
    print(f"Model input feature count: {features.shape[1]}")
    print(evidence.to_string(index=False))
    print(f"Feature config: {config_path.relative_to(ROOT)}")
    print("Feature evidence: artifacts/feature_evidence.csv")


if __name__ == "__main__":
    main()
