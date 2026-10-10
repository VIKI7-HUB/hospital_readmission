import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from charts import waterfall_chart
from loaders import load_json, load_table
from style import GREY, INK, RUST, TEAL, figure, setup, stat_row

from readmission import explain
from readmission.explain import FEATURE_LABELS
from readmission.scoring import frame_for_encounters, predict_raw

setup("Patient risk")

champion_info = load_json("champion.json")
champion_name = champion_info.get("champion", champion_info.get("model", "random_forest"))
tiers = load_json("tiers.json")
test_preds = load_table("test_predictions.parquet").copy()
if "p_cal" not in test_preds.columns and "probability_calibrated" in test_preds.columns:
    test_preds["p_cal"] = test_preds["probability_calibrated"]
elif "probability_calibrated" not in test_preds.columns and "p_cal" in test_preds.columns:
    test_preds["probability_calibrated"] = test_preds["p_cal"]
val_scores = load_table(f"scores/{champion_name}__val.parquet")
clean_data = load_table(
    "clean.parquet",
    columns=[
        "time_in_hospital",
        "num_medications",
        "number_inpatient",
        "number_emergency",
        "number_outpatient",
        "number_diagnoses",
        "age",
        "discharge_disposition_id",
        "A1Cresult",
        "insulin",
        "change",
        "diag_1",
    ],
)

calibrator = joblib.load(ROOT / "artifacts" / "models" / "calibrators" / f"{champion_name}.joblib")
val_p_cal = calibrator.predict(val_scores["p_raw"].to_numpy())

with (ROOT / "configs" / "care_actions.yaml").open(encoding="utf-8") as f:
    care_actions = yaml.safe_load(f)


def assign_tier(p_cal: float) -> str:
    if p_cal >= tiers["high_at_or_above"]:
        return "High"
    if p_cal >= tiers["elevated_from"]:
        return "Elevated"
    return "Low"


st.header("Patient information")
c_src1, c_src2 = st.columns([1, 1])

high_tier_encs = test_preds[test_preds["tier"] == "High"]["encounter_id"].tolist()
all_test_encs = test_preds["encounter_id"].tolist()
default_enc = high_tier_encs[0] if high_tier_encs else all_test_encs[0]

with c_src1:
    patient_source = st.radio(
        "Patient source",
        ["Held-out encounter", "Enter values"],
        horizontal=True,
    )

if patient_source == "Held-out encounter":
    with c_src2:
        default_index = all_test_encs.index(default_enc) if default_enc in all_test_encs else 0
        selected_enc = st.selectbox(
            "Select test encounter ID",
            all_test_encs,
            index=default_index,
        )
    patient_frame = frame_for_encounters([selected_enc]).copy()
    summary_df = pd.DataFrame(
        [
            {
                "Age band": patient_frame["age"].iloc[0],
                "Time in hospital": patient_frame["time_in_hospital"].iloc[0],
                "Number of inpatient visits": patient_frame["number_inpatient"].iloc[0],
                "Discharge group": patient_frame["discharge_group"].iloc[0],
                "Primary diagnosis category": patient_frame["diag_1_category"].iloc[0],
            }
        ]
    )
    st.dataframe(summary_df, hide_index=True)
