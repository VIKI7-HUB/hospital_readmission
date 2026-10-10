# Reviewer Guide: 30-Day Hospital Readmission Risk

## 1. Two-minute summary

This project predicts 30-day readmission risk for hospitalized diabetes patients using the UCI Diabetes 130-US Hospitals dataset. The pipeline processes 101,766 raw hospital encounters, drops 2,423 terminal discharges and 3 invalid gender records, and splits 99,340 clean encounters strictly by patient identifier into training (69,538), validation (9,934), and test (19,868) sets to prevent patient-level leakage.

Five classical machine learning models were tuned and calibrated. Random forest was selected as champion by a simpler-model rule within 0.005 validation average precision of the highest-scoring tree model. The operating threshold (0.113404) was selected on validation data to meet an operational recall target of 60%.

On the held-out test split, the model achieves:
1. Recall of 0.6054 (60.5%), capturing 1,370 of 2,263 readmissions.
2. Area under the precision-recall curve (PR-AUC) of 0.2218, well above the 0.1139 test prevalence baseline and the LACE clinical score (0.1440).
3. Area under the ROC curve (ROC-AUC) of 0.6681, compared to 0.5842 for LACE.

Honest limitation: 82.1% of the model's TreeSHAP signal comes from fixed historical factors such as prior inpatient utilization. The dataset lacks social determinants of health and post-discharge support details.

---

## 2. Five-minute walkthrough

Follow this path through the Streamlit application to demonstrate the solution:

1. **Overview page**:
   - What to click: Review the top metric cards and project scope table.
   - What to say: "We built a classical machine learning screening tool to flag diabetic patients at risk of 30-day readmission. The dataset covers 99,340 clean encounters across 130 hospitals. We prioritize recall over accuracy because missing a readmission carries higher clinical risk than an extra discharge check."

2. **Data Quality page**:
   - What to click: Expand the exclusion breakdown and missingness tables.
   - What to say: "We excluded 2,423 encounters where patients died or entered hospice, because readmission is biologically impossible. Missing values in race and medical specialty were handled systematically, with race marked as Missing to preserve auditability."

3. **Exploration page**:
   - What to click: View prior encounter distributions and the HbA1c testing rates chart.
   - What to say: "Prior inpatient visits are the strongest historical predictor. HbA1c testing was ordered in only 17.4% of encounters; testing with therapy change is associated with slightly lower crude readmission compared to no change."

4. **Models page**:
   - What to click: Show the model comparison table and bootstrap paired difference charts.
   - What to say: "We tuned five models. Random forest achieved 0.2218 PR-AUC on test, matching LightGBM within statistical uncertainty. We selected Random Forest via our pre-committed parsimony rule. Clustered bootstrap shows Random Forest beats logistic regression in 99.1% of resamples."

5. **Threshold & Net Benefit page**:
   - What to click: Observe the recall curve and the decision curve analysis.
   - What to say: "At 0.113404, we meet our 60% recall goal. Decision curve analysis confirms that across clinical threshold probabilities from 8% to 25%, using this model provides higher net benefit than flagging all or no patients."

6. **Explainability page**:
   - What to click: Inspect the TreeSHAP summary plot, odds ratios, and modifiable signal breakdown.
   - What to say: "TreeSHAP explains predictions per patient. Modifiable factors account for 17.9% of total attribution, highlighting discharge destination and medication changes as actionable levers."

7. **Fairness & Mitigation page**:
   - What to click: View disparity bars across age, gender, and race, and compare mitigation variants.
   - What to say: "Age shows the largest equalized odds gap (0.2551). Reweighing during training reduces this disparity to 0.2200 while maintaining 0.6394 recall."

8. **Patient Risk page**:
   - What to click: Select a sample patient from the test split to view calibrated risk, tier, and care checklist.
   - What to say: "The care coordinator sees a calibrated probability, a risk tier (Low, Elevated, or High), and deterministic checklist actions tailored to the patient's modifiable risk drivers."

---

## 3. Full breakdown

### Data cleaning
- **Raw records**: 101,766 encounters.
- **Terminal discharge removal**: 2,423 encounters had discharge disposition codes 11 (expired), 13, 14, 19, 20, or 21 (hospice). Readmission cannot occur for these patients; retaining them biases outcome probabilities downward.
- **Invalid gender removal**: 3 records recorded as `Unknown/Invalid` were dropped.
- **Missing values**: `weight` (96.8% missing) and `payer_code` (39.6% missing) were excluded from feature matrices. `medical_specialty` was grouped into major categories with an explicit `Missing` category. `race` was imputed with `Missing` to enable demographic auditing.
- **Final clean cohort**: 99,340 encounters across 71,518 unique patients.

