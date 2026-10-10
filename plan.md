# Hospital Readmission Risk Prediction -- Implementation Plan

> **Project 6B** -- AI-Based Predictive Analytics for Clinical Decision-Making
> **Workspace:** `c:\Users\vivek\OneDrive\Attachments\Desktop\Miniproject`
> **Backup (DO NOT TOUCH):** `D:\hackfest_backup`

---

## Specification Checklist (from Project 6B Image)

| # | Requirement | Status | Current Gap |
|---|-------------|--------|-------------|
| 1 | UCI Diabetes 130-US dataset (~100k encounters) | Done | -- |
| 2 | Binary readmission target | Done | -- |
| 3 | Missing-value handling with documented rationale | Partial | Rationale is in code comments but not surfaced as a standalone documented artifact |
| 4 | Outlier handling with documented rationale | Partial | Same -- Winsorization at 99th percentile is coded but not documented separately |
| 5 | Encoding & feature engineering with documented rationale | Partial | Encoding works; rationale needs a formal write-up |
| 6 | >= 3 model types with rationale | Done | LR, RF, XGBoost trained and saved |
| 7 | Common evaluation across models | Done | model_comparison_results.csv exists |
| 8 | Bias analysis across age, gender, race | Done | fairness_governance/ CSVs exist |
| 9 | Appropriate fairness metrics with justification | Partial | DPR & Equalized Odds computed; **justification for metric choice** not documented |
| 10 | Stretch -- fairness-aware models compared against base | Done | Group-threshold mitigation with mitigated CSVs |
| 11 | Application -- risk scoring for discharge readiness / readmission | Partial | Streamlit app exists but looks like a report, not a premium product |
| 12 | Guide discharge planning, follow-up, resource allocation | Partial | Basic resource allocation logic exists; UX is not production-grade |
| **KPI 1** | Accuracy, precision, recall (with metric-choice justification) + AUC | Partial | Numbers computed; **justification of why recall matters most** not documented |
| **KPI 2** | Comparison across >= 3 model types with rationale for chosen model | Partial | Comparison table exists; **rationale paragraph for choosing XGBoost** not documented |
| **KPI 3** | Fairness metrics across demographic groups + measured disparity | Done | CSVs + joblib saved |
| **KPI 4** | Improvement of fairness-aware models over base (stretch) | Partial | Mitigated thresholds computed; **before/after improvement summary** not generated |
| **KPI 5** | Documented data-quality handling: missing values, outliers, feature-selection | Partial | Code does this; **standalone documentation** missing |

---

## Architecture Overview

```
Miniproject/
--- data/
-   --- raw/               # UCI dataset (diabetic_data.csv)
-   --- processed/         # Cleaned CSV, preprocessor, train/test splits
--- models/                # Trained .joblib models + evaluation artifacts
--- fairness_governance/   # Bias audit CSVs + audit results joblib
--- src/
-   --- __init__.py
-   --- download_data.py   # Step 1: Data acquisition
-   --- preprocessing.py   # Step 2: Cleaning + feature engineering
-   --- models.py          # Step 3: Training + evaluation
-   --- fairness.py        # Step 4: Fairness audit + mitigation
-   --- explainability.py  # Patient-level risk scoring
--- docs/                  # NEW -- KPI documentation & rationale write-ups
--- run_pipeline.py        # Master orchestrator
--- app.py                 # Streamlit frontend (to be rebuilt as premium app)
--- requirements.txt
--- README.md
```

---

## Phase 1 -- Documentation & KPI Compliance

**Goal:** Fill every documentation gap the specification demands. No code logic changes -- only write-ups.

### 1.1 Create `docs/data_quality_report.md`

**Covers KPI 5:** *"Documented data-quality handling: missing values, outliers, feature-selection decisions"*

| Section | Content |
|---------|---------|
| Missing Values | Table of every column, its % missing, and the decision (drop, impute, or categorise as "Missing") with clinical rationale |
| Outliers | Explain 99th-percentile Winsorization on `number_outpatient`, `number_emergency`, `number_inpatient`, `total_visits` -- why 99th, why only these columns |
| Feature Engineering | `total_visits`, `high_prior_utilization`, `polypharmacy`, `num_med_changes`, `num_active_meds`, `lab_intensity_per_day`, ICD-9 category mapping -- rationale for each |
| Feature Selection / Exclusion | Why `encounter_id`, `patient_nbr`, `weight` (~97% missing), `examide`/`citoglipton` (constant), `payer_code`, `medical_specialty` were dropped or handled |