else:
    with c_src2:
        template_enc = st.selectbox(
            "Base template encounter",
            all_test_encs,
            index=all_test_encs.index(default_enc) if default_enc in all_test_encs else 0,
        )
    patient_frame = frame_for_encounters([template_enc]).copy()

    col_in1, col_in2, col_in3 = st.columns(3)
    with col_in1:
        tih_min = int(clean_data["time_in_hospital"].min())
        tih_max = int(clean_data["time_in_hospital"].max())
        curr_tih = int(patient_frame["time_in_hospital"].iloc[0])
        val_tih = st.slider(
            "Time in hospital (days)",
            min_value=tih_min,
            max_value=tih_max,
            value=min(max(curr_tih, tih_min), tih_max),
        )

        med_min = int(clean_data["num_medications"].min())
        med_max = int(clean_data["num_medications"].max())
        curr_med = int(patient_frame["num_medications"].iloc[0])
        val_med = st.slider(
            "Number of medications",
            min_value=med_min,
            max_value=med_max,
            value=min(max(curr_med, med_min), med_max),
        )

        curr_inp = int(patient_frame["number_inpatient"].iloc[0])
        val_inp = st.slider(
            "Prior inpatient stays (past year)",
            min_value=0,
            max_value=int(clean_data["number_inpatient"].max()),
            value=min(curr_inp, int(clean_data["number_inpatient"].max())),
        )

        curr_emg = int(patient_frame["number_emergency"].iloc[0])
        val_emg = st.slider(
            "Prior emergency visits (past year)",
            min_value=0,
            max_value=int(clean_data["number_emergency"].max()),
            value=min(curr_emg, int(clean_data["number_emergency"].max())),
        )

    with col_in2:
        curr_out = int(patient_frame["number_outpatient"].iloc[0])
        val_out = st.slider(
            "Prior outpatient visits (past year)",
            min_value=0,
            max_value=int(clean_data["number_outpatient"].max()),
            value=min(curr_out, int(clean_data["number_outpatient"].max())),
        )

        curr_diag_n = int(patient_frame["number_diagnoses"].iloc[0])
        val_diag_n = st.slider(
            "Number of documented diagnoses",
            min_value=int(clean_data["number_diagnoses"].min()),
            max_value=int(clean_data["number_diagnoses"].max()),
            value=curr_diag_n,
        )

        age_levels = sorted(clean_data["age"].dropna().unique().tolist())
        curr_age = str(patient_frame["age"].iloc[0])
        val_age = st.selectbox(
            "Age band",
            age_levels,
            index=age_levels.index(curr_age) if curr_age in age_levels else 0,
        )

        discharge_levels = ["home", "facility", "home_with_services", "left_ama", "other"]
        curr_dc = str(patient_frame["discharge_group"].iloc[0])
        val_dc = st.selectbox(
            "Discharge destination",
            discharge_levels,
            index=discharge_levels.index(curr_dc) if curr_dc in discharge_levels else 0,
        )

    with col_in3:
        a1c_levels = sorted(clean_data["A1Cresult"].dropna().unique().tolist())
        curr_a1c = str(patient_frame["A1Cresult"].iloc[0])
        val_a1c = st.selectbox(
            "HbA1c test result",
            a1c_levels,
            index=a1c_levels.index(curr_a1c) if curr_a1c in a1c_levels else 0,
        )

        insulin_levels = sorted(clean_data["insulin"].dropna().unique().tolist())
        curr_ins = str(patient_frame["insulin"].iloc[0])
        val_ins = st.selectbox(
            "Insulin therapy status",
            insulin_levels,
            index=insulin_levels.index(curr_ins) if curr_ins in insulin_levels else 0,
        )

        change_levels = sorted(clean_data["change"].dropna().unique().tolist())
        curr_chg = str(patient_frame["change"].iloc[0])
        val_chg = st.selectbox(
            "Diabetes medication changed",
            change_levels,
            index=change_levels.index(curr_chg) if curr_chg in change_levels else 0,
        )

        diag_cats = [
            "circulatory", "respiratory", "digestive", "diabetes",
            "genitourinary", "musculoskeletal", "injury", "neoplasms", "other",
        ]
        curr_diag_cat = str(patient_frame["diag_1_category"].iloc[0])
        val_diag_cat = st.selectbox(
            "Primary diagnosis chapter",
            diag_cats,
            index=diag_cats.index(curr_diag_cat) if curr_diag_cat in diag_cats else 0,
        )

    patient_frame["time_in_hospital"] = val_tih
    patient_frame["num_medications"] = val_med
    patient_frame["number_inpatient"] = val_inp
    patient_frame["number_emergency"] = val_emg
    patient_frame["number_outpatient"] = val_out
    patient_frame["number_diagnoses"] = val_diag_n
    patient_frame["prior_visits_total"] = val_inp + val_emg + val_out
    patient_frame["age"] = val_age
    patient_frame["discharge_group"] = val_dc
    patient_frame["A1Cresult"] = val_a1c
    patient_frame["insulin"] = val_ins
    patient_frame["change"] = val_chg
    patient_frame["diag_1_category"] = val_diag_cat

# Scoring
p_raw = predict_raw(champion_name, patient_frame)
p_cal = float(calibrator.predict(p_raw)[0])
patient_tier = assign_tier(p_cal)
patient_percentile = float((val_p_cal < p_cal).mean() * 100)

st.header("Risk estimation")
stat_row(
    [
        ("Calibrated 30-day risk", f"{p_cal:.1%}"),
        ("Assigned tier", patient_tier),
        ("Cohort percentile", f"{patient_percentile:.0f}th"),
    ]
)

