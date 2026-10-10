import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from loaders import load_json, load_table
from plotly.subplots import make_subplots
from style import GREY, TEAL, figure, setup

setup("Data quality")

dq = load_json("data_quality.json")
caps = load_json("caps.json")
split_data = load_json("split.json")
fe = load_table("feature_evidence.csv")

st.header("1. Cleaning steps")
cleaning_steps = [
    {
        "Cleaning step": "Invalid gender recorded",
        "Rows removed": dq["rows_removed"]["invalid_gender"],
    },
    {
        "Cleaning step": "Terminal discharge (hospice or expired)",
        "Rows removed": dq["rows_removed"]["terminal_discharge"],
    },
    {
        "Cleaning step": "Exact duplicate encounter records",
        "Rows removed": dq["rows_removed"]["exact_duplicates"],
    },
]
st.dataframe(pd.DataFrame(cleaning_steps), hide_index=True, width="stretch")

raw_count = dq["row_counts"]["raw"]
clean_count = dq["row_counts"]["clean"]
st.write(f"{raw_count:,} encounters before cleaning, {clean_count:,} after.")

st.header("2. Missing values")
missing_dict = {
    col: vals["raw"]
    for col, vals in dq["missing_percentages"].items()
    if isinstance(vals, dict) and vals.get("raw") is not None and vals["raw"] > 0
}
missing_sorted = sorted(missing_dict.items(), key=lambda x: x[1])
cols_missing = [item[0] for item in missing_sorted]
percents_missing = [item[1] for item in missing_sorted]

POLICIES = {
    "weight": "Dropped (96.9% missing)",
    "medical_specialty": "Kept as its own level ('Missing')",
    "payer_code": "Kept as its own level ('Missing')",
    "race": "Kept as its own level ('Unknown')",
    "diag_3": "Kept as its own level in diagnosis grouping",
    "diag_2": "Kept as its own level in diagnosis grouping",
    "diag_1": "Kept as its own level in diagnosis grouping",
}
policies = [POLICIES.get(c, "Not tested") for c in cols_missing]

fig_missing = go.Figure(
    go.Bar(
        x=percents_missing,
        y=cols_missing,
        orientation="h",
        marker=dict(color=TEAL),
        customdata=policies,
        hovertemplate="Column: %{y}<br>Missing: %{x:.2f}%<br>Policy: %{customdata}<extra></extra>",
    )
)
fig_missing.update_layout(
    height=320,
    xaxis_title="Percent missing in raw data (%)",
    yaxis_title="Feature",
)
figure(fig_missing, 1, "Missing percentage in raw clinical encounter records and imputation policy.")

st.header("3. Outliers")
capped_cols = list(caps.keys())
df_capped = load_table("clean.parquet", columns=capped_cols)

fig_outliers = make_subplots(
    rows=2,
    cols=4,
    subplot_titles=[f"{col} (cap = {caps[col]:.0f})" for col in capped_cols],
)
for i, col in enumerate(capped_cols):
    r = i // 4 + 1
    c = i % 4 + 1
    vals = df_capped[col].to_numpy()
    fig_outliers.add_trace(
        go.Box(
            y=vals,
            name="before cap",
            marker_color=GREY,
            boxpoints=False,
            showlegend=(i == 0),
        ),
        row=r,
        col=c,
    )
    fig_outliers.add_trace(
        go.Box(
            y=np.minimum(vals, caps[col]),
            name="after cap",
            marker_color=TEAL,
            boxpoints=False,
            showlegend=(i == 0),
        ),
        row=r,
        col=c,
    )
fig_outliers.update_layout(
    height=560,
    legend=dict(orientation="h", y=-0.15),
)
figure(fig_outliers, 2, "Outlier distribution before and after 99th percentile capping across numerical features.")

st.header("4. Feature selection")
decision_filter = st.selectbox("Filter by decision", ["all", "kept", "dropped"])
if decision_filter != "all":
    display_fe = fe[fe["decision"] == decision_filter]
else:
    display_fe = fe
st.dataframe(display_fe, hide_index=True, width="stretch")

st.header("5. Splits")
clean_split_df = load_table("clean.parquet", columns=["encounter_id", "patient_nbr", "readmit_30"])

split_map = {
    "train": set(split_data["train"]),
    "val": set(split_data["validation"]),
    "test": set(split_data["test"]),
}

split_rows = []
patient_sets: dict[str, set[int]] = {}

for split_name, enc_ids in split_map.items():
    sub_df = clean_split_df[clean_split_df["encounter_id"].isin(enc_ids)]
    pts = set(sub_df["patient_nbr"])
    patient_sets[split_name] = pts
    split_rows.append(
        {
            "Split": split_name,
            "Encounters": f"{len(sub_df):,}",
            "Patients": f"{len(pts):,}",
            "Positive rate": f"{sub_df['readmit_30'].mean():.1%}",
        }
    )

st.dataframe(pd.DataFrame(split_rows), hide_index=True, width="stretch")

overlap_count = (
    len(patient_sets["train"] & patient_sets["val"])
    + len(patient_sets["train"] & patient_sets["test"])
    + len(patient_sets["val"] & patient_sets["test"])
)
st.write(f"Patients appearing in more than one split: {overlap_count}")
