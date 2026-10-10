import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import pandas as pd
import streamlit as st
from loaders import load_json, load_table
from style import setup, stat_row

setup("Hospital readmission risk")

st.write(
    "This system predicts the risk of hospital readmission within 30 days of discharge for "
    "diabetic inpatients. The models and evaluations are built on the UCI Diabetes 130-US hospitals "
    "dataset spanning clinical encounters from 1999 to 2008."
)

dq = load_json("data_quality.json")
champ = load_json("champion.json")
metrics = load_json("metrics.json")
fairness_summary = load_json("fairness_summary.json")
fairness_mitigation = load_table("fairness_mitigation.csv")
feature_evidence = load_table("feature_evidence.csv")

clean_encounters = f"{dq['row_counts']['clean']:,}"
patients_val = (
    dq["patients"].get("unique_patients", dq["patients"])
    if isinstance(dq["patients"], dict)
    else dq["patients"]
)
patients = f"{patients_val:,}"
pos_share = dq["positive_class_share"]
if isinstance(pos_share, dict):
    pos_share = pos_share.get("clean", pos_share.get("raw", 0.0))
readmit_share = f"{float(pos_share):.1%}"
champion_name = champ["model"]

stat_row(
    [
        ("Encounters after cleaning", clean_encounters),
        ("Patients", patients),
        ("Readmitted within 30 days", readmit_share),
        ("Champion model", champion_name),
    ]
)

st.write("---")
st.subheader("KPI scorecard")

champ_metrics = metrics[champion_name]
acc = champ_metrics["accuracy"]
prec = champ_metrics["precision"]
rec = champ_metrics["recall"]
auc = champ_metrics["roc_auc"]
kpi1 = f"accuracy {acc:.1%}, precision {prec:.1%}, recall {rec:.1%}, ROC-AUC {auc:.3f}"

n_models = len(metrics)
kpi2 = f"{n_models} models compared; champion {champion_name}"

eod_items = []
for attr in ["age_band", "gender", "race"]:
    if attr in fairness_summary:
        val = fairness_summary[attr]["equalized_odds_difference"] * 100
        eod_items.append(f"{attr}: {val:.1f} pp")
kpi3 = ", ".join(eod_items)

tpr_items = []
for attr in ["age_band", "gender", "race"]:
    base_rows = fairness_mitigation[
        (fairness_mitigation["attribute"] == attr) & (fairness_mitigation["variant"] == "base")
    ]
    mit_rows = fairness_mitigation[
        (fairness_mitigation["attribute"] == attr)
        & (fairness_mitigation["variant"] == "group_threshold")
    ]
    if not base_rows.empty and not mit_rows.empty:
        base_tpr = float(base_rows["tpr_difference"].iloc[0])
        mit_tpr = float(mit_rows["tpr_difference"].iloc[0])
        diff_pp = (mit_tpr - base_tpr) * 100
        tpr_items.append(f"{attr}: {diff_pp:+.1f} pp")
kpi4 = ", ".join(tpr_items)

k_kept = int((feature_evidence["decision"] == "kept").sum())
d_dropped = int((feature_evidence["decision"] == "dropped").sum())
m_missing = sum(
    1
    for v in dq["missing_percentages"].values()
    if isinstance(v, dict) and v.get("raw") and v["raw"] > 0
)
kpi5 = (
    f"{k_kept} features kept, {d_dropped} dropped; {m_missing} columns with missing values handled"
)

scorecard_df = pd.DataFrame(
    [
        {
            "KPI": "Accuracy, precision, recall, AUC",
            "Result": kpi1,
            "Page": "Models",
        },
        {
            "KPI": "At least three model types compared",
            "Result": kpi2,
            "Page": "Models",
        },
        {
            "KPI": "Fairness across age, gender, race",
            "Result": kpi3,
            "Page": "Fairness",
        },
        {
            "KPI": "Fairness-aware model versus base",
            "Result": kpi4,
            "Page": "Fairness",
        },
        {
            "KPI": "Missing values, outliers, feature selection documented",
            "Result": kpi5,
            "Page": "Data quality",
        },
    ]
)

st.dataframe(scorecard_df, hide_index=True, width="stretch")

st.write("---")
st.subheader("Sections")

col1, col2 = st.columns(2)
try:
    with col1:
        st.page_link("pages/data_quality.py", label="Data quality")
        st.page_link("pages/exploration.py", label="Exploration")
        st.page_link("pages/models.py", label="Models")
        st.page_link("pages/threshold.py", label="Threshold and capacity")
    with col2:
        st.page_link("pages/explainability.py", label="Explainability")
        st.page_link("pages/fairness.py", label="Fairness")
        st.page_link("pages/patient_risk.py", label="Patient risk")
except Exception:
    pass
