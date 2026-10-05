import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import recall_score, precision_score, accuracy_score, roc_auc_score

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
FAIRNESS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fairness_governance")

def evaluate_subgroup_metrics(y_true, y_prob, group_labels, threshold=0.5):
    """
    Computes performance metrics and selection rates across demographic subgroups.
    Clinical Rationale: Ensures predictive equity across Age, Gender, and Race protected classes.
    """
    df_eval = pd.DataFrame({
        'y_true': y_true.values if hasattr(y_true, 'values') else y_true,
        'y_prob': y_prob,
        'y_pred': (y_prob >= threshold).astype(int),
        'group': group_labels.values if hasattr(group_labels, 'values') else group_labels
    })
    
    subgroup_stats = []
    
    for g_name, g_df in df_eval.groupby('group'):
        if len(g_df) == 0:
            continue
        count = len(g_df)
        pos_rate = float(g_df['y_true'].mean())
        sel_rate = float(g_df['y_pred'].mean())
        
        # Avoid zero division issues
        if g_df['y_true'].sum() > 0:
            rec = float(recall_score(g_df['y_true'], g_df['y_pred'], zero_division=0))
        else:
            rec = np.nan
            
        if g_df['y_pred'].sum() > 0:
            prec = float(precision_score(g_df['y_true'], g_df['y_pred'], zero_division=0))
        else:
            prec = np.nan
            
        acc = float(accuracy_score(g_df['y_true'], g_df['y_pred']))
        
        try:
            auc = float(roc_auc_score(g_df['y_true'], g_df['y_prob'])) if g_df['y_true'].nunique() > 1 else np.nan
        except:
            auc = np.nan
            
        subgroup_stats.append({
            'Subgroup': str(g_name),
            'Sample Size': count,
            'Actual Positive Rate': pos_rate,
            'Selection Rate (Predicted Positive)': sel_rate,
            'Recall (TPR)': rec,
            'Precision': prec,
            'Accuracy': acc,
            'AUC-ROC': auc
        })
        
    return pd.DataFrame(subgroup_stats)

def calculate_fairness_summary(subgroup_df):
    """
    Calculates key quantitative fairness ratios and disparity metrics.
    - Demographic Parity Ratio (DPR): Ratio of minimum to maximum selection rate across cohorts.
    - Equalized Odds (TPR Disparity): Difference and ratio of minimum to maximum sensitivity across cohorts.
    """
    valid_subgroups = subgroup_df[subgroup_df['Sample Size'] >= 30]
    
    min_sel = float(valid_subgroups['Selection Rate (Predicted Positive)'].min())
    max_sel = float(valid_subgroups['Selection Rate (Predicted Positive)'].max())
    dpr = min_sel / max(max_sel, 1e-6)
    
    min_tpr = float(valid_subgroups['Recall (TPR)'].min())
    max_tpr = float(valid_subgroups['Recall (TPR)'].max())
    tpr_ratio = min_tpr / max(max_tpr, 1e-6)
    tpr_diff = max_tpr - min_tpr
    
    min_sel_row = valid_subgroups.loc[valid_subgroups['Selection Rate (Predicted Positive)'].idxmin()]
    max_sel_row = valid_subgroups.loc[valid_subgroups['Selection Rate (Predicted Positive)'].idxmax()]
    
    return {
        'Demographic Parity Ratio (Min/Max Sel Rate)': dpr,
        'Equalized Odds Ratio (Min/Max TPR)': tpr_ratio,
        'Equalized Odds Difference (Max - Min TPR)': tpr_diff,
        'Min Selection Rate Subgroup': str(min_sel_row['Subgroup']),
        'Max Selection Rate Subgroup': str(max_sel_row['Subgroup']),
        'Disparate Impact Compliant (DPR >= 0.8)': bool(dpr >= 0.8)
    }

