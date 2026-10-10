"""Constants, mappings, and schema definitions for engineered features."""

from __future__ import annotations

import csv
from pathlib import Path

DEFAULT_SEED = 42

ORAL_MEDICATION_COLUMNS = (
    "metformin",
    "repaglinide",
    "nateglinide",
    "chlorpropamide",
    "glimepiride",
    "acetohexamide",
    "glipizide",
    "glyburide",
    "tolbutamide",
    "pioglitazone",
    "rosiglitazone",
    "acarbose",
    "miglitol",
    "troglitazone",
    "tolazamide",
    "examide",
    "citoglipton",
    "glyburide-metformin",
    "glipizide-metformin",
    "glimepiride-pioglitazone",
    "metformin-rosiglitazone",
    "metformin-pioglitazone",
)

DISCHARGE_GROUP_IDS = {
    "home": {1},
    "home_with_services": {6, 8},
    "facility": {2, 3, 4, 5, 10, 15, 22, 23, 24, 27, 28, 29, 30},
    "left_ama": {7},
}

FEATURE_RATIONALE = {
    "age": "Preserves the source decade band without implying exact age.",
    "age_mid": "Provides an approximate numeric age for smooth risk trends.",
    "gender": "Captures recorded gender differences in readmission risk.",
    "race": "Supports risk estimation and subgroup fairness review.",
    "time_in_hospital": "Summarizes the encounter length at discharge.",
    "num_lab_procedures": "Summarizes testing intensity during the encounter.",
    "num_procedures": "Summarizes procedures completed during the encounter.",
    "num_medications": "Measures medication burden at discharge.",
    "number_diagnoses": "Measures documented diagnosis burden.",
    "number_outpatient": "Captures recent outpatient utilization.",
    "number_emergency": "Captures recent emergency utilization.",
    "number_inpatient": "Captures recent inpatient utilization.",
    "prior_visits_total": "Summarizes prior outpatient, emergency, and inpatient visits.",
    "admission_type": "Adds readable context about the admission urgency or type.",
    "admission_source": "Captures how the patient arrived at the hospital.",
    "discharge_group": "Summarizes the destination or disposition at discharge.",
    "diag_1_category": "Groups the primary diagnosis into a broad ICD-9 chapter.",
    "diag_2_category": "Groups the secondary diagnosis into a broad ICD-9 chapter.",
    "diag_3_category": "Groups the tertiary diagnosis into a broad ICD-9 chapter.",
    "A1Cresult": "Captures the recorded glycated hemoglobin result or testing status.",
    "max_glu_serum": "Captures the recorded serum glucose result or testing status.",
    "insulin": "Captures insulin use and dose change at discharge.",
    "change": "Indicates whether diabetes medication changed during the encounter.",
    "diabetesMed": "Indicates whether diabetes medication was prescribed.",
    "n_meds_changed": "Counts oral diabetes medicines changed up or down.",
    "n_meds_active": "Counts oral diabetes medicines not recorded as No.",
    "medical_specialty": "Retains common specialties while grouping rare levels.",
    "payer_code": "Groups payer codes into broad coverage categories.",
    "age_band": "Provides a stable age subgroup for fairness reporting.",
}

MODEL_FEATURES = tuple(name for name in FEATURE_RATIONALE if name != "age_band")


def read_id_mappings(path: Path) -> dict[str, dict[str, str]]:
    """Parse CSV mappings for admission type, source, and discharge disposition."""
    mappings: dict[str, dict[str, str]] = {}
    current: str | None = None
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.reader(file):
            if len(row) >= 2 and row[0].strip().endswith("_id"):
                current = row[0].strip()
                mappings[current] = {}
                continue
            if not row or not row[0].strip():
                current = None
                continue
            if current is None or len(row) < 2:
                continue
            try:
                mappings[current][str(int(row[0].strip()))] = row[1].strip()
            except ValueError:
                continue

    required = ("admission_type_id", "admission_source_id", "discharge_disposition_id")
    missing = [name for name in required if not mappings.get(name)]
    if missing:
        raise ValueError(f"IDS mapping is missing sections: {missing}")
    return mappings


def normalize_mapping_label(value: str) -> str:
    """Standardize missing or placeholder labels to 'Unknown'."""
    if value.strip().casefold() in {"null", "not mapped", "not available", "unknown/invalid"}:
        return "Unknown"
    return value.strip()


def discharge_group_mapping(dispositions: dict[str, str]) -> dict[str, str]:
    """Map discharge disposition IDs into broad clinical categories."""
    groups = {code: "other" for code in dispositions}
    facility_keywords = (
        "hospital",
        "snf",
        "nursing",
        "icf",
        "rehab",
        "institution",
        "facility",
        "bed",
    )
    for group, codes in DISCHARGE_GROUP_IDS.items():
        for code in codes:
            description = dispositions.get(str(code))
            if description is None:
                raise ValueError(f"Discharge code {code} is absent from IDS_mapping.csv.")
            if not description or description.casefold() in {"null", "not mapped"}:
                raise ValueError(f"Discharge code {code} has no usable description.")
            label = description.casefold()
            valid_description = (
                (group == "home" and "home" in label)
                or (
                    group == "home_with_services"
                    and "home" in label
                    and any(word in label for word in ("service", "provider"))
                )
                or (group == "left_ama" and "ama" in label)
                or (group == "facility" and any(word in label for word in facility_keywords))
            )
            if not valid_description:
                raise ValueError(
                    f"Discharge description for code {code} does not match group {group!r}: "
                    f"{description}"
                )
            groups[str(code)] = group
    for code in ("1", "6", "8", "7", "3", "22"):
        if code not in dispositions:
            raise ValueError(f"Discharge code {code} is absent from IDS_mapping.csv.")
    return groups
