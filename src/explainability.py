import json
import os

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

FEATURE_LABELS = {
    'number_inpatient': 'Prior Inpatient Hospitalizations (Past 12 Mo)',
    'number_emergency': 'Prior Emergency Department Visits',
    'number_outpatient': 'Prior Outpatient Encounters',
    'time_in_hospital': 'Hospital Length of Stay (Days)',
    'num_medications': 'Total Inpatient Medications Administered',
    'num_lab_procedures': 'Diagnostic Laboratory Procedures Performed',
    'diag_1_group_Circulatory': 'Primary Diagnosis: Circulatory (CVD / CHF / CAD)',
    'diag_1_group_Respiratory': 'Primary Diagnosis: Respiratory (COPD / Pneumonia)',
    'diag_1_group_Diabetes': 'Primary Diagnosis: Diabetes Mellitus with Complications',
    'diag_1_group_Digestive': 'Primary Diagnosis: Digestive Disease',
    'diag_1_group_Genitourinary': 'Primary Diagnosis: Genitourinary / Renal Disease',
    'diag_1_group_Injury': 'Primary Diagnosis: Acute Trauma / Injury',
    'diag_1_group_Musculoskeletal': 'Primary Diagnosis: Musculoskeletal System',
    'diag_1_group_Neoplasms': 'Primary Diagnosis: Oncology / Neoplasms',
    'diag_1_group_Other': 'Primary Diagnosis: Other Specialized Conditions',
    'diag_1_group_Other/External': 'Primary Diagnosis: External Factors',
    'discharge_destination_Home': 'Discharge Destination: Home / Self-Care',
    'discharge_destination_Facility_Rehab': 'Discharge Destination: Skilled Nursing / Rehab Facility',
    'discharge_destination_Left_AMA': 'Discharge Destination: Left Against Medical Advice',
    'discharge_destination_Other_Unknown': 'Discharge Destination: Other Clinical Pathway',
    'insulin_regimen_No': 'Insulin Protocol: Not Prescribed',
    'insulin_regimen_Steady': 'Insulin Protocol: Maintained on Steady Regimen',
    'insulin_regimen_Up': 'Insulin Protocol: Dosage Escalated During Stay',
    'insulin_regimen_Down': 'Insulin Protocol: Dosage De-escalated During Stay',
    'medication_change_Ch': 'Medication Change: Inpatient Dose / Drug Adjustment Made',
    'medication_change_No': 'Medication Change: No Medication Adjustments Made',
    'age_group_<30 Years': 'Age Demographic: Younger Adult (<30 Years)',
    'age_group_30-60 Years': 'Age Demographic: Middle Adult (30-60 Years)',
    'age_group_60+ Years': 'Age Demographic: Older Adult (60+ Years)',
    'gender_clean_Female': 'Sex / Gender: Female',
    'gender_clean_Male': 'Sex / Gender: Male',
    'race_clean_Caucasian': 'Race Demographic: Caucasian',
    'race_clean_AfricanAmerican': 'Race Demographic: African American',
    'race_clean_Hispanic': 'Race Demographic: Hispanic',
    'race_clean_Asian': 'Race Demographic: Asian',
    'race_clean_Other/Unknown': 'Race Demographic: Other / Unspecified'
}

def clean_feature_name(col):
    if col.startswith('num__'):
        clean = col.replace('num__', '')
    elif col.startswith('cat__'):
        clean = col.replace('cat__', '')
    else:
        clean = col
    return FEATURE_LABELS.get(clean, clean.replace('_', ' ').title())

clean_feature_label = clean_feature_name