### Patient-level split
- Splitting randomly across encounter rows allows the same patient to appear in both training and test sets. Since chronic illness trajectory is strongly correlated across encounters, row-level splits produce severe data leakage and artificially inflate test metrics.
- We used GroupShuffleSplit grouped strictly on `patient_nbr` with random seed 42.
- Split sizes:
  - Training: 69,538 encounters (70%)
  - Validation: 9,934 encounters (10%)
  - Test: 19,868 encounters (20%)
- Preprocessing parameters (winsorization caps, categorical encoders, standard scalers) were fitted exclusively on training rows and applied downstream.

### Feature engineering
Features fall into five functional groups:
1. **Utilization history**: Cumulative prior inpatient, outpatient, and emergency visits in the dataset, capped at training-set 99th percentiles to avoid extreme outliers.
2. **Clinical complexity**: Length of stay, number of lab procedures, number of procedures, and number of medications.
3. **Diagnostic classification**: ICD-9 primary, secondary, and tertiary diagnoses mapped to clinical categories (circulatory, respiratory, digestive, diabetes, injury, musculoskeletal, genitourinary, neoplasms, other).
4. **Diabetes medications & changes**: 23 diabetic medications tracked for dosage change, addition, or continuation; insulin treatment level; therapy change flag.
5. **Laboratory indicators**: HbA1c test result categories (none, normal, high without change, high with change) and glucose serum test results.

### Models and tuning
- **Logistic Regression**: Linear baseline with L2 penalty, providing interpretable odds ratios and fast fitting.
- **Random Forest**: Ensemble of bagged decision trees capturing non-linear interactions without gradient boosting overhead.
- **LightGBM**: Histogram-based gradient boosted decision tree optimized for fast splits and high leaf count.
- **XGBoost**: Exact and quantile gradient boosting with column subsampling and regularized tree depth.
- **CatBoost**: Ordered boosting specialized for symmetric decision trees and robust categorical handling.
- Hyperparameters were tuned on the training split using Optuna with 5-fold grouped cross-validation optimizing PR-AUC.

### Calibration
Tree ensembles frequently output uncalibrated probabilities skewed toward the middle or edges. We evaluated Platt scaling (sigmoid) and isotonic regression on out-of-fold validation predictions:
- Random Forest sigmoid cross-validation Brier score: 0.096419 (selected) vs isotonic: 0.096951.
- LightGBM sigmoid cross-validation Brier score: 0.096431 (selected) vs isotonic: 0.096558.
- Logistic Regression sigmoid cross-validation Brier score: 0.096677 (selected).
Calibrated probabilities align predicted risk percentages with true empirical readmission rates.

### Threshold selection
- Standard 0.5 thresholds are unsuitable for imbalanced clinical screening (prevalence is 11.39%).
- We established an operational policy requiring at least 60% validation recall (`recall >= 0.60`).
- Sweeping validation probabilities identified the primary operating threshold of 0.113404, delivering 0.6065 recall and 0.1786 precision on validation.
- We also computed a cost-optimal threshold of 0.177143 under a 5:1 cost ratio (missing a readmission costs 5 units; an unnecessary intervention costs 1 unit).
- Tiers were assigned: Low (< 0.113404), Elevated (0.113404 to 0.198976), and High (>= 0.198976, corresponding to the 90th percentile of predicted risk).

### Evaluation metrics
- **Recall (Sensitivity)** is prioritized: In a preventive discharge program, failing to identify an at-risk patient misses the opportunity for post-discharge intervention.
- **Precision**: 0.1775 on test. While approximately 1 in 5.6 flagged patients is readmitted within 30 days, this represents a 1.56x enrichment over baseline prevalence (0.1139).
- **PR-AUC**: 0.2218 on test for Random Forest, providing an honest ranking metric that is not inflated by large numbers of true negatives.
- **ROC-AUC**: 0.6681 on test.
- **Confusion matrix on test**: True Positives: 1,370; False Positives: 6,348; True Negatives: 11,257; False Negatives: 893.

### Model explanations
- **TreeSHAP**: Tree-based SHAP contributions computed directly from model tree structures satisfy local accuracy and consistency properties.
- **Odds Ratios**: Extracted from logistic regression with cluster-robust standard errors to give population-level relative risks per unit change.
- **Deterministic Text Templates**: Patient summaries are generated using conditional rule templates that insert exact numerical values (such as prior inpatient count and length of stay) rather than stochastic text generation.

