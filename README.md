# Hospital readmission risk model

## Summary
This project predicts 30-day unplanned readmission risk for hospitalized diabetes patients using electronic health record data. It flags high-risk patients at discharge to support clinical care coordination and preventive post-discharge planning.

## Data
The dataset is the UCI "Diabetes 130-US hospitals for years 1999-2008" dataset:
https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008

Citation:
Strack, B., DeShazo, J. P., Gennings, C., Olmo, J. L., Ventura, S., Cios, K. J., and Clore, J. N. (2014). Impact of HbA1c Measurement on Hospital Readmission Rates: Analysis of 70,000 Clinical Database Patient Records. BioMed Research International, vol. 2014, Article ID 781670.

## Method
1. Cleaning: Exclude terminal discharges (hospice and expired patients, where readmission cannot occur) and invalid records.
2. Patient-level split: Partition data into 70% train, 10% validation, and 20% test splits grouped strictly by patient identifier to prevent data leakage.
3. Feature set: Inpatient utilization history, clinical stay metrics, diagnostic ICD-9 categories, diabetes medications, and laboratory tests. Preprocessing caps and encoders are fit on the training split only.
4. Five models: Train Logistic Regression, Random Forest, LightGBM, XGBoost, and CatBoost.
5. Tuning: Optimize hyperparameters on the training split using Optuna with 5-fold grouped cross-validation targeting PR-AUC.
6. Calibration: Fit Platt sigmoid calibrators on validation predictions to output true empirical probabilities.
7. Operating threshold: Choose a decision threshold on the validation split targeting at least 60% clinical recall.
8. Explanations: Compute exact TreeSHAP feature contributions and cluster-robust logistic odds ratios, rendered through deterministic templates.
9. Fairness audit: Audit demographic parity and equalized odds across age, gender, and race, and evaluate mitigation variants.

## Results
| model | threshold | accuracy | precision | recall | roc_auc | pr_auc | brier |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.108 | 0.632 | 0.175 | 0.598 | 0.663 | 0.213 | 0.097 |
| random_forest | 0.113 | 0.636 | 0.178 | 0.605 | 0.668 | 0.222 | 0.096 |
| lightgbm | 0.115 | 0.632 | 0.177 | 0.612 | 0.670 | 0.222 | 0.096 |
| xgboost | 0.096 | 0.438 | 0.139 | 0.757 | 0.627 | 0.183 | 0.098 |
| catboost | 0.120 | 0.574 | 0.162 | 0.660 | 0.656 | 0.199 | 0.097 |

The champion model is random_forest with a test recall of 0.605 and test precision of 0.178.

## Run it
```bash
make install
make pipeline
make app
```
The committed artifacts in artifacts/ let make app run directly without requiring the raw data files.

## Layout
- app/: Streamlit application pages and user interface components
- artifacts/: Fitted model pipelines, calibration objects, and evaluation metrics
- configs/: Pipeline configuration settings and care intervention rules
- data/: Raw data location instructions and expected file schema
- src/readmission/: Data processing, model training, scoring, and fairness routines
- tests/: Automated unit and integration test suite

## Limitations
The dataset originates from a single historical multi-hospital EHR system collected between 1999 and 2008, which may not reflect contemporary clinical practices or modern diabetes medication regimens. Tabular discrimination on 30-day all-cause readmissions is inherently modest because post-discharge social determinants of health and outpatient adherence are unmeasured. Patients may have repeated encounters over time, requiring patient-level clustering. Misclassification cost curves rely on assumed economic cost ratios. Group-specific threshold mitigation requires observing protected demographic attributes at inference time.