def recommend_clinical_interventions(patient_dict, prob):
    """
    Generates rule-based clinical intervention care bundles tailored to risk tier and patient utilization.
    """
    interventions = []
    
    if prob >= 0.120:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Assign Discharge Care Coordinator & Schedule 48-Hour Telehealth Outreach',
            'Rationale': f'Patient is in High Risk tier ({prob*100:.1f}% calibrated 30-day readmission probability).'
        })
    elif prob >= 0.080:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Schedule Primary Care Follow-up within 7-10 Days',
            'Rationale': f'Patient is in Moderate Risk tier ({prob*100:.1f}% calibrated readmission probability).'
        })
    else:
        interventions.append({
            'Category': 'Primary Clinical Action',
            'Recommendation': 'Standard Primary Care Follow-up within 14-30 Days',
            'Rationale': f'Patient is in Low Risk tier ({prob*100:.1f}% calibrated readmission probability).'
        })
        
    num_meds = float(patient_dict.get('num_medications', 0))
    if num_meds >= 10:
        interventions.append({
            'Category': 'Medication Safety',
            'Recommendation': 'Clinical Pharmacist Bedside Medication Reconciliation & Teach-Back Session',
            'Rationale': f'Polypharmacy detected ({int(num_meds)} active medications administered during stay).'
        })
        
    num_inpatient = float(patient_dict.get('number_inpatient', 0))
    num_emergency = float(patient_dict.get('number_emergency', 0))
    if num_inpatient > 0 or num_emergency > 0:
        interventions.append({
            'Category': 'Utilization Care Management',
            'Recommendation': 'Post-Acute Care Transition Protocol with Case Manager',
            'Rationale': f'Frequent prior acute utilization ({int(num_inpatient)} inpatient admissions, {int(num_emergency)} ED visits in prior 12 months).'
        })
        
    stay_days = float(patient_dict.get('time_in_hospital', 0))
    if stay_days >= 6:
        interventions.append({
            'Category': 'Functional Recovery',
            'Recommendation': 'Home Health Assessment & Physical Therapy Evaluation',
            'Rationale': f'Extended hospital stay ({int(stay_days)} days) increases functional deconditioning risk.'
        })
        
    a1c_val = str(patient_dict.get('A1Cresult', 'Missing'))
    if a1c_val in ['>8', '>7']:
        interventions.append({
            'Category': 'Endocrine Optimization',
            'Recommendation': 'Outpatient Certified Diabetes Care and Education Specialist (CDCES) Referral',
            'Rationale': f'Elevated glycated hemoglobin ({a1c_val}) indicates suboptimal glycemic control.'
        })
        
    return interventions

def compute_and_save_explainability_artifacts():
    print("[*] Generating explainability artifacts (Odds Ratios & Feature Importances)...")
    data_path = os.path.join(PROCESSED_DIR, "train_val_test_data.joblib")
    models_path = os.path.join(MODELS_DIR, "evaluation_artifacts.joblib")
    
    split_data = joblib.load(data_path)
    eval_artifacts = joblib.load(models_path)
    
    transformed_cols = split_data['transformed_feature_names']
    trained_models = eval_artifacts['trained_models']
    
    # 1. Logistic Regression Coefficients & Odds Ratios
    lr_calibrated = trained_models['Logistic Regression']
    lr_base = lr_calibrated.base_model
    lr_coefs = lr_base.coef_[0]
    lr_odds_ratios = np.exp(lr_coefs)
    
    lr_records = []
    for col, coef, odds in zip(transformed_cols, lr_coefs, lr_odds_ratios):
        lr_records.append({
            'raw_feature': col,
            'display_name': clean_feature_name(col),
            'coefficient': round(float(coef), 4),
            'odds_ratio': round(float(odds), 4),
            'direction': 'Increases Risk' if coef > 0 else 'Decreases Risk'
        })
    lr_records.sort(key=lambda r: abs(r['coefficient']), reverse=True)
    
    # 2. Ensemble & Tree Feature Importances
    ensemble = trained_models['Calibrated Ensemble']
    ens_fi = ensemble.feature_importances_
    
    rf_base = trained_models['Random Forest'].base_model
    rf_fi = rf_base.feature_importances_
    
    xgb_base = trained_models['XGBoost'].base_model
    xgb_fi = xgb_base.feature_importances_
    
    fi_records = []
    for idx, col in enumerate(transformed_cols):
        fi_records.append({
            'raw_feature': col,
            'display_name': clean_feature_name(col),
            'ensemble_importance': round(float(ens_fi[idx]), 4) if ens_fi is not None else 0.0,
            'rf_importance': round(float(rf_fi[idx]), 4) if rf_fi is not None else 0.0,
            'xgb_importance': round(float(xgb_fi[idx]), 4) if xgb_fi is not None else 0.0
        })
    fi_records.sort(key=lambda r: r['ensemble_importance'], reverse=True)
    
    explainability_payload = {
        'logistic_regression_odds_ratios': lr_records,
        'tree_feature_importances': fi_records,
        'top_ensemble_drivers': [r['display_name'] for r in fi_records[:10]]
    }
    
    out_path = os.path.join(MODELS_DIR, "explainability_feature_importance.json")
    with open(out_path, "w") as f:
        json.dump(explainability_payload, f, indent=4)
    print(f"[+] Saved Explainability JSON to {out_path}")
    
    return explainability_payload

