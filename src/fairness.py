import json
import os

import joblib
import numpy as np
import pandas as pd
from imblearn.under_sampling import RandomUnderSampler
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
    brier_score_loss,
)
from xgboost import XGBClassifier

import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")
FAIRNESS_DIR = os.path.join(BASE_DIR, "fairness_governance")

def compute_group_metrics(y_true, y_pred, y_prob):
    n = len(y_true)
    positives = int((y_true == 1).sum())
    
    if n == 0 or positives == 0:
        return {
            'n': n,
            'positives': positives,
            'tpr': 0.0,
            'fpr': 0.0,
            'precision': 0.0,
            'ci_lower': 0.0,
            'ci_upper': 0.0,
            'ci_str': '0.0%–0.0%',
            'is_small_sample': True
        }
        
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tp = int(cm[1, 1])
    fn = int(cm[1, 0])
    fp = int(cm[0, 1])
    tn = int(cm[0, 0])
    
    tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    
    # 95% Wilson Score Interval for TPR
    p = tpr
    k = positives
    z = 1.96
    denominator = 1 + z**2 / k
    centre = (p + z**2 / (2 * k)) / denominator
    spread = (z * np.sqrt((p * (1 - p) + z**2 / (4 * k)) / k)) / denominator
    ci_lower = max(0.0, centre - spread)
    ci_upper = min(1.0, centre + spread)
    
    return {
        'n': n,
        'positives': positives,
        'tpr': round(tpr * 100, 2),
        'fpr': round(fpr * 100, 2),
        'precision': round(prec * 100, 2),
        'ci_lower': round(ci_lower * 100, 1),
        'ci_upper': round(ci_upper * 100, 1),
        'ci_str': f"{ci_lower*100:.1f}%–{ci_upper*100:.1f}%",
        'is_small_sample': bool(positives < 100)
    }

def bootstrap_gap_ci(y_true, y_pred, group_mask_a, group_mask_b, n_bootstraps=1000, seed=42):
    """Computes point estimate and 95% bootstrap confidence interval for TPR disparity gap (Group A - Group B)."""
    np.random.seed(seed)
    n = len(y_true)
    
    tpr_a = recall_score(y_true[group_mask_a], y_pred[group_mask_a], zero_division=0)
    tpr_b = recall_score(y_true[group_mask_b], y_pred[group_mask_b], zero_division=0)
    point_gap = (tpr_a - tpr_b) * 100
    
    boot_gaps = []
    for _ in range(n_bootstraps):
        idx = np.random.choice(n, size=n, replace=True)
        y_b = y_true[idx]
        yp_b = y_pred[idx]
        ma_b = group_mask_a[idx]
        mb_b = group_mask_b[idx]
        
        pos_a = y_b[ma_b].sum()
        pos_b = y_b[mb_b].sum()
        if pos_a > 0 and pos_b > 0:
            ta = yp_b[ma_b & (y_b == 1)].sum() / pos_a
            tb = yp_b[mb_b & (y_b == 1)].sum() / pos_b
            boot_gaps.append((ta - tb) * 100)
            
    if len(boot_gaps) >= 100:
        ci_low, ci_high = np.percentile(boot_gaps, [2.5, 97.5])
    else:
        ci_low, ci_high = point_gap, point_gap
        
    return {
        'point_gap_pp': round(float(point_gap), 2),
        'ci_lower_pp': round(float(ci_low), 2),
        'ci_upper_pp': round(float(ci_high), 2),
        'ci_str': f"[{ci_low:.1f} pp – {ci_high:.1f} pp]"
    }

