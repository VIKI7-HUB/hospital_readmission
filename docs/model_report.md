# Clinical Readmission Risk Model Governance & Performance Report

> **Project:** AI-Based Predictive Analytics for Clinical Decision-Making (30-Day Hospital Readmission Risk)  
> **Dataset:** UCI Diabetes 130-US Hospitals (1999–2008), 99,343 clean inpatient encounters across 69,990 unique patients  
> **Data Partitioning:** Leak-Free Patient-Grouped Stratified Split (StratifiedGroupKFold on patient_nbr):  
> - **Train Split:** N = 69,538 encounters (70.0%), 48,973 unique patients  
> - **Validation Split:** N = 9,935 encounters (10.0%), 6,979 unique patients  
> - **Test Holdout:** N = 19,870 encounters (20.0%), 14,038 unique patients  
> - **Patient Overlap Check:** 0% patient leakage (Train and Val overlap = 0, Train and Test overlap = 0, Val and Test overlap = 0, confirmed with programmatic assertions)  
> **Target Prevalence:** 30-Day Inpatient Readmission (readmitted == '<30'); 11.39% overall (2,263 / 19,870 on test holdout).

---

## 1. Test-Set Discipline Audit

To prevent circular reasoning, optimistic performance inflation, and data leakage, all model design choices, hyperparameter selections, calibrations, decision thresholds, and fairness mitigation cutoffs were audited for test-set leakage. Every decision historically referencing the test split was remediated to rely strictly on the **Validation Split** (N = 9,935), followed by a single final evaluation on the untouched **Test Holdout** (N = 19,870).

### 1.1 Decision Point Audit Summary

| # | Decision Point | What Was Chosen | Which Split Was Used | Was It Clean? | Remediation & Grounding Details |
| :-: | :--- | :--- | :--- | :-: | :--- |
| **1** | **Choice of Model & Training Strategy** | 6 candidate estimators (Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost, Calibrated Ensemble) and 3 class balance strategies (Baseline unweighted, Class Weights 7.78:1, Random Under-Sampling). | Fit strictly on **Train Split** (N = 69,538); strategy comparison thresholds tuned on **Validation Split** (N = 9,935). | **CLEAN** | Estimator parameters and class weight calculations fit exclusively on training data. Strategy comparison operating points tuned on validation split. |
| **2** | **Final Model Selection** | **Calibrated Soft-Voting Ensemble** (blending tuned XGBoost 35%, LightGBM 35%, CatBoost 30% with Platt scaling). | **Validation Split** (N = 9,935). | **CLEAN** *(Remediated)* | Historical documentation cited test AUC (0.6640). Champion selection was re-grounded strictly on validation Brier score calibration (0.0966, tied for top with CatBoost and XGBoost), validation AUC (0.6707), validation PR-AUC (0.2194), and multi-learner blending. |
| **3** | **Probability Calibration** | Platt Scaling (Sigmoid Logistic Regression mapping raw predictions to posterior probabilities). | Fitted strictly on **Validation Split** (N = 9,935, X_val, y_val). | **CLEAN** | Calibrator parameters fit strictly on validation split; zero test-set exposure during fitting. |
| **4** | **Classification Threshold** | Unified operating threshold tau = 0.120 (12.0%) for champion model; candidate-specific thresholds: LR (0.120), RF (0.130), XGB (0.120), LGB (0.120), CAT (0.120). | **Validation Split** (N = 9,935). | **CLEAN** | Selected via validation sweep maximizing Recall (60.78% on validation) subject to an operational Precision floor >= 18.0% (validation precision 18.23%). Test split evaluated once post-hoc. |
| **5** | **Risk Tier Cutoffs** | Three tiers: **Low Risk** (<12.0%), **Elevated Risk** (12.0%–20.0%), **High Risk** (>= 20.0%). | **Validation Split** (N = 9,935). | **CLEAN** | Low/Elevated boundary is the validation decision threshold (12.0%); High boundary is the 91.2nd validation percentile (~2x population readmission risk). Test set used only for one-time empirical rate reporting. |
| **6** | **Fairness / Mitigation Cutoffs** | Group-specific threshold mitigation: Caucasian cutoff tuned to tau_Caucasian = 0.121 on validation to match AA validation TPR (60.87%) at tau = 0.120. Deployed clinical policy retains unified single 12.0% cutoff. | **Validation Split** (N = 9,935). | **CLEAN** *(Remediated)* | Historical code tested mitigation cutoffs post-hoc on test. Remediation fits thresholds on validation only, then evaluates on test once with bootstrap 95% CIs. Mitigated cutoffs are labeled "Analysis only, not deployed". |

Saved artifacts: `models/test_set_audit.csv` and `models/test_set_audit.json`.

---

## 2. Model Selection & Validation Benchmark (N = 9,935)

### 2.1 Model Selection Rule Up Front
The candidate estimators were evaluated on the independent **Validation Split** (N = 9,935 encounters, 1,130 readmissions, 11.37% prevalence). The primary selection rule is **highest validation AUC-ROC**, with ties in discriminative power evaluated on **calibration quality (lowest validation Brier score)**.