def get_clinical_risk_tier(prob, optimal_thresh=0.120):
    """
    Categorizes calibrated readmission risk into actionable clinical tiers
    using the unified optimal threshold (0.120 / 12.0%).
    """
    if prob >= optimal_thresh:
        return "High Risk", "red", "URGENT INTERVENTION REQUIRED. High 30-day readmission risk! Trigger multidisciplinary discharge care plan, 48-hr telehealth check-in, and pharmacy reconciliation."
    elif prob >= 0.080:
        return "Moderate Risk", "orange", "Enhanced discharge planning recommended. Schedule primary care follow-up within 7-10 days, verify prescription access."
    else:
        return "Low Risk", "green", "Standard discharge planning protocol. Patient demonstrates stable recuperation indicators."

def get_top_drivers_for_encounter(patient_dict, preprocessor, model, top_n=5):
    """
    Computes per-encounter top risk drivers based on feature contributions.
    """
    df_single = pd.DataFrame([patient_dict])
    X_trans = preprocessor.transform(df_single)
    prob = float(model.predict_proba(X_trans)[0, 1])
    
    # Use ensemble feature importances weighted by presence/magnitude
    ens_fi = model.feature_importances_
    contributions = []
    
    raw_vals = X_trans[0]
    for idx, (val, imp) in enumerate(zip(raw_vals, ens_fi)):
        if abs(val) > 0.01:
            contributions.append((idx, float(val * imp)))
            
    contributions.sort(key=lambda x: abs(x[1]), reverse=True)
    
    cat_encoder = preprocessor.named_transformers_['cat'].named_steps['encoder']
    numeric_features = ['number_inpatient', 'number_outpatient', 'number_emergency', 'time_in_hospital', 'num_lab_procedures', 'num_medications']
    categorical_features = ['diag_1_group', 'discharge_destination', 'insulin_regimen', 'medication_change', 'age_group', 'gender_clean', 'race_clean']
    one_hot_cols = list(cat_encoder.get_feature_names_out(categorical_features))
    transformed_feature_names = numeric_features + one_hot_cols
    
    top_drivers = []
    for idx, score in contributions[:top_n]:
        col_name = transformed_feature_names[idx]
        display_name = clean_feature_name(col_name)
        direction = "Increases Risk" if score > 0 else "Lowers Risk"
        top_drivers.append({
            'feature': col_name,
            'label': display_name,
            'direction': direction,
            'impact_score': round(abs(score), 4)
        })
        
    return prob, top_drivers