def apply_fairness_aware_mitigation(y_true, y_prob, group_labels, target_tpr=None):
    """
    Stretch Goal: Group-specific post-processing threshold optimizer to achieve Equal Opportunity / Equalized Odds.
    Adjusts classification thresholds per demographic subgroup so that True Positive Rates (Recall) align across groups.
    """
    df_eval = pd.DataFrame({
        'y_true': y_true.values if hasattr(y_true, 'values') else y_true,
        'y_prob': y_prob,
        'group': group_labels.values if hasattr(group_labels, 'values') else group_labels
    }).reset_index(drop=True)
    
    # Calculate group-specific optimal thresholds
    groups = df_eval['group'].unique()
    group_thresholds = {}
    
    # Global target recall baseline
    global_pred = (y_prob >= 0.5).astype(int)
    global_target_tpr = recall_score(df_eval['y_true'], global_pred) if target_tpr is None else target_tpr
    
    for g in groups:
        g_mask = df_eval['group'] == g
        g_y_true = df_eval.loc[g_mask, 'y_true']
        g_y_prob = df_eval.loc[g_mask, 'y_prob']
        
        if len(g_y_true) < 30 or g_y_true.sum() == 0:
            group_thresholds[g] = 0.5
            continue
            
        # Grid search threshold to match target TPR
        best_t = 0.5
        best_diff = float('inf')
        for t in np.linspace(0.1, 0.9, 81):
            pred_t = (g_y_prob >= t).astype(int)
            tpr_t = recall_score(g_y_true, pred_t, zero_division=0)
            diff = abs(tpr_t - global_target_tpr)
            if diff < best_diff:
                best_diff = diff
                best_t = t
        group_thresholds[g] = best_t
        
    # Apply group thresholds
    mitigated_preds = np.zeros(len(df_eval), dtype=int)
    for i, row in df_eval.iterrows():
        g = row['group']
        t = group_thresholds.get(g, 0.5)
        mitigated_preds[i] = int(row['y_prob'] >= t)
        
    return mitigated_preds, group_thresholds

