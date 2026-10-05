# Model Selection & Performance Evaluation Rationale

> **Project 6B:** AI-Based Predictive Analytics for Clinical Decision-Making (Hospital Readmission Risk Prediction)  
> **Dataset:** UCI Diabetes 130-US Hospitals (80/20 Stratified Split; Test Set = 20,354 encounters)  
> **Target:** 30-Day Readmission (`readmitted == '<30'`; 11.16% prevalence, ~8:1 imbalance ratio)  
> **Compliance:** Fulfills **KPI 1: Predictive performance (accuracy, precision, recall with justification, AUC)** and **KPI 2: Comparison across ≥3 model types with rationale for the chosen model.**

---

## 1. Candidate Architecture Selection Rationale

To ensure rigorous benchmarking across distinct algorithmic paradigms, three distinct machine learning model types were trained on an identical 80/20 stratified train/test split:

| Model Architecture | Paradigm | Algorithmic Rationale & Role in Clinical Evaluation |
| :--- | :--- | :--- |
| **Logistic Regression (L2 Regularized)** | Generalized Linear Model (Parametric) | **Interpretable Baseline.** Provides a transparent reference point. Assumes linear relationships between log-odds of readmission and predictors. Calibrated with balanced class weighting to handle minority prevalence. |
| **Random Forest Classifier** | Bagging Ensemble (Non-Parametric) | **Non-Linear Tree Ensemble.** Mitigates variance by aggregating 150 de-correlated decision trees. Evaluates interaction effects between clinical variables (e.g., age bracket combined with polypharmacy) without making linear additivity assumptions. |
| **XGBoost (Extreme Gradient Boosting)** | Gradient Boosted Decision Trees (Boosting) | **SOTA Sequential Optimization.** Sequentially builds shallow trees that minimize residual errors along the loss gradient. Natively supports minority class weighting via `scale_pos_weight = 7.96` to directly target the severe 89:11 class imbalance. |

---

## 2. Clinical Metric Choice & Objective Function Justification

In healthcare risk modeling, selecting the appropriate evaluation metrics is a matter of clinical patient safety and resource optimization:

### 2.1 Why Recall (Sensitivity) is the Primary Optimization Target
- **The Asymmetry of Clinical Errors:**
  - **False Negative (FN):** A high-risk patient is incorrectly predicted as low risk and discharged without enhanced care management, home health visits, or medication reconciliation. The patient experiences an acute relapse and is readmitted within 30 days—incurring severe clinical deterioration, patient distress, and institutional CMS penalties ($26,000+ per preventable readmission).
  - **False Positive (FP):** A low-risk patient is flagged as high risk. The consequence is allocating a follow-up telehealth call, a pharmacy consult, or outpatient scheduling. While this incurs minor labor overhead, it causes **no patient harm**.
- **Conclusion:** Minimizing False Negatives is paramount. Therefore, **Recall (Sensitivity)** must be prioritized over raw Precision or Accuracy.

### 2.2 Why Accuracy is Clinically Misleading
- The dataset exhibits an 11.16% readmission rate. A naive "dummy" model that predicts *every* patient will not be readmitted achieves **88.84% accuracy** while having **0% Recall** (missing 100% of readmitted patients).
- Accuracy fails entirely to distinguish model efficacy in class-imbalanced healthcare applications.

### 2.3 Why AUC-ROC is the Definitive Discrimination Metric
- **Area Under the Receiver Operating Characteristic (AUC-ROC):** Measures the probability that the model ranks a randomly chosen readmitted patient higher than a non-readmitted patient across *all possible classification thresholds*. It provides a robust, threshold-independent measure of true discriminative power.

---

## 3. Head-to-Head Model Performance Comparison

All models were evaluated on the held-out test cohort ($N = 20,354$). The results below reflect the official benchmark recorded in `models/model_comparison_results.csv`:

| Model | AUC-ROC | Recall (Sensitivity) | Precision | F1-Score | Accuracy | Brier Score (Calibration) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | 0.6810 | 57.90% | 18.34% | 0.2786 | 65.41% | 0.2185 |
| **Random Forest** | 0.6831 | 50.15% | 20.26% | 0.2886 | 72.10% | 0.1794 |
| **XGBoost (Selected)** | **0.6896** | **59.45%** | **19.15%** | **0.2897** | **67.09%** | **0.1983** |

### Detailed Metric Breakdown:
- **Logistic Regression:** Achieved 57.90% recall with AUC 0.6810. Shows acceptable baseline separation but suffers from higher linear prediction error.
- **Random Forest:** Achieved the highest raw accuracy (72.10%) and precision (20.26%), but **sacrificed recall to 50.15%** (missing half of readmission cases). This is clinically unacceptable for a patient safety screening tool.
- **XGBoost:** Achieved the **highest AUC-ROC (0.6896)** and the **highest Recall (59.45%)**, identifying nearly 60% of all early readmissions while maintaining balanced precision (19.15%).

---

## 4. Rationale for Selecting XGBoost as the Production Engine

**XGBoost was chosen as the primary clinical engine** based on three decisive factors:

1. **Superior Discriminative Performance:** Achieves the top AUC-ROC (0.6896), demonstrating superior ranking of readmission risk across diverse diabetic encounters.
2. **Maximum Patient Protection (Highest Recall):** At 59.45% recall, XGBoost successfully detects 1,351 out of 2,272 readmitted test patients—capturing 211 more high-risk individuals than Random Forest.
3. **Robust Handling of Class Imbalance:** Through exact gradient descent weighted by `scale_pos_weight = 7.96`, XGBoost penalizes missed positive encounters without requiring artificial synthetic oversampling (SMOTE), preserving true clinical distributions.
4. **Transparent Explainability Integration:** XGBoost tree structures natively output exact gain-based and TreeSHAP feature importances, enabling the bedside explainability layer in `src/explainability.py`.

---

## 5. Hyperparameter Specification

```python
# Production XGBoost Architecture
XGBClassifier(
    n_estimators=200,          # Sufficient iterations for convergence
    max_depth=6,               # Constrained tree depth to prevent clinical overfitting
    learning_rate=0.05,        # Conservative shrinkage parameter for generalization
    scale_pos_weight=7.96,     # Ratio of negative:positive instances (88.84% : 11.16%)
    eval_metric='logloss',     # Strictly proper scoring rule for probability calibration
    random_state=42,           # Reproducibility seed
    n_jobs=-1                  # Multi-threaded execution
)
```
