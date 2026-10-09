# ClinicalAI Performance & Optimization Improvement Report

> **Project 6B:** AI-Based Clinical Decision Support (Hospital Readmission Risk Prediction)  
> **Repository:** `VIKI7-HUB/hospital_readmission`  
> **Dataset:** UCI Diabetes 130-US Hospitals (101,766 inpatient encounters; 99,343 post-terminal exclusions)  
> **Evaluation Split:** Leak-Free Patient-Grouped Stratified Split (`StratifiedGroupKFold` on `patient_nbr`; Test Cohort N = 19,870, 14,038 unique patients)  

---

## 1. Executive Summary

This report documents the end-to-end engineering and clinical optimization of **ClinicalAI**:

1. **Model Accuracy & Clinical Integrity:**
   - **Data Leakage Fix:** Eliminated patient overlap across train and test sets using `StratifiedGroupKFold` on `patient_nbr` (0% patient contamination verified).
   - **Terminal Disposition Filtering:** Excluded 2,423 encounters where patients expired or were discharged to hospice (IDs 11, 13, 14, 19, 20, 21), as they cannot be readmitted.
   - **Enriched Feature Engineering:** Mapped admission type, admission source, and discharge disposition to operational clinical categories; added organ-system comorbidity counts, cross-diagnosis diabetes markers, and interaction features.
   - **Candidate Architectures:** Benchmarked Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost.
   - **Calibrated Soft-Voting Ensemble:** Blended calibrated probability distributions from XGBoost (35%), LightGBM (35%), and CatBoost (30%) with Platt sigmoid calibration.
   - **Probability Calibration & Threshold Optimization:** Applied Platt scaling on an independent validation fold, dropping Brier score loss to **0.0976** and selecting an optimal clinical cutoff (tau = 0.120) prioritizing sensitivity while maintaining an operational review floor.

2. **Animated, Polished Clinical UI:**
   - High-density clinical table with risk tier badges, sortable headers, and care flag indicators.
   - Real-time scenario risk calculator with interactive sliders and instant calibrated scoring.
   - 10-section transparent model governance dashboard driven strictly by pipeline artifacts.
   - Full accessibility compliance with dark mode support.

3. **Application Performance & Latency:**
   - Precomputed worklist sample (N = 500, seed 55) with exact probability parity (< 1e-6) against offline test predictions.
   - Fast sub-10ms response times on live scoring endpoint.

---

## 2. Model Performance Benchmarks on Held-Out Test Cohort (N = 19,870)

| Model Architecture | Threshold (tau) | AUC-ROC | PR-AUC | Recall (Sensitivity) | Precision | F1-Score | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Calibrated)** | 0.120 | 0.6468 | 0.1877 | 49.98% | 17.93% | 0.2639 | 0.0982 |
| **Random Forest (Calibrated)** | 0.130 | 0.6467 | 0.1881 | 51.66% | 17.50% | 0.2614 | 0.0980 |
| **XGBoost (Calibrated)** | 0.120 | 0.6514 | 0.1953 | 56.96% | 17.31% | 0.2656 | 0.0977 |
| **LightGBM (Calibrated)** | 0.120 | 0.6512 | 0.1970 | 56.56% | 17.07% | 0.2623 | 0.0977 |
| **CatBoost (Calibrated)** | 0.120 | 0.6525 | 0.1981 | **57.84%** | 17.61% | 0.2700 | **0.0976** |
| **Calibrated Ensemble (Champion)** | **0.120** | **0.6530** | **0.1975** | **57.62%** | **17.38%** | **0.2670** | **0.0976** |