**Files to create:**
- `docs/data_quality_report.md` (NEW)

### 1.2 Create `docs/model_selection_rationale.md`

**Covers KPI 1 & KPI 2:**
- *"Predictive performance: accuracy, precision, recall (with justification of metric choice) + AUC"*
- *"Comparison across >= 3 model types with rationale for chosen model"*

| Section | Content |
|---------|---------|
| Why These 3 Models | LR = interpretable baseline; RF = non-linear bagging; XGBoost = gradient-boosted ensemble -- covers spectrum from simple to complex |
| Metric Choice Justification | Clinical argument: **Recall** is prioritised because missing a high-risk patient (False Negative) is far more dangerous than a false alarm (False Positive). AUC gives threshold-independent ranking. Accuracy is misleading on 89/11 imbalanced data. |
| Head-to-head Comparison Table | Reproduce `model_comparison_results.csv` with commentary |
| Why XGBoost Was Chosen | Best AUC (0.6896), best Recall (59.45%), handles class imbalance via `scale_pos_weight`, and supports feature importance natively |
| Hyperparameter Summary | Document choices for each model (C, max_depth, n_estimators, etc.) and why |

**Files to create:**
- `docs/model_selection_rationale.md` (NEW)

### 1.3 Create `docs/fairness_justification.md`

**Covers KPI 3 & KPI 4:**
- *"Fairness metrics across demographic groups + measured disparity"*
- *"Improvement of fairness-aware models over base models (stretch)"*

| Section | Content |
|---------|---------|
| Why DPR & Equalized Odds | Demographic Parity Ratio measures whether all groups are flagged at similar rates; Equalized Odds (TPR ratio) ensures high-risk patients in every group are equally likely to be detected |
| Base Model Disparity Summary | Reproduce per-attribute DPR and EOdds numbers with interpretation |
| Stretch: Before vs After Mitigation | Table comparing base thresholds (0.5 everywhere) vs group-specific thresholds with DPR/TPR improvement |
| Limitations | Acknowledge small subgroup sizes, correlation-based limitations |

**Files to create:**
- `docs/fairness_justification.md` (NEW)

### 1.4 Update `README.md`

- Add a "Documentation" section linking to all three docs
- Add a "KPI Summary" section mapping each KPI to its deliverable
- Update setup/run instructions

**Files to modify:**
- `README.md` (MODIFY)

### Phase 1 Verification

```
Test 1.1: Confirm docs/data_quality_report.md exists and contains sections for missing values, outliers, feature engineering, feature selection.
Test 1.2: Confirm docs/model_selection_rationale.md exists and contains metric justification + model comparison table + XGBoost rationale.
Test 1.3: Confirm docs/fairness_justification.md exists and contains DPR/EOdds justification + base vs mitigated comparison.
Test 1.4: Confirm README.md links to all three docs.
Test 1.5: Run `python run_pipeline.py` -- exit code 0 (no regressions).
```

---

## Phase 2 -- Backend Hardening & Pipeline Improvements

**Goal:** Strengthen the backend so every spec requirement is bulletproof. Code logic improvements only -- no UI changes.

### 2.1 Enhance `src/preprocessing.py` -- Add Logging & Rationale Annotations

- Add detailed docstrings with clinical rationale for every engineering step
- Add a `generate_data_quality_summary()` function that programmatically produces a JSON summary of:
  - Per-column missing % before cleaning
  - Outlier stats (pre and post Winsorization)
  - Feature counts
- Save this summary to `data/processed/data_quality_summary.json`

**Files to modify:**
- `src/preprocessing.py` (MODIFY)

**Files to create:**
- `data/processed/data_quality_summary.json` (generated at runtime)

### 2.2 Enhance `src/models.py` -- Richer Evaluation Artifacts

- Add ROC curve data (fpr, tpr arrays per model) saved to evaluation artifacts
- Add precision-recall curve data per model
- Add calibration check (Brier score already exists -- ensure it is saved to the CSV)
- Generate `models/model_rationale_summary.json` with programmatic model selection reasoning

**Files to modify:**
- `src/models.py` (MODIFY)