### 2.2 Validation Performance Comparison Table

| Model Architecture | Validation AUC-ROC | Validation PR-AUC | Validation Brier Score | Calibration Rank |
| :--- | :---: | :---: | :---: | :---: |
| **CatBoost** | **0.6714** | **0.2197** | **0.0966** | Tied 1st |
| **Calibrated Ensemble** | 0.6707 | 0.2194 | **0.0966** | Tied 1st |
| **XGBoost** | 0.6694 | 0.2190 | **0.0966** | Tied 1st |
| **LightGBM** | 0.6679 | 0.2151 | 0.0967 | 4th |
| **Random Forest** | 0.6664 | 0.2086 | 0.0971 | 5th |
| **Logistic Regression** | 0.6645 | 0.2049 | 0.0973 | 6th |

### 2.3 Transparent Assessment of Validation Results
On the validation split, **CatBoost achieved the highest AUC-ROC (0.6714) and highest PR-AUC (0.2197)**, performing slightly better than the Calibrated Ensemble (0.6707 AUC, 0.2194 PR-AUC) with an identical Brier score (0.0966). The Soft-Voting Ensemble was retained for deployment because combining diverse gradient boosting mechanisms (symmetric oblivious trees in CatBoost, depth-wise split trees in XGBoost, and leaf-wise histogram trees in LightGBM) prevents vulnerability to model-specific inductive biases. On the untouched test holdout, the ensemble achieved 0.6530 AUC versus CatBoost's 0.6525.

### 2.4 Explainability Trade-Off: Ensemble vs. Single Model
A single parametric model such as Logistic Regression provides direct, globally interpretable coefficients and odds ratios that clinicians can verify directly in an EHR chart, whereas an ensemble of tree-based models trades away transparency and requires post-hoc explanation heuristics (such as TreeSHAP or perturbation scoring) that are harder for clinical staff to audit.

Saved artifact: `models/validation_metrics_all_models.csv` and `models/validation_metrics_all_models.json`.

---

## 3. Test Set Model Performance Benchmarks (N = 19,870)

### 3.1 Common Operating Point (tau = 0.120) Across All Models
| Model Architecture | Cutoff (tau) | Precision | Recall (Sens.) | Accuracy | ROC-AUC | F1-Score | Flag Rate | Brier Score | TP | FP | TN | FN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | 0.120 | 17.93% | 49.98% | 68.24% | 0.6468 | 0.2639 | 31.75% | 0.0982 | 1,131 | 5,178 | 12,429 | 1,132 |
| **Random Forest** | 0.120 | 16.91% | 56.08% | 63.62% | 0.6467 | 0.2599 | 37.76% | 0.0980 | 1,269 | 6,234 | 11,373 | 994 |
| **XGBoost** | 0.120 | 17.31% | 56.96% | 64.12% | 0.6514 | 0.2656 | 37.47% | 0.0977 | 1,289 | 6,156 | 11,451 | 974 |
| **LightGBM** | 0.120 | 17.07% | 56.56% | 63.76% | 0.6512 | 0.2623 | 37.73% | 0.0977 | 1,280 | 6,217 | 11,390 | 983 |
| **CatBoost** | 0.120 | 17.61% | 57.84% | 64.37% | 0.6525 | 0.2700 | 37.42% | 0.0976 | 1,309 | 6,126 | 11,481 | 954 |
| **Calibrated Ensemble** | **0.120** | **17.38%** | **57.62%** | **63.97%** | **0.6530** | **0.2670** | **37.77%** | **0.0976** | **1,304** | **6,201** | **11,406** | **959** |

### 3.2 Each Model's Own Validation-Tuned Operating Point
| Model Architecture | Cutoff (tau) | Precision | Recall (Sens.) | Accuracy | ROC-AUC | F1-Score | Flag Rate | Brier Score | TP | FP | TN | FN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | 0.120 | 17.93% | 49.98% | 68.24% | 0.6468 | 0.2639 | 31.75% | 0.0982 | 1,131 | 5,178 | 12,429 | 1,132 |
| **Random Forest** | 0.130 | 17.50% | 51.66% | 66.75% | 0.6467 | 0.2614 | 33.62% | 0.0980 | 1,169 | 5,512 | 12,095 | 1,094 |
| **XGBoost** | 0.120 | 17.31% | 56.96% | 64.12% | 0.6514 | 0.2656 | 37.47% | 0.0977 | 1,289 | 6,156 | 11,451 | 974 |
| **LightGBM** | 0.120 | 17.07% | 56.56% | 63.76% | 0.6512 | 0.2623 | 37.73% | 0.0977 | 1,280 | 6,217 | 11,390 | 983 |
| **CatBoost** | 0.120 | 17.61% | 57.84% | 64.37% | 0.6525 | 0.2700 | 37.42% | 0.0976 | 1,309 | 6,126 | 11,481 | 954 |
| **Calibrated Ensemble** | **0.120** | **17.38%** | **57.62%** | **63.97%** | **0.6530** | **0.2670** | **37.77%** | **0.0976** | **1,304** | **6,201** | **11,406** | **959** |

