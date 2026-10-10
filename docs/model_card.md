# Model Card: 30-Day Hospital Readmission Risk

## Intended Use
- Purpose: Clinical decision support tool to rank diabetic inpatients nearing discharge according to their 30-day readmission risk. Intended to guide transitional care follow-up and discharge planning.
- Not intended for: Diagnosis, prognostic scoring of non-diabetic conditions, automated treatment orders, or denial of care.

## Training and Evaluation Data
- Source: UCI Diabetes 130-US Hospitals (1999-2008).
- Size: 99,340 clean encounters across 69,987 unique patients.
- Splits: Patient-grouped split with 70% train (69,535 encounters), 10% validation (9,935 encounters), and 20% test (19,870 encounters). Zero patient overlap across splits.
- Outcome: Binary readmission within 30 days of discharge (prevalence: 11.39%).

## Model Architectures Compared
Five candidate architectures were evaluated:
1. Logistic Regression (L2 regularized)
2. Random Forest (balanced class weighting, max depth 12)
3. LightGBM (gradient boosted trees)
4. XGBoost (gradient boosted trees)
5. CatBoost (symmetric decision trees)

## Champion Selection
- Champion model: Random Forest.
- Selection rationale: Under the simpler-model selection hierarchy, Random Forest was selected because its validation PR-AUC (0.2259) is within 0.005 of the highest-scoring model (0.2273). Random Forest provides stable probability estimates, fast inference, and direct compatibility with TreeSHAP explanations.

## Threshold Selection and Calibration
- Calibration method: Sigmoid Platt scaling fit on the validation split (cross-validated Brier score: 0.0964).
- Operating threshold: 0.113, selected on validation data to achieve a target recall of at least 60% (validation recall: 60.7%, precision: 17.9%).

## Test Evaluation Metrics
All models evaluated once on the untouched test split (N = 19,870 encounters):

| Model | Threshold | Accuracy | Precision | Recall | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.108 | 0.632 | 0.175 | 0.598 | 0.663 | 0.213 | 0.097 |
| random_forest | 0.113 | 0.636 | 0.178 | 0.605 | 0.668 | 0.222 | 0.096 |
| lightgbm | 0.115 | 0.632 | 0.177 | 0.612 | 0.670 | 0.222 | 0.096 |
| xgboost | 0.096 | 0.438 | 0.139 | 0.757 | 0.627 | 0.183 | 0.098 |
| catboost | 0.120 | 0.574 | 0.162 | 0.660 | 0.656 | 0.199 | 0.097 |

## Fairness Evaluation and Mitigation
Audited across age bands, gender, and racial subgroups on the held-out test split:
- Demographic parity differences: age band 0.241, gender 0.041, race 0.003.
- Equalized odds differences:
  - Age band: 0.2551 (base) vs 0.2409 (group threshold)
  - Gender: 0.0516 (base) vs 0.0228 (group threshold)
  - Race: 0.0341 (base) vs 0.0222 (group threshold)
Group-specific thresholds are recorded as an analytical comparison only. The deployed application uses the single uniform threshold (0.113).

## Limitations
1. Single data source collected between 1999 and 2008; practice patterns and medications have evolved.
2. Readmissions are only tracked if the patient returned to one of the 130 participating hospitals.
3. Modest overall discrimination (ROC-AUC 0.668, PR-AUC 0.222), reflecting the multifactorial nature of hospital readmissions.
4. Operational cost assumptions are hypothetical planning values, not accounting costs.

## Prohibited Uses
- Automated denial of admission, coverage, or care.
- Use outside adult diabetes inpatient admissions.
- Use without clinical oversight by discharge planners or physicians.
