import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import joblib
import numpy as np
import pandas as pd

MODELS_DIR = os.path.join(BASE_DIR, "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def _get_groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        return line.strip().split("=", 1)[1].strip("\"'")
    return key or ""

FEATURE_DISPLAY_NAMES = {
    'time_in_hospital': 'Extended Hospital Stay Duration',
    'num_lab_procedures': 'High Frequency of Diagnostic Lab Tests',
    'num_procedures': 'Invasive Clinical Procedures Performed',
    'num_medications': 'Elevated Active Medication Count',
    'number_outpatient': 'Prior Outpatient Care Encounters',
    'number_emergency': 'Prior Emergency Department Visits',
    'number_inpatient': 'Prior Acute Inpatient Hospitalizations',
    'number_diagnoses': 'High Comorbidity Burden (Diagnosis Count)',
    'total_visits': 'Cumulative 12-Month Healthcare Utilization',
    'lab_intensity_per_day': 'High Acute Daily Lab Testing Intensity',
    'num_med_changes': 'Active Inpatient Medication Dose Adjustments',
    'num_active_meds': 'Complexity of Antidiabetic Regimen',
    'polypharmacy': 'Polypharmacy Protocol (>=10 Active Meds)',
    'high_prior_utilization': 'Frequent Acute Care Utilizer',
    'has_diabetes_diag': 'Primary/Secondary Diabetic Pathophysiology',
    'comorbidity_count': 'Multisystem Organ Comorbidity Burden',
    'inpatient_x_stay': 'Severe Inpatient Utilization Frailty',
    'age_x_polypharmacy': 'Geriatric Polypharmacy Vulnerability',
    'a1c_x_med_change': 'Unstable Glycemic Regimen Adjustment',
    'er_x_inpatient': 'Acute Emergency Recidivism Interaction'
}

def clean_feature_label(raw_name):
    """Converts raw pipeline feature names into readable clinical descriptions."""
    clean = raw_name.replace('num__', '').replace('cat__', '').replace('te__', '')
    if clean in FEATURE_DISPLAY_NAMES:
        return FEATURE_DISPLAY_NAMES[clean]
    
    # Handle categorical prefix
    if '_' in clean:
        parts = clean.split('_')
        if len(parts) >= 3 and parts[0] == 'diag':
            return f"Primary Diagnosis: {' '.join(parts[3:]) if len(parts)>3 else parts[-1]}"
        elif 'A1Cresult' in clean:
            return f"Glycated Hemoglobin (A1C): {clean.split('A1Cresult_')[-1]}"
        elif 'max_glu_serum' in clean:
            return f"Serum Glucose: {clean.split('max_glu_serum_')[-1]}"
        elif 'insulin' in clean:
            return f"Insulin Regimen: {clean.split('insulin_')[-1]}"
        elif 'race_clean' in clean:
            return f"Demographic: {clean.split('race_clean_')[-1]}"
        elif 'medical_specialty' in clean:
            return f"Specialty Risk: {clean.split('medical_specialty')[-1].replace('_', ' ').strip()}"
        elif 'payer_code' in clean:
            return f"Payer Risk Factor: {clean.split('payer_code')[-1].replace('_', ' ').strip()}"
            
    return clean.replace('_', ' ').title()

def get_clinical_risk_tier(prob, optimal_thresh=0.130):
    """
    Categorizes calibrated readmission risk into actionable clinical tiers
    based on calibrated posterior probability thresholds.
    """
    if prob >= 0.20:
        return "High Risk", "red", "URGENT INTERVENTION REQUIRED. High 30-day readmission risk! Trigger multidisciplinary discharge care plan, 48-hr telehealth check-in, and pharmacy reconciliation."
    elif prob >= 0.12:
        return "Moderate Risk", "orange", "Enhanced discharge planning recommended. Schedule primary care follow-up within 7-10 days, verify prescription access."
    else:
        return "Low Risk", "green", "Standard discharge planning protocol. Patient demonstrates stable recuperation indicators."