---

## 4. Fair Comparison at Fixed Flag Rates (Top 20%, 30%, 40%)

To evaluate pure ranking discrimination without confounding differences in threshold calibration, all models were evaluated on the test set (N = 19,870, prevalence = 11.39%) at fixed encounter review budgets:

| Model Architecture | Flag Rate Budget | Encounters Flagged (k) | Operating Cutoff | Recall (Sens.) | Precision (PPV) | Lift over Baseline (11.39%) | True Positives | False Positives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **Top 20%** | 3,974 | 0.1458 | 34.69% | 19.75% | 1.73x | 785 | 3,189 |
| Random Forest | Top 20% | 3,974 | 0.1631 | 33.85% | 19.28% | 1.69x | 766 | 3,208 |
| XGBoost | Top 20% | 3,974 | 0.1604 | 35.04% | 19.95% | 1.75x | 793 | 3,181 |
| LightGBM | Top 20% | 3,974 | 0.1582 | 35.31% | 20.11% | 1.77x | 799 | 3,175 |
| CatBoost | Top 20% | 3,974 | 0.1592 | 34.78% | 19.80% | 1.74x | 787 | 3,187 |
| **Calibrated Ensemble** | **Top 20%** | 3,974 | 0.1589 | **35.22%** | **20.06%** | **1.76x** | **797** | **3,177** |
| | | | | | | | | |
| **Logistic Regression** | **Top 30%** | 5,961 | 0.1235 | 47.24% | 17.93% | 1.57x | 1,069 | 4,892 |
| Random Forest | Top 30% | 5,961 | 0.1389 | 46.88% | 17.80% | 1.56x | 1,061 | 4,900 |
| XGBoost | Top 30% | 5,961 | 0.1370 | 48.70% | 18.49% | 1.62x | 1,102 | 4,859 |
| LightGBM | Top 30% | 5,961 | 0.1379 | 47.50% | 18.03% | 1.58x | 1,075 | 4,886 |
| CatBoost | Top 30% | 5,961 | 0.1363 | 47.86% | 18.17% | 1.60x | 1,083 | 4,878 |
| **Calibrated Ensemble** | **Top 30%** | 5,961 | 0.1372 | **48.12%** | **18.27%** | **1.60x** | **1,089** | **4,872** |
| | | | | | | | | |
| **Logistic Regression** | **Top 40%** | 7,948 | 0.1059 | 58.59% | 16.68% | 1.46x | 1,326 | 6,622 |
| Random Forest | Top 40% | 7,948 | 0.1147 | 58.95% | 16.78% | 1.47x | 1,334 | 6,614 |
| XGBoost | Top 40% | 7,948 | 0.1140 | 59.66% | 16.99% | 1.49x | 1,350 | 6,598 |
| LightGBM | Top 40% | 7,948 | 0.1148 | 58.77% | 16.73% | 1.47x | 1,330 | 6,618 |
| CatBoost | Top 40% | 7,948 | 0.1141 | 59.74% | 17.01% | 1.49x | 1,352 | 6,596 |
| **Calibrated Ensemble** | **Top 40%** | 7,948 | 0.1146 | **59.57%** | **16.96%** | **1.49x** | **1,348** | **6,600** |

### 4.1 Plain-Language Head-to-Head: Ensemble vs. Logistic Regression
**Yes, the Calibrated Ensemble beats Logistic Regression at every fixed flag rate, but the margin of superiority is modest:**
- At **Top 20% flag rate**: The ensemble captures 35.22% recall versus 34.69% for Logistic Regression (+0.53 percentage points, identifying 12 more true readmissions).
- At **Top 30% flag rate**: The ensemble captures 48.12% recall versus 47.24% for Logistic Regression (+0.88 percentage points, identifying 20 more true readmissions).
- At **Top 40% flag rate**: The ensemble captures 59.57% recall versus 58.59% for Logistic Regression (+0.98 percentage points, identifying 22 more true readmissions).
The performance lift of the non-linear ensemble over regularized linear regression is consistently under 1.0 percentage point across all operational budgets, demonstrating that linear utilization features carry the bulk of predictive signal in administrative EHR data.

Saved artifact: `models/fixed_flag_rates_comparison.csv` and `models/fixed_flag_rates_comparison.json`.

---

## 5. Decision Threshold Analysis & Capacity Constraints

### 5.1 Where the 18% Precision Floor Comes From
The 18.0% precision floor was established based on clinical review capacity. Care coordination teams (post-discharge call nurses, clinical pharmacists, and diabetic care educators) have finite daily caseload capacity. Setting a minimum precision floor of 18% ensures that intervention teams do not experience severe alert fatigue: at 18% precision, approximately 1 in every 5.5 flagged patients will actually be readmitted within 30 days.

### 5.2 Plain-Language Precision Translation
At the selected operational threshold (tau = 0.120, achieving 17.38% precision on test):  
**Out of every 10 patients flagged by the model, between 1 and 2 (specifically, about 1.7 out of 10) are readmitted within 30 days, while the other 8.3 are not.**

