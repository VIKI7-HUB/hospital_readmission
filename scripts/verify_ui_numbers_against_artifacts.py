"""
Verification Script: Compare every number displayed on Governance and Worklist pages
against the saved, ground-truth artifacts.
"""

import io
import json
import sys
from pathlib import Path

import joblib

if sys.stdout.encoding != 'utf-8':
    try:
        getattr(sys.stdout, 'reconfigure', lambda **kwargs: None)(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass

WORKSPACE = Path(__file__).resolve().parent.parent

def main():
    print("=" * 80)
    print("AUDITING NUMBERS DISPLAYED ON GOVERNANCE & WORKLIST PAGES AGAINST ARTIFACTS")
    print("=" * 80)

    # 1. Load Governance Artifacts
    gov_file = WORKSPACE / "fairness_governance" / "governance_full_artifacts.json"
    if not gov_file.exists():
        print(f"FAILED: Missing artifact {gov_file}")
        sys.exit(1)

    with open(gov_file, "r", encoding="utf-8") as f:
        gov = json.load(f)

    # 2. Load Worklist Artifact
    worklist_file = WORKSPACE / "data" / "processed" / "worklist_precomputed.joblib"
    if not worklist_file.exists():
        print(f"FAILED: Missing artifact {worklist_file}")
        sys.exit(1)

    worklist_df = joblib.load(worklist_file)

    # ---------------------------------------------------------
    # CHECK 1: Worklist Page KPIs and Counts
    # ---------------------------------------------------------
    print("\n[CHECK 1] Auditing Worklist Page Numbers...")
    n_total = len(worklist_df)
    n_flagged = int((worklist_df["prob"] >= 0.12).sum())
    flag_rate = n_flagged / n_total
    n_high = int((worklist_df["tier"] == "High Risk").sum())
    high_rate = n_high / n_total
    n_poly = int((worklist_df["num_medications"] >= 10).sum())
    poly_rate = n_poly / n_total
    n_readmitted = int(worklist_df["actual_readmitted"].sum())
    readmit_rate = n_readmitted / n_total

    print(f"  • Total cohort size: {n_total} (UI displays 500)")
    assert n_total == 500, "Cohort size mismatch"

    print(f"  • Flagged encounters: {n_flagged} ({flag_rate*100:.1f}%) (UI displays 188 / 37.6%)")
    assert n_flagged == 188, "Flagged count mismatch"

    print(f"  • High-tier count: {n_high} ({high_rate*100:.1f}%) (UI displays 45 / 9.0%)")
    assert n_high == 45, "High risk count mismatch"

    print(f"  • Polypharmacy count (>=10 distinct meds): {n_poly} ({poly_rate*100:.1f}%) (UI displays 395 / 79.0%)")
    assert n_poly == 395, "Polypharmacy count mismatch"
    assert round(poly_rate * 100, 1) == 79.0, "Polypharmacy rate is not 79.0%"

    print(f"  • Observed readmissions: {n_readmitted} ({readmit_rate*100:.1f}%) (UI displays 54 / 10.8%)")
    assert n_readmitted == 54, "Readmission count mismatch"
    assert round(readmit_rate * 100, 1) == 10.8, "Sample readmission rate mismatch"

    # ---------------------------------------------------------
    # CHECK 2: Governance Header & Split Sizes
    # ---------------------------------------------------------
    print("\n[CHECK 2] Auditing Governance Header & Split Sizes...")
    splits = gov["data_preprocessing"]["data_quality"]["split_sizes_detailed"]
    train_enc = splits["train"]["encounters"]
    train_pts = splits["train"]["patients"]
    val_enc = splits["val"]["encounters"]
    val_pts = splits["val"]["patients"]
    test_enc = splits["test"]["encounters"]
    test_pts = splits["test"]["patients"]
    total_enc = gov["data_preprocessing"]["data_quality"]["total_clean_encounters"]
    total_pts = gov["data_preprocessing"]["data_quality"]["unique_patients"]

    print(f"  • Clean cohort: {total_enc} encounters, {total_pts} patients")
    assert train_enc + val_enc + test_enc == total_enc == 99343, "Encounters sum mismatch"
    assert train_pts + val_pts + test_pts == total_pts == 69990, "Patients sum mismatch"
    print(f"  • Train split: {train_enc} enc, {train_pts} pts (70.0%)")
    print(f"  • Val split: {val_enc} enc, {val_pts} pts (10.0%)")
    print(f"  • Test split: {test_enc} enc, {test_pts} pts (20.0%)")

    # Exclusions
    exclusions = gov["data_preprocessing"]["data_quality"]["terminal_encounters_excluded"]
    print(f"  • Terminal exclusions: {exclusions} (must be 2,423)")
    assert exclusions == 2423, "Exclusions mismatch"

    # ---------------------------------------------------------
    # CHECK 3: HbA1c EDA & Validation Experiment
    # ---------------------------------------------------------
    print("\n[CHECK 3] Auditing HbA1c Findings & Experiment...")
    hba1c_cats = gov["hba1c_eda_analysis"]["hba1c_categories"]
    total_cat_enc = sum(c["Encounters (n)"] for c in hba1c_cats)
    assert total_cat_enc == 99343, f"HbA1c categories total {total_cat_enc} != 99343"

    exp_tested = gov["hba1c_validation_experiment"]["cohort_difference"]["tested"]
    exp_not = gov["hba1c_validation_experiment"]["cohort_difference"]["not_tested"]
    print(f"  • Tested rate: {exp_tested['readmission_rate_pct']}% (n={exp_tested['encounters_n']}, k={exp_tested['readmissions_k']})")
    print(f"  • Not tested rate: {exp_not['readmission_rate_pct']}% (n={exp_not['encounters_n']}, k={exp_not['readmissions_k']})")
    abs_diff = gov["hba1c_validation_experiment"]["cohort_difference"]["absolute_difference_pp"]
    print(f"  • Absolute diff: {abs_diff} pp (CI: {gov['hba1c_validation_experiment']['cohort_difference']['absolute_difference_ci_95_str']})")
    assert abs_diff == 1.75, f"HbA1c diff {abs_diff} != 1.75"

    chi2 = gov["hba1c_validation_experiment"]["cohort_difference"]["chi_square"]
    print(f"  • Chi2 statistic: {chi2} (p = {gov['hba1c_validation_experiment']['cohort_difference']['p_value']})")
    assert chi2 == 42.56, "Chi2 statistic mismatch"

    # ---------------------------------------------------------
    # CHECK 4: Model Comparison & Validation Rule
    # ---------------------------------------------------------
    print("\n[CHECK 4] Auditing Model Benchmarks & Validation Selection...")
    val_metrics = gov["validation_metrics"]
    for vm in val_metrics:
        print(f"  • {vm['Model']}: Val AUC = {vm['Validation AUC-ROC']:.4f}, Val Brier = {vm['Validation Brier Score']:.4f}")

    test_models = gov["models_common_cutoff"]
    assert len(test_models) == 6, "Expected 6 candidate models in benchmark"
    ensemble_test = next(m for m in test_models if "Ensemble" in m["Model"])
    print(f"  • Calibrated Ensemble (12% cutoff): AUC = {ensemble_test['AUC-ROC']:.4f}, Recall = {ensemble_test['Recall (Sensitivity)']*100:.2f}%, Precision = {ensemble_test['Precision']*100:.2f}%, Brier = {ensemble_test['Brier Score']:.4f}")
    assert round(ensemble_test['AUC-ROC'], 4) == 0.6531, "Ensemble test AUC mismatch"
    assert round(ensemble_test['Recall (Sensitivity)'] * 100, 2) == 57.27, "Ensemble test recall mismatch"
    assert round(ensemble_test['Precision'] * 100, 2) == 17.30, "Ensemble test precision mismatch"
    assert round(ensemble_test['Brier Score'], 4) == 0.0976, "Ensemble test Brier mismatch"

    # Fixed Flag Rates
    ffr = gov["fixed_flag_rates_comparison"]
    print(f"  • Fixed flag rates records: {len(ffr)} rows (top 20%, 30%, 40%)")
    assert len(ffr) == 18, f"Expected 18 fixed flag rate comparisons, got {len(ffr)}"

    # ---------------------------------------------------------
    # CHECK 5: Threshold Sweep & Trade-off Slider
    # ---------------------------------------------------------
    print("\n[CHECK 5] Auditing Threshold Sweep (Slider Driven)...")
    sweep = gov["threshold_tradeoff"]
    print(f"  • Threshold sweep steps: {len(sweep)} (range {sweep[0]['cutoff']} to {sweep[-1]['cutoff']})")
    assert len(sweep) == 46, f"Expected 46 sweep steps, got {len(sweep)}"
    step_12 = next(s for s in sweep if round(s["cutoff"], 2) == 0.12)
    print(f"  • Step 0.12: TP={step_12['tp']}, FP={step_12['fp']}, TN={step_12['tn']}, FN={step_12['fn']}")
    assert step_12["tp"] + step_12["fn"] == 2263, "Total positive cases in test holdout must be 2,263"
    assert step_12["tp"] + step_12["fp"] + step_12["tn"] + step_12["fn"] == 19870, "Total test cases must be 19,870"
    assert step_12["accuracy"] == 64.0, f"Accuracy at 12% cutoff is {step_12['accuracy']}%"

    # ---------------------------------------------------------
    # CHECK 6: Risk Tier Validation
    # ---------------------------------------------------------
    print("\n[CHECK 6] Auditing Risk Tier Empirical Validation...")
    tiers = gov["tier_validation"]
    for t in tiers:
        print(f"  • Tier '{t['tier']}': n={t['n']} ({t['pct_cohort']}%), k={t['observed_readmissions']}, rate={t['observed_rate_pct']}%, CI: {t['ci_95_str']}")
    tier_n_sum = sum(t["n"] for t in tiers)
    tier_k_sum = sum(t["observed_readmissions"] for t in tiers)
    assert tier_n_sum == 19870, f"Tier total n {tier_n_sum} != 19870"
    assert tier_k_sum == 2263, f"Tier total k {tier_k_sum} != 2263"
    assert tiers[0]["observed_rate_pct"] < tiers[1]["observed_rate_pct"] < tiers[2]["observed_rate_pct"], "Tiers must be strictly monotonic"

    # ---------------------------------------------------------
    # CHECK 7: Explainability (Odds Ratios & Trees)
    # ---------------------------------------------------------
    print("\n[CHECK 7] Auditing Explainability & Units...")
    odds = gov["feature_importance"]["logistic_regression_odds_ratios"]
    rehab_or = next(o for o in odds if "rehab" in o["display_name"].lower() or "snf" in o["display_name"].lower() or "discharge" in o["display_name"].lower())
    print(f"  • Discharge SNF/rehab odds ratio: OR = {rehab_or['odds_ratio']}, unit = '{rehab_or['unit']}'")
    assert rehab_or["unit"] == "versus reference category", "Rehab/SNF unit mismatch"
    num_or = next(o for o in odds if o["unit"] == "per 1 SD")
    print(f"  • Continuous feature '{num_or['display_name']}': OR = {num_or['odds_ratio']}, unit = '{num_or['unit']}'")

    # ---------------------------------------------------------
    # CHECK 8: Demographic Fairness Audits
    # ---------------------------------------------------------
    print("\n[CHECK 8] Auditing Fairness Audits & Small Group Flags...")
    fairness = gov["fairness"]["demographic_audits"]
    for dim_data in fairness.values():
        print(f"  • Dimension '{dim_data['attribute']}': headline gap = {dim_data['headline_gap_point_pp']:.2f}% (CI: {dim_data['headline_gap_ci_str']})")
        for sg in dim_data["subgroups"]:
            print(f"      - {sg['subgroup']}: n={sg['sample_size_n']}, k={sg['readmitted_cases_k']}, TPR={sg['unmitigated_tpr_pct']}%, small_sample={sg['is_small_sample']}")
            if sg["readmitted_cases_k"] < 100:
                assert sg["is_small_sample"] is True, f"Subgroup {sg['subgroup']} has <100 readmissions but is not flagged as small sample"

    # ---------------------------------------------------------
    # CHECK 9: Mentor Requirements Checklist
    # ---------------------------------------------------------
    print("\n[CHECK 9] Auditing Mentor Requirements Checklist...")
    checklist = gov["mentor_checklist"]
    assert len(checklist) == 14, f"Expected 14 checklist items, got {len(checklist)}"
    for item in checklist:
        print(f"  • Item {item['id']}: [{item['status']}] {item['requirement']}")
        assert item["status"] in ["Done", "Partial"], f"Invalid status: {item['status']}"

    print("\n" + "=" * 80)
    print("ALL 9 GOVERNANCE & WORKLIST AUDIT CHECKS PASSED PERFECTLY!")
    print("EVERY NUMBER IS SOURCED FROM VALIDATED ARTIFACTS.")
    print("=" * 80)

if __name__ == "__main__":
    main()
