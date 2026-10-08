# ClinicalAI: 30-Day Hospital Readmission Risk Prediction & Decision Support

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit UI](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/XGBoost-1.7+-green.svg)](https://xgboost.readthedocs.io/)
[![Fairlearn](https://img.shields.io/badge/Fairlearn-Governance-orange.svg)](https://fairlearn.org/)
[![Groq LPU](https://img.shields.io/badge/Groq%20LPU-Ultra--Fast%20AI-purple.svg)](https://groq.com/)

An enterprise-grade, explainable Clinical Decision Support (CDS) platform designed for hospital discharge planners, attending physicians, and clinical case managers. The system predicts 30-day inpatient readmission risk in complex diabetic cohorts, audits algorithmic fairness across protected demographics, generates on-demand 5-point clinical decision rationale via Groq LPUs (`openai/gpt-oss-120b`), and automatically prescribes targeted post-acute care bundles under the CMS Hospital Readmissions Reduction Program (HRRP).

---

## Executive Presentation Deck

The official **Hackfest 2026 Screening Round Idea Presentation** (strictly adhering to the 6-slide rule and all competition evaluation criteria) is available in the repository root:

- **Presentation Deck (PPTX):** [`Hackfest_2026_Screening_Presentation.pptx`](Hackfest_2026_Screening_Presentation.pptx)
- **High-Resolution Slide Previews:** [`slide_images/`](slide_images/) (`Slide1.JPG` through `Slide6.JPG`)
- **Slide-by-Slide Pitch Notes & Script:** [`docs/screening_presentation_guide.md`](docs/model_selection_rationale.md)

---

## 1. Project Overview & Clinical Context

- **Domain:** Healthcare & MedTech / Clinical Decision Support (CDS) & Inpatient Workflow Automation.
- **Specification:** Project 6B — Hospital Readmission Risk Prediction (Predictive Analytics & AI Governance).
- **Clinical Dataset:** UCI Machine Learning Repository — *Diabetes 130-US Hospitals (1999–2008)* covering **101,766 inpatient encounters** across multiple US hospital systems with 48 clinical features.
- **Primary Clinical Target:** 30-Day Inpatient Readmission (`readmitted == '<30'`; 11.16% baseline prevalence, ~8:1 class imbalance).
- **Core Clinical Problem:**
  - Over **$26 Billion** in avoidable annual US/global hospital readmission expenses.
  - Punitive CMS HRRP penalties up to **3% Medicare inpatient reimbursement forfeitures** for excess readmissions.
  - Diabetic comorbidity complexity: **43.8%** of patients present with severe polypharmacy ($\ge 10$ active medications).
  - Triage breakdown: Retrospective, manual discharge planning misses over **45%** of preventable readmission candidates.

---

## 2. Specification KPI Compliance Matrix

| KPI ID | Specification Requirement | Project Deliverable / Evidence | Location |
| :--- | :--- | :--- | :--- |
| **KPI 1** | Predictive performance: accuracy, precision, recall (with clinical justification of metric choice) and AUC | Test evaluation benchmarks across held-out cohort ($N=20,354$) with clinical justification prioritizing Recall over Accuracy | [`docs/model_selection_rationale.md`](docs/model_selection_rationale.md) & [`models/model_comparison_results.csv`](models/model_comparison_results.csv) |
| **KPI 2** | Comparison across $\ge 3$ model types with rationale for the chosen model | Head-to-head comparison of Logistic Regression, Random Forest, and XGBoost; technical justification for selecting XGBoost | [`docs/model_selection_rationale.md`](docs/model_selection_rationale.md) & [`models/model_rationale_summary.json`](models/model_rationale_summary.json) |
| **KPI 3** | Fairness metrics across demographic groups (age, gender, race) and measured disparity | Demographic Parity Ratio (DPR) and Equalized Odds (TPR ratio and difference) audited across all demographic strata | [`docs/fairness_justification.md`](docs/fairness_justification.md) & [`fairness_governance/`](fairness_governance/) |
| **KPI 4** | Improvement of fairness-aware models over base models (stretch goal) | Post-processing threshold optimizer equalizing Recall across groups; verified reduction of age TPR disparity from 17.13% to 0.96% | [`docs/fairness_justification.md`](docs/fairness_justification.md) & [`fairness_governance/mitigation_improvement_summary.json`](fairness_governance/mitigation_improvement_summary.json) |
| **KPI 5** | Documented data-quality handling: missing values, outliers, and feature-selection decisions | Statistical and clinical audit of missingness, 99th-percentile Winsorization, and ICD-9 organ category mapping | [`docs/data_quality_report.md`](docs/data_quality_report.md) & [`data/processed/data_quality_summary.json`](data/processed/data_quality_summary.json) |

---

## 3. Key Model Performance & Fairness Benchmarks

### Predictive Model Comparison (Held-Out Test Cohort $N=19,870$; 0% Patient Leakage)

| Model Architecture | Threshold ($\tau^*$) | AUC-ROC | PR-AUC | Recall (Sensitivity) | Precision | Brier Score Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Calibrated)** | 0.125 | 0.6508 | 0.1941 | 50.33% | 18.01% | 0.0978 |
| **Random Forest (Calibrated)** | 0.135 | 0.6590 | 0.1932 | 49.14% | 18.50% | 0.0976 |
| **XGBoost (Optuna Tuned)** | 0.130 | 0.6625 | 0.2064 | 53.20% | 18.64% | 0.0971 |
| **LightGBM (Optuna Tuned)** | 0.130 | 0.6628 | 0.2078 | 53.16% | 18.23% | 0.0971 |
| **CatBoost (Optuna Tuned)** | 0.125 | 0.6622 | 0.2050 | **55.02%** | 18.19% | 0.0972 |
| **Calibrated Ensemble (Champion)** | **0.130** | **0.6640** | **0.2081** | **53.38%** | **18.54%** | **0.0971** |

> **Clinical Decision Rationale:** In discharge triage, a **False Negative** (discharging a patient who will experience acute decompensation and readmission) is orders of magnitude more catastrophic than a **False Positive** (providing a high-touch post-discharge phone call or pharmacist review). Hence, the **Calibrated Soft-Voting Ensemble (blending XGBoost, LightGBM, and CatBoost with Platt scaling)** was selected for achieving the highest discriminative power (AUC 0.6640, PR-AUC 0.2081), robust Sensitivity (53.38%), and state-of-the-art calibration (Brier score 0.0971).

### Algorithmic Fairness & Disparity Mitigation (Stretch Goal)

| Protected Demographic | Baseline Disparity (Base Model) | Mitigated Disparity (Fairness-Aware) | Disparity Reduction | Compliance Status |
| :--- | :---: | :---: | :---: | :--- |
| **Age TPR Disparity** | 13.80% difference | **0.61% difference** | **-13.19% delta** | **Equitable Across Generations** |
| **Race TPR Disparity** | 11.28% difference | **3.09% difference** | **-8.19% delta** | **Equitable Across Racial Groups** |
| **Gender Demographic Parity** | 87.68% DPR | **87.68% DPR** | Parity preserved | **Complies with EEOC 4/5ths Rule (>80%)** |

---

## 4. End-to-End System Architecture

```mermaid
flowchart LR
    A["Inpatient EHR Intake<br/>101,766 Encounters"] --> B["Data Pipeline<br/>Winsorization & Preprocessing"]
    B --> C["Model & Fairness Engine<br/>XGBoost (scale_pos_weight)"]
    C --> D["Explainability Layer<br/>Local SHAP + Groq LLM"]
    D --> E["Clinical Slate UI<br/>Streamlit Dashboard"]
    E --> F["Actionable Protocols<br/>PharmD & Telehealth Dispatched"]
```

### Four-Tier Pipeline Architecture

1. **Data Ingestion & Preprocessing Tier (`src/preprocessing.py`):**
   - 99th-percentile Winsorization capping extreme utilization outliers.
   - Clinical feature derivation: `polypharmacy` ($\ge 10$ meds), `total_visits`, `high_prior_utilization`, `num_med_changes`.
   - Leakage-free Scikit-Learn Pipeline combining `OneHotEncoder` and `RobustScaler`.
2. **Predictive Modeling & Fairness Tier (`src/models.py`, `src/fairness.py`):**
   - Calibrated gradient boosting using XGBoost with native class imbalance weighting.
   - Fairlearn disparity audit engine verifying Equalized Odds and Demographic Parity Ratios.
3. **Explainability & LLM Reasoning Layer (`src/explainability.py`):**
   - Local directional feature attribution (identifying patient-specific risk drivers).
   - On-demand Groq API inference using **`openai/gpt-oss-120b`** synthesizing 5 structured clinical points (Clinical Stabilization, Polypharmacy, Glycemic Control, Prior Utilization, Post-Acute Support).
   - In-memory encounter caching via `@st.cache_data` preventing redundant LLM calls.
4. **Interactive Clinical Slate UI (`app.py`):**
   - **View 1: Discharge Readiness Worklist:** High-density queue with risk tier filtering, ID search, and single-click review modal.
   - **View 2: Bedside Risk Calculator:** Real-time slider simulation adjusting stay duration, active meds, and A1C in real-time.
   - **View 3: Clinical Governance & Benchmarks:** Multi-model benchmark curves and audited demographic disparity reduction metrics.

---

## 5. Repository Structure

```
hospital_readmission/
├── .streamlit/
│   └── config.toml                # Light medical slate theme configuration
├── data/
│   ├── raw/                       # UCI dataset (diabetic_data.csv & IDS_mapping.csv)
│   └── processed/                 # Cleaned datasets, preprocessor pipeline, train/test splits
├── docs/                          # Formal technical documentation
│   ├── data_quality_report.md     # KPI 5: Data quality and feature engineering rationale
│   ├── model_selection_rationale.md # KPI 1 & 2: Architecture comparison & metric choice
│   └── fairness_justification.md  # KPI 3 & 4: Demographic disparity & stretch mitigation
├── fairness_governance/           # Demographic bias audit reports & mitigated model artifacts
├── models/                        # Saved model artifacts (.joblib) & comparison CSV
├── slide_images/                  # Exported high-resolution presentation slide renders
├── src/
│   ├── __init__.py
│   ├── download_data.py           # Automated UCI dataset acquisition
│   ├── preprocessing.py          # Data cleaning, outlier capping & pipeline fitting
│   ├── models.py                 # Multi-model training and evaluation
│   ├── fairness.py               # Disparity auditing & threshold optimization
│   └── explainability.py         # SHAP feature impact & Groq AI clinical synthesis
├── app.py                         # Production Streamlit clinical decision support application
├── build_executive_presentation.py# Script to generate the executive PowerPoint deck
├── Hackfest_2026_Screening_Presentation.pptx # Official 6-slide screening presentation
├── requirements.txt               # Verified environment dependencies
├── run_pipeline.py                # End-to-end reproducible training & audit script
└── LICENSE                        # MIT License
```

---

## 6. Installation & Quickstart

### Prerequisites
- Python 3.10 or 3.11+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/VIKI7-HUB/hospital_readmission.git
cd hospital_readmission
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the End-to-End Pipeline (Optional - Pre-trained Artifacts Included)
```bash
python run_pipeline.py
```
*Executes leak-free data engineering, trains all 6 architectures (LR, RF, XGBoost, LightGBM, CatBoost, Calibrated Ensemble), optimizes clinical thresholds, precomputes worklist artifacts, and audits demographic parity.*

### 4. Launch the Clinical Decision Support Application
```bash
streamlit run app.py
```
Open your browser at **`http://localhost:8501`** to access the live clinical portal.

---

## 7. Vercel + Supabase + Render Research Demo

The web version uses three services:

- `frontend/` — responsive Vite/React interface hosted on Vercel.
- `supabase/` — public read-only Postgres tables and the `clinicalai-api` Edge Function. The migration loads the repository's 500-row de-identified demo cohort and governance summaries.
- `backend/` — Python model scoring API hosted on Render. Supabase forwards only prediction requests to this service because the trained Python model and its dependencies do not run inside the Edge Function runtime.

### Set up Supabase (free plan)

1. Create a Supabase project on the Free plan and install the Supabase CLI.
2. From the repository root, link the project and apply the migration:

   ```bash
   supabase login
   supabase link --project-ref YOUR_PROJECT_REF
   supabase db push
   ```

   The migration creates the two read-only public tables and seeds the demonstration records, benchmarks, fairness summaries, and aggregate counts. Row-level security is enabled; browser clients receive `SELECT` access only.
3. Deploy the API function and point it at the Render model service:

   ```bash
   supabase functions deploy clinicalai-api
   supabase secrets set MODEL_API_URL=https://hospital-readmission-api-ig1c.onrender.com
   ```

   Supabase supplies its project URL and legacy anonymous key to the function at runtime. No service-role key belongs in the frontend.

### Deploy the Python model service to Render

1. Create a Blueprint from this repository and select the deployment branch.
2. Render reads `render.yaml`, installs `requirements-render.txt`, and starts the scoring API. Wait for `/api/health` to report healthy.
3. The current Render service URL is `https://hospital-readmission-api-ig1c.onrender.com`; use the URL assigned by Render if it changes.

### Deploy the frontend to Vercel

1. Import the repository in Vercel and set the project root to `frontend`.
2. Use `npm run build` and `dist` as the output directory.
3. Set `VITE_SUPABASE_URL` to the Supabase project URL and `VITE_SUPABASE_PUBLISHABLE_KEY` to that project's publishable key, then deploy.

Copy `frontend/.env.example` to `frontend/.env.local` for local development. The app calls the Supabase Edge Function at `/functions/v1/clinicalai-api`; `VITE_API_BASE_URL` is only an optional fallback for the legacy local FastAPI server.

This is a **public research demonstration** using historical, de-identified data. It is not validated for clinical use, does not connect to an EHR, and does not save scenario inputs. Do not submit identifiable patient information or use its scores to make patient-care decisions.

## 8. Ethical Governance & Regulatory Alignment

- **CMS Hospital Readmissions Reduction Program (HRRP):** Aligned with Section 3025 of the Affordable Care Act.
- **EEOC Four-Fifths Rule Compliance:** Gender Demographic Parity Ratio (94.24%) exceeds the federal 80% threshold.
- **Explainability Standard:** In compliance with AMA Ethical AI Guidelines, every prediction is paired with verifiable feature impact and narrative physician reasoning before clinical action is taken.

---

## 9. License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more details.