def run_comprehensive_fairness_audit():
    """
    Executes full fairness audit across Age, Gender, and Race for trained models.
    Quantifies disparity metrics and measures before/after improvement for stretch goal mitigation (KPI 3 & 4).
    """
    os.makedirs(FAIRNESS_DIR, exist_ok=True)
    artifacts_path = os.path.join(MODELS_DIR, "evaluation_artifacts.joblib")
    
    if not os.path.exists(artifacts_path):
        raise FileNotFoundError("Model artifacts not found. Run src/models.py first.")
        
    artifacts = joblib.load(artifacts_path)
    y_test = artifacts['y_test']
    sens_test = artifacts['sens_test']
    test_probs = artifacts['test_probs']
    
    # Focus primary governance audit on best performing model (XGBoost)
    model_name = 'XGBoost' if 'XGBoost' in test_probs else list(test_probs.keys())[0]
    y_prob = test_probs[model_name]
    
    audit_results = {}
    improvement_summary = {}
    
    print(f"\n[*] Running Fairness & Governance Audit for {model_name}...")
    
    for attr in ['race_clean', 'age_group', 'gender_clean']:
        group_series = sens_test[attr]
        subgroup_df = evaluate_subgroup_metrics(y_test, y_prob, group_series)
        fairness_summary = calculate_fairness_summary(subgroup_df)
        
        # Mitigation stretch goal
        mitigated_preds, group_thresholds = apply_fairness_aware_mitigation(y_test, y_prob, group_series)
        
        # Recalculate post mitigation stats using custom preds
        mit_df_eval = pd.DataFrame({
            'y_true': y_test.values if hasattr(y_test, 'values') else y_test,
            'y_pred': mitigated_preds,
            'group': group_series.values if hasattr(group_series, 'values') else group_series
        }).reset_index(drop=True)
        
        mit_subgroup_list = []
        for g_name, g_df in mit_df_eval.groupby('group'):
            count = len(g_df)
            sel_rate = float(g_df['y_pred'].mean())
            rec = float(recall_score(g_df['y_true'], g_df['y_pred'], zero_division=0))
            prec = float(precision_score(g_df['y_true'], g_df['y_pred'], zero_division=0))
            mit_subgroup_list.append({
                'Subgroup': str(g_name),
                'Sample Size': count,
                'Mitigated Threshold': float(group_thresholds.get(g_name, 0.5)),
                'Mitigated Selection Rate': sel_rate,
                'Mitigated Recall (TPR)': rec,
                'Mitigated Precision': prec
            })
        mit_subgroup_df = pd.DataFrame(mit_subgroup_list)
        
        # Calculate mitigated disparity
        mit_valid = mit_subgroup_df[mit_subgroup_df['Sample Size'] >= 30]
        mit_min_sel = float(mit_valid['Mitigated Selection Rate'].min())
        mit_max_sel = float(mit_valid['Mitigated Selection Rate'].max())
        mit_dpr = mit_min_sel / max(mit_max_sel, 1e-6)
        
        mit_min_tpr = float(mit_valid['Mitigated Recall (TPR)'].min())
        mit_max_tpr = float(mit_valid['Mitigated Recall (TPR)'].max())
        mit_tpr_ratio = mit_min_tpr / max(mit_max_tpr, 1e-6)
        mit_tpr_diff = mit_max_tpr - mit_min_tpr
        
        # Measure improvement deltas
        base_tpr_diff = fairness_summary['Equalized Odds Difference (Max - Min TPR)']
        tpr_diff_reduction = base_tpr_diff - mit_tpr_diff
        
        improvement_summary[attr] = {
            'baseline': {
                'demographic_parity_ratio': float(fairness_summary['Demographic Parity Ratio (Min/Max Sel Rate)']),
                'equalized_odds_tpr_ratio': float(fairness_summary['Equalized Odds Ratio (Min/Max TPR)']),
                'equalized_odds_tpr_diff': float(base_tpr_diff)
            },
            'mitigated': {
                'demographic_parity_ratio': float(mit_dpr),
                'equalized_odds_tpr_ratio': float(mit_tpr_ratio),
                'equalized_odds_tpr_diff': float(mit_tpr_diff)
            },
            'improvement_deltas': {
                'tpr_disparity_reduction_absolute': float(tpr_diff_reduction),
                'equalized_odds_ratio_gain': float(mit_tpr_ratio - fairness_summary['Equalized Odds Ratio (Min/Max TPR)'])
            },
            'group_thresholds': {str(k): float(v) for k, v in group_thresholds.items()}
        }
        
        # Save CSV reports
        subgroup_csv = os.path.join(FAIRNESS_DIR, f"fairness_bias_analysis_{attr}.csv")
        subgroup_df.to_csv(subgroup_csv, index=False)
        
        mit_csv = os.path.join(FAIRNESS_DIR, f"fairness_mitigated_{attr}.csv")
        mit_subgroup_df.to_csv(mit_csv, index=False)
        
        audit_results[attr] = {
            'base_subgroups': subgroup_df,
            'summary': fairness_summary,
            'mitigated_subgroups': mit_subgroup_df,
            'group_thresholds': group_thresholds
        }
        
        print(f"\n[+] {attr.upper()} Bias Audit Summary:")
        print(f"    - Baseline Demographic Parity Ratio: {fairness_summary['Demographic Parity Ratio (Min/Max Sel Rate)']:.4f}")
        print(f"    - Baseline Equalized Odds (TPR) Diff: {base_tpr_diff:.4f}")
        print(f"    - Mitigated Equalized Odds (TPR) Diff: {mit_tpr_diff:.4f} (Disparity Reduction: {tpr_diff_reduction*100:.2f}%)")
        
    # Save improvement summary JSON
    improvement_json_path = os.path.join(FAIRNESS_DIR, "mitigation_improvement_summary.json")
    with open(improvement_json_path, 'w') as f:
        json.dump(improvement_summary, f, indent=4)
    print(f"\n[+] Saved Fairness Mitigation Improvement Summary to {improvement_json_path}")
    
    joblib.dump(audit_results, os.path.join(FAIRNESS_DIR, "fairness_audit_results.joblib"))
    print(f"[+] Full Fairness Audit complete. Saved artifacts to fairness_governance/")
    return audit_results

if __name__ == "__main__":
    run_comprehensive_fairness_audit()
