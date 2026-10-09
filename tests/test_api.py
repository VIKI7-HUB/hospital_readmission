"""
Smoke and integration tests for FastAPI backend endpoints.
Verifies status codes, JSON response shapes, error handling, and parameter validation.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "clinicalai-api"
    assert "docs_url" in data
    assert "health_check" in data

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "clinicalai-api"
    assert data["cohort_size"] == 500
    assert "model" in data

def test_worklist_default(client):
    response = client.get("/api/worklist")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "summary" in data
    assert "total" in data
    assert data["total"] == 500
    assert len(data["results"]) == 25
    summary = data["summary"]
    assert summary["cohort_size"] == 500
    assert summary["flagged"] == 189
    assert summary["high_risk"] == 44
    assert summary["elevated_risk"] == 145
    assert summary["low_risk"] == 311
    assert summary["polypharmacy"] == 395
    assert summary["readmissions"] == 54

def test_worklist_filters_and_pagination(client):
    # Tier filter: flagged (all >= 0.12)
    res_flagged = client.get("/api/worklist", params={"tier": "flagged", "page_size": 200})
    assert res_flagged.status_code == 200
    data_flagged = res_flagged.json()
    assert data_flagged["total"] == 189
    for row in data_flagged["results"]:
        assert row["prob"] >= 0.12

    # Tier filter: high (top decile >= 0.20)
    res_high = client.get("/api/worklist", params={"tier": "high", "page_size": 100})
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert data_high["total"] == 44
    for row in data_high["results"]:
        assert row["prob"] >= 0.20

    # Tier filter: elevated (0.12 <= prob < 0.20)
    res_elev = client.get("/api/worklist", params={"tier": "elevated", "page_size": 200})
    assert res_elev.status_code == 200
    data_elev = res_elev.json()
    assert data_elev["total"] == 145
    for row in data_elev["results"]:
        assert 0.12 <= row["prob"] < 0.20

    # Tier filter: low (< 0.12)
    res_low = client.get("/api/worklist", params={"tier": "low", "page_size": 400})
    assert res_low.status_code == 200
    data_low = res_low.json()
    assert data_low["total"] == 311
    for row in data_low["results"]:
        assert row["prob"] < 0.12

    # Age group filter
    res_age = client.get("/api/worklist", params={"age_group": "60+ Years"})
    assert res_age.status_code == 200
    for row in res_age.json()["results"]:
        assert row["age_group"] == "60+ Years"

    # Search filter
    sample_enc = data_high["results"][0]["enc_id"]
    res_search = client.get("/api/worklist", params={"search": sample_enc})
    assert res_search.status_code == 200
    assert len(res_search.json()["results"]) >= 1
    assert res_search.json()["results"][0]["enc_id"] == sample_enc

def test_get_encounter_success(client):
    # Get a valid encounter ID from worklist
    res_wl = client.get("/api/worklist", params={"page_size": 1})
    enc_id = res_wl.json()["results"][0]["enc_id"]
    
    response = client.get(f"/api/encounters/{enc_id}")
    assert response.status_code == 200
    data = response.json()
    assert "encounter" in data
    encounter = data["encounter"]
    assert encounter["enc_id"] == enc_id
    assert "stay" in encounter
    assert "meds" in encounter
    assert "inpatient" in encounter
    assert "er" in encounter
    assert "prob" in encounter
    assert "tier" in encounter
    assert "resources" in encounter
    assert isinstance(encounter["resources"], list)

def test_get_encounter_not_found(client):
    response = client.get("/api/encounters/ENC-999999999999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_predict_endpoint_success(client):
    res_wl = client.get("/api/worklist", params={"page_size": 1})
    first = res_wl.json()["results"][0]
    
    payload = {
        "enc_id": first["enc_id"],
        "time_in_hospital": first["stay"],
        "num_medications": first["meds"],
        "number_inpatient": first["inpatient"],
        "number_emergency": first["er"],
        "A1Cresult": first["a1c"] if first["a1c"] in [">8", ">7", "Norm", "None", "Missing"] else "Missing",
        "diag_1_cat": first["diag"] if first["diag"] in [
            "Circulatory", "Respiratory", "Digestive", "Diabetes", "Injury",
            "Musculoskeletal", "Genitourinary", "Neoplasms", "Other", "Other/External"
        ] else "Other"
    }
    
    # 1. Unchanged prediction
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_unchanged"] is True
    assert abs(data["probability"] - first["prob"]) < 1e-4
    assert data["tier"] == first["tier"]
    assert "interventions" in data
    assert "top_factors" in data

    # 2. Modified scenario prediction (reduce utilization to 0)
    modified_payload = payload.copy()
    modified_payload["time_in_hospital"] = 1
    modified_payload["num_medications"] = 2
    modified_payload["number_inpatient"] = 0
    modified_payload["number_emergency"] = 0
    
    res_mod = client.post("/api/predict", json=modified_payload)
    assert res_mod.status_code == 200
    data_mod = res_mod.json()
    assert data_mod["is_unchanged"] is False
    assert data_mod["probability"] < data["probability"]
    assert "interventions" in data_mod

def test_predict_validation_errors(client):
    # Invalid enc_id pattern
    res_bad_id = client.post("/api/predict", json={
        "enc_id": "INVALID-ID",
        "time_in_hospital": 3,
        "num_medications": 10,
        "number_inpatient": 0,
        "number_emergency": 0,
        "A1Cresult": "None",
        "diag_1_cat": "Circulatory"
    })
    assert res_bad_id.status_code == 422
    assert "detail" in res_bad_id.json()

    # Out of range time_in_hospital (> 14)
    res_bad_stay = client.post("/api/predict", json={
        "enc_id": "ENC-100",
        "time_in_hospital": 99,
        "num_medications": 10,
        "number_inpatient": 0,
        "number_emergency": 0,
        "A1Cresult": "None",
        "diag_1_cat": "Circulatory"
    })
    assert res_bad_stay.status_code == 422

    # Missing required field
    res_missing = client.post("/api/predict", json={
        "enc_id": "ENC-100",
        "time_in_hospital": 5
    })
    assert res_missing.status_code == 422

def test_governance_endpoint(client):
    response = client.get("/api/governance")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "fairness" in data
    assert "subgroups" in data
    assert data["selected_model"] == "Calibrated Ensemble"
    assert data["cohort_size"] == 19870
    assert data["demo_cohort_size"] == 500
    assert len(data["models"]) == 6
    # Verify candidate models list includes expected models
    model_names = [m["Model"] for m in data["models"]]
    assert "Logistic Regression" in model_names
    assert "Random Forest" in model_names
    assert "XGBoost" in model_names
    assert "LightGBM" in model_names
    assert "CatBoost" in model_names
    assert "Calibrated Ensemble" in model_names

def test_worklist_offline_prediction_parity(client):
    """
    Automated parity test: For all 500 worklist encounters, probabilities returned
    by the API must match the offline test-set predictions within 1e-6, and tiers
    must match exactly.
    """
    import os, joblib
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "data", "processed")
    models_dir = os.path.join(base_dir, "models")

    res = client.get("/api/worklist", params={"page_size": 500})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 500
    results = data["results"]
    assert len(results) == 500

    split_data = joblib.load(os.path.join(processed_dir, "train_val_test_data.joblib"))
    eval_artifacts = joblib.load(os.path.join(models_dir, "evaluation_artifacts.joblib"))

    df_test = split_data["df_test"]
    p_test = eval_artifacts["test_probs"]["Calibrated Ensemble"]
    enc_to_offline_prob = dict(zip(df_test["encounter_id"], p_test))

    for row in results:
        raw_id = int(row["enc_id"].replace("ENC-", ""))
        assert raw_id in enc_to_offline_prob, f"Encounter {raw_id} not found in offline test set"
        offline_p = enc_to_offline_prob[raw_id]
        api_p = row["prob"]

        # Parity check: difference within 1e-6
        assert abs(api_p - offline_p) < 1e-6, f"Parity mismatch for {row['enc_id']}: API={api_p}, Offline={offline_p}"

        # Tier check
        expected_tier = "High Risk" if offline_p >= 0.20 else ("Elevated Risk" if offline_p >= 0.12 else "Low Risk")
        assert row["tier"] == expected_tier, f"Tier mismatch for {row['enc_id']}: API={row['tier']}, Expected={expected_tier}"


def test_live_scoring_path_parity_50_encounters(client):
    """
    Automated parity test: Sends raw feature rows for 50 test encounters through
    the LIVE scoring path used by the Risk calculator (not the precomputed worklist)
    and verifies that probabilities match offline test predictions with diff < 1e-6.
    """
    import os, joblib, pandas as pd
    from src.preprocessing import engineer_features

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "data", "processed")
    models_dir = os.path.join(base_dir, "models")

    # Load offline test predictions and precomputed worklist encounters
    split_data = joblib.load(os.path.join(processed_dir, "train_val_test_data.joblib"))
    eval_artifacts = joblib.load(os.path.join(models_dir, "evaluation_artifacts.joblib"))
    worklist_df = joblib.load(os.path.join(processed_dir, "worklist_precomputed.joblib"))

    df_test = split_data["df_test"]
    p_test = eval_artifacts["test_probs"]["Calibrated Ensemble"]
    enc_to_offline_prob = dict(zip(df_test["encounter_id"], p_test))

    # Test first 50 encounters
    sample_50 = worklist_df.iloc[:50]
    for _, row in sample_50.iterrows():
        raw_id = int(str(row["enc_id"]).replace("ENC-", ""))
        assert raw_id in enc_to_offline_prob, f"Encounter {raw_id} not found in offline test set"
        offline_p = enc_to_offline_prob[raw_id]

        payload = {
            "enc_id": str(row["enc_id"]),
            "time_in_hospital": int(row["stay"]),
            "num_medications": int(row["meds"]),
            "number_inpatient": int(row["inpatient"]),
            "number_emergency": int(row["er"]),
            "A1Cresult": str(row["a1c"]) if str(row["a1c"]) in [">8", ">7", "Norm", "None", "Missing"] else "Missing",
            "diag_1_cat": str(row["diag"]) if str(row["diag"]) in [
                "Circulatory", "Respiratory", "Digestive", "Diabetes", "Injury",
                "Musculoskeletal", "Genitourinary", "Neoplasms", "Other", "Other/External"
            ] else "Other",
        }

        # 1. Test via LIVE scoring endpoint (calls engineer_features -> preprocessor.transform -> model.predict_proba)
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 200
        live_prob_api = response.json()["probability"]
        assert abs(live_prob_api - offline_p) < 1e-6, (
            f"API live scoring mismatch for {row['enc_id']}: API={live_prob_api}, Offline={offline_p}"
        )

        # 2. Test raw feature row dictionary directly through the live scoring pipeline components
        raw_dict = row["row_dict"].copy()
        raw_df = pd.DataFrame([raw_dict])
        eng_df = engineer_features(raw_df)
        model = eval_artifacts["trained_models"]["Calibrated Ensemble"]
        preproc = joblib.load(os.path.join(processed_dir, "preprocessor.joblib"))
        x_trans = preproc.transform(eng_df)
        live_prob_pipeline = float(model.predict_proba(x_trans)[0, 1])
        assert abs(live_prob_pipeline - offline_p) < 1e-6, (
            f"Pipeline live scoring mismatch for {row['enc_id']}: Pipeline={live_prob_pipeline}, Offline={offline_p}"
        )