### 2.3 Enhance `src/fairness.py` -- Before/After Improvement Metrics

- After mitigation, compute **improvement deltas** (DPR improvement, TPR disparity reduction)
- Save a `fairness_governance/mitigation_improvement_summary.json` with clear before/after numbers
- Add docstring justifications for DPR and Equalized Odds choice

**Files to modify:**
- `src/fairness.py` (MODIFY)

**Files to create:**
- `fairness_governance/mitigation_improvement_summary.json` (generated at runtime)

### 2.4 Update `run_pipeline.py`

- After each step, print a summary of what was produced
- At the end, print a KPI compliance checklist with pass/fail
- Handle any Unicode encoding issues (ASCII-only print statements)

**Files to modify:**
- `run_pipeline.py` (MODIFY)

### Phase 2 Verification

```
Test 2.1: Run `python run_pipeline.py` -- exit code 0.
Test 2.2: Confirm data/processed/data_quality_summary.json exists and is valid JSON.
Test 2.3: Confirm models/model_comparison_results.csv has all metrics (AUC, Recall, Precision, Accuracy, F1, Brier).
Test 2.4: Confirm fairness_governance/mitigation_improvement_summary.json exists with before/after deltas.
Test 2.5: Confirm models/evaluation_artifacts.joblib contains ROC curve data and PR curve data.
```

---

## Phase 3 -- Premium Application Rebuild

**Goal:** Completely rebuild `app.py` as a premium, production-grade clinical application that doctors and patients can actually use. **No report feel. No emojis. No raw data tables. Backend stays invisible.**

> [!IMPORTANT]
> The Application layer is the ONLY thing visible to users. Data Layer, Modeling/AI, and Fairness/Governance run silently in the backend.

### 3.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Premium aesthetic** | Dark luxury theme (#080c14 base), Plus Jakarta Sans font, glassmorphism cards, CSS animations (fade-in, pulse, slide-up) |
| **No emojis** | Zero emoji characters anywhere in the UI |
| **No report feel** | No raw DataFrames, no CSV dumps. All data rendered through custom styled cards and interactive Plotly charts |
| **Real data only** | Every score, every encounter comes from the real UCI test set through the real XGBoost model. No fake patient names. |
| **Clinical workflow** | App should feel like an EHR discharge tool, not an analytics dashboard |

### 3.2 Application Views

#### View 1: Discharge Worklist (Primary Screen)

- **Summary bar:** 4 animated KPI cards (Total Encounters, High Risk Count, Avg Risk Score, Readmission Rate) -- using custom HTML/CSS, not `st.metric`
- **Patient queue:** Rendered as individual glassmorphism cards (not a DataFrame), each showing:
  - Encounter ID, Age, Gender, Stay Duration
  - Animated risk gauge (SVG arc or Plotly gauge)
  - Risk tier badge (color-coded: red/amber/green)
  - Targeted resource allocation tags
- **Pagination:** Show 10 cards at a time with Next/Previous navigation
- **Sort & Filter:** Sidebar filters for risk tier, age bracket, diagnosis category
- **Click-to-expand:** Clicking a card reveals full clinical detail + intervention recommendations

#### View 2: Individual Risk Assessment (Calculator)

- **Patient selector:** Dropdown to load a real UCI encounter OR manual input form
- **Live prediction:** On parameter change, immediately re-runs through preprocessor -> XGBoost -> displays result
- **Risk gauge:** Large animated SVG/Plotly gauge showing probability
- **Intervention panel:** Styled intervention cards (not bullet lists) based on `explainability.py`
- **Discharge action:** "Approve Discharge Plan" button that confirms resource orders

#### View 3: Model Performance Summary (For clinical admins only -- hidden behind a sidebar toggle)

- **Comparison chart:** Plotly grouped bar chart of AUC/Recall/Precision across 3 models
- **Selected model badge:** Visual indicator of why XGBoost was chosen
- **This view is optional** -- toggle-able from sidebar, not the default

### 3.3 CSS/Animation Requirements

```css
/* Required animations */
@keyframes fadeInUp { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.4) } 50% { box-shadow: 0 0 20px 10px rgba(59,130,246,0) } }
@keyframes slideIn { from { opacity:0; transform:translateX(-20px) } to { opacity:1; transform:translateX(0) } }

/* Glassmorphism cards */
.glass-card { background: rgba(15,23,42,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; }

/* Risk tier badges */
.badge-high { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.badge-moderate { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.badge-low { background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
```