# Fig 1: Risk distribution histogram
fig1 = go.Figure()
fig1.add_trace(
    go.Histogram(
        x=test_preds["p_cal"],
        nbinsx=40,
        marker_color=GREY,
        name="Test cohort",
        opacity=0.7,
    )
)
fig1.add_vline(
    x=tiers["elevated_from"],
    line=dict(dash="dot", color=INK, width=1.2),
    annotation_text="Elevated boundary",
    annotation_position="top left",
)
fig1.add_vline(
    x=tiers["high_at_or_above"],
    line=dict(dash="dot", color=RUST, width=1.2),
    annotation_text="High boundary",
    annotation_position="top right",
)
fig1.add_vline(
    x=p_cal,
    line=dict(dash="solid", color=TEAL, width=2.5),
    annotation_text=f"This patient ({p_cal:.1%})",
    annotation_position="top",
)
fig1.update_layout(
    title="Patient risk within test cohort distribution",
    xaxis_title="Predicted readmission probability",
    yaxis_title="Patient count",
    xaxis=dict(tickformat=".0%"),
    height=520,
    showlegend=False,
)

explain_res = explain.explain_rows(patient_frame)
base_contrib = explain_res["base"]
margin_contrib = float(explain_res["margin"][0])
c_series = explain_res["contribs"].iloc[0]
v_series = explain_res["values"].iloc[0]

fig2 = waterfall_chart(base_contrib, margin_contrib, c_series, FEATURE_LABELS, height=520)

col_chart1, col_chart2 = st.columns([1, 1])
with col_chart1:
    figure(
        fig1,
        1,
        "Calibrated readmission risk of current encounter compared against held-out test cohort distribution.",
    )
with col_chart2:
    figure(
        fig2,
        2,
        "TreeSHAP waterfall plot breaking down encounter risk into baseline log-odds and feature adjustments.",
    )

st.subheader("Explanation summary")
sentence_summary = explain.top_sentence(c_series, v_series)
st.write(sentence_summary)

st.write("---")

# "What changes if..." section
st.header("What changes if...")
st.caption(
    "This shows how the model's output changes. It does not show that changing the item would change the patient's outcome."
)

col_mod1, col_mod2 = st.columns(2)

modifiable_frame = patient_frame.copy()

with col_mod1:
    dc_options = ["home", "facility", "home_with_services", "left_ama", "other"]
    cur_dc = str(patient_frame["discharge_group"].iloc[0])
    new_dc = st.selectbox(
        "Discharge destination (adjusted)",
        dc_options,
        index=dc_options.index(cur_dc) if cur_dc in dc_options else 0,
    )
    modifiable_frame["discharge_group"] = new_dc

    ins_options = ["No", "Steady", "Up", "Down"]
    cur_ins = str(patient_frame["insulin"].iloc[0])
    new_ins = st.selectbox(
        "Insulin regimen (adjusted)",
        ins_options,
        index=ins_options.index(cur_ins) if cur_ins in ins_options else 0,
    )
    modifiable_frame["insulin"] = new_ins

with col_mod2:
    chg_options = ["No", "Ch"]
    cur_chg = str(patient_frame["change"].iloc[0])
    new_chg = st.selectbox(
        "Medication change (adjusted)",
        chg_options,
        index=chg_options.index(cur_chg) if cur_chg in chg_options else 0,
    )
    modifiable_frame["change"] = new_chg

    a1c_options = ["None", "Norm", ">7", ">8"]
    cur_a1c = str(patient_frame["A1Cresult"].iloc[0])
    new_a1c = st.selectbox(
        "HbA1c result (adjusted)",
        a1c_options,
        index=a1c_options.index(cur_a1c) if cur_a1c in a1c_options else 0,
    )
    modifiable_frame["A1Cresult"] = new_a1c

new_p_raw = predict_raw(champion_name, modifiable_frame)
new_p_cal = float(calibrator.predict(new_p_raw)[0])
delta_pp = (new_p_cal - p_cal) * 100

stat_row(
    [
        ("Baseline calibrated risk", f"{p_cal:.1%}"),
        ("Adjusted calibrated risk", f"{new_p_cal:.1%}"),
        ("Risk delta", f"{delta_pp:+.1f} pp"),
    ]
)

st.write("---")

# "Suggested follow-up" section
st.header("Suggested follow-up")
st.info(care_actions.get("note", "Illustrative suggestions for discussion. Not clinical guidance."))

st.subheader(f"Tier suggestions ({patient_tier} risk)")
tier_suggestions = care_actions.get("tiers", {}).get(patient_tier, [])
for item in tier_suggestions:
    st.write(f"- {item}")

applicable_flags = []
if int(patient_frame["num_medications"].iloc[0]) >= 15:
    applicable_flags.append(care_actions["flags"]["many_medications"])
if int(patient_frame["number_inpatient"].iloc[0]) >= 2:
    applicable_flags.append(care_actions["flags"]["repeat_admissions"])
if int(patient_frame["time_in_hospital"].iloc[0]) >= 7:
    applicable_flags.append(care_actions["flags"]["long_stay"])

if applicable_flags:
    st.subheader("Clinical context flags")
    for flag_text in applicable_flags:
        st.write(f"- {flag_text}")
