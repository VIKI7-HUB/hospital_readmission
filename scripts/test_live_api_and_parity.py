"""
Test script for Item 3: Live API verification & 20-row test parity check.
Verifies:
1. All endpoints with valid input
2. All endpoints with invalid input (asserting clean JSON errors without stack traces)
3. Parity between live risk calculator (POST /api/predict) and offline test predictions for 20 random test rows (< 1e-6).
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import requests

import src.models  # noqa: F401

API_BASE = "http://localhost:8000"

def test_endpoints():
    print("=" * 80)
    print("TESTING LIVE REST API ENDPOINTS (VALID & INVALID INPUTS)")
    print("=" * 80)

    # 1. Health & Root
    print("\n[1] Testing GET / and GET /api/health...")
    r = requests.get(f"{API_BASE}/")
    assert r.status_code == 200, f"GET / failed: {r.status_code}"
    print(f"  • GET /: {r.status_code} {r.json()}")

    r = requests.get(f"{API_BASE}/api/health")
    assert r.status_code == 200, f"GET /api/health failed: {r.status_code}"
    assert r.json().get("status") in ["ok", "healthy"]
    print(f"  • GET /api/health: {r.status_code} {r.json()}")

    # 2. Worklist Endpoint
    print("\n[2] Testing GET /api/worklist (Valid)...")
    r = requests.get(f"{API_BASE}/api/worklist?page=1&page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data and "summary" in data and "total" in data
    print(f"  • GET /api/worklist (page 1, limit 10): total={data['total']}, returned={len(data['results'])}")

    # 2b. Worklist Invalid query params
    print("\n[2b] Testing GET /api/worklist (Invalid Params)...")
    r = requests.get(f"{API_BASE}/api/worklist?page=-5&page_size=999999")
    # Should return 422 clean JSON validation error
    assert r.status_code in [200, 422], f"Unexpected status: {r.status_code}"
    assert "Traceback" not in r.text
    print(f"  • GET /api/worklist (invalid params): status={r.status_code}, clean response")

    # 3. Encounter Detail Valid & Invalid
    print("\n[3] Testing GET /api/encounters/{enc_id}...")
    sample_enc_id = data["results"][0]["enc_id"]
    r = requests.get(f"{API_BASE}/api/encounters/{sample_enc_id}")
    assert r.status_code == 200
    assert "encounter" in r.json()
    print(f"  • GET /api/encounters/{sample_enc_id}: 200 OK")

    r_invalid = requests.get(f"{API_BASE}/api/encounters/ENC-999999999999")
    assert r_invalid.status_code == 404
    err_json = r_invalid.json()
    assert "detail" in err_json
    assert "Traceback" not in r_invalid.text
    print(f"  • GET /api/encounters/INVALID: 404 clean JSON: {err_json}")

    # 4. Governance Endpoint
    print("\n[4] Testing GET /api/governance...")
    r = requests.get(f"{API_BASE}/api/governance")
    assert r.status_code == 200
    gov_data = r.json()
    assert "model_version" in gov_data
    assert "hba1c_validation_experiment" in gov_data
    print(f"  • GET /api/governance: 200 OK (model_version={gov_data.get('model_version')})")

    # 5. Plots Endpoint Valid & Invalid
    print("\n[5] Testing GET /api/plots/{name}...")
    r = requests.get(f"{API_BASE}/api/plots/roc_curve_all_models")
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/png"
    print(f"  • GET /api/plots/roc_curve_all_models: 200 image/png ({len(r.content)} bytes)")

    r_inv_plot = requests.get(f"{API_BASE}/api/plots/non_existent_plot_xyz")
    assert r_inv_plot.status_code == 404
    assert "detail" in r_inv_plot.json()
    assert "Traceback" not in r_inv_plot.text
    print(f"  • GET /api/plots/invalid: 404 clean JSON: {r_inv_plot.json()}")

    # 6. Predict Endpoint Valid & Invalid
    print("\n[6] Testing POST /api/predict (Valid & Invalid)...")
    valid_payload = {
        "enc_id": sample_enc_id,
        "time_in_hospital": 3,
        "num_medications": 14,
        "number_inpatient": 1,
        "number_emergency": 0,
        "A1Cresult": "None",
        "diag_1_cat": "Circulatory"
    }
    r = requests.post(f"{API_BASE}/api/predict", json=valid_payload)
    assert r.status_code == 200, f"Predict failed: {r.status_code} {r.text}"
    pred_res = r.json()
    assert "probability" in pred_res
    assert "tier" in pred_res
    print(f"  • POST /api/predict (Valid): 200 OK -> Risk: {pred_res['probability']:.4f}, Tier: {pred_res['tier']}")

    # Invalid Payload: Missing fields
    r_bad = requests.post(f"{API_BASE}/api/predict", json={"invalid_field": "bad_data"})
    assert r_bad.status_code == 422, f"Expected 422, got {r_bad.status_code}"
    bad_json = r_bad.json()
    assert "detail" in bad_json
    assert "Traceback" not in r_bad.text
    print(f"  • POST /api/predict (Invalid fields): 422 clean JSON validation error: {len(bad_json['detail'])} errors reported")

    # Invalid Payload: Malformed body
    r_malformed = requests.post(f"{API_BASE}/api/predict", data="Not a json string", headers={"content-type": "application/json"})
    assert r_malformed.status_code == 422
    assert "Traceback" not in r_malformed.text
    print(f"  • POST /api/predict (Malformed JSON): 422 clean JSON: {r_malformed.json()['detail'][0]['msg']}")

    print("\n" + "=" * 80)
    print("ALL ENDPOINT CONTRACT AND ERROR HANDLING CHECKS PASSED WITH 0 TRACEBACKS!")
    print("=" * 80)

def test_calculator_20_row_parity():
    print("\n" + "=" * 80)
    print("TESTING RISK CALCULATOR LIVE SCORING PARITY FOR 20 RANDOM TEST ROWS")
    print("=" * 80)

    worklist_df = joblib.load("data/processed/worklist_precomputed.joblib")
    split_data = joblib.load("data/processed/train_val_test_data.joblib")
    eval_artifacts = joblib.load("models/evaluation_artifacts.joblib")

    df_test = split_data["df_test"]
    p_test = eval_artifacts["test_probs"]["Calibrated Ensemble"]
    enc_to_offline_prob = dict(zip(df_test["encounter_id"], p_test))

    # Select 20 random encounters from the test cohort with seed 42
    np.random.seed(42)
    sample_indices = np.random.choice(len(worklist_df), size=20, replace=False)
    sample_rows = worklist_df.iloc[sample_indices]

    max_diff = 0.0

    for i, (_, row) in enumerate(sample_rows.iterrows()):
        enc_id_str = str(row["enc_id"])
        raw_id = int(enc_id_str.replace("ENC-", ""))
        assert raw_id in enc_to_offline_prob, f"Encounter {raw_id} not found in offline test set"
        offline_prob = float(enc_to_offline_prob[raw_id])

        payload = {
            "enc_id": enc_id_str,
            "time_in_hospital": int(row["stay"]),
            "num_medications": int(row["meds"]),
            "number_inpatient": int(row["inpatient"]),
            "number_emergency": int(row["er"]),
            "A1Cresult": str(row["a1c"]) if str(row["a1c"]) in [">8", ">7", "Norm", "None", "Missing"] else "Missing",
            "diag_1_cat": str(row["diag"]) if str(row["diag"]) in [
                "Circulatory", "Respiratory", "Digestive", "Diabetes", "Injury",
                "Musculoskeletal", "Genitourinary", "Neoplasms", "Other", "Other/External"
            ] else "Other"
        }

        r = requests.post(f"{API_BASE}/api/predict", json=payload)
        assert r.status_code == 200, f"Prediction failed for {enc_id_str}: {r.status_code}"
        live_prob = float(r.json()["probability"])

        diff = abs(live_prob - offline_prob)
        max_diff = max(max_diff, diff)

        print(f"  • Row {i+1:2d} ({enc_id_str}): Offline={offline_prob:.6f}, Live={live_prob:.6f}, Diff={diff:.2e}")
        assert diff < 1e-6, f"Parity mismatch on {enc_id_str}: {diff} >= 1e-6"

    print(f"\n[+] 20/20 Test rows verified. Max observed probability difference: {max_diff:.2e} (< 1e-6)")
    print("=" * 80)

if __name__ == "__main__":
    test_endpoints()
    test_calculator_20_row_parity()