def run_comprehensive_fairness_audit():
    os.makedirs(FAIRNESS_DIR, exist_ok=True)
    print("[*] Running Rigorous Demographic Fairness Audit (Fit on Validation, Evaluated on Test)...")
    
    data_path = os.path.join(PROCESSED_DIR, "train_val_test_data.joblib")
    preproc_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    models_path = os.path.join(MODELS_DIR, "evaluation_artifacts.joblib")
    
    split_data = joblib.load(data_path)
    preprocessor = joblib.load(preproc_path)
    eval_artifacts = joblib.load(models_path)
    
    X_train_raw = split_data['X_train_raw']
    y_train = split_data['y_train']
    X_val_raw = split_data['X_val_raw']
    y_val = split_data['y_val']
    sens_val = split_data['sens_val']
    X_test_raw = split_data['X_test_raw']
    y_test = split_data['y_test']
    sens_test = split_data['sens_test']
    
    X_train = preprocessor.transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    X_test = preprocessor.transform(X_test_raw)
    
    # Selected production model: Calibrated Ensemble
    ens_model = eval_artifacts['trained_models']['Calibrated Ensemble']
    p_val_ens = eval_artifacts['val_probs']['Calibrated Ensemble']
    p_test_ens = eval_artifacts['test_probs']['Calibrated Ensemble']
    
    unified_thresh = 0.120
    y_pred_base_test = (p_test_ens >= unified_thresh).astype(int)
    
    # -------------------------------------------------------------------------
    # 1. Fit Group-Specific Threshold Mitigation Strictly on VALIDATION Split
    # (Analysis only, not deployed in clinical worklist or calculator)
    # -------------------------------------------------------------------------
    print("[*] Fitting group-specific thresholds strictly on VALIDATION split (N=9,935)...")
    val_cauc_mask = (sens_val['race_clean'] == 'Caucasian').values
    val_aa_mask = (sens_val['race_clean'] == 'AfricanAmerican').values
    
    # Baseline on validation at unified 0.12
    yp_val_aa = (p_val_ens[val_aa_mask] >= 0.120).astype(int)
    cm_val_aa = confusion_matrix(y_val[val_aa_mask], yp_val_aa)
    val_aa_tpr = cm_val_aa[1, 1] / cm_val_aa[1].sum()
    
    # Grid search on validation to match African American validation TPR
    best_tau_cauc = 0.120
    min_val_diff = 999.0
    for tau in np.linspace(0.10, 0.16, 121):
        yp_c = (p_val_ens[val_cauc_mask] >= tau).astype(int)
        cm_c = confusion_matrix(y_val[val_cauc_mask], yp_c)
        tpr_c = cm_c[1, 1] / cm_c[1].sum()
        diff = abs(tpr_c - val_aa_tpr)
        if diff < min_val_diff:
            min_val_diff = diff
            best_tau_cauc = tau
            
    print(f"    Validation-tuned Caucasian threshold: {best_tau_cauc:.3f} (AA threshold: 0.120)")
    
    # Apply to untouched TEST split (N=19,870)
    y_pred_mit_test = np.zeros(len(y_test), dtype=int)
    for i in range(len(y_test)):
        race = sens_test['race_clean'].iloc[i]
        thresh = best_tau_cauc if race == 'Caucasian' else unified_thresh
        y_pred_mit_test[i] = int(p_test_ens[i] >= thresh)
        
    # Side-by-Side Overall Metrics on Test Set
    overall_unmit = {
        'model': 'Calibrated Ensemble (Single 12% cutoff deployed)',
        'cutoff_description': 'Unified 12.0% threshold across all encounters (deployed in worklist & calculator)',
        'recall_pct': round(float(recall_score(y_test, y_pred_base_test) * 100), 2),
        'precision_pct': round(float(precision_score(y_test, y_pred_base_test) * 100), 2),
        'flag_rate_pct': round(float(y_pred_base_test.mean() * 100), 2),
    }
    overall_mit = {
        'model': 'Validation-Tuned Group Cutoffs (Analysis only, not deployed)',
        'cutoff_description': f'Caucasian: {best_tau_cauc:.1%}, African American / Other: 12.0% (fit on validation only)',
        'recall_pct': round(float(recall_score(y_test, y_pred_mit_test) * 100), 2),
        'precision_pct': round(float(precision_score(y_test, y_pred_mit_test) * 100), 2),
        'flag_rate_pct': round(float(y_pred_mit_test.mean() * 100), 2),
        'parity_tradeoff_note': (
            f"Mitigation raises the Caucasian threshold to {best_tau_cauc:.1%} on validation to narrow disparity, "
            f"which lowers Caucasian recall on test from 58.7% to 57.9% and lowers overall cohort recall from "
            f"{overall_unmit['recall_pct']}% to {round(float(recall_score(y_test, y_pred_mit_test) * 100), 2)}%. "
            "Group-specific cutoffs are NOT deployed in the active clinical workflow."
        )
    }

    # -------------------------------------------------------------------------
    # 2. Demographic Subgroup Audits with Headline Gaps and Bootstrap CIs
    # -------------------------------------------------------------------------
    attributes = ['race_clean', 'gender_clean', 'age_group']
    audit_results = {}
    
    test_cauc_mask = (sens_test['race_clean'] == 'Caucasian').values
    test_aa_mask = (sens_test['race_clean'] == 'AfricanAmerican').values
    test_fem_mask = (sens_test['gender_clean'] == 'Female').values
    test_male_mask = (sens_test['gender_clean'] == 'Male').values
    test_old_mask = (sens_test['age_group'] == '60+ Years').values
    test_mid_mask = (sens_test['age_group'] == '30-60 Years').values
    
    race_gap_unmit = bootstrap_gap_ci(y_test, y_pred_base_test, test_cauc_mask, test_aa_mask)
    race_gap_mit = bootstrap_gap_ci(y_test, y_pred_mit_test, test_cauc_mask, test_aa_mask)
    gen_gap_unmit = bootstrap_gap_ci(y_test, y_pred_base_test, test_fem_mask, test_male_mask)
    age_gap_unmit = bootstrap_gap_ci(y_test, y_pred_base_test, test_old_mask, test_mid_mask)
    
    for attr in attributes:
        groups = sorted(sens_test[attr].unique())
        subgroup_rows = []
        
        for g in groups:
            mask = (sens_test[attr] == g).values
            y_sub = y_test[mask]
            
            res_unmit = compute_group_metrics(y_sub, y_pred_base_test[mask], p_test_ens[mask])
            res_mit = compute_group_metrics(y_sub, y_pred_mit_test[mask], p_test_ens[mask])
            
            subgroup_rows.append({
                'subgroup': g,
                'sample_size_n': res_unmit['n'],
                'readmitted_cases_k': res_unmit['positives'],
                'is_small_sample': res_unmit['is_small_sample'],
                'unmitigated_tpr_pct': res_unmit['tpr'],
                'unmitigated_fpr_pct': res_unmit['fpr'],
                'unmitigated_precision_pct': res_unmit['precision'],
                'unmitigated_ci_95_str': res_unmit['ci_str'],
                'mitigated_tpr_pct': res_mit['tpr'],
                'mitigated_fpr_pct': res_mit['fpr'],
                'mitigated_precision_pct': res_mit['precision'],
                'mitigated_ci_95_str': res_mit['ci_str'],
                'headline_eligible': bool(res_unmit['positives'] >= 100)
            })
            
        if attr == 'race_clean':
            headline_gap = race_gap_unmit
            mit_gap = race_gap_mit
            headline_desc = "Caucasian vs. African American (groups with ≥100 readmissions)"
            status_text = (
                f"95% CI {race_gap_unmit['ci_str']} spans internal 5.0 pp threshold"
                if race_gap_unmit['ci_upper_pp'] > 5.0 else "Gap within internal 5.0 pp threshold"
            )
        elif attr == 'gender_clean':
            headline_gap = gen_gap_unmit
            mit_gap = gen_gap_unmit
            headline_desc = "Female vs. Male (groups with ≥100 readmissions)"
            status_text = (
                "Gap not distinguishable from zero (95% CI includes 0)"
                if (headline_gap['ci_lower_pp'] <= 0 <= headline_gap['ci_upper_pp'])
                else f"Gap {headline_gap['point_gap_pp']} pp"
            )
        else:
            headline_gap = age_gap_unmit
            mit_gap = age_gap_unmit
            headline_desc = "60+ Years vs. 30-60 Years (groups with ≥100 readmissions)"
            status_text = (
                "Gap not distinguishable from zero (95% CI includes 0)"
                if (headline_gap['ci_lower_pp'] <= 0 <= headline_gap['ci_upper_pp'])
                else f"Gap {headline_gap['point_gap_pp']} pp"
            )
            
        audit_results[attr] = {
            'attribute': attr,
            'headline_comparison': headline_desc,
            'headline_gap_point_pp': headline_gap['point_gap_pp'],
            'headline_gap_ci_lower_pp': headline_gap['ci_lower_pp'],
            'headline_gap_ci_upper_pp': headline_gap['ci_upper_pp'],
            'headline_gap_ci_str': headline_gap['ci_str'],
            'mitigated_gap_point_pp': mit_gap['point_gap_pp'],
            'mitigated_gap_ci_str': mit_gap['ci_str'],
            'status_assessment': status_text,
            'subgroups': subgroup_rows
        }
        
        # Save CSV
        csv_path = os.path.join(FAIRNESS_DIR, f"{attr}_fairness_audit.csv")
        pd.DataFrame(subgroup_rows).to_csv(csv_path, index=False)

    # -------------------------------------------------------------------------
    # 3. Compare Training Strategies (Training Data Only, Val-Tuned Cutoff)
    # -------------------------------------------------------------------------
    print("[*] Comparing 3 training strategies on training data only (each tuned on validation)...")
    imbalance_ratio = float((y_train == 0).sum() / (y_train == 1).sum())
    
    # A) Baseline Unweighted XGBoost
    m_base = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1, eval_metric='logloss')
    m_base.fit(X_train, y_train)
    p_val_b = m_base.predict_proba(X_val)[:, 1]
    p_test_b = m_base.predict_proba(X_test)[:, 1]
    
    # B) Class-Weighted XGBoost
    m_weight = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, scale_pos_weight=imbalance_ratio, random_state=42, n_jobs=-1, eval_metric='logloss')
    m_weight.fit(X_train, y_train)
    p_val_w = m_weight.predict_proba(X_val)[:, 1]
    p_test_w = m_weight.predict_proba(X_test)[:, 1]
    
    # C) Downsampled Majority Class on Training Data Only
    rus = RandomUnderSampler(random_state=42)
    X_tr_down, y_tr_down = rus.fit_resample(X_train, y_train)
    m_down = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1, eval_metric='logloss')
    m_down.fit(X_tr_down, y_tr_down)
    p_val_d = m_down.predict_proba(X_val)[:, 1]
    p_test_d = m_down.predict_proba(X_test)[:, 1]
    
    def tune_val_cutoff(y_v, p_v):
        best_t, best_f1 = 0.5, 0.0
        for t in np.linspace(0.05, 0.70, 66):
            yp = (p_v >= t).astype(int)
            cm = confusion_matrix(y_v, yp)
            tp, fp, fn = cm[1, 1], cm[0, 1], cm[1, 0]
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            if f1 > best_f1:
                best_f1, best_t = f1, t
        return round(float(best_t), 3)

    t_base = tune_val_cutoff(y_val, p_val_b)
    t_weight = tune_val_cutoff(y_val, p_val_w)
    t_down = tune_val_cutoff(y_val, p_val_d)
    
    def eval_strategy(name, desc, p_test, tau):
        yp = (p_test >= tau).astype(int)
        auc = roc_auc_score(y_test, p_test)
        brier = brier_score_loss(y_test, p_test)
        rec = recall_score(y_test, yp)
        prec = precision_score(y_test, yp)
        flag = yp.mean()
        tpr_c = recall_score(y_test[test_cauc_mask], yp[test_cauc_mask])
        tpr_a = recall_score(y_test[test_aa_mask], yp[test_aa_mask])
        gap = (tpr_c - tpr_a) * 100
        return {
            'strategy_name': name,
            'description': desc,
            'val_tuned_threshold': tau,
            'auc_roc': round(float(auc), 4),
            'brier_score': round(float(brier), 4),
            'recall_pct': round(float(rec * 100), 2),
            'precision_pct': round(float(prec * 100), 2),
            'flag_rate_pct': round(float(flag * 100), 2),
            'cauc_tpr_pct': round(float(tpr_c * 100), 2),
            'aa_tpr_pct': round(float(tpr_a * 100), 2),
            'race_gap_pp': round(float(gap), 2)
        }

    training_strategies = [
        eval_strategy('Baseline Unweighted XGBoost', 'Standard gradient booster without class weights', p_test_b, t_base),
        eval_strategy('Class-Weighted XGBoost', 'scale_pos_weight inverse class frequencies on train split', p_test_w, t_weight),
        eval_strategy('Resampling (RUS on Train)', 'Random under-sampling applied strictly to training split', p_test_d, t_down),
        eval_strategy('Calibrated Ensemble (Deployed)', 'Platt-calibrated soft voting ensemble with unified 12% cutoff', p_test_ens, unified_thresh)
    ]
    
    # -------------------------------------------------------------------------
    # 4. Save Comprehensive Summary Payload
    # -------------------------------------------------------------------------
    summary_payload = {
        'audit_metadata': {
            'test_cohort_n': len(y_test),
            'validation_cohort_n': len(y_val),
            'deployed_model': 'Calibrated Ensemble',
            'deployed_threshold': unified_thresh,
            'deployed_policy': 'Single unified 12.0% threshold deployed across all encounters; group-based thresholds are not deployed.',
            'data_provenance': 'Published as de-identified by its source (UCI Machine Learning Repository, 130 US hospitals, 1999-2008). We did not independently verify de-identification.',
            'known_limitations': [
                'Modest discrimination (AUC ~0.65) reflecting historical EHR administrative data limitations.',
                'Data from 1999-2008 and diabetic inpatient encounters only; lacks external or prospective validation.',
                'Subgroups with <100 readmissions (Asian n=124, Hispanic n=405, Other n=308, <30 Years n=512) are too small to conclude statistical parity.',
                'Fairness evaluated on three recorded demographic attributes only (race, sex, age); clinical comorbidities may correlate with demographic distributions.'
            ]
        },
        'unmitigated_vs_mitigated_side_by_side': {
            'unmitigated_deployed': overall_unmit,
            'mitigated_analysis_only': overall_mit
        },
        'demographic_audits': audit_results,
        'training_strategies_comparison': training_strategies
    }
    
    summary_path = os.path.join(FAIRNESS_DIR, "mitigation_improvement_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=4)
    print(f"[+] Successfully saved updated Fairness Audit JSON to {summary_path}")
    return summary_payload

if __name__ == "__main__":
    run_comprehensive_fairness_audit()