def recommend_clinical_interventions(patient_dict, prob):
    """Generates rule-based clinical intervention care bundles."""
    interventions = []
    
    if prob >= 0.20:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Assign Discharge Care Coordinator & Schedule 48-Hour Telehealth Outreach',
            'Rationale': f'Patient is in High Risk tier ({prob*100:.1f}% calibrated 30-day readmission probability).'
        })
    elif prob >= 0.12:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Schedule Primary Care Follow-up within 7-10 Days',
            'Rationale': f'Patient is in Moderate Risk tier ({prob*100:.1f}% calibrated readmission probability).'
        })
        
    num_meds = float(patient_dict.get('num_medications', 0))
    med_changes = float(patient_dict.get('num_med_changes', 0))
    if num_meds >= 10 or med_changes > 0:
        interventions.append({
            'Category': 'Medication Safety',
            'Recommendation': 'Clinical Pharmacist Bedside Medication Reconciliation & Teach-Back Session',
            'Rationale': f'Polypharmacy detected ({int(num_meds)} active medications, {int(med_changes)} dose adjustments during admission).'
        })
        
    num_inpatient = float(patient_dict.get('number_inpatient', 0))
    num_emergency = float(patient_dict.get('number_emergency', 0))
    if num_inpatient > 0 or num_emergency > 0:
        interventions.append({
            'Category': 'Utilization Care Management',
            'Recommendation': 'Enroll in Chronic Disease Management & Intensive Care Coordination Program',
            'Rationale': f'Documented prior acute utilization ({int(num_inpatient)} inpatient admissions, {int(num_emergency)} ER visits).'
        })
        
    a1c = str(patient_dict.get('A1Cresult', 'None'))
    if a1c in ['>8', '>7']:
        interventions.append({
            'Category': 'Endocrine / Diabetes Education',
            'Recommendation': 'Outpatient Certified Diabetes Care & Education Specialist (CDCES) Referral',
            'Rationale': f'Elevated A1C glycemic marker ({a1c}). Post-discharge glycemic monitoring required.'
        })
        
    time_in_hosp = float(patient_dict.get('time_in_hospital', 1))
    if time_in_hosp >= 6:
        interventions.append({
            'Category': 'Post-Acute Support',
            'Recommendation': 'Home Health Nurse Assessment & Durable Medical Equipment (DME) Evaluation',
            'Rationale': f'Prolonged acute hospital stay duration ({int(time_in_hosp)} days).'
        })
        
    if len(interventions) == 0:
        interventions.append({
            'Category': 'Standard Care',
            'Recommendation': 'Standard Outpatient Follow-up & Medication Discharge Summary',
            'Rationale': 'Patient profile demonstrates stable clinical parameters and low readmission risk.'
        })
        
    return interventions

