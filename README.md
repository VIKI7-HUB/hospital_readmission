# ClinicalAI: 30-Day Hospital Readmission Risk Prediction & Decision Support

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E.svg)](https://scikit-learn.org/)
[![Fairlearn](https://img.shields.io/badge/Fairlearn-Governance-orange.svg)](https://fairlearn.org/)

An enterprise-grade, explainable Clinical Decision Support (CDS) platform designed for hospital discharge planners, attending physicians, and clinical case managers. The system predicts 30-day inpatient readmission risk in complex diabetic cohorts using classical, explainable machine learning models, audits algorithmic fairness across protected demographics, generates feature-attribution rationale, and prescribes targeted post-acute care bundles under the CMS Hospital Readmissions Reduction Program (HRRP).

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
  - Diabetic comorbidity complexity: **79.0%** of patients have 10 or more distinct medications administered during the stay.
  - Triage breakdown: Retrospective, manual discharge planning misses over **45%** of preventable readmission candidates.

---

## 2. Specification KPI Compliance Matrix

| KPI ID | Specification Requirement | Project Deliverable / Evidence | Location |
| :--- | :--- | :--- | :--- |
| **KPI 1** | Predictive performance: accuracy, precision, recall (with clinical justification of metric choice) and AUC | Test evaluation benchmarks across held-out cohort (N = 19,870) with clinical justification prioritizing Recall over Accuracy | [`docs/model_selection_rationale.md`](docs/model_selection_rationale.md) & [`models/model_comparison_results.csv`](models/model_comparison_results.csv) |
| **KPI 2** | Comparison across 3 or more model types with rationale for the chosen model | Head-to-head comparison of Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost, and Ensemble; rationale for Soft-Voting Ensemble | [`docs/model_selection_rationale.md`](docs/model_selection_rationale.md) & [`models/model_rationale_summary.json`](models/model_rationale_summary.json) |
| **KPI 3** | Fairness metrics across demographic groups (age, gender, race) and measured disparity | Demographic Parity Ratio (DPR) and Equalized Odds (TPR ratio, difference, and Wilson 95% CIs) audited across all demographic strata | [`docs/fairness_justification.md`](docs/fairness_justification.md) & [`fairness_governance/`](fairness_governance/) |
| **KPI 4** | Improvement of fairness-aware models over base models (stretch goal) | Gender disparity reduced by 10% (3.70 pp to 3.33 pp); audited across all demographic subgroups with Wilson 95% confidence intervals | [`docs/fairness_justification.md`](docs/fairness_justification.md) & [`fairness_governance/mitigation_improvement_summary.json`](fairness_governance/mitigation_improvement_summary.json) |
| **KPI 5** | Documented data-quality handling: missing values, outliers, and feature-selection decisions | Statistical and clinical audit of missingness, 99th-percentile Winsorization, and ICD-9 organ category mapping | [`docs/data_quality_report.md`](docs/data_quality_report.md) & [`data/processed/data_quality_summary.json`](data/processed/data_quality_summary.json) |

---

## 3. Key Model Performance & Fairness Benchmarks

### Predictive Model Comparison (Held-Out Test Cohort N = 19,870; 0% Patient Leakage)

| Model Architecture | Threshold (tau) | AUC-ROC | PR-AUC | Accuracy | Recall (Sensitivity) | Precision | F1-Score | Brier Score Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Calibrated)** | 0.120 | 0.6468 | 0.1877 | **68.24%** | 49.98% | **17.93%** | 0.2639 | 0.0982 |
| **Random Forest (Calibrated)** | 0.130 | 0.6467 | 0.1881 | 66.75% | 51.66% | 17.50% | 0.2614 | 0.0980 |
| **XGBoost (Calibrated)** | 0.120 | 0.6516 | 0.1976 | 64.18% | 56.65% | 17.28% | 0.2648 | 0.0977 |
| **LightGBM (Calibrated)** | 0.120 | 0.6512 | 0.1970 | 63.76% | 56.56% | 17.07% | 0.2623 | 0.0977 |
| **CatBoost (Calibrated)** | 0.120 | 0.6526 | **0.2001** | 64.22% | **57.76%** | 17.52% | **0.2688** | **0.0976** |
| **Calibrated Ensemble (Champion)** | **0.120** | **0.6531** | 0.1987 | 63.95% | 57.27% | 17.30% | 0.2657 | **0.0976** |

> **Clinical Decision Rationale:** In discharge triage, a **False Negative** (discharging a patient who will experience acute decompensation and readmission) is orders of magnitude more catastrophic than a **False Positive** (providing a high-touch post-discharge phone call or pharmacist review). Hence, the **Calibrated Soft-Voting Ensemble (blending XGBoost, LightGBM, and CatBoost with Platt scaling)** was selected at cutoff tau = 0.120 for achieving the highest discriminative power (AUC 0.6531, PR-AUC 0.1987), robust Sensitivity (57.27%), and state-of-the-art calibration (Brier score 0.0976).

### Demographic Fairness Audits (Analysis Only, Not Deployed; Deployed Cutoff: 12.0%)

The deployed clinical system applies a uniform 12.0% threshold across all patients without demographic adjustments. Group-specific threshold adjustments were evaluated solely as an offline exploratory analysis.

| Demographic Dimension | Evaluated Groups (Test Set N = 19,870) | Deployed Sensitivity (TPR) Range | Headline Disparity Gap (95% CI) | Status / Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Gender / Sex** | Female (n=10,615), Male (n=9,254) | 55.41% - 58.80% | 3.39 pp [-0.9 pp to 7.5 pp] | Both groups >=100 readmissions; difference not statistically significant |
| **Race / Ethnicity** | Caucasian (n=14,874), African American (n=3,716) | 52.71% - 58.39% | 5.68 pp [0.3 pp to 10.9 pp] | Subgroups with <100 readmissions (Asian, Hispanic, Other) flagged as underpowered |
| **Age Brackets** | 30-60 Years (n=6,131), 60+ Years (n=13,227) | 53.72% - 58.13% | 4.41 pp [-0.4 pp to 9.2 pp] | <30 Years cohort (n=512, 66 readmissions) flagged as small sample |

---

## 4. End-to-End System Architecture

```mermaid
flowchart LR
    A["Inpatient EHR Intake<br/>101,766 Encounters"] --> B["Data Pipeline<br/>Winsorization & Preprocessing<br/>(Fit on Train Split Only)"]
    B --> C["Predictive Modeling Engine<br/>Calibrated Ensemble (tau = 0.120)"]
    B --> C
    C --> D["Explainability Layer<br/>Tree Feature Attribution & Guidance"]
    D --> E["Clinical CDS Dashboard<br/>React 18 + Vite (Port 5173)<br/>FastAPI Backend (Port 8000)"]
    E --> F["Actionable Post-Acute Bundles<br/>PharmD, Telehealth & Care Coordination"]
```

### Four-Tier Pipeline Architecture

1. **Data Ingestion & Preprocessing Tier (`src/preprocessing.py`):**
   - 99th-percentile Winsorization capping extreme utilization outliers.
   - Clinical feature derivation: `polypharmacy` (>=10 distinct medications during stay; 79% of sample), `total_visits`, `high_prior_utilization`, `num_med_changes`.
   - Leakage-free Scikit-Learn Pipeline combining `OneHotEncoder` and `StandardScaler` fit strictly on the training partition (N = 69,538 encounters, 48,973 patients).
2. **Predictive Modeling & Fairness Tier (`src/models.py`, `src/fairness.py`):**
   - Calibrated gradient boosting using LightGBM, XGBoost, and CatBoost with Platt sigmoid scaling.
   - Disparity audit engine verifying Equal Opportunity (TPR) with bootstrap 95% confidence intervals on the untouched test holdout.
3. **Explainability Layer (`src/explainability.py`):**
   - Directional feature attribution identifying patient-specific risk drivers (units: per 1 SD for continuous numeric, versus reference category for categorical).
   - Observational note that discharge to SNF/rehab is an observational marker of higher clinical acuity.
4. **Clinical Decision Support UI (`frontend/` + `backend/`):**
   - **View 1: Discharge Readiness Worklist:** High-density queue with risk tier filtering, ID search, pagination, and patient review drawer.
   - **View 2: Bedside Risk Calculator:** Real-time scenario simulation adjusting stay duration, medications, and A1C in real-time.
   - **View 3: Clinical Governance & Benchmarks:** 10-section artifact-driven audit report.

---

## 5. Repository Structure

```
hospital_readmission/
├── backend/                       # FastAPI production REST API
│   └── main.py                   # Health, worklist, prediction & governance endpoints
├── frontend/                      # Vite + React 18 high-density clinical user interface
│   ├── src/main.jsx              # Worklist, calculator, governance & command palette
│   └── package.json              # Frontend dependencies
├── data/
│   ├── raw/                       # UCI dataset (diabetic_data.csv & IDS_mapping.csv)
│   └── processed/                 # Cleaned datasets, preprocessor pipeline, train/val/test splits
├── docs/                          # Formal technical documentation & audit reports
│   ├── audit_report.md            # Comprehensive verification & quality assurance report
│   ├── data_quality_report.md     # KPI 5: Data quality and feature engineering rationale
│   ├── model_selection_rationale.md # KPI 1 & 2: Architecture comparison & metric choice
│   └── fairness_justification.md  # KPI 3 & 4: Demographic disparity & stretch mitigation
├── fairness_governance/           # Demographic bias audit reports & mitigated model artifacts
├── models/                        # Saved model artifacts (.joblib) & comparison CSV/JSON
├── scripts/                       # Automated testing & browser verification scripts
│   └── verify_frontend_audit.py   # Selenium headless full-interface QA script
├── src/
│   ├── __init__.py
│   ├── download_data.py           # Automated UCI dataset acquisition
│   ├── preprocessing.py          # Data cleaning, outlier capping & pipeline fitting
│   ├── models.py                 # Multi-model training and evaluation
│   ├── fairness.py               # Disparity auditing & threshold optimization
│   └── explainability.py         # Feature impact attribution & clinical synthesis
├── tests/                         # Pytest test suite (16 tests, 100% pass)
│   ├── test_api.py               # Smoke & contract tests for all FastAPI endpoints
│   ├── test_leakage.py           # Patient grouping & preprocessor leak-free tests
│   └── test_metrics.py           # Sklearn benchmark & Wilson CI verification
├── requirements.txt               # Verified environment dependencies
├── run_pipeline.py                # End-to-end reproducible training & audit script
└── LICENSE                        # MIT License
```

---

---

## 6. Installation & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/VIKI7-HUB/hospital_readmission.git
cd hospital_readmission
```

### 2. Dataset Source & Placement
The project uses the **Diabetes 130-US Hospitals (1999–2008)** dataset from the UCI Machine Learning Repository (Strack et al., 2014).
- Place raw files in `data/raw/`:
  - `data/raw/diabetic_data.csv`
  - `data/raw/IDS_mapping.csv`
- If not present, acquire them automatically via:
  ```bash
  python src/download_data.py
  ```

### 3. Install Dependencies
```bash
# Python backend and pipeline dependencies
pip install -r requirements.txt

# Frontend UI dependencies
npm --prefix frontend install
```

### 4. Model Artifacts & Regeneration
All required model artifacts, preprocessor pipelines, and governance summaries are precomputed and included in the repository:
- `models/calibrated_ensemble.joblib`
- `models/pipeline_preprocessor.joblib`
- `models/hba1c_validation_experiment.json`
- `data/processed/worklist_precomputed.joblib`
- `fairness_governance/governance_full_artifacts.json`

To regenerate all model artifacts, re-run training, and reproduce all benchmarks from scratch:
```bash
python run_pipeline.py
```
*Executes leak-free data engineering, trains all 6 architectures (LR, RF, XGBoost, LightGBM, CatBoost, Calibrated Ensemble), optimizes clinical threshold (tau = 0.120), precomputes worklist artifacts, and audits demographic parity.*

### 5. Run Automated Tests
```bash
python -m pytest -v
```
*Validates 19 automated tests covering API endpoints, live scoring parity against offline test holdout (< 1e-6 diff), 0% patient leakage assertions, sklearn metric consistency, and Wilson score confidence intervals.*

### 6. Launch the Application
```bash
# Terminal 1: Start the FastAPI Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start the Vite / React Frontend
npm --prefix frontend run dev
```
Open your browser at **`http://localhost:5173`** to access the live clinical decision support portal.

*(Note: `app.py` is an archived legacy Streamlit prototype kept for historical reference. The primary production application is the FastAPI + React system.)*


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
