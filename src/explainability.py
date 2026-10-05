import os
import joblib
import numpy as np
import pandas as pd

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")

def _get_groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        return line.strip().split("=", 1)[1].strip("\"'")
    return key or ""

GROQ_API_KEY = _get_groq_key()

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
    'high_prior_utilization': 'Frequent Acute Care Utilizer'
}

def clean_feature_label(raw_name):
    """Converts raw pipeline feature names into readable clinical descriptions."""
    clean = raw_name.replace('num__', '').replace('cat__', '')
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
            
    return clean.replace('_', ' ').title()

def get_clinical_risk_tier(prob):
    """Categorizes readmission risk into actionable clinical tiers."""
    if prob < 0.25:
        return "Low Risk", "green", "Standard discharge planning protocol. Provide routine discharge summary and outpatient follow-up instructions."
    elif prob < 0.50:
        return "Moderate Risk", "orange", "Enhanced discharge planning recommended. Schedule outpatient follow-up within 7-10 days, verify prescription access."
    else:
        return "High Risk", "red", "URGENT INTERVENTION REQUIRED. High 30-day readmission risk! Trigger multidisciplinary discharge care plan, 48-hr telehealth check-in, and home health consult."

def recommend_clinical_interventions(patient_dict, prob):
    """
    Generates rule-based clinical intervention recommendations based on patient encounter features.
    """
    interventions = []
    
    if prob >= 0.50:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Assign Discharge Care Coordinator & Schedule 48-Hour Telehealth Follow-up',
            'Rationale': f'Patient is in High Risk tier ({prob*100:.1f}% 30-day readmission probability).'
        })
    elif prob >= 0.25:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Schedule Primary Care Follow-up within 7 Days',
            'Rationale': f'Patient is in Moderate Risk tier ({prob*100:.1f}% 30-day readmission probability).'
        })
        
    # Polypharmacy / Med Changes
    num_meds = float(patient_dict.get('num_medications', 0))
    med_changes = float(patient_dict.get('num_med_changes', 0))
    if num_meds >= 10 or med_changes > 0:
        interventions.append({
            'Category': 'Medication Safety',
            'Recommendation': 'Clinical Pharmacist Bedside Medication Reconciliation & Teach-Back Session',
            'Rationale': f'Polypharmacy detected ({int(num_meds)} active medications, {int(med_changes)} dose adjustments during admission).'
        })
        
    # High Prior Utilization
    num_inpatient = float(patient_dict.get('number_inpatient', 0))
    num_emergency = float(patient_dict.get('number_emergency', 0))
    if num_inpatient > 0 or num_emergency > 0:
        interventions.append({
            'Category': 'Utilization Care Management',
            'Recommendation': 'Enroll in Chronic Disease Management & Intensive Care Coordination Program',
            'Rationale': f'Documented prior acute utilization ({int(num_inpatient)} inpatient admissions, {int(num_emergency)} ER visits).'
        })
        
    # Glycemic Control
    a1c = str(patient_dict.get('A1Cresult', 'None'))
    if a1c in ['>8', '>7']:
        interventions.append({
            'Category': 'Endocrine / Diabetes Education',
            'Recommendation': 'Outpatient Certified Diabetes Care & Education Specialist (CDCES) Referral',
            'Rationale': f'Elevated A1C glycemic marker ({a1c}). Post-discharge glycemic monitoring required.'
        })
        
    # Extended Stay / Lab Intensity
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

def explain_patient_risk(patient_dict, model_name='XGBoost'):
    """
    Computes patient-specific readmission risk score, tier, and top contributing risk factors.
    """
    preprocessor_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    model_path = os.path.join(MODELS_DIR, f"{model_name.lower().replace(' ', '_')}.joblib")
    
    if not os.path.exists(preprocessor_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Model or preprocessor missing. Please complete training first.")
        
    preprocessor = joblib.load(preprocessor_path)
    model = joblib.load(model_path)
    
    df_patient = pd.DataFrame([patient_dict])
    X_trans = preprocessor.transform(df_patient)
    
    prob = float(model.predict_proba(X_trans)[0, 1])
    tier, color, tier_desc = get_clinical_risk_tier(prob)
    interventions = recommend_clinical_interventions(patient_dict, prob)
    
    feature_names = preprocessor.get_feature_names_out()
    
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
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

def generate_groq_clinical_decision_points(patient_dict, prob, verdict_status, api_key=None):
    """
    Calls Groq API (model: openai/gpt-oss-120b) to synthesize exactly 5 clinical points
    explaining why the patient should or should not be discharged based on authentic EHR details.
    Called on-demand when the patient popup is invoked.
    """
    key = api_key or GROQ_API_KEY
    try:
        from groq import Groq
        client = Groq(api_key=key)
        
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
- XGBoost Predictive Readmission Risk: {prob*100:.1f}% ({'High Risk' if prob>=0.5 else ('Moderate Risk' if prob>=0.25 else 'Low Risk')})
- Clinical Verdict: {verdict_status}

Provide exactly 5 concise, professional clinical bullet points explaining your decision on why this patient {'should NOT be discharged (delay discharge required)' if prob>=0.50 else ('requires conditional discharge with enhanced care coordination' if prob>=0.25 else 'is clinically safe to be discharged')}.
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
    except Exception as e:
        # Fallback to rule-based points in case of rate limits or network issues
        err_msg = str(e)
        return (
            f"- **Clinical Risk Evaluation**: Model calculates {prob*100:.1f}% 30-day readmission risk based on clinical parameters.\n"
            f"- **Acute Utilization Pattern**: Documented history of {patient_dict.get('number_inpatient', 0)} prior inpatient admissions and {patient_dict.get('number_emergency', 0)} emergency visits.\n"
            f"- **Therapeutic Regimen Complexity**: Active count of {patient_dict.get('num_medications', 0)} concurrent medications requiring reconciliation.\n"
            f"- **Glycemic Stability**: A1C result recorded as {patient_dict.get('A1Cresult', 'None')}.\n"
            f"- **Post-Acute Transition Plan**: Multidisciplinary discharge follow-up required before home release."
        )
