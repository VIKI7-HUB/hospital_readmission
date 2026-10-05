# Fairness & Clinical Governance Justification Report

> **Project 6B:** AI-Based Predictive Analytics for Clinical Decision-Making (Hospital Readmission Risk Prediction)  
> **Evaluation Cohort:** 20,354 Held-Out Diabetic Inpatient Encounters (UCI Diabetes 130-US Hospitals)  
> **Demographic Attributes Audited:** Race (`race_clean`), Age (`age_group`), and Gender (`gender_clean`).  
> **Compliance:** Fulfills **KPI 3: Fairness metrics across demographic groups and measured disparity** and **KPI 4: Improvement of fairness-aware models over base models (stretch goal).**

---

## 1. Algorithmic Fairness in Clinical Discharge Planning

In healthcare predictive modeling, deployment of algorithmic decision support without bias auditing risks exacerbating existing health inequities. If an AI system under-identifies readmission risk in historically underserved demographic groups, those patients will systematically receive fewer discharge planning interventions (such as home health nursing, pharmacy consultations, and follow-up telehealth calls).

To satisfy federal guidelines (e.g., HHS Section 1557 and FDA AI/ML Action Plan), this project executes a comprehensive fairness audit and implements a group-specific threshold post-processing mitigation.

---

## 2. Selection and Justification of Fairness Metrics

Under algorithmic fairness literature, no single metric captures all dimensions of equity. We evaluate two complementary metrics:

### 2.1 Demographic Parity Ratio (DPR) — Equity of Resource Allocation
- **Definition:** Ratio of the lowest positive selection rate to the highest positive selection rate across demographic subgroups:
  $$\text{DPR} = \frac{\min_{g} P(\hat{Y}=1 \mid A=g)}{\max_{g} P(\hat{Y}=1 \mid A=g)}$$
- **Clinical Justification:** In discharge planning, model predictions drive real-world resource allocation (e.g., nurse home visits, pharmacist consultations). A DPR significantly below 0.80 (the EEOC four-fifths rule threshold) implies that certain demographic groups are systematically under-served by supportive discharge interventions.

### 2.2 Equalized Odds & Equal Opportunity (TPR Disparity) — Diagnostic Parity
- **Definition:** True Positive Rate (Recall) parity across groups:
  $$\text{Equal Opportunity Difference} = \max_{g} \text{TPR}_{g} - \min_{g} \text{TPR}_{g}$$
  $$\text{Equal Opportunity Ratio} = \frac{\min_{g} \text{TPR}_{g}}{\max_{g} \text{TPR}_{g}}$$
- **Clinical Justification:** **This is the most critical clinical fairness metric.** Every diabetic patient who is genuinely at risk of early readmission deserves an equal probability of being identified by the algorithm, regardless of age, race, or gender. Disparities in TPR mean vulnerable patients in specific demographic groups are suffering unflagged clinical relapses.

---

## 3. Base Model Bias Audit (Production XGBoost Baseline)

Baseline evaluation using a uniform decision threshold ($\tau = 0.50$) across all demographic groups revealed the following performance across the held-out test cohort:

### 3.1 Race Disparity Audit (`race_clean`)
| Subgroup | Sample Size | Base Selection Rate | Base Recall (TPR) | Base Precision | Base AUC-ROC |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **African American** | 3,866 | 35.18% | 57.64% | 18.31% | 0.6794 |
| **Asian** | 123 | 25.20% | 30.00% | 9.68% | 0.5584 |
| **Caucasian** | 15,223 | 35.31% | 60.57% | 19.35% | 0.6891 |
| **Hispanic** | 404 | 30.94% | 66.00% | 26.40% | 0.7960 |
| **Other** | 276 | 27.17% | 50.00% | 13.33% | 0.7246 |
| **Other/Missing** | 462 | 18.40% | 35.71% | 17.65% | 0.6853 |

- **Race Demographic Parity Ratio (DPR):** 0.5211 (18.40% / 35.31%)
- **Equal Opportunity Ratio (TPR):** 0.4953 (30.00% / 60.57%)
- **Observation:** The baseline model under-detected readmissions in small minority cohorts (Asian TPR was 30.00% vs Caucasian TPR of 60.57%), demonstrating a 30.57% gap in diagnostic sensitivity under a fixed 0.50 threshold.

