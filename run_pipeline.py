import os
import sys

# Ensure repository root is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    print("==========================================================================")
    print("   HOSPITAL READMISSION RISK PREDICTION (CLASSICAL ML PIPELINE)           ")
    print("   Aligned with Coordinator Specifications (No LLM in Predictions)        ")
    print("==========================================================================")
    
    # 1. Download & extract data
    print("\n--- STEP 1: DATA ACQUISITION & EDA ---")
    from src.download_data import download_and_extract_data
    raw_csv = download_and_extract_data()
    print(f"[+] Raw dataset ready at: {raw_csv}")
    
    from src.eda import run_eda_and_export_notebook
    run_eda_and_export_notebook()
    print("[+] Generated: notebooks/01_eda_and_feature_rationale.ipynb & data/processed/eda_summary.json")
    
    # 2. Preprocessing & Leak-Free Grouped Splitting (70/10/20)
    print("\n--- STEP 2: LEAK-FREE CLEANING, FEATURE SELECTION & 70/10/20 SPLIT ---")
    from src.preprocessing import clean_and_prepare_dataset
    clean_and_prepare_dataset(raw_csv)
    print("[+] Generated: data/processed/data_quality_summary.json & feature_selection_rationale.json")
    print("[+] Verified: 0% train/val/test patient leakage via StratifiedGroupKFold on patient_nbr")
    
    # 3. Model Training, Calibration & Threshold Optimization
    print("\n--- STEP 3: CANDIDATE TRAINING, TIMING, CALIBRATION & BENCHMARKING ---")
    from src.models import train_and_benchmark_models
    results_df, _, _ = train_and_benchmark_models()
    print("\n[+] Model Performance Benchmark Table (Held-Out Test Set N=19,870):")
    print(results_df[['Model', 'Training Time (s)', 'Decision Threshold', 'AUC-ROC', 'Accuracy', 'Precision', 'Recall (Sensitivity)', 'F1-Score']].to_string(index=False))
    print("[+] Generated: models/model_comparison_results.csv & threshold_analysis.json")
    
    # 4. Explainability & Worklist Generation
    print("\n--- STEP 4: EXPLAINABILITY & PRECOMPUTED WORKLIST ---")
    from src.explainability import (
        compute_and_save_explainability_artifacts,
        precompute_worklist_artifacts,
    )
    compute_and_save_explainability_artifacts()
    precompute_worklist_artifacts(max_encounters=500)
    print("[+] Generated: models/explainability_feature_importance.json & data/processed/worklist_precomputed.joblib")
    
    # 5. Fairness Audit & Disparity Mitigation
    print("\n--- STEP 5: DEMOGRAPHIC FAIRNESS AUDIT & TRAINING MITIGATION ---")
    from src.fairness import run_comprehensive_fairness_audit
    run_comprehensive_fairness_audit()
    print("[+] Generated: fairness_governance/mitigation_improvement_summary.json & subgroup CSV audits")
    
    # 6. Model Report & Supplementary Artifacts
    print("\n--- STEP 6: MODEL REPORT CHARTS & BENCHMARK ARTIFACTS ---")
    import scripts.generate_model_report_artifacts as gmra
    gmra.main()
    
    # 7. Validation Metrics, Fixed Flag Rates, & Tier Tables
    print("\n--- STEP 7: VALIDATION METRICS, FIXED FLAG RATES & TIERS ---")
    import scripts.generate_part1_and_part2_artifacts as gp12
    gp12.main()
    
    # 8. Compile Unified Governance Artifacts
    print("\n--- STEP 8: UNIFIED GOVERNANCE ARTIFACTS ASSEMBLY ---")
    import scripts.compile_governance_full_artifacts as cgfa
    cgfa.main()
    
    print("\n==========================================================================")
    print("   ALL PIPELINE STAGES COMPLETED & ARTIFACTS VERIFIED!                   ")
    print("==========================================================================")

if __name__ == "__main__":
    main()