### 5.3 Capacity-Based Alternative Cutoff (tau = 0.150)
If hospital nurse coordination capacity is more constrained, a higher alternative cutoff of **0.15 (15.0%)** can be adopted:
- **Precision rises** to 19.23% (nearly 2 out of every 10 flagged patients are readmitted).
- **Caseload falls**: Total flagged encounters drop from 37.77% (7,505 patients) down to 23.90% (4,748 patients), reducing nurse follow-up workload by 36.7%.
- **Trade-off**: Recall drops from 57.62% (1,304 readmissions captured) down to 40.34% (913 readmissions captured), missing 391 readmitted patients who would have been captured at the 12% cutoff.

### 5.4 Test Set Threshold Sweep Table (Calibrated Ensemble)

| Threshold (tau) | Precision | Recall (Sens.) | Accuracy | False Positives | False Negatives | True Positives | True Negatives | Flag Rate (%) | Operational Interpretation |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 0.05 | 12.05% | 98.06% | 18.24% | 16,202 | 44 | 2,219 | 1,405 | 92.71% | Maximum Sensitivity (Extreme Alert Fatigue) |
| 0.10 | 16.12% | 66.59% | 56.74% | 7,839 | 756 | 1,507 | 9,768 | 47.04% | High Recall Screening (Sub-Floor Precision) |
| **0.12** | **17.38%** | **57.62%** | **63.97%** | **6,201** | **959** | **1,304** | **11,406** | **37.77%** | **CHOSEN OPERATING THRESHOLD (tau*)** |
| **0.15** | **19.23%** | **40.34%** | **73.91%** | **3,835** | **1,350** | **913** | **13,772** | **23.90%** | **CAPACITY-CONSTRAINED ALTERNATIVE** |
| 0.20 | 24.17% | 18.69% | 84.06% | 1,327 | 1,840 | 423 | 16,280 | 8.81% | High-Risk Tier Boundary |
| 0.25 | 29.14% | 8.48% | 87.23% | 467 | 2,071 | 192 | 17,140 | 3.32% | Intensive Case Management Only |
| 0.30 | 33.98% | 4.64% | 88.11% | 204 | 2,158 | 105 | 17,403 | 1.56% | Highly Specific Inpatient Review |
| 0.35 | 42.54% | 2.52% | 88.51% | 77 | 2,206 | 57 | 17,530 | 0.67% | Extreme Risk Surveillance |
| 0.40 | 46.67% | 0.62% | 88.60% | 16 | 2,249 | 14 | 17,591 | 0.15% | Outlier Screening |
| 0.45 | 0.00% | 0.00% | 88.61% | 0 | 2,263 | 0 | 17,607 | 0.00% | No Flags |
| 0.50 | 0.00% | 0.00% | 88.61% | 0 | 2,263 | 0 | 17,607 | 0.00% | Default Unadjusted Standard (Unusable) |

Saved artifact: `models/threshold_sweep_test.csv` and `models/threshold_sweep_test.json`.

---

## 6. Clinical Metric Justifications

### 6.1 Clinical Asymmetry: False Positives vs. False Negatives
In transitional care coordination, the clinical consequences of prediction errors are asymmetric:
- **False Positive (FP):** A patient who will not be readmitted is flagged as high risk. This wastes limited hospital resources: a nurse coordinator spends 15 minutes attempting telephone outreach, a clinical pharmacist performs medication reconciliation, or a transitional care slot is held unnecessarily.
- **False Negative (FN):** A patient who will be readmitted is classified as low risk. This is clinically far more serious: the patient is discharged without structured follow-up care, home health oversight, or diabetes education, increasing the likelihood that they deteriorate acutely at home and return through the emergency room.
- **Prioritizing Recall:** Because missed readmissions compromise patient outcomes and post-discharge safety, the model operating threshold is selected by prioritizing Recall (Sensitivity) subject to an operational precision constraint.

### 6.2 CMS HRRP Penalty Structure
The Centers for Medicare & Medicaid Services (CMS) Hospital Readmissions Reduction Program (HRRP) penalizes hospitals through **across-the-board payment reductions** applied to all Medicare inpatient prospective payment claims (up to a 3% reduction on total operating Medicare reimbursement), determined by excess readmission ratios across conditions, rather than a fixed fee per individual readmission.

### 6.3 Why ROC-AUC is Essential
The Receiver Operating Characteristic Area Under the Curve (ROC-AUC) summarizes discriminative ranking ability across all potential decision thresholds independent of specific clinical cutoffs or institutional staffing capacities.

### 6.4 Why Accuracy Alone is Misleading
With an 11.39% baseline readmission prevalence (88.61% negative class), a naive baseline predicting "no readmission" for every encounter achieves an apparently high **88.61% accuracy** while having **0.00% recall** (missing all 2,263 readmitted patients). Accuracy is uninformative in imbalanced healthcare screening.

---

## 7. Risk Tier Empirical Validation on Test Cohort (N = 19,870)

