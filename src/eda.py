import json
import os

import nbformat as nbf
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(BASE_DIR, "data", "raw", "diabetic_data.csv")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")

TERMINAL_DISCHARGE_IDS = {11, 13, 14, 19, 20, 21, '11', '13', '14', '19', '20', '21'}

def run_eda_and_export_notebook():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(NOTEBOOKS_DIR, exist_ok=True)
    
    print("[*] Loading raw dataset for comprehensive EDA...")
    df_raw = pd.read_csv(DATA_RAW)
    
    # 1. Basic shape & schema
    raw_shape = list(df_raw.shape)
    
    # 2. Missing values per column ('?' and NaN)
    missing_counts = {}
    missing_pcts = {}
    for col in df_raw.columns:
        cnt = int(((df_raw[col] == '?') | (df_raw[col].isna())).sum())
        if cnt > 0:
            missing_counts[col] = cnt
            missing_pcts[col] = round(float(cnt / len(df_raw) * 100), 2)
            
    # 3. Target distribution in raw data (<30 vs >30 vs NO)
    raw_target_counts = {str(k): int(v) for k, v in df_raw['readmitted'].value_counts().items()}
    
    # Binary target choice documentation:
    # Under CMS HRRP (Hospital Readmissions Reduction Program), hospitals face financial penalties
    # exclusively for unscheduled readmissions occurring within 30 days of discharge (<30).
    # Encounters readmitted after 30 days (>30) or not readmitted (NO) do not trigger CMS penalties.
    target_binary_raw = (df_raw['readmitted'] == '<30').astype(int)
    class_balance_raw = {
        'negative_count_NO_or_gt30': int((target_binary_raw == 0).sum()),
        'positive_count_lt30': int((target_binary_raw == 1).sum()),
        'prevalence_pct': round(float(target_binary_raw.mean() * 100), 2)
    }
    
    # 4. Duplicate encounters per patient
    total_encounters = len(df_raw)
    unique_patients = int(df_raw['patient_nbr'].nunique())
    enc_per_patient = df_raw.groupby('patient_nbr')['encounter_id'].count()
    dup_stats = {
        'total_encounters': total_encounters,
        'unique_patients': unique_patients,
        'multiple_encounter_patients': int((enc_per_patient > 1).sum()),
        'max_encounters_single_patient': int(enc_per_patient.max()),
        'mean_encounters_per_patient': round(float(enc_per_patient.mean()), 2),
        'leakage_mitigation_strategy': (
            'Patient-Grouped Stratified Splitting (StratifiedGroupKFold on patient_nbr). '
            'All encounters belonging to any individual patient are strictly constrained to a single partition '
            '(Train, Validation, or Test) to ensure 0% patient leakage.'
        )
    }
    
    # 5. Terminal / Hospice Discharges
    dead_mask = df_raw['discharge_disposition_id'].astype(str).isin(TERMINAL_DISCHARGE_IDS)
    terminal_count = int(dead_mask.sum())
    
    # Filter clean dataset for distribution analysis
    df_clean = df_raw[~dead_mask].copy().reset_index(drop=True)
    df_clean['target'] = (df_clean['readmitted'] == '<30').astype(int)
    
    # 6. Readmission rate breakdowns by key features
    # Age
    age_rates = {}
    for grp, sub in df_clean.groupby('age'):
        age_rates[str(grp)] = {
            'count': len(sub),
            'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
        }
        
    # Gender
    gender_rates = {}
    for grp, sub in df_clean.groupby('gender'):
        if grp in ['Female', 'Male']:
            gender_rates[str(grp)] = {
                'count': len(sub),
                'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
            }
            
    # Race
    race_rates = {}
    df_clean['race_clean'] = df_clean['race'].replace('?', 'Other/Unknown')
    for grp, sub in df_clean.groupby('race_clean'):
        race_rates[str(grp)] = {
            'count': len(sub),
            'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
        }
        
    # Prior Inpatient Visits
    inpatient_rates = {}
    df_clean['inpatient_binned'] = pd.cut(
        df_clean['number_inpatient'],
        bins=[-1, 0, 1, 2, 5, 100],
        labels=['0 visits', '1 visit', '2 visits', '3-5 visits', '6+ visits']
    )
    for grp, sub in df_clean.groupby('inpatient_binned', observed=False):
        inpatient_rates[str(grp)] = {
            'count': len(sub),
            'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
        }
        
    # Prior ER Visits
    er_rates = {}
    df_clean['er_binned'] = pd.cut(
        df_clean['number_emergency'],
        bins=[-1, 0, 1, 3, 100],
        labels=['0 ER visits', '1 ER visit', '2-3 ER visits', '4+ ER visits']
    )
    for grp, sub in df_clean.groupby('er_binned', observed=False):
        er_rates[str(grp)] = {
            'count': len(sub),
            'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
        }
        
    # Discharge Disposition (grouped Home vs Facility vs Other)
    def map_disp(v):
        try:
            val = int(v)
        except (ValueError, TypeError):
            return 'Other/Unknown'
        if val in [1, 6, 8]:
            return 'Home / Self-Care'
        elif val in [2, 3, 4, 5, 9, 10, 15, 22, 23, 24, 27, 28, 29, 30]:
            return 'Rehab / Skilled Nursing / Facility'
        elif val == 7:
            return 'Left Against Medical Advice (AMA)'
        else:
            return 'Other/Unknown'
            
    df_clean['disp_group'] = df_clean['discharge_disposition_id'].apply(map_disp)
    disp_rates = {}
    for grp, sub in df_clean.groupby('disp_group'):
        disp_rates[str(grp)] = {
            'count': len(sub),
            'readmit_rate_pct': round(float(sub['target'].mean() * 100), 2)
        }
        
    # Outlier statistics
    util_cols = ['time_in_hospital', 'num_lab_procedures', 'num_medications', 'number_outpatient', 'number_emergency', 'number_inpatient']
    outlier_stats = {}
    for col in util_cols:
        outlier_stats[col] = {
            'mean': round(float(df_clean[col].mean()), 2),
            'median': round(float(df_clean[col].median()), 2),
            'std': round(float(df_clean[col].std()), 2),
            'p95': round(float(df_clean[col].quantile(0.95)), 2),
            'p99': round(float(df_clean[col].quantile(0.99)), 2),
            'max': round(float(df_clean[col].max()), 2)
        }
        
    eda_summary = {
        'dataset_name': 'Diabetes 130-US Hospitals (1999-2008)',
        'raw_shape': raw_shape,
        'raw_target_distribution': raw_target_counts,
        'class_balance_raw': class_balance_raw,
        'terminal_encounters_excluded': terminal_count,
        'clean_encounters': len(df_clean),
        'class_balance_clean': {
            'negative_count (NO or >30)': int((df_clean['target'] == 0).sum()),
            'positive_count (<30)': int((df_clean['target'] == 1).sum()),
            'prevalence_percentage': round(float(df_clean['target'].mean() * 100), 2)
        },
        'target_definition_rationale': (
            'Binary classification target defined as readmitted < 30 days = 1, else 0. '
            'This choice directly models CMS HRRP penalty thresholds where readmissions within 30 days '
            'incur up to 3% reimbursement reductions on inpatient prospective payments.'
        ),
        'missing_values_audit': {
            col: {'count': missing_counts[col], 'percentage': missing_pcts[col]}
            for col in missing_counts
        },
        'patient_duplicates': dup_stats,
        'outlier_distributions': outlier_stats,
        'subgroup_readmission_rates': {
            'by_age': age_rates,
            'by_gender': gender_rates,
            'by_race': race_rates,
            'by_prior_inpatient': inpatient_rates,
            'by_prior_er': er_rates,
            'by_discharge_disposition': disp_rates
        }
    }
    
    # Save eda_summary.json
    summary_path = os.path.join(PROCESSED_DIR, "eda_summary.json")
    with open(summary_path, "w") as f:
        json.dump(eda_summary, f, indent=4)
    print(f"[+] EDA Summary JSON successfully saved to {summary_path}")
    
    # Build Jupyter Notebook
    nb = nbf.v4.new_notebook()
    nb['cells'] = [
        nbf.v4.new_markdown_cell(
            "# Exploratory Data Analysis & Feature Decision Rationale\n"
            "## Diabetes 130-US Hospitals (1999-2008) Readmission Prediction Pipeline\n"
            "This notebook details the statistical properties, missingness structure, class balance, "
            "clinical subgroup disparity rates, and feature selection rationales for the hospital readmission model."
        ),
        nbf.v4.new_code_cell(
            "import pandas as pd\nimport numpy as np\nimport json\n\n"
            "# Load raw dataset\ndf = pd.read_csv('../data/raw/diabetic_data.csv')\n"
            "print(f'Raw dataset shape: {df.shape}')\n"
            "df.head()"
        ),
        nbf.v4.new_markdown_cell(
            "### 1. Target Definition & CMS HRRP Clinical Context\n"
            "The readmission outcome contains three levels: `<30` (early readmission within 30 days), "
            "`>30` (late readmission after 30 days), and `NO` (no recorded readmission).\n"
            "Under the CMS Hospital Readmissions Reduction Program (HRRP), federal hospital reimbursement "
            "penalties apply strictly to uncoordinated 30-day readmissions. Therefore, the target is defined as:\n"
            "- **Positive Class (1):** `readmitted == '<30'`\n"
            "- **Negative Class (0):** `readmitted in ['>30', 'NO']`"
        ),
        nbf.v4.new_code_cell(
            "# Target distribution\n"
            "print('Raw 3-class distribution:')\n"
            "print(df['readmitted'].value_counts(normalize=True) * 100)\n\n"
            "df['target'] = (df['readmitted'] == '<30').astype(int)\n"
            "print('\\nBinary 30-day early readmission rate:')\n"
            "print(df['target'].value_counts(normalize=True) * 100)"
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Missing Values Audit & Handling Policy\n"
            "In this dataset, missing values are denoted by `'?'`.\n"
            "- **Weight (>96% missing):** Dropped due to extreme sparsity across facilities.\n"
            "- **Payer code (39.6% missing) & Medical specialty (49.1% missing):** Administrative/billing variables excluded to prevent overfitting.\n"
            "- **Race (2.2% missing):** Imputed to explicit category `'Other/Unknown'` to support algorithmic fairness audits.\n"
            "- **Diagnoses (0.02% - 1.4% missing):** Primary ICD-9 diagnosis grouped into standard clinical categories."
        ),
        nbf.v4.new_code_cell(
            "missing = ((df == '?') | (df.isna())).sum()\n"
            "missing_pct = (missing / len(df)) * 100\n"
            "missing_df = pd.DataFrame({'Missing_Count': missing, 'Percentage': missing_pct})\n"
            "missing_df[missing_df['Missing_Count'] > 0].sort_values(by='Percentage', ascending=False)"
        ),
        nbf.v4.new_markdown_cell(
            "### 3. Patient Duplication & Train-Test Leakage Integrity\n"
            "Many patients had multiple hospital admissions over the 10-year tracking period. "
            "To prevent data leakage, all encounters for a given patient must be strictly partitioned "
            "together using `StratifiedGroupKFold` on `patient_nbr`."
        ),
        nbf.v4.new_code_cell(
            "enc_counts = df.groupby('patient_nbr')['encounter_id'].count()\n"
            "print(f'Total encounters: {len(df)}')\n"
            "print(f'Unique patients: {df.patient_nbr.nunique()}')\n"
            "print(f'Patients with multiple encounters: {(enc_counts > 1).sum()} ({(enc_counts > 1).mean()*100:.1f}%)')\n"
            "print(f'Max encounters for a single patient: {enc_counts.max()}')"
        ),
        nbf.v4.new_markdown_cell(
            "### 4. Terminal Disposition Exclusions\n"
            "Patients discharged to hospice or who expired during the inpatient stay cannot experience 30-day readmissions. "
            "Including them artificially inflates negative survival predictions."
        ),
        nbf.v4.new_code_cell(
            "dead_ids = {11, 13, 14, 19, 20, 21, '11', '13', '14', '19', '20', '21'}\n"
            "dead_mask = df['discharge_disposition_id'].astype(str).isin(dead_ids)\n"
            "print(f'Terminal/hospice encounters excluded: {dead_mask.sum()}')\n"
            "df_clean = df[~dead_mask].copy().reset_index(drop=True)\n"
            "df_clean['target'] = (df_clean['readmitted'] == '<30').astype(int)\n"
            "print(f'Remaining clean encounters: {len(df_clean)}')\n"
            "print(f'Clean 30-day readmission rate: {df_clean.target.mean()*100:.2f}%')"
        ),
        nbf.v4.new_markdown_cell(
            "### 5. Empirical Readmission Disparities across Clinical & Demographic Cohorts"
        ),
        nbf.v4.new_code_cell(
            "print('--- Readmission Rate by Prior Inpatient Hospitalizations ---')\n"
            "print(df_clean.groupby(pd.cut(df_clean['number_inpatient'], [-1, 0, 1, 2, 5, 50]))['target'].agg(['count', 'mean']))\n\n"
            "print('\\n--- Readmission Rate by Age Cohort ---')\n"
            "print(df_clean.groupby('age')['target'].agg(['count', 'mean']))\n\n"
            "print('\\n--- Readmission Rate by Race ---')\n"
            "print(df_clean.groupby(df_clean['race'].replace('?', 'Other/Unknown'))['target'].agg(['count', 'mean']))"
        )
    ]
    
    nb_path = os.path.join(NOTEBOOKS_DIR, "01_eda_and_feature_rationale.ipynb")
    with open(nb_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"[+] EDA Jupyter Notebook successfully exported to {nb_path}")
    
    return eda_summary

if __name__ == "__main__":
    run_eda_and_export_notebook()