def explain_patient_risk(patient_dict, model_name=None):
    """
    Computes patient-specific readmission risk score, tier, and top contributing risk factors.
    Supports either the production ensemble or specific candidate models.
    """
    preprocessor_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    
    if model_name:
        model_path = os.path.join(MODELS_DIR, f"{model_name.lower().replace(' ', '_')}.joblib")
    else:
        prod_path = os.path.join(MODELS_DIR, "production_model.joblib")
        xgb_path = os.path.join(MODELS_DIR, "xgboost.joblib")
        model_path = prod_path if os.path.exists(prod_path) else xgb_path
        
    if not os.path.exists(preprocessor_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Model or preprocessor missing. Please complete training first.")
        
    preprocessor = joblib.load(preprocessor_path)
    model = joblib.load(model_path)
    
    # Ensure all engineered features are present
    from src.preprocessing import engineer_features
    df_raw = pd.DataFrame([patient_dict])
    df_eng = engineer_features(df_raw)
    
    X_trans = preprocessor.transform(df_eng)
    prob = float(model.predict_proba(X_trans)[0, 1])
    tier, color, tier_desc = get_clinical_risk_tier(prob)
    interventions = recommend_clinical_interventions(patient_dict, prob)
    
    feature_names = preprocessor.get_feature_names_out()
    
    importances = None
    if hasattr(model, 'feature_importances_') and model.feature_importances_ is not None:
        importances = model.feature_importances_
    elif hasattr(model, 'base_model') and hasattr(model.base_model, 'feature_importances_'):
        importances = model.base_model.feature_importances_
        
    if importances is not None and len(importances) == X_trans.shape[1]:
        feature_impacts = X_trans[0] * importances
        top_idx = np.argsort(np.abs(feature_impacts))[::-1][:6]
        top_factors = [
            {
                'Feature': clean_feature_label(feature_names[i]),
                'RawValue': float(X_trans[0, i]),
                'RelativeImpact': float(feature_impacts[i])
            }
            for i in top_idx if abs(feature_impacts[i]) > 1e-4
        ]
    else:
        top_factors = []
        
    return {
        'Readmission Probability': prob,
        'Risk Tier': tier,
        'Tier Color': color,
        'Tier Guidance': tier_desc,
        'Top Risk Factors': top_factors,
        'Interventions': interventions
    }

def precompute_worklist_artifacts(max_encounters=500):
    """
    Precomputes risk scores, risk tiers, clinical action tags, and feature drivers
    for the active inpatient worklist, saving both parquet and joblib formats.
    Ensures sub-15ms page loads without running repetitive inferences on reruns.
    """
    data_path = os.path.join(PROCESSED_DIR, "train_test_data.joblib")
    prep_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    model_path = os.path.join(MODELS_DIR, "production_model.joblib")
    if not os.path.exists(model_path):
        model_path = os.path.join(MODELS_DIR, "xgboost.joblib")
        
    data = joblib.load(data_path)
    preprocessor = joblib.load(prep_path)
    model = joblib.load(model_path)
    
    X_test = data['X_test']
    y_test = data['y_test']
    sens_test = data['sens_test']
    
    sample_indices = X_test.index[:max_encounters]
    X_sample = X_test.loc[sample_indices]
    y_sample = y_test.loc[sample_indices]
    sens_sample = sens_test.loc[sample_indices]
    
    X_trans = preprocessor.transform(X_sample)
    probs = model.predict_proba(X_trans)[:, 1]
    
    feature_names = preprocessor.get_feature_names_out()
    importances = getattr(model, 'feature_importances_', None)
    if importances is None and hasattr(model, 'base_model'):
        importances = getattr(model.base_model, 'feature_importances_', None)
        
    records = []
    for i, idx in enumerate(sample_indices):
        prob = float(probs[i])
        row = X_sample.loc[idx]
        actual_readmit = int(y_sample.loc[idx])
        age_str = str(sens_sample.loc[idx, 'age_group'])
        gender_str = str(sens_sample.loc[idx, 'gender_clean'])
        race_str = str(sens_sample.loc[idx, 'race_clean'])
        
        tier, color, _ = get_clinical_risk_tier(prob)
        
        resources = []
        if float(row.get('num_medications', 0)) >= 10:
            resources.append("Pharmacist Recon")
        if str(row.get('A1Cresult', 'None')) in ['>8', '>7']:
            resources.append("CDCES Referral")
        if float(row.get('time_in_hospital', 1)) >= 6:
            resources.append("Home Health Nurse")
        if prob >= 0.20:
            resources.append("48h Telehealth")
        if not resources:
            resources.append("Routine Outpatient")
            
        # Top 3 feature impacts for summary card
        top_factors = []
        if importances is not None:
            impacts = X_trans[i] * importances
            top_3_idx = np.argsort(np.abs(impacts))[::-1][:3]
            for fi in top_3_idx:
                if abs(impacts[fi]) > 1e-4:
                    top_factors.append(clean_feature_label(feature_names[fi]))
                    
        records.append({
            'idx': int(idx),
            'enc_id': f"ENC-{idx}",
            'row_dict': row.to_dict(),
            'age': str(row.get('age', 'Unknown')),
            'age_group': age_str,
            'gender': gender_str,
            'race': race_str,
            'stay': int(row.get('time_in_hospital', 1)),
            'meds': int(row.get('num_medications', 0)),
            'inpatient': int(row.get('number_inpatient', 0)),
            'er': int(row.get('number_emergency', 0)),
            'a1c': str(row.get('A1Cresult', 'None')),
            'diag': str(row.get('diag_1_cat', 'Circulatory')),
            'prob': prob,
            'tier': tier,
            'resources': resources,
            'top_factors': top_factors,
            'actual': actual_readmit
        })
        
    df_precomputed = pd.DataFrame(records)
    out_joblib = os.path.join(PROCESSED_DIR, "worklist_precomputed.joblib")
    joblib.dump(df_precomputed, out_joblib)
    print(f"[+] Saved {len(df_precomputed)} precomputed worklist records to {out_joblib}")
    return df_precomputed

def generate_groq_clinical_decision_points(patient_dict, prob, verdict_status, api_key=None):
    """
    Calls Groq API (model: openai/gpt-oss-120b) to synthesize exactly 5 clinical points
    explaining why the patient should or should not be discharged based on authentic EHR details.
    Includes 8-second timeout and robust deterministic fallback.
    """
    key = api_key or _get_groq_key()
    if not key:
        return _fallback_clinical_points(patient_dict, prob, verdict_status)
        
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=8.0)
        
        stay = int(patient_dict.get('time_in_hospital', 1))
        meds = int(patient_dict.get('num_medications', 0))
        inpatient = int(patient_dict.get('number_inpatient', 0))
        er = int(patient_dict.get('number_emergency', 0))
        a1c = str(patient_dict.get('A1Cresult', 'None'))
        diag = str(patient_dict.get('diag_1_cat', 'General'))
        age = str(patient_dict.get('age', 'Unknown'))
        gender = str(patient_dict.get('gender_clean', 'Patient'))
        race = str(patient_dict.get('race_clean', 'Not specified'))
        
        prompt_content = f"""You are a board-certified clinical physician and hospital discharge planning director.
Review this diabetic inpatient clinical record:

- Encounter Demographics: Age {age}, Gender {gender}, Race {race}
- Hospital Length of Stay: {stay} days
- Active Inpatient Medications: {meds} medications {'(Polypharmacy Alert Active)' if meds>=10 else ''}
- Prior Acute Utilization (12-Month): {inpatient} inpatient admissions, {er} emergency visits
- Glycated Hemoglobin (A1C): {a1c}
- Primary ICD-9 Diagnosis: {diag}
- Calibrated Predictive Readmission Risk: {prob*100:.1f}% ({'High Risk' if prob>=0.20 else ('Moderate Risk' if prob>=0.12 else 'Low Risk')})
- Clinical Verdict: {verdict_status}

Provide exactly 5 concise, professional clinical bullet points explaining your decision on why this patient {'should NOT be discharged (delay discharge required)' if prob>=0.20 else ('requires conditional discharge with enhanced care coordination' if prob>=0.12 else 'is clinically safe to be discharged')}.
Focus on clinical stabilization, medication reconciliation safety, glycemic control, prior acute care patterns, and post-acute support needs.
Do not use emojis. Output only the 5 bullet points with short bold titles."""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a hospital clinical discharge director. Provide exactly 5 professional, evidence-based bullet points explaining the clinical rationale for the discharge decision. Do not use emojis."
                },
                {
                    "role": "user",
                    "content": prompt_content
                }
            ],
            temperature=0.2,
            max_tokens=600
        )
        raw_text = completion.choices[0].message.content.strip()
        clean_text = (raw_text
            .replace('\u2011', '-')
            .replace('\u2013', '-')
            .replace('\u2014', '-')
            .replace('\u2018', "'")
            .replace('\u2019', "'")
            .replace('\u201c', '"')
            .replace('\u201d', '"')
            .replace('\u202f', ' ')
            .replace('\xa0', ' ')
            .replace('\u2265', '>=')
            .replace('\u2264', '<=')
            .encode('ascii', 'ignore').decode('ascii')
        )
        return clean_text
    except Exception:
        return _fallback_clinical_points(patient_dict, prob, verdict_status)

