import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from charts import interval_chart
from loaders import load_json, load_table
from style import GREY, TEAL, figure, setup

from readmission import eda
from readmission.features import _diagnosis_category, build_fairness_attributes

setup("Exploration")

REQUIRED_COLS = [
    "age",
    "gender",
    "readmit_30",
    "number_inpatient",
    "number_emergency",
    "time_in_hospital",
    "discharge_disposition_id",
    "admission_source_id",
    "diag_1",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_diagnoses",
    "number_outpatient",
]


@st.cache_data(show_spinner=False)
def load_prepared_data() -> pd.DataFrame:
    df = load_table("clean.parquet", columns=REQUIRED_COLS)
    cfg = load_json("feature_config.json")

    df["age_band"] = build_fairness_attributes(df)["age_band"]

    dc_map = cfg["discharge_group"]
    dc_names = {
        "home": "Home",
        "facility": "Facility",
        "home_with_services": "Home with services",
        "left_ama": "Left AMA",
        "other": "Other",
    }
    df["discharge_group"] = (
        df["discharge_disposition_id"].astype(str).map(dc_map).map(dc_names).fillna("Other")
    )

    src_map = cfg["admission_source"]
    src_labels = df["admission_source_id"].astype(str).map(src_map).fillna("Other")
    df["admission_source_group"] = src_labels.apply(
        lambda s: (
            "Emergency Room"
            if "Emergency" in s
            else ("Referral" if "Referral" in s else ("Transfer" if "Transfer" in s else "Other"))
        )
    )

    df["primary_diagnosis_category"] = (
        df["diag_1"].apply(_diagnosis_category).astype(str).str.capitalize()
    )
    df["inpatient_disp"] = df["number_inpatient"].apply(lambda v: "5+" if v >= 5 else str(int(v)))
    df["emergency_disp"] = df["number_emergency"].apply(lambda v: "5+" if v >= 5 else str(int(v)))
    return df


full_df = load_prepared_data()


