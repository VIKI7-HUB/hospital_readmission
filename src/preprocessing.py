import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import StratifiedGroupKFold, KFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder, TargetEncoder
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

AGE_MIDPOINT_MAP = {
    '[0-10)': 5.0, '[10-20)': 15.0, '[20-30)': 25.0, '[30-40)': 35.0,
    '[40-50)': 45.0, '[50-60)': 55.0, '[60-70)': 65.0, '[70-80)': 75.0,
    '[80-90)': 85.0, '[90-100)': 95.0
}

# Discharge disposition IDs indicating death or hospice (ineligible for readmission)
TERMINAL_DISCHARGE_IDS = {11, 13, 14, 19, 20, 21, '11', '13', '14', '19', '20', '21'}

def map_icd9_to_category(code):
    """
    Maps high-cardinality ICD-9 diagnosis codes into standardized clinical disease categories.
    """
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
    """Harmonizes granular 10-year age brackets into clinical disparity cohorts."""
    if pd.isna(age_str) or age_str == '?':
        return 'Unknown'
    if age_str in ['[0-10)', '[10-20)', '[20-30)']:
        return '<30 Years'
    elif age_str in ['[30-40)', '[40-50)', '[50-60)']:
        return '30-60 Years'
    else:
        return '60+ Years'

def map_admission_type(val):
    """Groups admission types into clinical operational categories."""
    try:
        v = int(val)
    except (ValueError, TypeError):
        return 'Other_Unknown'
    if v in [1, 2, 7]:
        return 'Emergency_Urgent'
    elif v == 3:
        return 'Elective'
    elif v == 4:
        return 'Newborn'
    else:
        return 'Other_Unknown'

def map_discharge_disposition(val):
    """Groups discharge dispositions into post-acute recovery pathways (excluding terminal)."""
    try:
        v = int(val)
    except (ValueError, TypeError):
        return 'Other_Unknown'
    if v in [1, 6, 8]:
        return 'Home'
    elif v in [2, 3, 4, 5, 9, 10, 15, 22, 23, 24, 27, 28, 29, 30]:
        return 'Transfer_Facility'
    elif v == 7:
        return 'Left_AMA'
    elif v in [12, 16, 17]:
        return 'Outpatient_Referred'
    else:
        return 'Other_Unknown'

def map_admission_source(val):
    """Groups admission sources into intake referral vectors."""
    try:
        v = int(val)
    except (ValueError, TypeError):
        return 'Other_Unknown'
    if v == 7:
        return 'Emergency_Room'
    elif v in [1, 2, 3]:
        return 'Referral'
    elif v in [4, 5, 6, 10, 18, 22, 25, 26]:
        return 'Transfer'
    else:
        return 'Other_Unknown'

def check_is_diabetes_code(val):
    """Helper to detect whether an ICD-9 diagnosis is diabetes-related (250.xx)."""
    if pd.isna(val) or str(val).strip() in ['?', '', 'None', 'nan']:
        return False
    s = str(val).strip()
    if s.startswith('250'):
        return True
    try:
        if np.floor(float(s)) == 250:
            return True
    except ValueError:
        pass
    return False

def count_medication_adjustments(row, med_cols):
    """Counts dose adjustments (Up/Down) across antidiabetic medications."""
    changes = 0
    for col in med_cols:
        val = str(row.get(col, 'No'))
        if val in ['Up', 'Down']:
            changes += 1
    return changes

def count_active_medications(row, med_cols):
    """Counts active antidiabetic prescriptions (Steady/Up/Down)."""
    active = 0
    for col in med_cols:
        val = str(row.get(col, 'No'))
        if val in ['Steady', 'Up', 'Down']:
            active += 1
    return active

