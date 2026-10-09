# Demographic Fairness & Algorithmic Parity Audit Report

> **Project 6B:** AI-Based Predictive Analytics for Clinical Decision-Making (Hospital Readmission Risk Prediction)  
> **Evaluation Cohort:** 19,870 Held-Out Diabetic Inpatient Encounters (14,038 Unique Patients; 0% Patient Leakage)  
> **Demographic Dimensions Audited:** Race (`race_clean`), Gender (`gender_clean`), and Age Brackets (`age_group`).  
> **Deployment Policy:** Uniform 12.0% decision threshold applied to all patients. Group-specific thresholds were evaluated solely as an offline exploratory analysis and are not deployed in production.

---

## 1. Algorithmic Fairness in Inpatient Discharge Triage

In acute hospital discharge planning, predictive decision support flags patients at elevated risk of 30-day readmission for specialized post-acute clinical services, including bedside pharmacist medication reconciliation, diabetes self-management education (CDCES), home health nursing, and 48-hour post-discharge telehealth follow-up.

If a predictive model under-identifies readmission risk in historically marginalized or medically vulnerable populations, those patients systematically miss supportive transitional care interventions. Therefore, auditing sensitivity across demographic groups is a clinical and ethical prerequisite for assistive AI deployment.

---

## 2. Fairness Metric Justification & Clinical Framing

Under algorithmic fairness literature, standard metrics evaluate distinct operational principles:

### 2.1 Equal Opportunity / Sensitivity Parity (Primary Clinical Metric)
- **Definition:** True Positive Rate (Sensitivity / Recall) parity across demographic groups:
  - TPR = TP / (TP + FN)
  - Disparity Gap = TPR(Reference Group) - TPR(Evaluated Group)
- **Clinical Justification:** In discharge planning, Sensitivity is the paramount ethical criterion. Every patient destined for an unplanned 30-day readmission deserves an equal probability of being identified and offered preventative care, irrespective of race, sex, or age.

### 2.2 Demographic Parity Ratio (Selection Rate)
- **Definition:** Ratio of the positive flag rate across demographic groups:
  - DPR = min_g P(Flagged = 1 | Group = g) / max_g P(Flagged = 1 | Group = g)
- **Clinical Context:** While monitored to ensure resource allocation does not arbitrarily favor specific demographic cohorts, strict DPR parity is not enforced as a sole criterion because baseline clinical morbidity, age, and chronic disease prevalence legitimately differ across inpatient cohorts.

---

## 3. Test-Set Demographic Audits (Uniform 12.0% Deployed Cutoff)

All metrics were evaluated on the leak-free held-out test cohort (N = 19,870 encounters, 2,263 true 30-day readmissions). Disparities and 95% confidence intervals were generated via 1,000 bootstrap iterations on the untouched test split.

### 3.1 Race and Ethnicity Audit (`race_clean`)

| Demographic Subgroup | Encounters (n) | Readmissions (k) | Sensitivity (TPR) | 95% Bootstrap CI | Specificity (TNR) | Flag Rate | Small-Sample Flag |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Caucasian (Reference)** | 14,874 | 1,735 | **58.67%** | [56.3%, 61.0%] | 63.84% | 37.89% | No (Powered) |
| **African American** | 3,716 | 406 | **53.69%** | [48.8%, 58.5%] | 65.14% | 36.92% | No (Powered) |
| **Asian** | 124 | 13 | 38.46% | [17.7%, 64.5%] | 75.68% | 25.81% | **Yes (k < 100)** |
| **Hispanic** | 405 | 45 | 60.00% | [44.7%, 73.8%] | 65.56% | 37.53% | **Yes (k < 100)** |
| **Other** | 308 | 25 | 60.00% | [40.0%, 78.3%] | 65.02% | 37.01% | **Yes (k < 100)** |
| **Other/Unknown** | 443 | 39 | 53.85% | [37.8%, 68.4%] | 66.83% | 35.44% | **Yes (k < 100)** |

