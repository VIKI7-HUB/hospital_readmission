# Data quality and cleaning

## Overview
The raw UCI Diabetes dataset contains 101,766 inpatient encounters across 50 columns. After data quality filters, the clean dataset contains 99,340 encounters across 69,987 unique patients.

## Exclusions and removals
Rows were excluded based on clinical validity:
- Invalid gender: 3 encounters with missing or invalid gender recorded.
- Terminal discharge: 2,423 encounters where the patient died or was transferred to hospice care (discharge disposition IDs 11, 13, 14, 19, 20, 21), because 30-day readmission is not possible.
- Exact duplicates: 0 rows.

## Target definition
The target is binary readmission within 30 days (`readmitted == '<30'`).
- Raw positive class share: 11.16% (11,357 encounters).
- Clean positive class share: 11.39% (11,314 encounters).

## Missing-value policy
- `weight`: Dropped entirely due to 96.86% missing values.
- `payer_code`: 39.56% missing; mapped to explicit "Unknown" level and grouped into broad payer categories (Medicare, Medicaid, Self-pay, Commercial/Other, Unknown).
- `medical_specialty`: 49.08% missing; the 10 most frequent non-missing specialties in the training split were preserved; remaining specialties were mapped to "Other"; missing entries were retained as "Unknown".
- `race`: 2.23% missing; retained as explicit "Unknown" category.
- `diag_1`, `diag_2`, `diag_3`: Categorized into broad ICD-9 clinical chapters (circulatory, respiratory, digestive, diabetes, injury, musculoskeletal, genitourinary, neoplasms, other). Missing values and supplementary V/E codes are grouped into "other".
- Diabetes medications: Missing medication entries are filled with "No".

## Outlier capping policy
Extreme numeric values are capped using the 99th percentile computed strictly on the training split to prevent leakage. Training caps applied:
- `time_in_hospital`: 13.0 days
- `num_lab_procedures`: 84.0
- `num_procedures`: 6.0
- `num_medications`: 43.0
- `number_outpatient`: 5.0 visits
- `number_emergency`: 3.0 visits
- `number_inpatient`: 6.0 visits
- `number_diagnoses`: 9.0