### 3.4 File Changes

**Files to modify:**
- `app.py` -- Complete rewrite (keep imports + data loading, rewrite all rendering)

**Files to modify (if needed):**
- `src/explainability.py` -- May need to add a `get_top_risk_factors_for_display()` function returning simplified factor names suitable for the UI

### Phase 3 Verification

```
Test 3.1: Run `streamlit run app.py --server.headless true` -- app launches without errors.
Test 3.2: Visual inspection -- no emojis visible anywhere.
Test 3.3: Visual inspection -- no raw DataFrame/table dump visible on any default view.
Test 3.4: Visual inspection -- CSS animations are present (fade-in on cards, pulse on risk badges).
Test 3.5: Visual inspection -- font is Plus Jakarta Sans throughout.
Test 3.6: Functional test -- selecting a patient from the worklist shows real XGBoost risk score.
Test 3.7: Functional test -- adjusting sliders in the calculator recalculates the risk score in real time.
Test 3.8: Functional test -- all data comes from real UCI test set (verify encounter IDs match test split indices).
```

---

## Phase 4 -- Integration, Cleanup & Final Verification

**Goal:** End-to-end validation that every specification requirement and KPI is met.

### 4.1 Clean Up Legacy Files

- Remove old/unrelated files from a previous project:
  - `emotional_social_engineering_attacks.csv`
  - `exporter.py`
  - `gemini_helper.py`
  - `mitre_mapping.py`
  - `phishtank_analyzer.py`
  - `verified_online.csv`
  - `team-08_cybershield.pdf`
  - `Team8-Implementation-Video.mp4`
- Remove `__pycache__/` directories for old modules (exporter, gemini_helper, mitre_mapping, phishtank_analyzer)

**Files to delete:**
- `emotional_social_engineering_attacks.csv`
- `exporter.py`
- `gemini_helper.py`
- `mitre_mapping.py`
- `phishtank_analyzer.py`
- `verified_online.csv`
- `team-08_cybershield.pdf`
- `Team8-Implementation-Video.mp4`
- `__pycache__/exporter.cpython-313.pyc`
- `__pycache__/gemini_helper.cpython-313.pyc`
- `__pycache__/mitre_mapping.cpython-313.pyc`
- `__pycache__/phishtank_analyzer.cpython-313.pyc`

### 4.2 Update `requirements.txt`

Ensure it includes only the packages actually used:
```
pandas
numpy
scikit-learn
xgboost
joblib
streamlit
plotly
matplotlib
seaborn
fairlearn
```

### 4.3 Final `README.md` Update

- Project title & description matching spec
- Installation instructions
- How to run the pipeline (`python run_pipeline.py`)
- How to launch the app (`streamlit run app.py`)
- KPI compliance matrix
- Links to all docs
- Architecture diagram (text-based)

### 4.4 End-to-End Smoke Test

Run the full pipeline from scratch and launch the app:

```bash
# Step 1: Run full pipeline
python run_pipeline.py

# Step 2: Verify all artifacts exist
# - data/raw/diabetic_data.csv
# - data/processed/clean_diabetic_data.csv
# - data/processed/preprocessor.joblib
# - data/processed/train_test_data.joblib
# - data/processed/data_quality_summary.json
# - models/logistic_regression.joblib
# - models/random_forest.joblib
# - models/xgboost.joblib
# - models/evaluation_artifacts.joblib
# - models/model_comparison_results.csv
# - fairness_governance/fairness_audit_results.joblib
# - fairness_governance/mitigation_improvement_summary.json
# - fairness_governance/fairness_bias_analysis_*.csv
# - fairness_governance/fairness_mitigated_*.csv

# Step 3: Launch app
streamlit run app.py --server.headless true
```

### Phase 4 Verification

```
Test 4.1: No legacy/unrelated files remain in project root.
Test 4.2: requirements.txt contains all needed packages and no extras.
Test 4.3: README.md has complete documentation with KPI matrix.
Test 4.4: `python run_pipeline.py` exits with code 0.
Test 4.5: All artifact files listed above exist after pipeline run.
Test 4.6: `streamlit run app.py` launches without errors.
Test 4.7: App displays real data from UCI dataset with premium UI.
```

---

## KPI Compliance Matrix