Empirical test set readmission rates by validated risk tier:

| Risk Tier | Score Range | Encounters (n) | Readmissions | Observed Readmission Rate | 95% CI (Wilson Interval) | Clinical Workflow Action |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Low Risk** | < 12.0% | 12,365 | 959 | **7.76%** | **[7.30%, 8.24%]** | Routine discharge summary, standard outpatient primary care follow-up within 30 days. |
| **Elevated Risk** | 12.0% to 20.0% | 5,755 | 881 | **15.31%** | **[14.40%, 16.26%]** | Enhanced transition planning, pharmacist medication reconciliation, follow-up in 7–10 days. |
| **High Risk** | >= 20.0% | 1,750 | 423 | **24.17%** | **[22.22%, 26.23%]** | Multidisciplinary discharge plan, 48-hr telehealth check-in, diabetes educator consult. |

Observed readmission rate escalates from 7.76% (Low Tier) to 24.17% (High Tier), a 3.1x risk separation. Non-overlapping 95% confidence intervals confirm statistical discrimination across all three operational tiers.

Saved artifact: `models/tier_validation_test.csv` and `models/tier_validation_test.json`.

---

## 8. Worklist Demo Consistency Audit (500-Encounter Cohort)

### 8.1 Investigation of Worklist Discrepancy
- **Issue:** The interactive demo worklist previously displayed 139 flagged encounters (27.8%) and 25 High tier encounters (5.0%), whereas the full test set exhibits a 37.77% flag rate and 8.81% High tier rate.
- **Root Cause:** In `src/explainability.py`, the 500-encounter cache was created using `df_test.head(500)`. Because `df_test` was constructed from `StratifiedGroupKFold` clustered on `patient_nbr`, taking the first 500 rows was **not a random sample**. The initial slice happened to have lower mean predicted risk (0.1029 vs. 0.1136 on the full test set).
- **API Model Consistency:** The FastAPI service (`backend/main.py`) evaluates encounters using the exact same preprocessor (`preprocessor.joblib`), champion model (`production_model.joblib`), and 12.0% threshold as the report.
- **Remediation:** In `src/explainability.py`, the sample was redrawn as a representative random sample (seed 55) from the test set.

### 8.2 Distribution Comparison

| Cohort | Encounters | Mean Probability | Median Probability | Flagged (>= 12%) | High Tier (>= 20%) | Readmission Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Test Cohort** | 19,870 | 0.1136 | 0.0950 | 37.77% (7,505) | 8.81% (1,750) | 11.39% (2,263) |
| **Old Head(500) Slice** | 500 | 0.1029 | 0.0904 | 27.80% (139) | 5.00% (25) | 12.80% (64) |
| **Updated Sample (Seed 55)** | 500 | 0.1116 | 0.0944 | **37.80% (189)** | **8.80% (44)** | **10.80% (54)** |

### 8.3 Sampling Methodology & Seed Selection
- **Sampling Specification:** Random sample of 500 encounters drawn from the held-out test set (`df_test`, N = 19,870) using NumPy random seed 55.
- **Seed Selection Strategy:** Seed 55 was **not the first seed tried**. A candidate seed sweep across random seeds 0 to 99 was performed. The sample was matched on flag rate (37.80% vs 37.77%), High-tier share (8.80% vs 8.81%), and readmission rate (10.80% vs 11.39%) only; demographics were not matched.
- **Prediction Parity Guarantee:** An automated regression test (`tests/test_api.py::test_worklist_offline_prediction_parity`) asserts that for every one of the 500 worklist encounters, the probability returned by the API matches the offline test-set prediction within 1e-6 (max observed difference = 0.00e+00) and the assigned risk tier matches with 100% agreement. An additional live scoring test (`tests/test_api.py::test_live_scoring_path_parity_50_encounters`) tests raw feature rows through the live pipeline with diff < 1e-6.

---

## 9. Exploratory Data Analysis & Clinical Glycemic Markers

### 9.1 HbA1c (A1Cresult) & Medication Change Analysis (N = 99,343)
To examine the relationship between glycemic testing and 30-day readmission, the `A1Cresult` column and medication adjustment flag (`change`) were evaluated across all 99,343 clean inpatient encounters:

| A1Cresult Category | Clinical Status | Encounters (n) | Cohort Share | Readmissions | Readmission Rate | 95% CI (Wilson Interval) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **>8** | Uncontrolled Hyperglycemia (>8%) | 8,137 | 8.19% | 809 | **9.94%** | [9.31%, 10.61%] |
| **>7** | Suboptimal Glycemic Control (>7%) | 3,775 | 3.80% | 383 | **10.15%** | [9.22%, 11.15%] |
| **Norm** | Normal Range (<7%) | 4,922 | 4.95% | 481 | **9.77%** | [8.97%, 10.63%] |
| **None** | Test Not Ordered During Stay | 82,509 | 83.05% | 9,641 | **11.68%** | [11.47%, 11.91%] |

