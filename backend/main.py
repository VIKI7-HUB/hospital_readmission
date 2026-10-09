"""Read-only API for the ClinicalAI research demo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
FAIRNESS_DIR = BASE_DIR / "fairness_governance"

# These class definitions are needed to load the saved calibrated ensemble.
import src.models  # noqa: F401
from src.explainability import (
    clean_feature_label,
    get_clinical_risk_tier,
    recommend_clinical_interventions,
)
from src.preprocessing import engineer_features

DIAGNOSIS_CATEGORIES = (
    "Circulatory",
    "Respiratory",
    "Digestive",
    "Diabetes",
    "Injury",
    "Musculoskeletal",
    "Genitourinary",
    "Neoplasms",
    "Other",
    "Other/External",
)


@lru_cache(maxsize=1)
def load_assets() -> dict:
    """Load the already-trained artifacts once per service process."""
    required = {
        "model": MODELS_DIR / "production_model.joblib",
        "preprocessor": PROCESSED_DIR / "preprocessor.joblib",
        "worklist": PROCESSED_DIR / "worklist_precomputed.joblib",
        "benchmarks": MODELS_DIR / "model_comparison_results.csv",
        "fairness": FAIRNESS_DIR / "mitigation_improvement_summary.json",
    }
    missing = [str(path.relative_to(BASE_DIR)) for path in required.values() if not path.is_file()]
    if missing:
        raise RuntimeError("Required model artifacts are missing: " + ", ".join(missing))

    worklist = joblib.load(required["worklist"]).reset_index(drop=True)
    benchmarks_df = pd.read_csv(required["benchmarks"]).replace({np.nan: None})
    benchmarks = []
    for row in benchmarks_df.to_dict(orient="records"):
        recall_val = row.get("Recall (Sensitivity)") if "Recall (Sensitivity)" in row else row.get("Recall")
        row["Recall"] = float(recall_val) if recall_val is not None else 0.0
        row["Sensitivity"] = row["Recall"]
        benchmarks.append(row)

    with required["fairness"].open(encoding="utf-8") as file:
        fairness = json.load(file)

    subgroups = {}
    for name, file_name in [
        ("race", "fairness_mitigated_race_clean.csv"),
        ("gender", "fairness_mitigated_gender_clean.csv"),
        ("age", "fairness_mitigated_age_group.csv"),
    ]:
        p = FAIRNESS_DIR / file_name
        if p.is_file():
            df = pd.read_csv(p).replace({np.nan: None})
            subgroups[name] = df.to_dict(orient="records")

    return {
        "model": joblib.load(required["model"]),
        "preprocessor": joblib.load(required["preprocessor"]),
        "worklist": worklist,
        "benchmarks": benchmarks,
        "fairness": fairness,
        "subgroups": subgroups,
    }


def _public_record(row: pd.Series) -> dict:
    return {
        "idx": int(row["idx"]),
        "enc_id": str(row["enc_id"]),
        "age": str(row["age"]),
        "age_group": str(row["age_group"]),
        "gender": str(row["gender"]),
        "race": str(row["race"]),
        "stay": int(row["stay"]),
        "meds": int(row["meds"]),
        "inpatient": int(row["inpatient"]),
        "er": int(row["er"]),
        "a1c": str(row["a1c"]),
        "diag": str(row["diag"]),
        "prob": float(row["prob"]),
        "tier": str(row["tier"]),
        "resources": [str(item) for item in row["resources"]],
        "top_factors": [str(item) for item in row["top_factors"]],
        "actual": int(row["actual"]),
    }


def _find_encounter(enc_id: str) -> pd.Series:
    worklist = load_assets()["worklist"]
    match = worklist.loc[worklist["enc_id"].astype(str) == enc_id]
    if match.empty:
        raise HTTPException(status_code=404, detail="Encounter not found in the demo cohort")
    return match.iloc[0]


class PredictionRequest(BaseModel):
    enc_id: str = Field(pattern=r"^ENC-\d+$")
    time_in_hospital: int = Field(ge=1, le=14)
    num_medications: int = Field(ge=1, le=50)
    number_inpatient: int = Field(ge=0, le=10)
    number_emergency: int = Field(ge=0, le=10)
    A1Cresult: Literal[">8", ">7", "Norm", "None", "Missing"]
    diag_1_cat: Literal[
        "Circulatory",
        "Respiratory",
        "Digestive",
        "Diabetes",
        "Injury",
        "Musculoskeletal",
        "Genitourinary",
        "Neoplasms",
        "Other",
        "Other/External",
    ]


app = FastAPI(
    title="ClinicalAI Research Demo API",
    version="1.0.0",
    description="Read-only scoring and cohort endpoints for a de-identified research demo.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "status": "online",
        "service": "clinicalai-api",
        "message": "ClinicalAI Hospital Readmission API is running.",
        "docs_url": "/docs",
        "health_check": "/api/health",
    }


@app.get("/api/health")
def health() -> dict:
    assets = load_assets()
    return {
        "status": "ok",
        "service": "clinicalai-api",
        "cohort_size": len(assets["worklist"]),
        "model": "calibrated ensemble",
    }


@app.get("/api/worklist")
def get_worklist(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=500),
    tier: Literal["all", "high", "moderate", "low"] = "all",
    age_group: str = "all",
    search: str = Query(default="", max_length=80),
) -> dict:
    records = load_assets()["worklist"]
    filtered = records
    if tier == "high":
        filtered = filtered.loc[filtered["prob"] >= 0.12]
    elif tier == "moderate":
        filtered = filtered.loc[(filtered["prob"] >= 0.08) & (filtered["prob"] < 0.12)]
    elif tier == "low":
        filtered = filtered.loc[filtered["prob"] < 0.08]
    if age_group != "all":
        filtered = filtered.loc[filtered["age_group"].astype(str) == age_group]
    page_num = page if isinstance(page, int) else 1
    page_len = page_size if isinstance(page_size, int) else 25
    search_query = str(search).strip() if isinstance(search, str) else ""
    if search_query:
        filtered = filtered.loc[
            filtered["enc_id"].astype(str).str.contains(search_query, case=False, regex=False)
        ]

    # Sort encounters by saved demo risk score, highest probability first
    filtered = filtered.sort_values(by=["prob", "idx"], ascending=[False, True])

    total = len(filtered)
    start = (page_num - 1) * page_len
    page_rows = filtered.iloc[start : start + page_len]
    all_records = records

    return {
        "results": [_public_record(row) for _, row in page_rows.iterrows()],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
        "summary": {
            "cohort_size": len(all_records),
            "high_risk": int((all_records["prob"] >= 0.12).sum()),
            "polypharmacy": int((all_records["meds"] >= 10).sum()),
            "readmissions": int((all_records["actual"] == 1).sum()),
        },
    }


@app.get("/api/encounters/{enc_id}")
def get_encounter(enc_id: str) -> dict:
    return {"encounter": _public_record(_find_encounter(enc_id))}


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict:
    encounter = _find_encounter(request.enc_id)
    patient = encounter["row_dict"].copy()
    assets = load_assets()

    orig_stay = int(encounter["stay"])
    orig_meds = int(encounter["meds"])
    orig_inpatient = int(encounter["inpatient"])
    orig_er = int(encounter["er"])
    orig_a1c = str(encounter["a1c"])
    orig_diag = str(encounter["diag"])

    # Normalize A1C test indicators: "None" and "Missing" both indicate unmeasured test
    requested_a1c = "Missing" if request.A1Cresult in ["None", "Missing"] else request.A1Cresult
    normalized_orig_a1c = "Missing" if orig_a1c in ["None", "Missing"] else orig_a1c

    is_unchanged = (
        request.time_in_hospital == orig_stay
        and request.num_medications == orig_meds
        and request.number_inpatient == orig_inpatient
        and request.number_emergency == orig_er
        and requested_a1c == normalized_orig_a1c
        and request.diag_1_cat == orig_diag
    )

    if is_unchanged:
        probability = float(encounter["prob"])
        tier = str(encounter["tier"])
        _, color, guidance = get_clinical_risk_tier(probability, optimal_thresh=0.120)
        engineered = engineer_features(pd.DataFrame([patient]))
    else:
        patient.update(
            {
                "time_in_hospital": request.time_in_hospital,
                "num_medications": request.num_medications,
                "number_inpatient": request.number_inpatient,
                "number_emergency": request.number_emergency,
                "A1Cresult": requested_a1c,
                "diag_1_cat": request.diag_1_cat,
                "diag_1_group": request.diag_1_cat,
            }
        )
        engineered = engineer_features(pd.DataFrame([patient]))
        transformed = assets["preprocessor"].transform(engineered)
        probability = float(assets["model"].predict_proba(transformed)[0, 1])
        tier, color, guidance = get_clinical_risk_tier(probability, optimal_thresh=0.120)

    patient_for_interventions = patient.copy()
    patient_for_interventions.update(
        {
            "time_in_hospital": request.time_in_hospital,
            "num_medications": request.num_medications,
            "number_inpatient": request.number_inpatient,
            "number_emergency": request.number_emergency,
            "A1Cresult": requested_a1c,
            "diag_1_cat": request.diag_1_cat,
            "diag_1_group": request.diag_1_cat,
        }
    )
    interventions = recommend_clinical_interventions(patient_for_interventions, probability)

    transformed = assets["preprocessor"].transform(engineered)
    model = assets["model"]
    importances = getattr(model, "feature_importances_", None)
    if importances is None and hasattr(model, "base_model"):
        importances = getattr(model.base_model, "feature_importances_", None)
    impacts = []
    if importances is not None:
        values = transformed.toarray()[0] if hasattr(transformed, "toarray") else np.asarray(transformed)[0]
        feature_names = assets["preprocessor"].get_feature_names_out()
        scored = values * np.asarray(importances)
        top_indices = np.argsort(np.abs(scored))[::-1][:6]
        impacts = [
            {"feature": clean_feature_label(str(feature_names[index])), "impact": float(scored[index])}
            for index in top_indices
            if abs(float(scored[index])) > 1e-4
        ]

    return {
        "enc_id": request.enc_id,
        "probability": probability,
        "tier": tier,
        "original_tier": str(encounter["tier"]),
        "original_probability": float(encounter["prob"]),
        "is_unchanged": is_unchanged,
        "color": color,
        "guidance": guidance,
        "interventions": interventions,
        "top_factors": impacts,
        "notice": "Research demonstration only; not validated for clinical use.",
    }


@app.get("/api/governance")
def get_governance() -> dict:
    assets = load_assets()
    return {
        "models": assets["benchmarks"],
        "fairness": assets["fairness"],
        "subgroups": assets.get("subgroups", {}),
        "selected_model": "Calibrated Ensemble",
        "last_audited": "October 2026",
        "model_version": "v2.4.1-calibrated-ensemble",
        "cohort_size": 19870,
        "demo_cohort_size": 500,
        "selected_unified_threshold": 0.12,
    }