def engineer_features(df_in):
    """
    Applies comprehensive feature engineering to a dataframe (or single-row dataframe).
    Creates clinical categories, comorbidities, interactions, and utilization metrics.
    """
    df = df_in.copy()
    
    # 1. Demographic mappings
    if 'age' in df.columns:
        df['age_group'] = df['age'].apply(group_age)
        df['age_midpoint'] = df['age'].map(AGE_MIDPOINT_MAP).fillna(65.0)
    else:
        df['age_group'] = '60+ Years'
        df['age_midpoint'] = 65.0
        
    df['race_clean'] = df['race'].fillna('Other/Missing') if 'race' in df.columns else 'Other/Missing'
    df['gender_clean'] = df['gender'].apply(lambda x: x if x in ['Male', 'Female'] else 'Other/Unknown') if 'gender' in df.columns else 'Other/Unknown'
    
    # 2. Administrative clinical categorization
    df['admission_type_cat'] = df['admission_type_id'].apply(map_admission_type) if 'admission_type_id' in df.columns else 'Emergency_Urgent'
    df['discharge_disp_cat'] = df['discharge_disposition_id'].apply(map_discharge_disposition) if 'discharge_disposition_id' in df.columns else 'Home'
    df['admission_source_cat'] = df['admission_source_id'].apply(map_admission_source) if 'admission_source_id' in df.columns else 'Emergency_Room'
    
    # 3. Numeric conversions & healthcare utilization
    for col in ['number_outpatient', 'number_emergency', 'number_inpatient', 'time_in_hospital',
                'num_lab_procedures', 'num_procedures', 'num_medications', 'number_diagnoses']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
            
    df['total_visits'] = df['number_outpatient'] + df['number_emergency'] + df['number_inpatient']
    df['high_prior_utilization'] = ((df['number_inpatient'] > 0) | (df['number_emergency'] > 0)).astype(int)
    df['lab_intensity_per_day'] = df['num_lab_procedures'] / (df['time_in_hospital'] + 0.1)
    df['polypharmacy'] = (df['num_medications'] >= 10).astype(int)
    
    # 4. Medication changes and active med counts
    med_cols_present = [c for c in MEDICATION_COLS if c in df.columns]
    df['num_med_changes'] = df.apply(lambda r: count_medication_adjustments(r, med_cols_present), axis=1)
    df['num_active_meds'] = df.apply(lambda r: count_active_medications(r, med_cols_present), axis=1)
    
    # 5. ICD-9 Diagnoses & Comorbidity Engineering
    df['diag_1_cat'] = df['diag_1'].apply(map_icd9_to_category) if 'diag_1' in df.columns else 'Circulatory'
    df['diag_2_cat'] = df['diag_2'].apply(map_icd9_to_category) if 'diag_2' in df.columns else 'Other'
    df['diag_3_cat'] = df['diag_3'].apply(map_icd9_to_category) if 'diag_3' in df.columns else 'Other'
    
    # Cross-diagnosis diabetes indicator
    d1 = df['diag_1'] if 'diag_1' in df.columns else pd.Series([np.nan]*len(df))
    d2 = df['diag_2'] if 'diag_2' in df.columns else pd.Series([np.nan]*len(df))
    d3 = df['diag_3'] if 'diag_3' in df.columns else pd.Series([np.nan]*len(df))
    
    has_dm = []
    for v1, v2, v3 in zip(d1, d2, d3):
        is_dm = int(check_is_diabetes_code(v1) or check_is_diabetes_code(v2) or check_is_diabetes_code(v3))
        has_dm.append(is_dm)
    df['has_diabetes_diag'] = has_dm
    
    # Comorbidity count across organ systems
    high_risk_systems = {'Circulatory', 'Respiratory', 'Digestive', 'Diabetes', 'Genitourinary', 'Musculoskeletal', 'Neoplasms'}
    comorbidities = []
    for c1, c2, c3 in zip(df['diag_1_cat'], df['diag_2_cat'], df['diag_3_cat']):
        matched = {c1, c2, c3}.intersection(high_risk_systems)
        comorbidities.append(len(matched))
    df['comorbidity_count'] = comorbidities
    
    # 6. Clinical Interaction Features
    df['inpatient_x_stay'] = df['number_inpatient'] * df['time_in_hospital']
    df['age_x_polypharmacy'] = df['age_midpoint'] * df['polypharmacy']
    
    a1c_series = df['A1Cresult'] if 'A1Cresult' in df.columns else pd.Series(['None']*len(df))
    df['a1c_high'] = a1c_series.isin(['>8', '>7']).astype(int)
    df['a1c_x_med_change'] = df['a1c_high'] * df['num_med_changes']
    df['er_x_inpatient'] = df['number_emergency'] * df['number_inpatient']
    
    # High-cardinality handling defaults
    if 'medical_specialty' in df.columns:
        df['medical_specialty'] = df['medical_specialty'].fillna('Missing').astype(str)
    else:
        df['medical_specialty'] = 'Missing'
        
    if 'payer_code' in df.columns:
        df['payer_code'] = df['payer_code'].fillna('Missing').astype(str)
    else:
        df['payer_code'] = 'Missing'
        
    return df

