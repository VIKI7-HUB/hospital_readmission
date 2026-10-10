"""Tests for engineered model input names."""

import pandas as pd

from readmission.features import ORAL_MEDICATION_COLUMNS, build_features


def test_model_feature_names_do_not_include_readmit() -> None:
    row = {
        "age": "[60-70)",
        "gender": "Female",
        "race": "White",
        "admission_type_id": 1,
        "admission_source_id": 1,
        "discharge_disposition_id": 1,
        "time_in_hospital": 4,
        "num_lab_procedures": 40,
        "num_procedures": 1,
        "num_medications": 12,
        "number_diagnoses": 6,
        "number_outpatient": 1,
        "number_emergency": 0,
        "number_inpatient": 2,
        "diag_1": "250.83",
        "diag_2": "E879.8",
        "diag_3": "Unknown",
        "A1Cresult": "Not tested",
        "max_glu_serum": "None",
        "insulin": "Steady",
        "change": "Ch",
        "diabetesMed": "Yes",
        "medical_specialty": "Cardiology",
        "payer_code": "MC",
        "encounter_id": 100,
        "patient_nbr": 10,
        "readmit_30": 1,
    }
    row.update({column: "No" for column in ORAL_MEDICATION_COLUMNS})
    feature_config = {
        "specialty_top_10": ["Cardiology"],
        "admission_type": {"1": "Emergency"},
        "admission_source": {"1": "Physician Referral"},
        "discharge_group": {"1": "home"},
    }

    features = build_features(pd.DataFrame([row]), feature_config)

    assert len(features.columns) == 28
    assert all("readmit" not in name.casefold() for name in features.columns)
    assert features.loc[0, "diag_1_category"] == "diabetes"
    assert features.loc[0, "diag_2_category"] == "other"
