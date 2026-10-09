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
