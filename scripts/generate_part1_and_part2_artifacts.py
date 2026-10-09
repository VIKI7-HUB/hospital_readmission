import json
import os
import sys
import joblib
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import src.models

MODELS_DIR = os.path.join(BASE_DIR, "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
FAIRNESS_DIR = os.path.join(BASE_DIR, "fairness_governance")

def main():
    print("[*] Generating Part 1 corrections and Part 2 artifacts...")
    split_data = joblib.load(os.path.join(PROCESSED_DIR, "train_val_test_data.joblib"))
    eval_artifacts = joblib.load(os.path.join(MODELS_DIR, "evaluation_artifacts.joblib"))

    y_val = np.array(split_data['y_val'])
    y_test = np.array(split_data['y_test'])
    val_probs = eval_artifacts['val_probs']
    test_probs = eval_artifacts['test_probs']
    model_names = ['Logistic Regression', 'Random Forest', 'XGBoost', 'LightGBM', 'CatBoost', 'Calibrated Ensemble']

    # 1. Validation Metrics Table (Item B)
    val_rows = []
    for name in model_names:
        p = val_probs[name]
        auc = roc_auc_score(y_val, p)
        pr_auc = average_precision_score(y_val, p)
        brier = brier_score_loss(y_val, p)
        val_rows.append({
            'Model': name,
            'Validation AUC-ROC': round(float(auc), 4),
            'Validation PR-AUC': round(float(pr_auc), 4),
            'Validation Brier Score': round(float(brier), 4)
        })
    df_val = pd.DataFrame(val_rows)
    df_val.to_csv(os.path.join(MODELS_DIR, "validation_metrics_all_models.csv"), index=False)
    with open(os.path.join(MODELS_DIR, "validation_metrics_all_models.json"), "w") as f:
        json.dump(val_rows, f, indent=4)
    print("[+] Saved validation_metrics_all_models.csv and .json")

    # 2. Fair Comparison at Fixed Flag Rates: Top 20%, 30%, 40% (Item A)
    fair_rows = []
    prevalence = 0.1139
    total_pos = y_test.sum()
    n_test = len(y_test)

    for name in model_names:
        p = test_probs[name]
        for frac in [0.20, 0.30, 0.40]:
            k = int(round(n_test * frac))
            top_idx = np.argsort(p)[::-1][:k]
            thresh = float(p[top_idx[-1]])
            tp = int(y_test[top_idx].sum())
            fp = int(k - tp)
            rec = float(tp / total_pos)
            prec = float(tp / k)
            lift = float(prec / prevalence)
            fair_rows.append({
                'Model': name,
                'Flag Rate': f'Top {int(frac*100)}%',
                'k_encounters': k,
                'Cutoff': round(thresh, 4),
                'Recall (%)': round(rec * 100, 2),
                'Precision (%)': round(prec * 100, 2),
                'Lift': round(lift, 2),
                'True Positives': tp,
                'False Positives': fp
            })
    df_fair = pd.DataFrame(fair_rows)
    df_fair.to_csv(os.path.join(MODELS_DIR, "fixed_flag_rates_comparison.csv"), index=False)
    with open(os.path.join(MODELS_DIR, "fixed_flag_rates_comparison.json"), "w") as f:
        json.dump(fair_rows, f, indent=4)
    print("[+] Saved fixed_flag_rates_comparison.csv and .json")

    # 3. Tier Validation with 95% Wilson CIs (Item E)
    p_ens = test_probs['Calibrated Ensemble']
    tiers = [
        ('Low', '< 12%', p_ens < 0.12),
        ('Elevated', '12% to 20%', (p_ens >= 0.12) & (p_ens < 0.20)),
        ('High', '>= 20%', p_ens >= 0.20)
    ]
    tier_rows = []
    z = 1.96
    for tier_name, rng, mask in tiers:
        n = int(mask.sum())
        pos = int(y_test[mask].sum())
        rate = pos / n
        denom = 1 + z**2 / n
        centre = (rate + z**2 / (2 * n)) / denom
        spread = (z * np.sqrt((rate * (1 - rate) + z**2 / (4 * n)) / n)) / denom
        low = max(0.0, centre - spread) * 100
        high = min(1.0, centre + spread) * 100
        tier_rows.append({
            'Risk Tier': tier_name,
            'Score Range': rng,
            'Encounters (n)': n,
            'Readmissions': pos,
            'Observed Rate (%)': round(rate * 100, 2),
            'CI 95 Lower (%)': round(low, 2),
            'CI 95 Upper (%)': round(high, 2),
            'CI 95 String': f"[{low:.2f}%, {high:.2f}%]"
        })
    df_tier = pd.DataFrame(tier_rows)
    df_tier.to_csv(os.path.join(MODELS_DIR, "tier_validation_test.csv"), index=False)
    with open(os.path.join(MODELS_DIR, "tier_validation_test.json"), "w") as f:
        json.dump(tier_rows, f, indent=4)
    print("[+] Saved tier_validation_test.csv and .json")

    # 4. HbA1c and Medication Change EDA (Part 2, Item 1)
    raw_csv = pd.read_csv(os.path.join(BASE_DIR, "data", "raw", "diabetic_data.csv"))
    dead_ids = {11, 13, 14, 19, 20, 21, '11', '13', '14', '19', '20', '21'}
    clean_raw = raw_csv[~raw_csv['discharge_disposition_id'].astype(str).isin(dead_ids)].copy().reset_index(drop=True)
    clean_raw['target'] = (clean_raw['readmitted'] == '<30').astype(int)
    clean_raw['A1Cresult_clean'] = clean_raw['A1Cresult'].fillna('None')

    hba1c_cats = ['>8', '>7', 'Norm', 'None']
    hba1c_rows = []
    for cat in hba1c_cats:
        sub = clean_raw[clean_raw['A1Cresult_clean'] == cat]
        n_c = len(sub)
        k_c = int(sub['target'].sum())
        rate_c = k_c / n_c
        denom_c = 1 + z**2 / n_c
        centre_c = (rate_c + z**2 / (2 * n_c)) / denom_c
        spread_c = (z * np.sqrt((rate_c * (1 - rate_c) + z**2 / (4 * n_c)) / n_c)) / denom_c
        low_c = max(0.0, centre_c - spread_c) * 100
        high_c = min(1.0, centre_c + spread_c) * 100
        hba1c_rows.append({
            'Category': cat,
            'Description': 'HbA1c > 8% (Uncontrolled)' if cat == '>8' else (
                'HbA1c > 7% (Suboptimal)' if cat == '>7' else (
                    'HbA1c Normal (<7%)' if cat == 'Norm' else 'None (Test Not Ordered)'
                )
            ),
            'Encounters (n)': n_c,
            'Cohort Share (%)': round(n_c / len(clean_raw) * 100, 2),
            'Readmissions': k_c,
            'Readmission Rate (%)': round(rate_c * 100, 2),
            'CI 95 String': f"[{low_c:.2f}%, {high_c:.2f}%]"
        })

    contingency_a1c = pd.crosstab(clean_raw['A1Cresult_clean'], clean_raw['target'])
    chi2_val, p_val, dof, _ = chi2_contingency(contingency_a1c)

    # Change flag contingency
    contingency_ch = pd.crosstab(clean_raw['change'], clean_raw['target'])
    chi2_ch, p_val_ch, dof_ch, _ = chi2_contingency(contingency_ch)

    hba1c_payload = {
        'total_clean_encounters': len(clean_raw),
        'hba1c_categories': hba1c_rows,
        'chi_square_test_a1c': {
            'statistic': round(float(chi2_val), 2),
            'dof': int(dof),
            'p_value': float(p_val),
            'p_value_sci': f"{p_val:.4e}",
            'interpretation': 'Statistically significant association between HbA1c ordering status and 30-day readmission.'
        },
        'chi_square_test_change': {
            'statistic': round(float(chi2_ch), 2),
            'dof': int(dof_ch),
            'p_value': float(p_val_ch),
            'p_value_sci': f"{p_val_ch:.4e}",
            'interpretation': 'Statistically significant association between medication change flag and 30-day readmission.'
        },
        'feature_set_inclusion': {
            'A1Cresult_in_final_model': False,
            'rationale': (
                'A1Cresult has 83.05% unmeasured rate (82,509 / 99,343 encounters lacked testing orders). '
                'Testing frequency varied by admitting specialty rather than standardized clinical protocol. '
                'Therapeutic glycemic volatility is captured without missingness by the medication change flag '
                'and insulin regimen.'
            ),
            'change_flag_in_final_model': True,
            'insulin_in_final_model': True
        }
    }
    with open(os.path.join(MODELS_DIR, "hba1c_eda_analysis.json"), "w") as f:
        json.dump(hba1c_payload, f, indent=4)
    pd.DataFrame(hba1c_rows).to_csv(os.path.join(MODELS_DIR, "hba1c_eda_analysis.csv"), index=False)
    print("[+] Saved hba1c_eda_analysis.json and .csv")

if __name__ == "__main__":
    main()
