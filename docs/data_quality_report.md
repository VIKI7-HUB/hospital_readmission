# Data Quality & Preprocessing Rationale Report

> **Project 6B:** AI-Based Predictive Analytics for Clinical Decision-Making (Hospital Readmission Risk Prediction)  
> **Dataset:** UCI Diabetes 130-US Hospitals (1999–2008), ~101,766 inpatient encounters across multiple US health systems.  
> **Target:** 30-Day Inpatient Readmission (`readmitted == '<30'`).  
> **Compliance:** Fulfills **KPI 5: Documented data-quality handling: missing values, outliers, and feature-selection decisions.**

---

## 1. Executive Summary & Clinical Context

In clinical predictive modeling, electronic health record (EHR) data presents unique challenges: high missingness, extreme outliers due to healthcare utilization skew, high-cardinality diagnosis codes, and administrative noise. Under Value-Based Care and CMS Hospital Readmissions Reduction Program (HRRP) penalties, predictive models must balance data integrity with clinical validity.

This document details all data cleaning, outlier mitigation, encoding, and feature engineering transformations performed in `src/preprocessing.py`, providing clear statistical and clinical justifications.

---

## 2. Missing-Value Handling Strategy

### 2.1 Missingness Audit
In the raw UCI diabetic dataset, missing values were recorded primarily as the string `'?'`. Across 101,766 encounters, the missingness distribution is as follows:

| Column | Data Type | Missing Count | Missing % | Action Taken | Clinical & Analytical Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `weight` | Categorical | 98,569 | 96.86% | **Dropped** | Over 96% missingness across participating hospitals. Imputing would introduce severe artificial noise; weight tracking was inconsistently documented during 1999–2008. |
| `medical_specialty` | Categorical | 49,949 | 49.08% | **Imputed as 'Missing'** | Represents the admitting physician's specialty. The absence of documentation is clinically informative (often indicating general admission or urgent triage). Retained as an explicit categorical level. |
| `payer_code` | Categorical | 40,256 | 39.56% | **Imputed as 'Missing'** | Health insurance classification (Medicare, Medicaid, Private, Self-Pay). Missingness correlates with self-pay/uninsured status or administrative variations; preserved as a distinct category. |
| `race` | Categorical | 2,273 | 2.23% | **Imputed as 'Other/Missing'** | Critical demographic feature for algorithmic fairness auditing. Rather than dropping encounters (which would introduce selection bias), encounters are grouped under `'Other/Missing'`. |
| `diag_1` | Categorical | 21 | 0.02% | **Imputed as 'Missing' -> 'Other'** | Primary ICD-9 discharge diagnosis. Negligible missingness; mapped to 'Other' ICD-9 category. |
| `diag_2` | Categorical | 358 | 0.35% | **Imputed as 'Missing' -> 'Other'** | Secondary ICD-9 diagnosis. Mapped to 'Other' category. |
| `diag_3` | Categorical | 1,423 | 1.40% | **Imputed as 'Missing' -> 'Other'** | Tertiary ICD-9 diagnosis. Mapped to 'Other' category. |

### 2.2 Pipeline Imputation Architecture
- **Numerical Features:** Imputed using **Median** strategy (`SimpleImputer(strategy='median')`), ensuring robustness against skewed medical count variables.
- **Categorical Features:** Imputed using **Constant** strategy (`SimpleImputer(strategy='constant', fill_value='Missing')`), ensuring missingness is tracked as an explicit signal rather than discarded.

---

## 3. Outlier Mitigation & Distribution Handling

### 3.1 Skewed Healthcare Utilization Metrics
Healthcare utilization metrics (prior emergency visits, outpatient encounters, and inpatient hospitalizations) follow heavy-tailed Pareto distributions. A small cohort of high-utilizers displays extreme counts (e.g., >60 visits), which would distort gradient calculations in linear models and destabilize leaf splits.

### 3.2 99th-Percentile Winsorization
Rather than truncating records (which would discard critical high-risk patients), a **99th-percentile right-sided Winsorization (capping)** was implemented for utilization variables:

| Metric | Raw Min | Raw Max | 99th Percentile Cap | Post-Cap Max | Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `number_inpatient` | 0 | 21 | **6.0** | 6.0 | Differentiates frequent admissions from extreme recording anomalies while retaining high-risk signal. |
| `number_emergency` | 0 | 76 | **4.0** | 4.0 | Captures high acute emergency utilization without allowing extreme outliers (76 visits) to dominate loss functions. |
| `number_outpatient` | 0 | 42 | **5.0** | 5.0 | Normalizes outpatient frequency; values above 5 represent continuous chronic care. |
| `total_visits` | 0 | 90 | **10.0** | 10.0 | Composite utilization cap preventing extreme leverage points. |

---

## 4. Clinical Feature Engineering Rationale

| Engineered Feature | Definition / Formula | Clinical Rationale & Impact |
| :--- | :--- | :--- |
| `total_visits` | `number_outpatient + number_emergency + number_inpatient` | Quantifies total patient interaction with the healthcare system in the preceding 12 months. Primary proxy for overall health frailty. |
| `high_prior_utilization` | Binary indicator: `(number_inpatient > 0) OR (number_emergency > 0)` | Captures whether the patient has acute prior medical crises versus scheduled elective care. |
| `polypharmacy` | Binary indicator: `num_medications >= 10` | Standard clinical geriatrics threshold. Diabetic patients taking ≥10 concurrent medications exhibit significantly elevated rates of adverse drug reactions, drug-drug interactions, and readmissions. |
| `num_med_changes` | Sum of all medications with dosage status `'Up'` or `'Down'` | Titration marker. Distinct medication modifications during hospital stay reflect glycemic instability or acute therapeutic adjustment, elevating post-discharge vulnerability (79% of the sample has 10 or more distinct medications administered during stay). |
| `num_active_meds` | Sum of all medications with status `'Steady'`, `'Up'`, or `'Down'` | Directly measures diabetic treatment regimen complexity across 23 antidiabetic agents. |
| `lab_intensity_per_day` | `num_lab_procedures / (time_in_hospital + 0.1)` | Measures clinical acuity. A patient receiving 50 lab tests over 2 days (25/day) is in acute crisis compared to a patient receiving 50 tests over 10 days (5/day). |
| `diag_1_cat`, `diag_2_cat`, `diag_3_cat` | Clinical ICD-9 grouping into 9 organ system categories | Reduces >700 raw ICD-9 codes into 9 pathophysiological clusters: Circulatory, Respiratory, Digestive, Diabetes, Injury, Musculoskeletal, Genitourinary, Neoplasms, Other. Prevents dimensionality explosion while preserving clinical etiology. |
| `age_group` | Categorical binned into `'<30 Years'`, `'30-60 Years'`, `'60+ Years'` | Harmonizes age brackets for demographic disparity evaluation and clinical risk grouping. |

---

## 5. Feature Selection & Exclusion Decisions

The following features were explicitly dropped with documented rationale:

1. **`encounter_id`, `patient_nbr`**: Unique administrative identifiers. Dropped to prevent data leakage and memorization.
2. **`weight`**: Dropped due to 96.86% missingness (non-recoverable without synthetic imputation bias).
3. **`readmitted`**: Original multi-class string column (`'<30'`, `'>30'`, `'NO'`). Transformed into binary target `target = (readmitted == '<30')` and dropped from feature matrix $X$.
4. **`examide`, `citogliptin`**: Dropped because these medications had zero variance (all records recorded as `'No'` across the entire 101,766 cohort). Constant columns provide zero mutual information.