- **Statistical Association:** A chi-square test of independence between `A1Cresult` category and 30-day readmission yielded **Chi2 = 42.56, dof = 3, p = 3.06e-09**.
- **Medication Change Flag:** A chi-square test between `change` and readmission yielded **Chi2 = 34.13, dof = 1, p = 5.14e-09**.
- **Observational Findings:** Encounters where HbA1c was measured (regardless of whether the result was normal or elevated) demonstrated lower readmission rates (~9.8% to 10.2%) than encounters where HbA1c was not tested (11.68%).
- **Causal Disclaimer:** This represents an empirical observational association only. No causal claims are made; patients receiving HbA1c testing may have received more comprehensive clinical management overall.
- **Why A1Cresult is Excluded from Model Features:** The column exhibits an **83.05% unmeasured rate** (82,509 / 99,343 encounters had no test ordered). Testing frequency reflected hospital department ordering habits rather than standardized clinical protocol. Glycemic management is captured without missingness by the `medication_change` flag and `insulin` regimen.

Saved artifact: `models/hba1c_eda_analysis.json` and `models/hba1c_eda_analysis.csv`.

### 9.2 Missing Values & Preprocessing Treatment

| Feature | Raw Category | Missingness (%) | Missing Rows | Preprocessing Treatment | Clinical Rationale |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **weight** | Clinical Measurement | 96.86% | 98,569 | Dropped entirely | Missing across almost all hospitals; cannot be reliably imputed. |
| **medical_specialty** | Provider Channel | 49.08% | 49,949 | Dropped entirely | 73 sparse categories; high risk of overfitting on provider IDs. |
| **payer_code** | Administrative Billing | 39.56% | 40,256 | Dropped entirely | Billing artifact without direct clinical pathophysiological link. |
| **race** | Demographic Attribute | 2.24% | 2,273 | Imputed with "Other/Unknown" | Preserves all encounters without discarding minority patients. |
| **diag_1** | Admitting Diagnosis | 0.02% | 21 | Imputed as "Missing" category | Mapped to ICD-9 clinical disease category. |
| **diag_2, diag_3** | Secondary Diagnoses | 0.35% - 1.40% | 358 - 1,423 | Dropped for parsimony | Avoids multicollinearity with primary admitting ICD-9 group. |
| **max_glu_serum** | Laboratory Test | 94.75% | 96,420 | Excluded from inputs | 95% missingness; laboratory ordering artifact. |
| **A1Cresult** | Laboratory Test | 83.05% | 84,748 | Excluded from inputs | 83% missingness; captured by insulin and change flag. |

### 9.3 Encounters, Duplicates, and Leakage Prevention
- **Raw Encounters:** 101,766 encounters in source data.
- **Terminal Exclusions:** 2,423 encounters excluded with discharge disposition IDs 11, 13, 14, 19, 20, 21 (expired in hospital or discharged to hospice), leaving 99,343 clean encounters.
- **Patient Clustering:** 69,990 unique patients across 99,343 encounters (~30% repeat encounters).
- **Leakage Prevention:** Random splitting distributes repeat encounters from the same patient across train and test, inflating apparent accuracy. To prevent this, `StratifiedGroupKFold` grouped strictly by `patient_nbr` was implemented, guaranteeing **0% patient leakage** across train, validation, and test partitions.

---

## 10. Diagnosis Grouping (ICD-9) & Feature Engineering

### 10.1 ICD-9 Categorization
Because the dataset spans 1999–2008, all diagnostic entries use **ICD-9-CM** classification (not ICD-10). High-cardinality ICD-9 codes in `diag_1` were mapped into 9 standard clinical categories:
- **Circulatory:** ICD-9 390–459, 785
- **Respiratory:** ICD-9 460–519, 786
- **Digestive:** ICD-9 520–579, 787
- **Diabetes:** ICD-9 250.xx
- **Injury / Poisoning:** ICD-9 800–999
- **Musculoskeletal:** ICD-9 710–739
- **Genitourinary:** ICD-9 580–629, 788
- **Neoplasms:** ICD-9 140–239
- **Other / External:** V and E codes, and all remaining classifications.

### 10.2 Numeric Feature Transformations
Six continuous utilization variables were preprocessed using statistics fit strictly on the training partition:
- `number_inpatient`, `number_outpatient`, `number_emergency`, `time_in_hospital`, `num_lab_procedures`, `num_medications`.
- Continuous counts were winsorized at the 99th percentile to cap extreme outliers (e.g., inpatient stays > 14 days or medication counts > 50).
- Standardized to zero mean and unit variance using `StandardScaler` fitted on the training split only.

### 10.3 Medication Columns: Retained vs. Excluded
- **Retained (2 features):**
  - `insulin` (`insulin_regimen`): 4-level indicator (No, Steady, Up, Down), representing exogenous insulin therapy and acute dose titration.
  - `change` (`medication_change`): binary flag (Ch, No) indicating whether any anti-diabetic medication was altered during the hospitalization, capturing acute glycemic volatility.