def precompute_worklist_artifacts(max_encounters=500):
    """
    Precomputes predictions and top drivers for an indexed sample of 500 encounters
    from the held-out test cohort to power the interactive worklist.
    """
    print(f"[*] Precomputing active clinical worklist for {max_encounters} held-out encounters...")
    data_path = os.path.join(PROCESSED_DIR, "train_val_test_data.joblib")
    preproc_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    models_path = os.path.join(MODELS_DIR, "evaluation_artifacts.joblib")
    
    split_data = joblib.load(data_path)
    preprocessor = joblib.load(preproc_path)
    eval_artifacts = joblib.load(models_path)
    
    df_test = split_data['df_test'].head(max_encounters).copy().reset_index(drop=True)
    X_test_raw = split_data['X_test_raw'].head(max_encounters).copy().reset_index(drop=True)
    model = eval_artifacts['trained_models']['Calibrated Ensemble']
    unified_thresh = eval_artifacts['unified_threshold']
    
    X_test_trans = preprocessor.transform(X_test_raw)
    probs = model.predict_proba(X_test_trans)[:, 1]
    
    records = []
    for idx, row in df_test.iterrows():
        p = float(probs[idx])
        tier, color, guidance = get_clinical_risk_tier(p, optimal_thresh=unified_thresh)
        
        # Extract patient attributes
        p_dict = X_test_raw.iloc[idx].to_dict()
        _, drivers = get_top_drivers_for_encounter(p_dict, preprocessor, model, top_n=3)
        
        stay_val = int(row.get('time_in_hospital', 3))
        num_meds = int(row.get('num_medications', 10))
        inpatient_val = int(row.get('number_inpatient', 0))
        er_val = int(row.get('number_emergency', 0))
        a1c_raw = str(row.get('A1Cresult', 'Missing'))
        if a1c_raw in ['nan', 'None', '?', '']:
            a1c_raw = 'Missing'
            
        resources = []
        if num_meds >= 10:
            resources.append("Pharmacist Recon")
        if a1c_raw in ['>8', '>7']:
            resources.append("CDCES Referral")
        if stay_val >= 6:
            resources.append("Home Health Nurse")
        if p >= unified_thresh:
            resources.append("48h Telehealth")
        if inpatient_val > 0:
            resources.append("Care Coordinator")
        if not resources:
            resources.append("Routine Outpatient")
            
        top_factors = [d['label'] for d in drivers]
        enc_id_num = int(row.get('encounter_id', idx + 100000))
        patient_nbr_num = int(row.get('patient_nbr', idx + 500000))
        
        p_dict['A1Cresult'] = a1c_raw
        p_dict['diag_1_cat'] = str(row.get('diag_1_group', 'Circulatory'))
        p_dict['stay'] = stay_val
        p_dict['meds'] = num_meds
        p_dict['inpatient'] = inpatient_val
        p_dict['er'] = er_val

        rec = {
            'idx': idx,
            'enc_id': f"ENC-{enc_id_num}",
            'encounter_id': enc_id_num,
            'patient_nbr': patient_nbr_num,
            'row_dict': p_dict,
            'age': str(row.get('age', '[60-70)')),
            'age_group': str(row.get('age_group', '60+ Years')),
            'gender': str(row.get('gender_clean', 'Female')),
            'race': str(row.get('race_clean', 'Caucasian')),
            'stay': stay_val,
            'meds': num_meds,
            'inpatient': inpatient_val,
            'er': er_val,
            'a1c': a1c_raw,
            'diag': str(row.get('diag_1_group', 'Circulatory')),
            'prob': round(p, 4),
            'probability_pct': round(p * 100, 1),
            'tier': tier,
            'tier_color': color,
            'guidance': guidance,
            'resources': resources,
            'top_factors': top_factors,
            'top_drivers': drivers,
            'actual': int(row['target']),
            'actual_readmitted': int(row['target']),
            'primary_diagnosis': str(row.get('diag_1_group', 'Circulatory')),
            'discharge_destination': str(row.get('discharge_destination', 'Home')),
            'time_in_hospital': stay_val,
            'number_inpatient': inpatient_val,
            'number_emergency': er_val,
            'number_outpatient': int(row.get('number_outpatient', 0)),
            'num_medications': num_meds,
            'num_lab_procedures': int(row.get('num_lab_procedures', 40)),
            'insulin': str(row.get('insulin_regimen', 'No')),
            'med_change': str(row.get('medication_change', 'No')),
        }
        records.append(rec)
        
    out_df = pd.DataFrame(records)
    worklist_path = os.path.join(PROCESSED_DIR, "worklist_precomputed.joblib")
    joblib.dump(out_df, worklist_path, compress=3)
    print(f"[+] Saved precomputed worklist of {len(out_df)} encounters to {worklist_path}")
    return out_df

if __name__ == "__main__":
    compute_and_save_explainability_artifacts()
    precompute_worklist_artifacts(max_encounters=500)
