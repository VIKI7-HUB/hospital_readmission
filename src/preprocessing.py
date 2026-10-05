import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

# Define paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

MEDICATION_COLS = [
    'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 'glimepiride',
    'acetohexamide', 'glipizide', 'gliquidone', 'glimepiride-pioglitazone',
    'metformin-rosiglitazone', 'metformin-pioglitazone', 'glyburide', 'tolbutamide',
    'pioglitazone', 'rosiglitazone', 'acarbose', 'miglitol', 'troglitazone',
    'tolazamide', 'examide', 'citogliptin', 'insulin', 'glyburide-metformin'
]

def map_icd9_to_category(code):
    """
    Maps high-cardinality ICD-9 diagnosis codes into 9 standardized clinical disease categories.
    Clinical Rationale: Reduces >700 distinct diagnostic codes to primary organ system etiologies,
    preventing one-hot dimensionality explosion while preserving clinical pathophysiological signals.
    """
    if pd.isna(code) or code == '?':
        return 'Missing'
    
    code_str = str(code).strip()
    
    # Handle supplementary ICD-9 V and E codes (factors influencing health status / external causes)
    if code_str.startswith('V') or code_str.startswith('E'):
        return 'Other/External'
    
    try:
        val = float(code_str)
    except ValueError:
        return 'Other'
    
    if (390 <= val <= 459) or val == 785:
        return 'Circulatory'
    elif (460 <= val <= 519) or val == 786:
        return 'Respiratory'
    elif (520 <= val <= 579) or val == 787:
        return 'Digestive'
    elif np.floor(val) == 250:
        return 'Diabetes'
    elif (800 <= val <= 999):
        return 'Injury'
    elif (710 <= val <= 739):
        return 'Musculoskeletal'
    elif (580 <= val <= 629) or val == 788:
        return 'Genitourinary'
    elif (140 <= val <= 239):
        return 'Neoplasms'
    else:
        return 'Other'

def group_age(age_str):
    """
    Harmonizes granular 10-year age brackets into clinical and demographic disparity cohorts:
    '<30 Years' (pediatric / young adult), '30-60 Years' (working age), '60+ Years' (geriatric / Medicare eligible).
    Clinical Rationale: Readmission risk dynamics and polypharmacy vulnerability diverge sharply at age 60+.
    """
    if pd.isna(age_str) or age_str == '?':
        return 'Unknown'
    if age_str in ['[0-10)', '[10-20)', '[20-30)']:
        return '<30 Years'
    elif age_str in ['[30-40)', '[40-50)', '[50-60)']:
        return '30-60 Years'
    else:
        return '60+ Years'