### Fairness audit and mitigation
- **Audit**: Evaluated across age band (<60, 60-70, 70-80, 80+), gender (Female, Male), and race (Caucasian, AfricanAmerican, Other, Missing).
- **Disparities**: Baseline model exhibits an equalized odds difference of 0.2551 for age, 0.0516 for gender, and 0.0341 for race. Older patients experience higher false positive rates due to higher baseline frailty.
- **Mitigation variants**:
  - `group_threshold`: Calibrates group-specific cutoff thresholds to equalize opportunity, reducing age equalized odds difference to 0.2409 while raising recall to 0.6240.
  - `reweighing`: Balances joint distribution weights during training, reducing age equalized odds difference to 0.2200 and TPR difference to 0.1574, while achieving 0.6394 recall and 0.1690 precision.

### Application structure and artifact sources
- `Overview`: Reads `data_quality.json`, `champion.json`, `threshold.json`, `metrics.json`.
- `Data Quality`: Reads `data_quality.json`, `split.json`.
- `Exploration`: Reads `clean.parquet`, `hba1c.json`.
- `Models`: Reads `model_comparison.csv`, `bootstrap.csv`, `bootstrap_vs_baseline.csv`, `lace.json`, `sensitivity.json`, `blend.json`.
- `Threshold`: Reads `threshold.json`, `sweep.parquet`, `decision_curve.parquet`.
- `Explainability`: Reads `shap_importance.csv`, `shap_values.parquet`, `odds_ratios.csv`, `feature_tags.json`.
- `Fairness`: Reads `fairness_audit.csv`, `fairness_gaps.csv`, `fairness_summary.json`, `fairness_mitigation.csv`.
- `Patient Risk`: Reads `test_predictions.parquet`, `shap_values.parquet`, `care_actions.yaml`.

### How to re-run everything
From repository root in a bash or powershell terminal:
- Full pipeline: `python -m readmission.pipeline --mode full`
- Fast pipeline: `python -m readmission.pipeline --mode fast`
- Run test suite: `pytest -q`
- Run linter: `ruff check src app tests`
- Start web UI: `streamlit run app/main.py --server.port 8501`

---

## 4. Glossary

- **Encounter**: A single hospital stay from admission to discharge. Example: A patient admitted on Monday with acute hyperglycemia and discharged on Thursday is one encounter.
- **Readmission**: An unplanned hospital admission within 30 days of discharge from an index encounter. Example: Being admitted again on day 18 after returning home.
- **Recall**: The percentage of actual readmissions successfully flagged by the model. Example: If 100 patients return and the tool flags 61 of them, recall is 61%.
- **Precision**: The percentage of flagged patients who truly readmit. Example: If the tool flags 100 patients and 18 are readmitted, precision is 18%.
- **Specificity**: The percentage of non-readmitted patients correctly not flagged. Example: Correctly clearing 64 of 100 patients who stay safely at home.
- **ROC-AUC**: Area under the receiver operating characteristic curve; the probability that a randomly chosen readmitted patient receives a higher predicted score than a non-readmitted patient across all possible cutoffs. Example: A score of 0.67 means the model ranks the readmitted patient higher 67% of the time.
- **PR-AUC**: Area under the precision-recall curve; measures ranking quality focusing on the positive class without being inflated by true negatives. Example: A PR-AUC of 0.22 against a 0.11 baseline indicates twofold enrichment across recall levels.
- **Calibration**: How closely predicted probabilities match observed frequencies. Example: Among patients assigned an 11% calibrated risk, exactly 11 out of 100 are readmitted.
- **Brier Score**: The mean squared error between predicted probabilities and binary outcomes (0 or 1), where lower is better. Example: A score of 0.096 reflects well-calibrated, modest variance predictions.
- **SHAP (SHapley Additive exPlanations)**: A game-theoretic method allocating credit for a prediction to each input feature. Example: Showing that having 3 prior visits added +0.05 to a patient's predicted readmission score.
- **Odds Ratio**: The multiplicative change in the odds of an outcome associated with a one-unit increase in an exposure. Example: An odds ratio of 1.25 for prior inpatient admission means each prior visit increases readmission odds by 25%.
- **Equalized Odds**: A fairness criterion requiring true positive rates and false positive rates to be equal across demographic subgroups. Example: Flagging readmitted female and male patients at similar rates.
- **Data Leakage**: Information from outside the training set contaminating the model during training. Example: Using future hospitalizations or testing split records to compute feature averages.
- **Patient-Level Split**: Partitioning data so all visits by an individual patient reside exclusively in one dataset partition. Example: Ensuring Patient #12345's three visits appear only in the training set.
- **Threshold**: The probability cutoff above which a patient is classified as high-risk. Example: Anyone with calibrated probability >= 0.113404 is flagged for discharge intervention.