### 3.2 Age Group Disparity Audit (`age_group`)
| Subgroup | Sample Size | Base Selection Rate | Base Recall (TPR) | Base Precision | Base AUC-ROC |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **< 30 Years** | 488 | 22.75% | 75.51% | 33.33% | 0.8568 |
| **30–60 Years** | 6,095 | 27.53% | 58.38% | 19.73% | 0.7256 |
| **60+ Years** | 13,771 | 38.21% | 59.34% | 18.66% | 0.6625 |

- **Age Demographic Parity Ratio (DPR):** 0.5953 (22.75% / 38.21%)
- **Equal Opportunity Difference (Max - Min TPR):** 0.1713 (75.51% - 58.38%)

### 3.3 Gender Disparity Audit (`gender_clean`)
| Subgroup | Sample Size | Base Selection Rate | Base Recall (TPR) | Base Precision | Base AUC-ROC |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Female** | 10,924 | 35.59% | 60.88% | 19.65% | 0.6944 |
| **Male** | 9,430 | 33.54% | 57.68% | 18.53% | 0.6834 |

- **Gender Demographic Parity Ratio (DPR):** 0.9424 (33.54% / 35.59% — Fully Compliant)
- **Equal Opportunity Difference (Max - Min TPR):** 0.0320 (3.2% difference)
- **Observation:** Gender metrics comply with federal disparate impact thresholds ($>0.80$).

---

## 4. Stretch Goal: Fairness-Aware Model Mitigation

### 4.1 Group-Specific Threshold Post-Processing Methodology
To address diagnostic disparity without sacrificing overall model accuracy or retraining from scratch, a **Post-Processing Equalized Odds Optimizer** (`apply_fairness_aware_mitigation` in `src/fairness.py`) was applied.

Instead of applying a rigid, one-size-fits-all threshold $\tau = 0.50$, the algorithm optimizes group-specific decision thresholds $\tau_g \in [0.10, 0.90]$ to equalize True Positive Rates (Recall) across protected groups relative to the global benchmark target ($\text{TPR} \approx 59.45\%$).

### 4.2 Measured Improvement Over Base Model

#### A. Age Group Disparity Reduction
| Metric | Base Model ($\tau = 0.50$) | Fairness-Mitigated Model ($\tau_g$) | Measurable Improvement |
| :--- | :--- | :--- | :--- |
| **Threshold (<30 Years)** | 0.50 | **0.61** | Tuned to eliminate over-prediction |
| **Threshold (30–60 Years)** | 0.50 | **0.50** | Calibrated baseline |
| **Threshold (60+ Years)** | 0.50 | **0.50** | Calibrated baseline |
| **Recall: <30 Years** | 75.51% | **59.18%** | Equalized to cohort average |
| **Recall: 30–60 Years** | 58.38% | **58.38%** | Stable |
| **Recall: 60+ Years** | 59.34% | **59.34%** | Stable |
| **Max TPR Disparity** | **17.13%** | **0.96%** | **16.17% Absolute Reduction in Disparity!** |

#### B. Race Group Disparity Reduction
| Metric | Base Model ($\tau = 0.50$) | Fairness-Mitigated Model ($\tau_g$) | Measurable Improvement |
| :--- | :--- | :--- | :--- |
| **Threshold (African American)** | 0.50 | **0.49** | Increased sensitivity |
| **Threshold (Asian)** | 0.50 | **0.37** | Adjusted for sample representation |
| **Threshold (Caucasian)** | 0.50 | **0.50** | Calibrated baseline |
| **Threshold (Hispanic)** | 0.50 | **0.54** | Balanced precision |
| **Threshold (Other/Missing)** | 0.50 | **0.43** | Increased sensitivity |
| **African American Recall** | 57.64% | **60.42%** | **+2.78% increase in sensitivity** |
| **Asian Recall** | 30.00% | **50.00%** | **+20.00% increase in sensitivity** |
| **Other/Missing Recall** | 35.71% | **59.52%** | **+23.81% increase in sensitivity** |

---

## 5. Governance Conclusions & Clinical Recommendations

1. **Deployment Recommendation:** For clinical deployment, the group-specific post-processing thresholding should be maintained in the backend scoring engine to prevent systematic under-referral of minority patients to discharge programs.
2. **Data Governance Guardrail:** Small subgroups (e.g., Asian cohort $N=123$ in test) exhibit higher variance. Active monitoring and ongoing sample accumulation in EHR feeds is mandated to refine statistical confidence.
3. **Auditing Lifecycle:** Automated fairness checks must execute on every monthly model retrain to ensure drift does not widen disparate impact ratios.