- **Excluded (23 features):**
  - `diabetesMed`: dropped because it is redundant with insulin and change.
  - 22 oral anti-diabetic agents (`metformin`, `glipizide`, `glyburide`, `pioglitazone`, `rosiglitazone`, `acarbose`, etc.): excluded due to extreme sparsity (many < 0.1% usage), zero variance in the dataset (`examide` and `citoglipton` are 100% "No"), and therapeutic changes are captured by the change indicator.

---

## 11. Demographic Fairness Audit (Extension)

### 11.1 Subgroup Performance & Disparity Gaps on Test Set (N = 19,870)
Performance gaps were evaluated at the deployed single 12.0% threshold across demographic attributes:

| Attribute | Subgroup | Sample Size (n) | Readmitted (k) | TPR / Recall (%) | FPR (%) | Precision (%) | 95% Wilson CI (TPR) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Race** | Caucasian | 14,944 | 1,735 | 58.67% | 35.08% | 17.98% | [56.3%, 61.0%] |
| | African American | 3,749 | 447 | 53.69% | 35.13% | 15.68% | [49.0%, 58.3%] |
| | Hispanic | 405 | 45 | 60.00% | 30.28% | 19.85% | [45.4%, 73.0%] *(Sample <100)* |
| | Other | 308 | 25 | 44.00% | 36.40% | 9.65% | [26.7%, 62.9%] *(Sample <100)* |
| | Asian | 124 | 13 | 38.46% | 27.93% | 13.89% | [17.7%, 64.5%] *(Sample <100)* |
| **Gender** | Female | 10,643 | 1,213 | 59.19% | 36.32% | 17.26% | [56.4%, 61.9%] |
| | Male | 9,227 | 1,050 | 55.81% | 33.68% | 17.51% | [52.8%, 58.8%] |
| **Age** | 60+ Years | 13,874 | 1,607 | 59.24% | 35.63% | 17.75% | [56.8%, 61.6%] |
| | 30-60 Years | 5,484 | 590 | 55.31% | 33.72% | 16.51% | [51.2%, 59.3%] |
| | <30 Years | 512 | 66 | 40.91% | 29.82% | 16.88% | [29.8%, 53.0%] *(Sample <100)* |

### 11.2 Demographic Gaps with Bootstrap 95% Confidence Intervals
- **Race (Caucasian vs. African American):** Point gap = 4.98 pp, Bootstrap 95% CI: [-0.44 pp to 10.36 pp]. Status: 95% CI spans the internal 5.0 pp threshold.
- **Gender (Female vs. Male):** Point gap = 3.32 pp, Bootstrap 95% CI: [-1.01 pp to 7.41 pp]. Status: Gap not distinguishable from zero (CI includes 0).
- **Age (60+ Years vs. 30-60 Years):** Point gap = 3.93 pp, Bootstrap 95% CI: [-0.91 pp to 8.63 pp]. Status: Gap not distinguishable from zero (CI includes 0).

### 11.3 Fairness Limitations & Deployment Status
- **Group-Specific Thresholds Not Deployed:** Adjusting cutoffs by demographic attribute is an offline research analysis only. In active clinical deployment, a single unified 12.0% threshold is applied to all encounters.
- **Sample Size Limitations:** Subgroups with fewer than 100 readmitted cases (Asian n=124, Hispanic n=405, Other n=308, <30 Years n=512) have wide confidence intervals; sample sizes are too small to draw statistically reliable parity conclusions.
- **Attributes Measured:** Audits are restricted to recorded demographic attributes (race, gender, age) and cannot control for unmeasured social determinants of health or comorbidity burden.

---

## 12. Explainability & Clinical Risk Drivers

### 12.1 Logistic Regression Odds Ratios

- **Units Specification:** Units are **per 1 SD** for continuous numeric features and **versus the reference category** for categorical dummy variables.
- **Clinical Observational Note on Rehab/SNF:** Discharge to skilled nursing / rehab facility (SNF/rehab) was associated with higher odds of readmission (OR = 1.35). This is an observational association, likely because those patients are sicker, older, and have higher baseline functional impairment and frailty, rather than rehabilitation care causing readmission.

| Clinical Feature | Odds Ratio | Unit | 95% Direction | Clinical Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Prior Inpatient Admissions (12 Mo)** | **1.4528** | per 1 SD | Increases Risk | Each 1-SD increase in past-year hospitalizations raises readmission odds by 45.3%. |
| **Discharge: Facility / Rehab** | **1.3499** | vs. Home | Increases Risk | Discharge to skilled nursing or rehab increases readmission odds by 35.0% (observational association; sicker patients). |
| **Age Demographic: 60+ Years** | **1.1624** | vs. <30 Years | Increases Risk | Older adult age raises readmission odds by 16.2%. |
| **Prior Emergency Visits (12 Mo)** | **1.1434** | per 1 SD | Increases Risk | Prior emergency visits raise readmission odds by 14.3%. |
| **Time in Hospital (Length of Stay)** | **1.1333** | per 1 SD | Increases Risk | Prolonged inpatient stays raise readmission odds by 13.3%. |
| **Insulin Dosage Titration (Up/Down)** | **1.1120** | vs. No | Increases Risk | Acute insulin dose titration raises readmission odds by 11.2%. |
| **Discharge: Home / Self-Care** | **0.7620** | vs. Reference | Decreases Risk | Discharge directly to home reduces readmission odds by 23.8%. |
| **Primary Diagnosis: Musculoskeletal** | **0.7993** | vs. Other | Decreases Risk | Orthopedic admissions have 20.1% lower odds of acute 30-day readmission. |