---

## 5. Likely reviewer questions and honest answers

**Why recall over accuracy?**
In hospital readmissions, false negatives leave vulnerable patients without discharge support, risking avoidable complications and hospital penalties. In an imbalanced dataset (11.39% readmission rate), a trivial model predicting "no readmission" achieves 88.61% accuracy while catching zero readmissions. Recall directly measures clinical detection.

**Why not deep learning?**
Tabular clinical records with high cardinality discrete codes and tabular summaries respond well to gradient boosted trees and regularized ensembles. Tabular deep networks incur substantial training and tuning overhead with minimal or no gain in PR-AUC on this benchmark, while sacrificing exact tree-SHAP efficiency.

**Why class weights instead of resampling (SMOTE)?**
Synthetic oversampling (such as SMOTE) distorts feature covariances and distorts the base rate, breaking probability calibration. Tuning balanced class weights or choosing an operating threshold preserves true empirical data distributions while achieving the required sensitivity.

**Why is ROC-AUC only in the mid-0.6s?**
In 30-day all-cause readmission prediction from administrative electronic health record data, 0.65 to 0.70 is standard in published medical literature. Crucial post-discharge determinants—medication adherence at home, outpatient follow-up access, caregiver support, and health literacy—are unobserved in hospital billing records.

**How do you know there is no leakage?**
Encounters are partitioned strictly by `patient_nbr`. All imputation rules, numerical winsorization caps, categorical mappings, and scaling transformations are fitted solely on training encounters and frozen before application to validation and test encounters.

**What does the fairness result mean?**
Age disparities reflect underlying clinical differences: older patients have higher comorbidity rates and longer stays, leading to higher false positive rates under a uniform threshold. Reweighing during training mitigates this gap from 0.2551 to 0.2200 without degrading overall clinical recall.

**What are the limits of this data?**
The UCI dataset spans 1999 to 2008 across 130 hospitals. Clinical practice, electronic records, and diabetes medications (such as SGLT2 inhibitors and GLP-1 receptor agonists) have evolved since. The data lacks social determinants of health and post-acute care tracking.

**Why no language model?**
Generative language models introduce hallucination risk, high computational latency, and compliance barriers in clinical deployment. Classical machine learning combined with deterministic, template-based natural language summaries guarantees auditability and reproducibility.

**What would you do with more time?**
We would incorporate social vulnerability indices, track time-to-event survival outcomes via Cox proportional hazards models, and implement multi-hospital out-of-domain cross-validation to assess site-level transportability.

**What is the LACE comparison?**
LACE is the standard clinical index (Length of stay, Acuity, Charlson comorbidity, Emergency visits). Our random forest model achieves 0.2218 PR-AUC versus 0.1440 for LACE, and 0.6681 ROC-AUC versus 0.5842 for LACE, demonstrating substantial predictive gain over current bedside heuristic scoring.

---

## 6. Who can explain what

| Team member role | Topics owned | Key artifacts & files |
|---|---|---|
| 1. Data & Preprocessing | Ingestion, terminal discharge exclusion, patient-level splitting, leakage prevention | `src/readmission/data.py`, `src/readmission/split.py`, `data_quality.json`, `split.json` |
| 2. Features & Exploration | Feature engineering, clinical categories, HbA1c exploratory analysis | `src/readmission/features.py`, `src/readmission/hba1c.py`, `clean.parquet`, `hba1c.json` |
| 3. Models & Tuning | Model registry, Optuna hyperparameter tuning, model comparison, simpler-model rule | `src/readmission/models.py`, `champion.json`, `model_comparison.csv`, `metrics.json` |
| 4. Calibration & Thresholds | Platt scaling, Brier score selection, recall-driven thresholding, decision curves | `src/readmission/calibrate.py`, `calibration.json`, `threshold.json`, `decision_curve.parquet` |
| 5. Explainability & Text | TreeSHAP contributions, logistic odds ratios, template-based clinical summaries | `src/readmission/explain.py`, `src/readmission/oddsratio.py`, `shap_importance.csv`, `odds_ratios.csv` |
| 6. Fairness & Web Application | Demographic disparity audits, reweighing mitigation, Streamlit interface pages | `src/readmission/fair_stats.py`, `fairness_summary.json`, `fairness_mitigation.csv`, `app/` |