- **Headline Disparity Gap (Caucasian vs. African American):** 4.98 percentage points (95% CI: [-0.4 pp to 10.4 pp]). Because the 95% bootstrap confidence interval spans zero, the observed disparity is not statistically significant at alpha = 0.05.
- **Statistical Power Limitation:** Subgroups with fewer than 100 readmissions (Asian, Hispanic, Other, Unknown) exhibit very wide confidence intervals and are statistically underpowered to draw conclusive parity determinations.

### 3.2 Gender / Sex Audit (`gender_clean`)

| Gender Subgroup | Encounters (n) | Readmissions (k) | Sensitivity (TPR) | 95% Bootstrap CI | Specificity (TNR) | Flag Rate | Small-Sample Flag |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Female (Reference)** | 10,615 | 1,238 | **59.13%** | [56.4%, 61.9%] | 63.26% | 38.53% | No (Powered) |
| **Male** | 9,254 | 1,025 | **55.80%** | [52.7%, 58.8%] | 65.05% | 36.90% | No (Powered) |
| **Other/Unknown** | 1 | 0 | 0.00% | N/A | 100.0% | 0.00% | **Yes (k < 100)** |

- **Headline Disparity Gap (Female vs. Male):** 3.32 percentage points (95% CI: [-1.0 pp to 7.4 pp]). The 95% confidence interval spans zero, indicating no statistically significant gender disparity in diagnostic recall.

### 3.3 Age Category Audit (`age_group`)

| Age Bracket | Encounters (n) | Readmissions (k) | Sensitivity (TPR) | 95% Bootstrap CI | Specificity (TNR) | Flag Rate | Small-Sample Flag |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **60+ Years (Reference)** | 13,227 | 1,605 | **58.32%** | [55.9%, 60.7%] | 63.78% | 38.16% | No (Powered) |
| **30-60 Years** | 6,131 | 592 | **54.39%** | [50.4%, 58.4%] | 64.67% | 36.98% | No (Powered) |
| **<30 Years** | 512 | 66 | 69.70% | [58.2%, 79.7%] | 64.13% | 40.04% | **Yes (k < 100)** |

- **Headline Disparity Gap (60+ Years vs. 30-60 Years):** 3.93 percentage points (95% CI: [-0.9 pp to 8.6 pp]). The 95% confidence interval spans zero.

---

## 4. Exploratory Post-Processing Mitigation Analysis (Not Deployed)

As an exploratory academic exercise, group-specific classification thresholds were tuned strictly on the validation partition (N = 9,935) to equalize sensitivity relative to African American validation TPR (60.87%). When evaluated on the untouched test holdout (N = 19,870):

| Cohort Stratum / Metric | Unmitigated Deployed (12.0% Cutoff) | Mitigated (Val-Tuned Cutoff, Analysis Only) | Trade-Off Impact |
| :--- | :---: | :---: | :--- |
| **Overall Cohort Recall** | **57.62%** | **57.05%** | -0.57 pp overall sensitivity loss |
| **Overall Cohort Precision** | **17.38%** | **17.37%** | -0.01 pp precision |
| **Overall Cohort Flag Rate** | **37.77%** | **37.41%** | 71 fewer patients flagged |
| **Caucasian Recall (TPR)** | **58.67%** | **57.93%** | -0.74 pp recall drop in largest group |
| **African American Recall (TPR)** | **53.69%** | **53.69%** | 0.00 pp change (threshold held at 12.0%) |

### Clinical Conclusion on Threshold Mitigation
Applying group-specific thresholds achieved minor demographic parity closure strictly by **lowering recall for Caucasian patients** (from 58.67% to 57.93%) rather than increasing recall for African American patients. This "leveling down" reduces total readmission detection across the hospital system without providing clinical benefit to minority patients. 

Consequently, the production system **retains a single, unified 12.0% decision threshold across all patients**.