| KPI | Requirement | Deliverable | Phase |
|-----|-------------|-------------|-------|
| **KPI 1** | Accuracy, precision, recall (with justification) + AUC | `docs/model_selection_rationale.md` + `models/model_comparison_results.csv` | Phase 1 + 2 |
| **KPI 2** | Comparison across >= 3 models with rationale | `docs/model_selection_rationale.md` + `models/model_rationale_summary.json` | Phase 1 + 2 |
| **KPI 3** | Fairness metrics across demographics + disparity | `docs/fairness_justification.md` + `fairness_governance/*.csv` | Phase 1 + 2 |
| **KPI 4** | Improvement of fairness-aware models (stretch) | `docs/fairness_justification.md` + `fairness_governance/mitigation_improvement_summary.json` | Phase 1 + 2 |
| **KPI 5** | Documented data-quality handling | `docs/data_quality_report.md` + `data/processed/data_quality_summary.json` | Phase 1 + 2 |

---

## Implementation Stack Compliance Matrix

| Layer | Requirement | Deliverable | Phase |
|-------|-------------|-------------|-------|
| **Data Layer** | pandas/scikit-learn -- missing-value, outlier, encoding, feature engineering with documented rationale | `src/preprocessing.py` + `docs/data_quality_report.md` | Phase 1 + 2 |
| **Modeling/AI** | >= 3 model types (LR, RF, XGBoost) compared on common evaluation | `src/models.py` + `docs/model_selection_rationale.md` | Phase 1 + 2 |
| **Fairness/Governance** | Bias analysis (age, gender, race), fairness metrics, stretch mitigation | `src/fairness.py` + `docs/fairness_justification.md` | Phase 1 + 2 |
| **Application** | Risk scoring for discharge readiness/readmission, discharge planning, follow-up, resource allocation | `app.py` (premium rebuild) | Phase 3 |

---

## File Change Summary

### New Files (6)
| File | Phase | Purpose |
|------|-------|---------|
| `docs/data_quality_report.md` | 1 | KPI 5 documentation |
| `docs/model_selection_rationale.md` | 1 | KPI 1 + 2 documentation |
| `docs/fairness_justification.md` | 1 | KPI 3 + 4 documentation |
| `data/processed/data_quality_summary.json` | 2 | Runtime-generated quality stats |
| `models/model_rationale_summary.json` | 2 | Runtime-generated model selection data |
| `fairness_governance/mitigation_improvement_summary.json` | 2 | Runtime-generated before/after metrics |

### Modified Files (7)
| File | Phase | Changes |
|------|-------|---------|
| `README.md` | 1 + 4 | Add doc links, KPI matrix, architecture |
| `src/preprocessing.py` | 2 | Add rationale docstrings, quality summary generator |
| `src/models.py` | 2 | Add ROC/PR curve data, rationale JSON |
| `src/fairness.py` | 2 | Add improvement deltas, justification docstrings |
| `src/explainability.py` | 3 | Add UI-friendly risk factor formatting |
| `run_pipeline.py` | 2 | Add KPI compliance checklist at end |
| `app.py` | 3 | Complete premium UI rebuild |

### Deleted Files (8)
| File | Phase | Reason |
|------|-------|--------|
| `emotional_social_engineering_attacks.csv` | 4 | Unrelated to Project 6B |
| `exporter.py` | 4 | Unrelated |
| `gemini_helper.py` | 4 | Unrelated |
| `mitre_mapping.py` | 4 | Unrelated |
| `phishtank_analyzer.py` | 4 | Unrelated |
| `verified_online.csv` | 4 | Unrelated |
| `team-08_cybershield.pdf` | 4 | Unrelated |
| `Team8-Implementation-Video.mp4` | 4 | Unrelated |

---

## Estimated Effort

| Phase | Scope | Estimated Tasks |
|-------|-------|-----------------|
| Phase 1 | Documentation only | 4 files to create/modify |
| Phase 2 | Backend hardening | 4 files to modify |
| Phase 3 | Premium app rebuild | 1-2 files, major rewrite |
| Phase 4 | Cleanup + final test | 8 deletions + final validation |

---

> [!CAUTION]
> **DO NOT modify anything in `D:\hackfest_backup`.** That is the safety copy. All work happens in `c:\Users\vivek\OneDrive\Attachments\Desktop\Miniproject`.
