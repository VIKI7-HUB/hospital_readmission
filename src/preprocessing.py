import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Terminal discharge disposition IDs (death or hospice)
TERMINAL_DISCHARGE_IDS = {11, 13, 14, 19, 20, 21, '11', '13', '14', '19', '20', '21'}

# Grouping high-cardinality ICD-9 codes into standardized clinical disease categories
def map_icd9_to_category(code):
    if pd.isna(code) or str(code).strip() in ['?', '', 'None', 'nan']:
        return 'Missing'
    
    code_str = str(code).strip()
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
    if pd.isna(age_str) or str(age_str).strip() in ['?', '', 'None', 'nan']:
        return 'Unknown'
    if age_str in ['[0-10)', '[10-20)', '[20-30)']:
        return '<30 Years'
    elif age_str in ['[30-40)', '[40-50)', '[50-60)']:
        return '30-60 Years'
    else:
        return '60+ Years'

def map_discharge_disposition(val):
    try:
        v = int(val)
    except (ValueError, TypeError):
        return 'Other_Unknown'
    if v in [1, 6, 8]:
        return 'Home'
    elif v in [2, 3, 4, 5, 9, 10, 15, 22, 23, 24, 27, 28, 29, 30]:
        return 'Facility_Rehab'
    elif v == 7:
        return 'Left_AMA'
    else:
        return 'Other_Unknown'

def get_feature_exclusion_rationale():
    """Returns structured table of excluded features with explicit written rationales."""
    return [
        {
            "feature": "weight",
            "category": "Clinical Measurement",
            "missingness": "96.86%",
            "reason": "High missingness across almost all participating clinical centers (>96% missing); unreliable across sites."
        },
        {
            "feature": "payer_code",
            "category": "Administrative / Billing",
            "missingness": "39.56%",
            "reason": "Billing artifact without direct pathophysiological relationship to acute readmission risk; high missingness."
        },
        {
            "feature": "medical_specialty",
            "category": "Administrative / Provider",
            "missingness": "49.08%",
            "reason": "High missingness and high cardinality (73 categories) causing severe risk of overfitting on sparse specialties."
        },
        {
            "feature": "diag_2, diag_3",
            "category": "Secondary Diagnoses",
            "missingness": "0.35% - 1.40%",
            "reason": "Excluded to maintain strict clinical parsimony around the principal admitting diagnosis (diag_1) and avoid multicollinearity."
        },
        {
            "feature": "admission_type_id, admission_source_id",
            "category": "Intake Administrative Channels",
            "missingness": "0.00%",
            "reason": "Intake channel categories provide redundant signals already captured by prior utilization counts and primary diagnosis."
        },
        {
            "feature": "num_procedures",
            "category": "Inpatient Utilization",
            "missingness": "0.00%",
            "reason": "Excluded to maintain parsimony; inpatient intervention intensity is already represented by time_in_hospital and num_lab_procedures."
        },
        {
            "feature": "number_diagnoses",
            "category": "Clinical Count",
            "missingness": "0.00%",
            "reason": "Redundant comorbidity signal that tracks closely with primary diagnosis category and length of stay."
        },
        {
            "feature": "max_glu_serum, A1Cresult",
            "category": "Laboratory Testing",
            "missingness": "83.28% - 94.75%",
            "reason": "Extreme unmeasured rate (>83-94% not ordered); testing frequency varies by admitting specialty rather than acute 30-day recidivism."
        },
        {
            "feature": "diabetesMed",
            "category": "Medication Flag",
            "missingness": "0.00%",
            "reason": "Highly redundant with insulin regimen and the medication-change (change) indicator."
        },
        {
            "feature": "22 individual antidiabetic oral medications (metformin, glipizide, glyburide, pioglitazone, etc.)",
            "category": "Specific Pharmacology",
            "missingness": "0.00%",
            "reason": "Extreme sparsity across individual chemical agents (many <0.1% usage), zero variance for examide/citoglipton, and therapeutic volatility is already captured by insulin and change."
        },
        {
            "feature": "encounter_id",
            "category": "Identifier",
            "missingness": "0.00%",
            "reason": "Administrative surrogate key; dropped to prevent memorization and data leakage."
        },
        {
            "feature": "patient_nbr",
            "category": "Cluster Key",
            "missingness": "0.00%",
            "reason": "Used exclusively for leak-free patient-grouped train/val/test splitting; removed from model input space."
        },
        {
            "feature": "terminal_discharge_dispositions (IDs 11, 13, 14, 19, 20, 21)",
            "category": "Clinical Exclusions",
            "missingness": "0.00%",
            "reason": "Patients discharged to hospice or who expired in hospital cannot experience 30-day readmissions; excluded to prevent target contamination."
        }
    ]

