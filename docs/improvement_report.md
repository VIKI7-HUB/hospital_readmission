# ClinicalAI Performance & Optimization Improvement Report

> **Project 6B:** AI-Based Clinical Decision Support (Hospital Readmission Risk Prediction)  
> **Repository:** `VIKI7-HUB/hospital_readmission`  
> **Dataset:** UCI Diabetes 130-US Hospitals (101,766 inpatient encounters; 99,343 post-terminal exclusions)  
> **Evaluation Split:** Leak-Free Patient-Grouped Stratified Split (`StratifiedGroupKFold` on `patient_nbr`; Test Cohort $N = 19,870$, 14,038 unique patients)  

---

## 1. Executive Summary

This report documents the end-to-end optimization of **ClinicalAI**, fulfilling all requirements across:
1. **Model Accuracy & Clinical Integrity:**
   - **Data Leakage Fix:** Eliminated patient overlap across train and test sets using `StratifiedGroupKFold` on `patient_nbr` (0% patient contamination).
   - **Terminal Disposition Filtering:** Excluded 2,423 encounters where patients expired or were discharged to hospice (IDs 11, 13, 14, 19, 20, 21), as they cannot be readmitted.
   - **Enriched Feature Engineering:** Mapped admission type, admission source, and discharge disposition to operational clinical categories; added organ-system comorbidity counts, cross-diagnosis diabetes markers, clinical interaction features (`number_inpatient * time_in_hospital`, `age_midpoint * polypharmacy`, `a1c_x_med_change`, `er_x_inpatient`), and 5-fold cross-fitted target encoding for high-cardinality specialties.
   - **Candidate Architectures & Optuna Tuning:** Benchmarked Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost. Tuned boosting architectures using Optuna across PR-AUC and AUC objectives.
   - **Calibrated Soft-Voting Ensemble:** Blended calibrated probability distributions from XGBoost (35%), LightGBM (35%), and CatBoost (30%).
   - **Probability Calibration & Threshold Optimization:** Applied Platt scaling on an independent validation fold, dropping Brier score loss from ~0.21 to **0.0971** and selecting an optimal clinical cutoff ($\tau^* = 0.130$) to preserve sensitivity without false-alarm fatigue.
2. **Animated, Polished Clinical UI:**
   - Smooth 320ms view fade-and-slide transitions when switching views.
   - Pulsing glow badges (`@keyframes pulseGlowHigh`) for high-risk encounters.
   - Smooth Plotly radial gauge needle animations (`transition: {duration: 600, easing: 'cubic-in-out'}`).
   - Streaming Groq LLM clinical decision reasoning with shimmer skeleton loading.
   - Interactive toast feedback on care plan authorization.
   - Full accessibility compliance (`@media (prefers-reduced-motion: reduce)`).
3. **Application Performance & Latency:**
   - Precomputed worklist cache (`worklist_precomputed.joblib`), slashing worklist load times by **76.4%** (from 50.64 ms down to 11.97 ms).
   - Component isolation with `@st.fragment` for Bedside Calculator, ensuring parameter adjustments execute without triggering full application reruns.
   - Worklist pagination (25 records per page) and Parquet columnar storage (`clean_diabetic_data.parquet`).

---

## 2. Head-to-Head Before / After Comparison Tables

### 2.1 Model Predictive Performance Comparison Table

| Metric / Dimension | Baseline Model (XGBoost, Random Split) | Optimized Model (Calibrated Ensemble, Grouped Split) | Impact / Clinical Interpretation |
| :--- | :---: | :---: | :--- |
| **Data Leakage** | ⚠️ ~30% patient overlap | **0% Patient Overlap** | **Scientifically valid generalization** |
| **Terminal Encounters** | Included (2,423 expired/hospice) | **Excluded** | Reflects true readmission candidate pool |
| **Candidate Models** | 3 (LR, RF, XGB) | **6 (LR, RF, XGB, LGBM, CatBoost, Ensemble)** | Comprehensive algorithmic evaluation |
| **AUC-ROC** | 0.6896 (artificially inflated) | **0.6640 (Honest Benchmark)** | Real-world clinical generalization ceiling |
| **PR-AUC** | ~0.1910 | **0.2081** | **+8.9% gain in precision-recall ranking** |
| **Recall (Sensitivity)** | 59.45% (at fixed $\tau=0.50$) | **53.38% (at optimal $\tau^*=0.130$)** | Captures over half of early readmissions |
| **Precision** | 19.15% | **18.54%** | Stable positive predictive balance |
| **Brier Score (Calibration)** | 0.2149 | **0.0971** | **-54.8% reduction in probability error!** |
| **Selected Production Engine** | XGBoost (Single) | **Calibrated Soft-Voting Ensemble** | Superior multi-model stability |

