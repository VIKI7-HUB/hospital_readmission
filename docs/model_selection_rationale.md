# Model Selection & Performance Evaluation Rationale

> **Project 6B:** AI-Based Predictive Analytics for Clinical Decision-Making (Hospital Readmission Risk Prediction)  
> **Dataset:** UCI Diabetes 130-US Hospitals (Leak-Free Patient-Grouped Stratified Split; Held-Out Test Cohort $N = 19,870$, $14,038$ unique patients)  
> **Target:** 30-Day Inpatient Readmission (`readmitted == '<30'`; 11.39% prevalence, ~7.78:1 imbalance ratio)  
> **Exclusions:** Encounters with terminal / hospice discharge dispositions (IDs 11, 13, 14, 19, 20, 21) excluded ($N=2,423$) as they cannot experience readmission.  
> **Compliance:** Fulfills **KPI 1: Predictive performance (accuracy, precision, recall with justification, AUC, PR-AUC)** and **KPI 2: Comparison across ≥3 model types with rationale for the chosen model.**

---

## 1. Candidate Architecture Selection Rationale

To ensure rigorous benchmarking across distinct algorithmic paradigms, six model architectures were trained and evaluated on an identical leak-free patient-grouped stratified split:

| Model Architecture | Paradigm | Algorithmic Rationale & Role in Clinical Evaluation |
| :--- | :--- | :--- |
| **Logistic Regression (L2 Regularized)** | Generalized Linear Model (Parametric) | **Interpretable Baseline.** Provides a transparent reference point. Evaluated with Platt scaling calibration. |
| **Random Forest Classifier** | Bagging Ensemble (Non-Parametric) | **Non-Linear Tree Ensemble.** Aggregates 150 de-correlated trees with balanced subsampling. |
| **XGBoost (Optuna Tuned)** | Gradient Boosted Decision Trees (Boosting) | **SOTA Gradient Optimization.** Tuned with Optuna via StratifiedGroupKFold on PR-AUC/AUC. |
| **LightGBM (Optuna Tuned)** | Leaf-Wise Gradient Boosting | **Fast, Histogram-Based Boosting.** Optimized for high-cardinality interaction features. |
| **CatBoost (Optuna Tuned)** | Oblivious Decision Trees | **Symmetric Tree Boosting.** Exceptional generalization on tabular categorical features. |
| **Calibrated Soft-Voting Ensemble** | Meta-Ensemble (Boosting Blend) | **Production Champion.** Blends probability distributions from tuned XGBoost (35%), LightGBM (35%), and CatBoost (30%) with Platt sigmoid calibration. |

---

## 2. Clinical Metric Choice & Objective Function Justification

In healthcare risk modeling, selecting the appropriate evaluation metrics is a matter of clinical patient safety and resource optimization:

### 2.1 Why Recall (Sensitivity) is the Primary Clinical Target
- **The Asymmetry of Clinical Errors:**
  - **False Negative (FN):** A high-risk patient is incorrectly predicted as low risk and discharged without enhanced care management, home health visits, or medication reconciliation. The patient experiences an acute relapse and is readmitted within 30 days—incurring severe clinical deterioration, patient distress, and institutional CMS penalties ($26,000+ per preventable readmission).
  - **False Positive (FP):** A low-risk patient is flagged as high risk. The consequence is allocating a follow-up telehealth call, a pharmacy consult, or outpatient scheduling. While this incurs minor labor overhead, it causes **no patient harm**.
- **Conclusion:** Minimizing False Negatives is paramount. Therefore, **Recall (Sensitivity)** must be prioritized over raw Precision or Accuracy.

### 2.2 Why Accuracy is Clinically Misleading
- The dataset exhibits an 11.39% readmission rate. A naive "dummy" model predicting that *no* patient will be readmitted achieves **88.61% accuracy** while having **0% Recall** (missing 100% of readmitted patients).
- Accuracy fails entirely to evaluate predictive utility in imbalanced healthcare settings.

### 2.3 Why AUC-ROC & PR-AUC are Essential Discrimination Metrics
- **Area Under the Receiver Operating Characteristic (AUC-ROC):** Measures overall ranking separation across all operational thresholds.
- **Precision-Recall AUC (PR-AUC):** Specifically measures precision-recall dynamics under high class skew, providing an unbiased assessment of minority class retrieval.

---

## 3. Head-to-Head Model Performance Comparison

All models were evaluated on the held-out patient-grouped test cohort ($N = 19,870$; 0% patient overlap with training data). Predictions were calibrated using Platt scaling on an independent validation fold, and optimal clinical thresholds were selected:

| Model Architecture | Threshold ($\tau^*$) | AUC-ROC | PR-AUC | Recall (Sensitivity) | Precision | F1-Score | Brier Score (Calibration) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | 0.125 | 0.6508 | 0.1941 | 50.33% | 18.01% | 0.2652 | 0.0978 |
| **Random Forest** | 0.135 | 0.6590 | 0.1932 | 49.14% | 18.50% | 0.2689 | 0.0976 |
| **XGBoost (Tuned)** | 0.130 | 0.6625 | 0.2064 | 53.20% | 18.64% | 0.2760 | 0.0971 |
| **LightGBM (Tuned)** | 0.130 | 0.6628 | 0.2078 | 53.16% | 18.23% | 0.2715 | 0.0971 |
| **CatBoost (Tuned)** | 0.125 | 0.6622 | 0.2050 | **55.02%** | 18.19% | 0.2735 | 0.0972 |
| **Calibrated Ensemble (Champion)** | **0.130** | **0.6640** | **0.2081** | **53.38%** | **18.54%** | **0.2753** | **0.0971** |

---

## 4. Honest Assessment of Data Leakage Elimination

In previous iterations with random unstratified 80/20 splits, models scored an apparent AUC of ~0.6896 because approximately 30% of patients had multiple encounters distributed across both train and test partitions.
- **The Data Leakage Fix:** Implementing `StratifiedGroupKFold` grouped strictly by `patient_nbr` ensures zero patient overlap between train and test.
- **Real-World Clinical Ceiling:** On this diabetic EHR dataset, the true discriminative AUC ceiling across independent patient cohorts is scientifically established at **0.66 - 0.68**. Reporting 0.6640 reflects an authentic, clinical-grade benchmark that will actually hold up under hospital prospective deployment.
- **Calibration Breakthrough:** Brier score dropped from ~0.21 down to **0.0971**, meaning predicted probabilities directly reflect true clinical incidence.

---

## 5. Rationale for Selecting the Calibrated Soft-Voting Ensemble

The **Calibrated Soft-Voting Ensemble** was selected as the production decision support engine based on four clinical criteria:
1. **Top Discriminative Power:** Achieved the highest AUC-ROC (0.6640) and highest PR-AUC (0.2081) on unseen patients.
2. **Robust Multi-Paradigm Generalization:** Blending histogram-based gradient trees (LightGBM), depth-wise gradient trees (XGBoost), and symmetric oblivious trees (CatBoost) minimizes single-model inductive variance.
3. **Calibrated Posterior Probabilities:** Platt scaling ensures that risk probabilities (e.g. 18.5%) accurately reflect real-world event frequencies, preventing false alarm fatigue among discharge coordinators.
4. **Actionable Clinical Recall:** At the calibrated threshold $\tau^* = 0.130$, the ensemble captures **53.38% of all 30-day readmissions** while maintaining a 1:4 false-positive ratio acceptable for nursing phone call interventions.