@st.fragment
def render_filtered_charts(data: pd.DataFrame) -> None:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        age_bands = ["<40", "40-59", "60-79", "80+"]
        avail_ages = [b for b in age_bands if b in data["age_band"].values]
        selected_age = st.multiselect("Filter by age band", avail_ages, default=avail_ages)
    with col_f2:
        avail_genders = sorted(data["gender"].dropna().unique().tolist())
        selected_gender = st.multiselect("Filter by gender", avail_genders, default=avail_genders)

    if not selected_age or not selected_gender:
        st.warning("Please select at least one age band and gender.")
        return

    df = data[data["age_band"].isin(selected_age) & data["gender"].isin(selected_gender)]
    if df.empty:
        st.warning("No encounter records match the selected filters.")
        return

    # Fig 1: Class balance
    counts = df["readmit_30"].value_counts().sort_index()
    labels = ["Not readmitted", "Readmitted within 30 days"]
    vals = [int(counts.get(0, 0)), int(counts.get(1, 0))]
    total = sum(vals) if sum(vals) > 0 else 1
    fig1 = go.Figure(
        go.Bar(
            x=vals,
            y=labels,
            orientation="h",
            marker_color=[GREY, TEAL],
            text=[f"{v:,} ({v / total:.1%})" for v in vals],
            textposition="auto",
        )
    )
    fig1.update_layout(
        height=220,
        xaxis_title="Encounter count",
        yaxis_title="Outcome",
    )
    figure(
        fig1,
        1,
        "Class balance showing count and share of encounters readmitted within 30 days.",
    )

    # Figs 2 to 7: Six rate interval charts in 2x3 grid
    col1, col2 = st.columns(2)

    with col1:
        # Fig 2: number_inpatient
        t_inp = eda.rate_table(df, "inpatient_disp")
        t_inp["sorter"] = t_inp["inpatient_disp"].map(
            {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5+": 5}
        )
        t_inp = t_inp.sort_values(by="sorter").drop(columns=["sorter"])
        fig2 = interval_chart(
            t_inp,
            "inpatient_disp",
            "Readmission rate by prior inpatient stays",
            x_title="Readmission rate",
        )
        figure(
            fig2,
            2,
            "Readmission rate by prior inpatient encounters in the past 12 months with 95% Wilson intervals.",
        )

        # Fig 4: time_in_hospital
        t_tih = eda.rate_table(df, "time_in_hospital").sort_values(by="time_in_hospital")
        fig4 = interval_chart(
            t_tih,
            "time_in_hospital",
            "Readmission rate by length of stay (days)",
            x_title="Readmission rate",
        )
        figure(
            fig4,
            4,
            "Readmission rate by encounter length of stay (days) with 95% Wilson intervals.",
        )

        # Fig 6: discharge_group
        t_dc = eda.rate_table(df, "discharge_group").sort_values(by="rate", ascending=False)
        fig6 = interval_chart(
            t_dc,
            "discharge_group",
            "Readmission rate by discharge group",
            x_title="Readmission rate",
        )
        figure(
            fig6,
            6,
            "Readmission rate by discharge destination category with 95% Wilson intervals.",
        )

    with col2:
        # Fig 3: number_emergency
        t_emg = eda.rate_table(df, "emergency_disp")
        t_emg["sorter"] = t_emg["emergency_disp"].map(
            {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5+": 5}
        )
        t_emg = t_emg.sort_values(by="sorter").drop(columns=["sorter"])
        fig3 = interval_chart(
            t_emg,
            "emergency_disp",
            "Readmission rate by prior emergency visits",
            x_title="Readmission rate",
        )
        figure(
            fig3,
            3,
            "Readmission rate by prior emergency room visits in the past 12 months with 95% Wilson intervals.",
        )

        # Fig 5: age_band
        t_age = eda.rate_table(df, "age_band")
        t_age["sorter"] = t_age["age_band"].map(
            {"<40": 0, "40-59": 1, "60-79": 2, "80+": 3, "Unknown": 4}
        )
        t_age = t_age.sort_values(by="sorter").drop(columns=["sorter"])
        fig5 = interval_chart(
            t_age,
            "age_band",
            "Readmission rate by age band",
            x_title="Readmission rate",
        )
        figure(
            fig5,
            5,
            "Readmission rate across patient age bands with 95% Wilson intervals.",
        )

        # Fig 7: primary diagnosis category (sorted by rate)
        t_diag = eda.rate_table(df, "primary_diagnosis_category").sort_values(
            by="rate", ascending=False
        )
        fig7 = interval_chart(
            t_diag,
            "primary_diagnosis_category",
            "Readmission rate by primary diagnosis category",
            x_title="Readmission rate",
        )
        figure(
            fig7,
            7,
            "Readmission rate by primary ICD-9 diagnosis category, sorted by rate, with 95% Wilson intervals.",
        )

    # Fig 8: Flow diagram (Sankey)
    df_sankey = df.copy()
    df_sankey["outcome"] = df_sankey["readmit_30"].map(
        {1: "Readmitted within 30 days", 0: "Not readmitted"}
    )
    labels, source, target, value = eda.sankey_links(
        df_sankey, ["admission_source_group", "discharge_group", "outcome"]
    )
    fig8 = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="#1c1f23", width=0.5),
                    label=labels,
                    color="#8a8f98",
                ),
                link=dict(
                    source=source,
                    target=target,
                    value=value,
                    color="rgba(138, 143, 152, 0.35)",
                ),
            )
        ]
    )
    fig8.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    figure(
        fig8,
        8,
        "Clinical pathway flow connecting admission source, discharge destination, and 30-day readmission outcome.",
    )

    # Fig 9: Treemap of primary diagnosis category
    t_tree = eda.rate_table(df, "primary_diagnosis_category").rename(
        columns={"n": "encounters", "rate": "readmission rate"}
    )
    fig9 = px.treemap(
        t_tree,
        path=["primary_diagnosis_category"],
        values="encounters",
        color="readmission rate",
        color_continuous_scale=[[0, "#e8efef"], [1, "#1f6f78"]],
    )
    fig9.update_traces(
        hovertemplate="Category: %{label}<br>Encounters: %{value:,}<br>Readmission rate: %{color:.1%}<extra></extra>"
    )
    fig9.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
    figure(
        fig9,
        9,
        "Primary diagnosis categories sized by encounter volume and shaded by 30-day readmission rate.",
    )

    # Fig 10: Correlation heatmap of numeric inputs
    numeric_inputs = [
        "time_in_hospital",
        "num_lab_procedures",
        "num_procedures",
        "num_medications",
        "number_diagnoses",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
    ]
    corr = df[numeric_inputs].corr()
    fig10 = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=numeric_inputs,
            y=numeric_inputs,
            zmid=0,
            colorscale=[[0, "#b5523b"], [0.5, "#fbfaf6"], [1, "#1f6f78"]],
            text=corr.round(2).values.astype(str),
            texttemplate="%{text}",
            hoverongaps=False,
        )
    )
    fig10.update_layout(height=480, margin=dict(l=40, r=40, t=20, b=40))
    figure(
        fig10,
        10,
        "Pearson correlation matrix across numerical clinical features.",
    )


render_filtered_charts(full_df)

hba1c_path = ROOT / "artifacts" / "hba1c.json"
if hba1c_path.exists():
    st.header("11. HbA1c testing and readmission")
    hba1c_data = load_json("hba1c.json")

    crude_df = pd.DataFrame(hba1c_data["crude"])
    fig11 = interval_chart(
        crude_df,
        "group",
        "Readmission rate by HbA1c testing category",
        x_title="Readmission rate",
    )
    figure(
        fig11,
        11,
        "Crude readmission rates by HbA1c testing status with 95% Wilson intervals on training split.",
    )

    st.subheader("Adjusted odds ratios (cluster-robust)")
    adj_df = pd.DataFrame(hba1c_data["adjusted"])
    formatter = {"or": "{:.3f}", "lower": "{:.3f}", "upper": "{:.3f}", "p_value": "{:.4f}"}
    st.dataframe(adj_df.style.format(formatter), hide_index=True, width="stretch")

    for _, row in adj_df.iterrows():
        grp = row["group"]
        o = float(row["or"])
        lo = float(row["lower"])
        hi = float(row["upper"])
        msg = (
            f"Compared with patients not tested, the adjusted odds of readmission for {grp} "
            f"are {o:.3f} (95% interval {lo:.3f} to {hi:.3f})."
        )
        if lo <= 1.0 <= hi:
            msg += " The interval includes 1.0, indicating no statistically clear difference."
        st.write(msg)

    st.write(
        "These are associations in observational data and do not show that testing causes the difference. "
        "(Source question: Strack et al., 2014)."
    )