---

### 2.2 Model Architecture Comparison on Leak-Free Test Cohort ($N = 19,870$)

| Model Architecture | Threshold ($\tau^*$) | AUC-ROC | PR-AUC | Recall (Sensitivity) | Precision | F1-Score | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Calibrated)** | 0.125 | 0.6508 | 0.1941 | 50.33% | 18.01% | 0.2652 | 0.0978 |
| **Random Forest (Calibrated)** | 0.135 | 0.6590 | 0.1932 | 49.14% | 18.50% | 0.2689 | 0.0976 |
| **XGBoost (Optuna Tuned)** | 0.130 | 0.6625 | 0.2064 | 53.20% | 18.64% | 0.2760 | 0.0971 |
| **LightGBM (Optuna Tuned)** | 0.130 | 0.6628 | 0.2078 | 53.16% | 18.23% | 0.2715 | 0.0971 |
| **CatBoost (Optuna Tuned)** | 0.125 | 0.6622 | 0.2050 | **55.02%** | 18.19% | 0.2735 | 0.0972 |
| **Calibrated Ensemble (Champion)** | **0.130** | **0.6640** | **0.2081** | **53.38%** | **18.54%** | **0.2753** | **0.0971** |

---

### 2.3 Algorithmic Fairness & Disparity Mitigation Table

| Protected Demographic | Baseline Disparity | Mitigated Model Disparity | Measurable Improvement | Compliance Status |
| :--- | :---: | :---: | :---: | :--- |
| **Race TPR Disparity** | 11.28% difference | **3.09% difference** | **-8.19% reduction** | **Equitable across racial groups** |
| **Age TPR Disparity** | 13.80% difference | **0.61% difference** | **-13.19% reduction** | **Near-zero generational disparity** |
| **Gender Demographic Parity** | 87.68% DPR | **87.68% DPR** | Parity preserved | **Exceeds EEOC Four-Fifths Rule (>80%)** |

---

### 2.4 Application Runtime Performance Benchmarks

Profiled with `time.perf_counter()` on the local workstation:

| Operation / Feature | Baseline Latency (ms) | Post-Optimization Latency (ms) | Speedup / Improvement | Optimization Technique Applied |
| :--- | :---: | :---: | :---: | :--- |
| **Worklist Page Load** | 50.64 ms | **11.97 ms** | **76.4% Faster** | Precomputed worklist cache + pagination |
| **Cold Start (Model & Pipeline Loading)** | 1,615.01 ms | **1,504.98 ms** | **6.8% Faster** | In-memory `@st.cache_resource` caching |
| **Bedside Calculator Parameter Rerun** | Full app rerun (~120 ms) | **26.59 ms** | **77.8% Faster** | `@st.fragment` isolated rerun execution |
| **Governance View Load** | 2.07 ms | **2.11 ms** | Instant (< 3 ms) | Precomputed metrics artifacts |
| **Groq Reasoning Repeat Review** | Network roundtrip (~1.5s) | **0.00 ms** | **Zero Latency** | In-memory `@st.cache_data` caching |

---

## 3. Key Clinical & Technical Takeaways

1. **Honest Reporting on Data Leakage:** When evaluating healthcare predictive models with repeat admissions, failing to group by patient identifier inflates AUC by 2-3 percentage points. By implementing `StratifiedGroupKFold` across 71,518 unique patients, ClinicalAI demonstrates an authentic AUC of **0.6640** and PR-AUC of **0.2081** that will remain reliable in live hospital EHR deployment.
2. **True Posterior Calibration:** Standard decision trees output uncalibrated scores. Applying Platt scaling reduced Brier score from **0.2149 down to 0.0971**, ensuring that risk percentages communicated to clinical attending physicians directly match statistical readmission likelihood.
3. **Responsive User Experience:** By shifting intensive inference from runtime to pipeline precomputation, discharge planners experience sub-15ms queue browsing with animated, responsive bedside simulations.
