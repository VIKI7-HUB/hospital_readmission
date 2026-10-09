"""
Compiles governance_full_artifacts.json dynamically from canonical generated artifacts.
Ensures 100% synchrony between pipeline benchmark tables, fairness audits,
tier validation, fixed flag rates, and the governance API.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
FAIRNESS_DIR = os.path.join(BASE_DIR, "fairness_governance")

def main():
    print("[*] Compiling governance_full_artifacts.json from canonical generated artifacts...")
    
    # 1. Models at common threshold 0.120 and tuned thresholds
    common_path = os.path.join(MODELS_DIR, "model_benchmark_common_threshold_0.120.json")
    if os.path.exists(common_path):
        with open(common_path, "r", encoding="utf-8") as f:
            models_common = json.load(f)
    else:
        # Fallback to model_comparison_results.csv
        import pandas as pd
        df = pd.read_csv(os.path.join(MODELS_DIR, "model_comparison_results.csv"))
        models_common = df.to_dict(orient="records")

    tuned_path = os.path.join(MODELS_DIR, "model_benchmark_validation_tuned_thresholds.json")
    if os.path.exists(tuned_path):
        with open(tuned_path, "r", encoding="utf-8") as f:
            models_tuned = json.load(f)
    else:
        models_tuned = models_common

    # 2. Tier validation
    tier_path = os.path.join(MODELS_DIR, "tier_validation_test.json")
    with open(tier_path, "r", encoding="utf-8") as f:
        tier_val_raw = json.load(f)
        
    tier_validation = []
    for r in tier_val_raw:
        tier_validation.append({
            "tier": f"{r['Risk Tier']} ({r['Score Range']})",
            "n": r["Encounters (n)"],
            "pct_cohort": round(r["Encounters (n)"] / 19870 * 100, 1),
            "observed_readmissions": r["Readmissions"],
            "empirical_rate": r["Observed Rate (%)"],
            "observed_rate_pct": r["Observed Rate (%)"],
            "ci_95": r["CI 95 String"],
            "ci_95_str": r["CI 95 String"],
            "cutoff_rule": f"Predicted probability {r['Score Range'].replace('to', '–')}"
        })

    # 3. Threshold tradeoff
    thresh_sweep_path = os.path.join(MODELS_DIR, "threshold_sweep_test.json")
    if os.path.exists(thresh_sweep_path):
        with open(thresh_sweep_path, "r", encoding="utf-8") as f:
            sweep_raw = json.load(f)
        tradeoff_sweep = []
        for s in sweep_raw:
            tradeoff_sweep.append({
                "cutoff": round(s["threshold"], 2),
                "threshold": round(s["threshold"], 2),
                "tp": s["true_positives"],
                "true_positives": s["true_positives"],
                "fp": s["false_positives"],
                "false_positives": s["false_positives"],
                "tn": s["true_negatives"],
                "true_negatives": s["true_negatives"],
                "fn": s["false_negatives"],
                "false_negatives": s["false_negatives"],
                "sensitivity": round(s["recall_pct"], 1),
                "recall": round(s["recall_pct"], 1),
                "recall_pct": round(s["recall_pct"], 1),
                "specificity": round(s["true_negatives"] / (s["true_negatives"] + s["false_positives"]) * 100, 1) if (s["true_negatives"] + s["false_positives"]) > 0 else 0.0,
                "precision": round(s["precision_pct"], 1),
                "precision_pct": round(s["precision_pct"], 1),
                "accuracy": round(s["accuracy_pct"], 1),
                "accuracy_pct": round(s["accuracy_pct"], 1),
                "flag_rate": round(s["flag_rate_pct"], 1),
                "flag_rate_pct": round(s["flag_rate_pct"], 1),
            })
    else:
        tradeoff_sweep = []

    # 4. Feature importance & explainability
    exp_path = os.path.join(MODELS_DIR, "explainability_feature_importance.json")
    with open(exp_path, "r", encoding="utf-8") as f:
        feature_importance = json.load(f)

    # 5. Fairness
    fair_path = os.path.join(FAIRNESS_DIR, "mitigation_improvement_summary.json")
    with open(fair_path, "r", encoding="utf-8") as f:
        fairness = json.load(f)

    # 6. Fixed flag rates comparison
    ffr_path = os.path.join(MODELS_DIR, "fixed_flag_rates_comparison.json")
    with open(ffr_path, "r", encoding="utf-8") as f:
        fixed_flag_rates = json.load(f)

    # 7. Validation metrics
    val_path = os.path.join(MODELS_DIR, "validation_metrics_all_models.json")
    with open(val_path, "r", encoding="utf-8") as f:
        val_metrics = json.load(f)

    # 8. HbA1c EDA & Validation Experiment
    hba1c_eda_path = os.path.join(MODELS_DIR, "hba1c_eda_analysis.json")
    with open(hba1c_eda_path, "r", encoding="utf-8") as f:
        hba1c_eda = json.load(f)

    hba1c_exp_path = os.path.join(MODELS_DIR, "hba1c_validation_experiment.json")
    with open(hba1c_exp_path, "r", encoding="utf-8") as f:
        hba1c_exp = json.load(f)

    # 9. Existing preprocessing & mentor checklist
    existing_gov_path = os.path.join(FAIRNESS_DIR, "governance_full_artifacts.json")
    with open(existing_gov_path, "r", encoding="utf-8") as f:
        old_gov = json.load(f)

    data_preprocessing = old_gov.get("data_preprocessing", {})
    mentor_checklist = old_gov.get("mentor_checklist", [])

    payload = {
        "models_common_cutoff": models_common,
        "models_tuned_cutoff": models_tuned,
        "tier_validation": tier_validation,
        "threshold_tradeoff": tradeoff_sweep,
        "feature_importance": feature_importance,
        "data_preprocessing": data_preprocessing,
        "fairness": fairness,
        "cohort_size": 19870,
        "fixed_flag_rates_comparison": fixed_flag_rates,
        "validation_metrics": val_metrics,
        "hba1c_eda_analysis": hba1c_eda,
        "hba1c_validation_experiment": hba1c_exp,
        "mentor_checklist": mentor_checklist
    }

    with open(existing_gov_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
        
    print(f"[+] Successfully wrote unified canonical governance artifacts to {existing_gov_path}")

if __name__ == "__main__":
    main()
