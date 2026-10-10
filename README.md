# Hospital readmission risk (diabetes, 130 US hospitals)

This system predicts the risk of 30-day all-cause hospital readmission for diabetic patients at the time of discharge. It provides clinical decision support for hospital discharge planners and case managers prioritizing post-discharge care coordination.

## Problem

Unplanned 30-day hospital readmissions are frequent, costly, and often preventable complications of diabetes care. Hospital clinical teams have limited outreach capacity and cannot contact every discharged patient personally. This model ranks patients by predicted readmission risk so that transitional care programs and follow-up resources reach the individuals most likely to benefit.

## Data

The dataset comes from the UCI Machine Learning Repository: Diabetes 130-US Hospitals for Years 1999-2008. After quality filters, the clean dataset contains 99,340 inpatient encounters across 69,987 unique patients, with 16,341 patients having multiple encounters. The prediction target is binary readmission within 30 days of discharge (`readmit_30`), with a positive class prevalence of 11.39% (11,314 readmissions). For full citations and licensing details, see [docs/references.md](docs/references.md).

## Method

1. Data cleaning: Excluded deceased patients, hospice discharges, and invalid records as detailed in [docs/data_quality.md](docs/data_quality.md).
2. Patient-level split: Partitioned data into 70% training (69,535 encounters), 10% validation (9,935 encounters), and 20% test (19,870 encounters) grouped strictly by patient identifier to eliminate patient overlap.
3. Feature engineering: Constructed 28 model features including prior utilization counts, medication changes, ICD-9 diagnosis categories, and continuous features capped at the 99th percentile of the training split.
4. Model training and tuning: Trained logistic regression, random forest, LightGBM, XGBoost, and CatBoost models using balanced class weighting.
5. Probability calibration: Calibrated model probabilities using Platt sigmoid scaling fitted on validation predictions.
6. Operating threshold rule: Selected the classification threshold on validation data to achieve a clinical recall target of at least 60%.
7. Explanations: Computed local and global feature attributions via TreeSHAP and patient-clustered odds ratios.
8. Fairness audit: Evaluated demographic parity, equalized odds, and calibration across age, gender, and racial subgroups.

## Results

| model | threshold | accuracy | precision | recall | roc_auc | pr_auc | brier |
|---|---|---|---|---|---|---|---|
| logistic_regression | 0.108 | 0.632 | 0.175 | 0.598 | 0.663 | 0.213 | 0.097 |
| random_forest | 0.113 | 0.636 | 0.178 | 0.605 | 0.668 | 0.222 | 0.096 |
| lightgbm | 0.115 | 0.632 | 0.177 | 0.612 | 0.670 | 0.222 | 0.096 |
| xgboost | 0.096 | 0.438 | 0.139 | 0.757 | 0.627 | 0.183 | 0.098 |
| catboost | 0.120 | 0.574 | 0.162 | 0.660 | 0.656 | 0.199 | 0.097 |

The champion model is random_forest, selected under the simpler-model hierarchy within 0.005 of peak validation average precision. At its validation-selected threshold of 0.113, it achieved a test recall of 60.5% and a precision of 17.8% on the held-out test cohort.

## Run it

Install dependencies:
```bash
make install
```

Run the pipeline:
```bash
make pipeline
```

Launch the Streamlit clinical decision support application:
```bash
make app
```

All evaluation artifacts are committed in `artifacts/`, so running `make app` starts the full application without needing to re-run the pipeline or download the raw data.

## Repository layout

- `.streamlit/`: Streamlit configuration and theme tokens.
- `app/`: Multi-page clinical decision support user interface.
- `app/pages/`: Seven clinical application pages.
- `artifacts/`: Exported model binaries, metric JSON files, and evaluation tables.
- `configs/`: Pipeline, feature, and care action configuration files.
- `data/`: Data directory and raw data download instructions.
- `docs/`: Methodological reports, decisions log, model card, and references.
- `src/readmission/`: Preprocessing, feature engineering, modeling, and evaluation source code.
- `tests/`: Automated unit, integration, and UI regression tests.

## KPI map

| Metric / KPI | Value | Application location |
|---|---|---|
| Clean cohort volume | 99,340 encounters, 69,987 patients | Overview, Data quality |
| Baseline readmission rate | 11.4% (11,314 events) | Overview, Data quality, Exploration |
| Test recall | 60.5% | Overview, Models, Threshold |
| Test precision | 17.8% | Overview, Models, Threshold |
| ROC-AUC / PR-AUC | 0.668 / 0.222 | Overview, Models |
| Calibration Brier score | 0.096 | Overview, Models |
| Race equalized odds disparity | 0.034 | Overview, Fairness |
| Gender equalized odds disparity | 0.052 | Overview, Fairness |
| Age equalized odds disparity | 0.255 | Overview, Fairness |
| Patient risk estimate and SHAP | Individual score | Patient risk |

## Limitations

1. Single data source collected from 130 hospitals between 1999 and 2008; clinical standards and available medications have changed since collection.
2. Readmissions are only captured if they occurred within the same participating health system.
3. Multiple admissions per patient are present (23.3% of patients had more than one encounter), requiring patient-level split controls.
4. Discrimination is modest (ROC-AUC 0.668), reflecting the influence of social and post-discharge factors not recorded in inpatient encounter data.
5. Cost curve calculations rely on illustrative operational ratios, not observed institutional costs.
6. Group-specific threshold mitigation requires observing protected demographic attributes during patient care, so it is presented only as an analytical baseline.

## References

For full dataset citations, primary publication references, and licensing details, see [docs/references.md](docs/references.md).