def generate_data_quality_summary(df_raw, df_clean, missing_stats, winsor_stats, num_cols, cat_cols):
    """
    Generates a structured, machine-readable summary of data quality metrics, missing value handling,
    outlier mitigation, and feature allocations for clinical governance auditing (KPI 5).
    """
    summary = {
        'total_raw_encounters': int(len(df_raw)),
        'total_clean_encounters': int(len(df_clean)),
        'target_distribution': {
            'negative_count (no readmit or >30d)': int((df_clean['target'] == 0).sum()),
            'positive_count (early readmit <30d)': int((df_clean['target'] == 1).sum()),
            'prevalence_percentage': float(df_clean['target'].mean() * 100)
        },
        'missing_value_audit': missing_stats,
        'outlier_winsorization_caps': winsor_stats,
        'feature_engineering': {
            'numerical_features': num_cols,
            'categorical_features': cat_cols,
            'total_feature_count': len(num_cols) + len(cat_cols)
        },
        'excluded_features_rationale': {
            'encounter_id': 'Administrative encounter identifier; prevents memorization',
            'patient_nbr': 'Unique patient identifier; prevents data leakage',
            'weight': 'Dropped due to 96.86% missingness across clinical encounters',
            'readmitted': 'Original multi-class string; converted into binary target readmitted_30d',
            'examide': 'Zero variance (all records constant "No")',
            'citogliptin': 'Zero variance (all records constant "No")'
        }
    }
    
    summary_path = os.path.join(PROCESSED_DIR, "data_quality_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=4)
    print(f"[+] Saved comprehensive Data Quality Summary to {summary_path}")
    return summary

def clean_and_preprocess_data(raw_csv_path, target_col='readmitted_30d'):
    """
    Full clinical data cleaning, feature engineering, missing value handling,
    outlier capping, and train/test splitting with documented rationale.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"[*] Reading raw data from {raw_csv_path}...")
    df_raw = pd.read_csv(raw_csv_path)
    print(f"[*] Raw dataset shape: {df_raw.shape}")
    
    # Audit raw missing values (represented as '?' or NaN)
    raw_missing_counts = ((df_raw == '?') | (df_raw.isna())).sum()
    raw_missing_pcts = (raw_missing_counts / len(df_raw)) * 100
    missing_stats = {}
    for col in df_raw.columns:
        if raw_missing_counts[col] > 0:
            missing_stats[col] = {
                'missing_count': int(raw_missing_counts[col]),
                'missing_percentage': round(float(raw_missing_pcts[col]), 2),
                'action_taken': 'Dropped' if col == 'weight' else ('Imputed as explicit category' if col in ['medical_specialty', 'payer_code', 'race'] else 'Mapped to category/imputed')
            }
            
    df = df_raw.copy()
    # Replace '?' with NaN
    df = df.replace('?', np.nan)
    
    # 1. Target Variable Engineering
    # Clinical standard: early readmission (<30 days) is the key risk target under value-based care
    if target_col == 'readmitted_30d':
        df['target'] = (df['readmitted'] == '<30').astype(int)
    else:
        df['target'] = (df['readmitted'] != 'NO').astype(int)
        
    print(f"[+] Target variable ('{target_col}') distribution:\n{df['target'].value_counts(normalize=True)}")
    
    # 2. Demographic Feature Preparation (Age, Gender, Race)
    df['age_group'] = df['age'].apply(group_age)
    df['race_clean'] = df['race'].fillna('Other/Missing')
    df['gender_clean'] = df['gender'].apply(lambda x: x if x in ['Male', 'Female'] else 'Other/Unknown')
    
    # 3. Feature Engineering with Clinical Rationale
    df['number_outpatient'] = pd.to_numeric(df['number_outpatient'], errors='coerce').fillna(0)
    df['number_emergency'] = pd.to_numeric(df['number_emergency'], errors='coerce').fillna(0)
    df['number_inpatient'] = pd.to_numeric(df['number_inpatient'], errors='coerce').fillna(0)
    
    # Composite health frailty index
    df['total_visits'] = df['number_outpatient'] + df['number_emergency'] + df['number_inpatient']
    df['high_prior_utilization'] = ((df['number_inpatient'] > 0) | (df['number_emergency'] > 0)).astype(int)
    
    # Inpatient treatment intensity
    df['time_in_hospital'] = pd.to_numeric(df['time_in_hospital'], errors='coerce').fillna(1)
    df['num_lab_procedures'] = pd.to_numeric(df['num_lab_procedures'], errors='coerce').fillna(0)
    df['num_procedures'] = pd.to_numeric(df['num_procedures'], errors='coerce').fillna(0)
    df['num_medications'] = pd.to_numeric(df['num_medications'], errors='coerce').fillna(0)
    df['number_diagnoses'] = pd.to_numeric(df['number_diagnoses'], errors='coerce').fillna(0)
    
    df['lab_intensity_per_day'] = df['num_lab_procedures'] / (df['time_in_hospital'] + 0.1)
    # Clinical geriatrics threshold for polypharmacy
    df['polypharmacy'] = (df['num_medications'] >= 10).astype(int)
    
    # Medication changes and active meds counts
    med_cols_present = [col for col in MEDICATION_COLS if col in df.columns]
    
    def count_med_changes(row):
        changes = 0
        for col in med_cols_present:
            val = str(row[col])
            if val in ['Up', 'Down']:
                changes += 1
        return changes

    def count_active_meds(row):
        active = 0
        for col in med_cols_present:
            val = str(row[col])
            if val in ['Steady', 'Up', 'Down']:
                active += 1
        return active

    df['num_med_changes'] = df.apply(count_med_changes, axis=1)
    df['num_active_meds'] = df.apply(count_active_meds, axis=1)
    
    # ICD-9 Clinical Category Mapping
    df['diag_1_cat'] = df['diag_1'].apply(map_icd9_to_category)
    df['diag_2_cat'] = df['diag_2'].apply(map_icd9_to_category)
    df['diag_3_cat'] = df['diag_3'].apply(map_icd9_to_category)
    
    # 4. Outlier Capping (Winsorization at 99th percentile for extreme visit counts)
    winsor_stats = {}
    for col in ['number_outpatient', 'number_emergency', 'number_inpatient', 'total_visits']:
        pre_max = float(df[col].max())
        q99 = float(df[col].quantile(0.99))
        df[col] = np.minimum(df[col], q99)
        winsor_stats[col] = {
            'raw_max': pre_max,
            '99th_percentile_cap': q99,
            'post_cap_max': float(df[col].max())
        }
        
    # 5. Drop Uninformative / Leakage / Constant Columns with documented rationale
    cols_to_drop = [
        'encounter_id', 'patient_nbr', 'weight', 'readmitted',
        'examide', 'citogliptin'
    ]
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    
    # Save cleaned dataset with demographics intact for fairness evaluation
    clean_csv_path = os.path.join(PROCESSED_DIR, "clean_diabetic_data.csv")
    df_clean.to_csv(clean_csv_path, index=False)
    print(f"[+] Cleaned dataset saved to {clean_csv_path}")
    
    # 6. Define Feature Groups for Pipeline
    numerical_features = [
        'time_in_hospital', 'num_lab_procedures', 'num_procedures',
        'num_medications', 'number_outpatient', 'number_emergency',
        'number_inpatient', 'number_diagnoses', 'total_visits',
        'lab_intensity_per_day', 'num_med_changes', 'num_active_meds'
    ]
    
    categorical_features = [
        'race_clean', 'gender_clean', 'age', 'admission_type_id',
        'discharge_disposition_id', 'admission_source_id',
        'payer_code', 'medical_specialty', 'diag_1_cat', 'diag_2_cat',
        'diag_3_cat', 'max_glu_serum', 'A1Cresult', 'change', 'diabetesMed'
    ]
    for med in med_cols_present:
        if med not in ['examide', 'citogliptin'] and df_clean[med].nunique() > 1:
            categorical_features.append(med)
            
    # Ensure missing values in categoricals are explicitly handled as 'Missing'
    for c in categorical_features:
        df_clean[c] = df_clean[c].fillna('Missing').astype(str)
        
    # Generate data quality summary JSON artifact
    generate_data_quality_summary(df_raw, df_clean, missing_stats, winsor_stats, numerical_features, categorical_features)
    
    # Extract features, target, and demographic sensitive attributes
    X = df_clean[numerical_features + categorical_features]
    y = df_clean['target']
    sensitive_attrs = df_clean[['age_group', 'gender_clean', 'race_clean']]
    
    # Train / Test Split (80% train, 20% test stratified)
    X_train, X_test, y_train, y_test, sens_train, sens_test = train_test_split(
        X, y, sensitive_attrs, test_size=0.20, random_state=42, stratify=y
    )
    
    # Build Preprocessing Pipeline (Median Imputation + Standard Scaling, Constant Imputation + One-Hot Encoding)
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_pipeline, numerical_features),
            ('cat', cat_pipeline, categorical_features)
        ]
    )
    
    print("[*] Fitting preprocessing pipeline on training set...")
    preprocessor.fit(X_train)
    
    # Save Preprocessor pipeline artifact
    joblib.dump(preprocessor, os.path.join(PROCESSED_DIR, "preprocessor.joblib"))
    
    # Save splits
    joblib.dump({
        'X_train': X_train, 'X_test': X_test,
        'y_train': y_train, 'y_test': y_test,
        'sens_train': sens_train, 'sens_test': sens_test,
        'num_cols': numerical_features,
        'cat_cols': categorical_features
    }, os.path.join(PROCESSED_DIR, "train_test_data.joblib"))
    
    print("[+] Data preprocessing complete. Pipeline saved successfully!")
    return clean_csv_path

if __name__ == "__main__":
    raw_path = os.path.join(DATA_DIR, "raw", "diabetic_data.csv")
    if os.path.exists(raw_path):
        clean_and_preprocess_data(raw_path)
    else:
        from src.download_data import download_and_extract_data
        raw_path = download_and_extract_data()
        clean_and_preprocess_data(raw_path)