def clean_and_prepare_dataset(raw_csv_path):
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"[*] Reading raw data from {raw_csv_path}...")
    df_raw = pd.read_csv(raw_csv_path)
    total_raw = len(df_raw)
    
    # 1. Target Definition: readmitted <30 days = 1, else 0
    df = df_raw.copy()
    df['target'] = (df['readmitted'] == '<30').astype(int)
    
    # 2. Exclude terminal / hospice discharges
    dead_mask = df['discharge_disposition_id'].astype(str).isin(TERMINAL_DISCHARGE_IDS)
    terminal_excluded = int(dead_mask.sum())
    df = df[~dead_mask].reset_index(drop=True)
    total_clean = len(df)
    print(f"[+] Excluded {terminal_excluded} terminal/hospice encounters ({total_raw} -> {total_clean} clean encounters)")
    
    # 3. Clean and map features
    # Primary Diagnosis
    df['diag_1_group'] = df['diag_1'].apply(map_icd9_to_category)
    
    # Discharge destination
    df['discharge_destination'] = df['discharge_disposition_id'].apply(map_discharge_disposition)
    
    # Demographics
    df['age_group'] = df['age'].apply(group_age)
    df['gender_clean'] = df['gender'].apply(lambda x: x if x in ['Male', 'Female'] else 'Other/Unknown')
    df['race_clean'] = df['race'].replace('?', 'Other/Unknown').fillna('Other/Unknown')
    
    # Medication flags
    df['insulin_regimen'] = df['insulin'].replace('?', 'No').fillna('No')
    df['medication_change'] = df['change'].replace('?', 'No').fillna('No')
    
    # Continuous utilization features with 99th percentile winsorization
    numeric_features = [
        'number_inpatient', 'number_outpatient', 'number_emergency',
        'time_in_hospital', 'num_lab_procedures', 'num_medications'
    ]
    winsor_stats = {}
    for col in numeric_features:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        raw_max = float(df[col].max())
        cap_val = float(df[col].quantile(0.99))
        df[col] = np.minimum(df[col], cap_val)
        winsor_stats[col] = {
            'raw_max': raw_max,
            'cap_99th': cap_val,
            'post_cap_max': float(df[col].max())
        }
        
    categorical_features = [
        'diag_1_group', 'discharge_destination', 'insulin_regimen',
        'medication_change', 'age_group', 'gender_clean', 'race_clean'
    ]
    
    for col in categorical_features:
        df[col] = df[col].astype(str)
        
    all_feature_cols = numeric_features + categorical_features
    print(f"[+] Total aligned feature set: {len(all_feature_cols)} features ({len(numeric_features)} numeric, {len(categorical_features)} categorical)")
    
    # 4. Leak-Free Patient-Grouped Stratified 70/10/20 Split
    print("[*] Performing leak-free patient-grouped stratified 70/10/20 split...")
    sgkf5 = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_val_idx, test_idx = next(sgkf5.split(df, df['target'], df['patient_nbr']))
    
    df_tv = df.iloc[train_val_idx].reset_index(drop=True)
    df_test = df.iloc[test_idx].reset_index(drop=True)
    
    sgkf8 = StratifiedGroupKFold(n_splits=8, shuffle=True, random_state=42)
    train_idx, val_idx = next(sgkf8.split(df_tv, df_tv['target'], df_tv['patient_nbr']))
    
    df_train = df_tv.iloc[train_idx].reset_index(drop=True)
    df_val = df_tv.iloc[val_idx].reset_index(drop=True)
    
    n_train = len(df_train)
    n_val = len(df_val)
    n_test = len(df_test)
    
    pts_train = set(df_train['patient_nbr'])
    pts_val = set(df_val['patient_nbr'])
    pts_test = set(df_test['patient_nbr'])
    
    overlap_tv = len(pts_train.intersection(pts_val))
    overlap_tt = len(pts_train.intersection(pts_test))
    overlap_vt = len(pts_val.intersection(pts_test))
    
    print(f"[+] Split sizes: Train={n_train} ({n_train/total_clean*100:.1f}%), Val={n_val} ({n_val/total_clean*100:.1f}%), Test={n_test} ({n_test/total_clean*100:.1f}%)")
    print(f"[+] Verified patient overlap: Train-Val={overlap_tv}, Train-Test={overlap_tt}, Val-Test={overlap_vt} (0% LEAKAGE)")
    
    # 5. Build and Fit Preprocessing Pipeline (FIT ON TRAIN ONLY)
    print("[*] Fitting preprocessing pipeline strictly on training split...")
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer([
        ('num', num_pipeline, numeric_features),
        ('cat', cat_pipeline, categorical_features)
    ])
    
    X_train_raw = df_train[all_feature_cols]
    y_train = df_train['target'].values
    
    X_val_raw = df_val[all_feature_cols]
    y_val = df_val['target'].values
    
    X_test_raw = df_test[all_feature_cols]
    y_test = df_test['target'].values
    
    preprocessor.fit(X_train_raw, y_train)
    
    # Extract transformed feature names
    cat_encoder = preprocessor.named_transformers_['cat'].named_steps['encoder']
    one_hot_cols = list(cat_encoder.get_feature_names_out(categorical_features))
    transformed_feature_names = numeric_features + one_hot_cols
    print(f"[+] Preprocessor fitted: {len(transformed_feature_names)} transformed feature columns after one-hot encoding.")
    
    # Save artifacts
    joblib.dump(preprocessor, os.path.join(PROCESSED_DIR, "preprocessor.joblib"))
    
    split_artifacts = {
        'df_train': df_train, 'df_val': df_val, 'df_test': df_test,
        'X_train_raw': X_train_raw, 'X_val_raw': X_val_raw, 'X_test_raw': X_test_raw,
        'y_train': y_train, 'y_val': y_val, 'y_test': y_test,
        'numeric_features': numeric_features,
        'categorical_features': categorical_features,
        'all_feature_cols': all_feature_cols,
        'transformed_feature_names': transformed_feature_names,
        'sens_train': df_train[['age_group', 'gender_clean', 'race_clean']],
        'sens_val': df_val[['age_group', 'gender_clean', 'race_clean']],
        'sens_test': df_test[['age_group', 'gender_clean', 'race_clean']],
        'patient_nbr_train': df_train['patient_nbr'],
        'patient_nbr_val': df_val['patient_nbr'],
        'patient_nbr_test': df_test['patient_nbr'],
        'encounter_id_test': df_test['encounter_id']
    }
    joblib.dump(split_artifacts, os.path.join(PROCESSED_DIR, "train_val_test_data.joblib"), compress=3)
    
    # Save feature exclusion table
    exclusion_table = get_feature_exclusion_rationale()
    with open(os.path.join(PROCESSED_DIR, "feature_selection_rationale.json"), "w") as f:
        json.dump(exclusion_table, f, indent=4)
        
    # Save data quality summary
    data_quality_summary = {
        "total_raw_encounters": total_raw,
        "terminal_encounters_excluded": terminal_excluded,
        "total_clean_encounters": total_clean,
        "unique_patients": int(df['patient_nbr'].nunique()),
        "target_distribution": {
            "negative_count": int((df['target'] == 0).sum()),
            "positive_count": int((df['target'] == 1).sum()),
            "prevalence_percentage": round(float(df['target'].mean() * 100), 2)
        },
        "split_strategy": "Patient-Grouped Stratified Split (70% Train, 10% Val, 20% Test; 0% leakage)",
        "split_sizes": {
            "train": {"encounters": n_train, "percentage": round(n_train / total_clean * 100, 2)},
            "val": {"encounters": n_val, "percentage": round(n_val / total_clean * 100, 2)},
            "test": {"encounters": n_test, "percentage": round(n_test / total_clean * 100, 2)}
        },
        "features_kept": all_feature_cols,
        "features_excluded_count": len(exclusion_table),
        "outlier_winsorization_caps": winsor_stats
    }
    with open(os.path.join(PROCESSED_DIR, "data_quality_summary.json"), "w") as f:
        json.dump(data_quality_summary, f, indent=4)
        
    print("[+] Preprocessing and split artifacts successfully saved!")
    return split_artifacts

if __name__ == "__main__":
    raw_path = os.path.join(DATA_DIR, "raw", "diabetic_data.csv")
    clean_and_prepare_dataset(raw_path)