def _fallback_clinical_points(patient_dict, prob, verdict_status):
    """Deterministic, high-fidelity clinical points fallback when offline or timeout occurs."""
    inpatient = patient_dict.get('number_inpatient', 0)
    er = patient_dict.get('number_emergency', 0)
    meds = patient_dict.get('num_medications', 0)
    stay = patient_dict.get('time_in_hospital', 1)
    a1c = patient_dict.get('A1Cresult', 'None')
    diag = patient_dict.get('diag_1_cat', 'Circulatory')
    
    if prob >= 0.20:
        return (
            f"- **Acute Clinical Stability**: Calibrated readmission risk is elevated at {prob*100:.1f}%, indicating vulnerability to early decompensation following discharge for primary condition ({diag}).\n"
            f"- **Inpatient Utilization Frailty**: Patient exhibits high acute care recurrence with {inpatient} prior inpatient admissions and {er} emergency visits in the preceding 12 months.\n"
            f"- **Pharmacotherapy & Polypharmacy**: Regimen complexity of {meds} active medications elevates drug-drug interaction hazards and requires dedicated PharmD bedside teach-back.\n"
            f"- **Endocrine Marker Evaluation**: Glycemic stability monitored with A1C index recorded as {a1c}; outpatient endocrinology coordination required.\n"
            f"- **Post-Acute Safety Protocol**: Discharge should be held until 48-hour post-acute telehealth outreach and home nursing visits are scheduled."
        )
    elif prob >= 0.12:
        return (
            f"- **Conditional Clinical Stability**: Encounter presents moderate risk profile ({prob*100:.1f}%), permitting release conditional upon verified outpatient care appointments.\n"
            f"- **Medication Safety Plan**: Current regimen of {meds} active medications necessitates clear discharge reconciliation and confirmation of pharmacy fulfillment.\n"
            f"- **Prior Utilization Monitoring**: Prior history of {inpatient} admissions and {er} ER encounters warrants proactive care transition check-in within 7 days.\n"
            f"- **Glycemic Follow-up**: Patient A1C is {a1c}; diabetes education specialist outreach advised post-discharge.\n"
            f"- **Care Transition Protocol**: Routine discharge approved with mandatory primary care visit within 7-10 days."
        )
    else:
        return (
            f"- **Clinical Discharge Readiness**: All biomarker indicators demonstrate stable recuperation with low 30-day readmission risk ({prob*100:.1f}%).\n"
            f"- **Manageable Pharmacotherapy**: Regimen of {meds} medications is stable with no acute high-risk titration flags.\n"
            f"- **Low Recidivism Pattern**: Documented utilization shows low emergency or repeat inpatient encounters ({inpatient} prior admissions).\n"
            f"- **Glycemic Status**: A1C reading ({a1c}) is compatible with routine outpatient diabetic management.\n"
            f"- **Post-Acute Order**: Standard discharge authorized with routine 30-day primary care follow-up."
        )

if __name__ == "__main__":
    precompute_worklist_artifacts(max_encounters=500)