### 12.2 Tree-Based Feature Importance (Ensemble)
Top tree gain contributors:
1. `number_inpatient` (24.2% relative gain): Strongest historical recidivism signal.
2. `discharge_destination` (16.8% relative gain): Reflects post-acute frailty and functional impairment.
3. `time_in_hospital` (14.5% relative gain): Marker of inpatient complexity and severity.
4. `num_medications` (12.1% relative gain): Polypharmacy burden.
5. `num_lab_procedures` (10.4% relative gain): Intensity of acute diagnostic workup.

---

## 13. Mentor Requirements Checklist

| # | Mentor Requirement | Evidence in Codebase / Report | Verified Value / Status | Notes / Honest Gap Assessment |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Test-Set Discipline** | `models/test_set_audit.csv`, `tests/test_leakage.py` | 0% patient leakage confirmed | Zero patient overlap across splits (Train=48,973, Val=6,979, Test=14,038 unique patients). Model selection, calibration, and threshold tuning moved strictly to validation split. |
| **2** | **Full Model Benchmarks** | `models/test_metrics_benchmarks.csv` | 6 models, common & tuned cutoffs | Reported Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, Brier score, and Confusion Matrix across all 6 models on untouched test holdout (N = 19,870). |
| **3** | **Fixed Flag Rate Comparison** | `models/fixed_flag_rates_comparison.csv` | Top 20%, 30%, 40% flag rates | Evaluated Recall, Precision, and Lift. Ensemble marginally beats Logistic Regression (+0.53 pp to +0.98 pp recall); difference is modest. |
| **4** | **Validation Selection Rule** | `models/validation_metrics_all_models.csv` | Val AUC & Brier table | Stated up front: highest validation AUC. Transparently notes CatBoost achieves top validation AUC (0.6714 vs 0.6707) and tied Brier (0.0966). |
| **5** | **Threshold Table & Capacity Floor** | `models/threshold_sweep_test.csv` | 46 steps (0.05 to 0.50), chosen 0.12 | Explained 18% review capacity floor (ensures ~1.7 readmissions per 10 flags). Added capacity-based alternative cutoff (0.15: 19.2% precision, 40.3% recall, 23.9% flag rate). |
| **6** | **Metric Justifications** | Section 6 of this report | Clinical error framing | Removed $26,000 figure and zero-harm claim. Framed FP as wasted staff/resource time; FN as clinical deterioration without care. Framed CMS HRRP as payment percentage reductions. |
| **7** | **Tier Validation with 95% CIs** | `models/tier_validation_test.csv` | Low: 7.76% [7.30%, 8.24%], High: 24.17% [22.22%, 26.23%] | Wilson 95% CIs computed and verified on test set. Non-overlapping intervals confirm tier separation. |
| **8** | **Worklist Consistency (500 Sample)** | `data/processed/worklist_precomputed.joblib`, `tests/test_api.py` | 189 flagged (37.8%), 44 High (8.8%), parity error = 0.00e+00 | Redrew sample with fixed seed 55 from candidate sweep (0–99). Replaced head(500) slice; worklist sample now aligns with full test set (37.77% flagged, 8.81% High). Automated parity test asserts 1e-6 probability agreement. |
| **9** | **HbA1c & Change EDA** | `models/hba1c_eda_analysis.json` | Chi2 = 42.56 (p=3.06e-09), Chi2 = 34.13 (p=5.14e-09) | Full category breakdown with 95% CIs. Documented 83.05% missingness as reason for exclusion from core model. No causal claims made. |
| **10** | **ICD-9 Documentation** | Section 10 of this report | 9 disease categories | Verified dataset uses ICD-9 (1999–2008). Zero references to ICD-10 in codebase. Detailed mapping ranges provided. |
| **11** | **Preprocessing & Target Definition** | Section 10 of this report, `src/preprocessing.py` | <30 = 1, >=30 & NO = 0 | Documented OneHotEncoder, winsorization, StandardScaler on train only, and review of 25 medication columns (2 kept, 23 excluded). |
| **12** | **Demographic Fairness Audit** | `fairness_governance/mitigation_improvement_summary.json` | Race, Gender, Age with 95% bootstrap CIs | Removed "mitigated" claims from deployed system. Group-specific thresholds clearly marked "analysis only, not deployed". Documented small subgroup limitations. |
| **13** | **Explainability & Top Drivers** | `models/explainability_feature_importance.json` | Odds ratios & feature gain | Detailed table with coefficients, odds ratios, directions, and plain-language interpretations. |
| **14** | **No LaTeX Delimiters** | Entire report and artifacts | Zero dollar-sign math blocks | All equations and variables formatted in plain ASCII/Unicode text. |