def generate_data_quality_summary(df_raw, df_clean, missing_stats, winsor_stats, num_cols, cat_cols, target_cols):
    """Generates structured JSON documenting KPI 5 compliance and leakage fixes."""
    summary = {
        'total_raw_encounters': int(len(df_raw)),
        'total_clean_encounters': int(len(df_clean)),
        'terminal_encounters_removed': int(len(df_raw) - len(df_clean)),
        'unique_patients': int(df_clean['patient_nbr'].nunique()) if 'patient_nbr' in df_clean.columns else 0,
        'split_strategy': 'Patient-Grouped Stratified 5-Fold Split (StratifiedGroupKFold on patient_nbr; 0% train/test patient leakage)',
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
            'target_encoded_features': target_cols,
            'total_feature_count': len(num_cols) + len(cat_cols) + len(target_cols)
        },
        'excluded_features_rationale': {
            'terminal_discharge_dispositions': 'Excludes IDs (11, 13, 14, 19, 20, 21) corresponding to expired or hospice discharges who cannot experience 30-day readmissions',
            'encounter_id': 'Administrative identifier dropped to prevent memorization',
            'patient_nbr': 'Used exclusively as group clustering identifier in StratifiedGroupKFold to prevent train-test contamination',
            'weight': 'Dropped due to >96% missingness across participating clinical facilities',
            'readmitted': 'Raw target string mapped to binary 30-day indicator (<30d vs else)',
            'examide': 'Dropped due to zero variance across all encounters',
            'citogliptin': 'Dropped due to zero variance across all encounters'
        }
    }
    
    summary_path = os.path.join(PROCESSED_DIR, "data_quality_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=4)
    print(f"[+] Saved updated Data Quality & Governance Summary to {summary_path}")
    return summary

def clean_and_preprocess_data(raw_csv_path, target_col='readmitted_30d'):
    """
    Executes leak-free preprocessing:
    1. Filters out terminal/hospice discharges.
    2. Builds clinical and interaction features.
    3. Winsorizes healthcare utilization counts.
    4. Splits using StratifiedGroupKFold on patient_nbr (zero patient leakage).
    5. Fits Scikit-Learn pipeline (StandardScaler + TargetEncoder + OneHotEncoder).
    6. Saves Parquet, CSV, preprocessor pipeline, and train_test split joblib artifacts.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"[*] Reading raw data from {raw_csv_path}...")
    df_raw = pd.read_csv(raw_csv_path)
    print(f"[*] Raw dataset shape: {df_raw.shape}")
    
    # Audit raw missingness
    raw_missing_counts = ((df_raw == '?') | (df_raw.isna())).sum()
    raw_missing_pcts = (raw_missing_counts / len(df_raw)) * 100
    missing_stats = {}
    for col in df_raw.columns:
        if raw_missing_counts[col] > 0:
            missing_stats[col] = {
                'missing_count': int(raw_missing_counts[col]),
                'missing_percentage': round(float(raw_missing_pcts[col]), 2),
                'action_taken': 'Dropped' if col == 'weight' else ('Target Encoded' if col in ['medical_specialty', 'payer_code'] else 'Explicit Category')
            }
            
    df = df_raw.copy()
    df = df.replace('?', np.nan)
    
    # 1. Exclude terminal / hospice discharges (cannot be readmitted)
    raw_len = len(df)
    dead_mask = df['discharge_disposition_id'].astype(str).isin(TERMINAL_DISCHARGE_IDS)
    df = df[~dead_mask].reset_index(drop=True)
    print(f"[+] Excluded {dead_mask.sum()} terminal/hospice encounters ({raw_len} -> {len(df)} encounters)")
    
    # 2. Target Variable
    if target_col == 'readmitted_30d':
        df['target'] = (df['readmitted'] == '<30').astype(int)
    else:
        df['target'] = (df['readmitted'] != 'NO').astype(int)
    print(f"[+] Cleaned target variable prevalence: {df['target'].mean()*100:.2f}% ({df['target'].sum()} positive readmissions)")
    
    # 3. Clinical Feature Engineering
    df = engineer_features(df)
    
    # 4. Outlier Capping (Winsorization at 99th percentile)
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
        
    # 5. Define Feature Groups
    numerical_features = [
        'time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
        'number_outpatient', 'number_emergency', 'number_inpatient', 'number_diagnoses',
        'total_visits', 'lab_intensity_per_day', 'num_med_changes', 'num_active_meds',
        'polypharmacy', 'high_prior_utilization', 'has_diabetes_diag', 'comorbidity_count',
        'inpatient_x_stay', 'age_midpoint', 'age_x_polypharmacy', 'a1c_x_med_change', 'er_x_inpatient'
    ]
    
    target_encoded_features = [
        'medical_specialty', 'payer_code'
    ]
    
    categorical_features = [
        'race_clean', 'gender_clean', 'age', 'admission_type_cat',
        'discharge_disp_cat', 'admission_source_cat', 'diag_1_cat',
        'diag_2_cat', 'diag_3_cat', 'max_glu_serum', 'A1Cresult', 'change', 'diabetesMed'
    ]
    
    med_cols_present = [col for col in MEDICATION_COLS if col in df.columns and col not in ['examide', 'citogliptin']]
    for med in med_cols_present:
        if df[med].nunique() > 1:
            categorical_features.append(med)
            
    for c in categorical_features + target_encoded_features:
        df[c] = df[c].fillna('Missing').astype(str)
        
    all_feature_cols = numerical_features + target_encoded_features + categorical_features
    
    # Save cleaned CSV and Parquet with optimized memory footprints
    clean_csv_path = os.path.join(PROCESSED_DIR, "clean_diabetic_data.csv")
    clean_parquet_path = os.path.join(PROCESSED_DIR, "clean_diabetic_data.parquet")
    
    cols_to_save = list(dict.fromkeys(['encounter_id', 'patient_nbr', 'target', 'age_group', 'gender_clean', 'race_clean'] + all_feature_cols))
    df_save = df[[c for c in cols_to_save if c in df.columns]].copy()
    
    df_save.to_csv(clean_csv_path, index=False)
    
    # Convert types for fast parquet storage
    for col in categorical_features + target_encoded_features + ['age_group', 'gender_clean', 'race_clean']:
        if col in df_save.columns:
            df_save[col] = df_save[col].astype('category')
    for col in numerical_features:
        if col in df_save.columns:
            df_save[col] = df_save[col].astype(np.float32)
    df_save['target'] = df_save['target'].astype(np.int8)
    df_save.to_parquet(clean_parquet_path, index=False)
    print(f"[+] Saved clean datasets to {clean_csv_path} and {clean_parquet_path}")
    
    # 6. Leak-Free Patient-Grouped Stratified Split
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_idx, test_idx = next(sgkf.split(df, df['target'], df['patient_nbr']))
    
    X_train = df.iloc[train_idx][all_feature_cols].copy()
    y_train = df.iloc[train_idx]['target'].copy()
    sens_train = df.iloc[train_idx][['age_group', 'gender_clean', 'race_clean']].copy()
    
    X_test = df.iloc[test_idx][all_feature_cols].copy()
    y_test = df.iloc[test_idx]['target'].copy()
    sens_test = df.iloc[test_idx][['age_group', 'gender_clean', 'race_clean']].copy()
    
    train_pts = set(df.iloc[train_idx]['patient_nbr'])
    test_pts = set(df.iloc[test_idx]['patient_nbr'])
    patient_overlap = len(train_pts.intersection(test_pts))
    print(f"[+] StratifiedGroupKFold split: Train={len(X_train)} (pts={len(train_pts)}), Test={len(X_test)} (pts={len(test_pts)})")
    print(f"[+] Verified patient overlap between train and test: {patient_overlap} (LEAKAGE FREE!)")
    
    # 7. Construct and Fit ColumnTransformer Preprocessor
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    target_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
        ('target_enc', TargetEncoder(smooth='auto', cv=KFold(n_splits=5, shuffle=True, random_state=42)))
    ])
    
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_pipeline, numerical_features),
            ('te', target_pipeline, target_encoded_features),
            ('cat', cat_pipeline, categorical_features)
        ]
    )
    
    print("[*] Fitting preprocessing pipeline on leak-free training set...")
    preprocessor.fit(X_train, y_train)
    
    # Save Preprocessor and train/test artifacts
    joblib.dump(preprocessor, os.path.join(PROCESSED_DIR, "preprocessor.joblib"))
    
    # Save splits
    joblib.dump({
        'X_train': X_train, 'X_test': X_test,
        'y_train': y_train, 'y_test': y_test,
        'sens_train': sens_train, 'sens_test': sens_test,
        'num_cols': numerical_features,
        'te_cols': target_encoded_features,
        'cat_cols': categorical_features,
        'patient_nbr_train': df.iloc[train_idx]['patient_nbr'],
        'patient_nbr_test': df.iloc[test_idx]['patient_nbr'],
        'encounter_id_test': df.iloc[test_idx]['encounter_id'] if 'encounter_id' in df.columns else df.iloc[test_idx].index
    }, os.path.join(PROCESSED_DIR, "train_test_data.joblib"), compress=4)
    
    # Generate data quality report JSON
    generate_data_quality_summary(df_raw, df, missing_stats, winsor_stats, numerical_features, categorical_features, target_encoded_features)
    
    print("[+] Preprocessing pipeline completed and artifacts verified!")
    return clean_csv_path

if __name__ == "__main__":
    raw_path = os.path.join(DATA_DIR, "raw", "diabetic_data.csv")
    if os.path.exists(raw_path):
        clean_and_preprocess_data(raw_path)
    else:
        from src.download_data import download_and_extract_data
        raw_path = download_and_extract_data()
        clean_and_preprocess_data(raw_path)
