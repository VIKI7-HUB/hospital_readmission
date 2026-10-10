import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts import dot_whisker
from loaders import load_json, load_table
from style import GREY, TEAL, figure, setup

from readmission.explain import FEATURE_LABELS, MODIFIABLE

setup("Explainability")

imp = load_table("shap_importance.csv")
shap_df = load_table("shap_values.parquet")
raw_df = load_table("shap_feature_values.parquet")
odds_df = load_table("odds_ratios.csv")

st.header("1. What drives the model")

top15 = imp.head(15).copy()
labels_15 = [
    f"{FEATURE_LABELS.get(f, f.replace('_', ' ').capitalize())} ({'modifiable' if f in MODIFIABLE else 'fixed'})"
    for f in top15["feature"]
]

fig1 = go.Figure(
    go.Bar(
        x=top15["mean_abs_shap"],
        y=labels_15,
        orientation="h",
        marker_color=TEAL,
        hovertemplate="Feature: %{y}<br>Mean |SHAP|: %{x:.4f}<extra></extra>",
    )
)
fig1.update_yaxes(autorange="reversed")
fig1.update_layout(
    title="Top 15 features by global TreeSHAP importance",
    xaxis_title="Mean absolute SHAP value (log-odds scale)",
    yaxis_title="Feature",
    height=440,
)
figure(
    fig1,
    1,
    "Mean absolute TreeSHAP contributions to model log-odds of readmission across the top 15 features.",
)

st.header("2. Direction of effect")

top12_features = imp.head(12)["feature"].tolist()
rng = np.random.default_rng(42)

fig2 = go.Figure()
y_tick_labels = []

for r, f in enumerate(top12_features, start=1):
    display_name = f"{FEATURE_LABELS.get(f, f.replace('_', ' ').capitalize())} ({'modifiable' if f in MODIFIABLE else 'fixed'})"
    y_tick_labels.append(display_name)

    sv = shap_df[f].to_numpy()
    rv = raw_df[f]
    numeric_s = pd.to_numeric(rv, errors="coerce")

    if numeric_s.notna().mean() > 0.8:
        pct = numeric_s.rank(pct=True).to_numpy()
    else:
        lvl_means = pd.DataFrame({"lvl": rv, "s": sv}).groupby("lvl")["s"].mean()
        pct = rv.map(lvl_means.rank(pct=True).to_dict()).to_numpy()

    jitter = rng.uniform(-0.25, 0.25, size=len(sv))
    y_coords = np.full_like(sv, r, dtype=float) + jitter

    fig2.add_trace(
        go.Scatter(
            x=sv,
            y=y_coords,
            mode="markers",
            marker=dict(
                size=4,
                opacity=0.5,
                color=pct,
                colorscale=[[0, "#8a8f98"], [1, "#b5523b"]],
                showscale=(r == 1),
                colorbar=dict(
                    title="feature value (low to high)",
                    len=0.7,
                    y=0.5,
                    thickness=12,
                )
                if (r == 1)
                else None,
            ),
            name=display_name,
            showlegend=False,
            hovertemplate=f"<b>{display_name}</b><br>SHAP: %{{x:.4f}}<extra></extra>",
        )
    )

fig2.update_layout(
    title="TreeSHAP beeswarm / strip plot (top 12 features)",
    xaxis_title="SHAP value (impact on model log-odds)",
    yaxis=dict(
        tickmode="array",
        tickvals=list(range(1, 13)),
        ticktext=y_tick_labels,
        autorange="reversed",
    ),
    height=480,
)
figure(
    fig2,
    2,
    "SHAP value distribution by feature value percentile rank. For categorical features, color represents the percentile rank of the mean SHAP per category level.",
)

st.header("3. One feature at a time")

feature_options = imp["feature"].tolist()
selected_f = st.selectbox(
    "Select feature to inspect dependence",
    feature_options,
    format_func=lambda x: (
        f"{FEATURE_LABELS.get(x, x)} ({'modifiable' if x in MODIFIABLE else 'fixed'})"
    ),
)

raw_s = pd.to_numeric(raw_df[selected_f], errors="coerce")
is_numeric_feat = raw_s.notna().mean() > 0.8

if is_numeric_feat:
    fig3 = go.Figure(
        go.Scatter(
            x=raw_s,
            y=shap_df[selected_f],
            mode="markers",
            marker=dict(size=4, color=TEAL, opacity=0.6),
            hovertemplate="Observed value: %{x}<br>SHAP: %{y:.4f}<extra></extra>",
        )
    )
    fig3.add_hline(y=0, line=dict(dash="dot", color=GREY, width=1))
    fig3.update_layout(
        title=f"Feature dependence: {FEATURE_LABELS.get(selected_f, selected_f)}",
        xaxis_title="Observed feature value",
        yaxis_title="SHAP value",
        height=360,
    )
else:
    fig3 = go.Figure()
    unique_levels = sorted(raw_df[selected_f].dropna().astype(str).unique())
    for lvl in unique_levels:
        mask = raw_df[selected_f].astype(str) == lvl
        fig3.add_trace(
            go.Box(
                y=shap_df.loc[mask, selected_f],
                name=str(lvl),
                marker_color=TEAL,
                boxpoints=False,
                showlegend=False,
            )
        )
    fig3.add_hline(y=0, line=dict(dash="dot", color=GREY, width=1))
    fig3.update_layout(
        title=f"Feature dependence by category: {FEATURE_LABELS.get(selected_f, selected_f)}",
        xaxis_title="Category level",
        yaxis_title="SHAP value",
        height=360,
    )

figure(
    fig3,
    3,
    f"Single-feature dependence plot showing SHAP contribution across values of {FEATURE_LABELS.get(selected_f, selected_f)}.",
)

st.header("4. Logistic regression odds ratios")

odds_work = odds_df.copy()
odds_work["abs_log_or"] = np.abs(np.log(odds_work["odds_ratio"]))
top20_odds = odds_work.sort_values(by="abs_log_or", ascending=False).head(20).copy()

fig4 = dot_whisker(
    top20_odds["term"],
    top20_odds["odds_ratio"],
    top20_odds["lower"],
    top20_odds["upper"],
    x_title="Odds ratio (log scale)",
    reference=1.0,
    fmt=".2f",
    log_x=True,
    height=480,
    title="Top 20 logistic regression odds ratios",
)
figure(
    fig4,
    4,
    "Odds ratios come from a separate inference model fitted on the training split with standard errors clustered by patient.",
)

table_odds = top20_odds[["term", "odds_ratio", "lower", "upper", "unit"]].copy()
table_odds["interval"] = table_odds.apply(lambda r: f"[{r['lower']:.2f}, {r['upper']:.2f}]", axis=1)
table_odds["odds_ratio"] = table_odds["odds_ratio"].apply(lambda v: f"{v:.2f}")
st.dataframe(
    table_odds[["term", "odds_ratio", "interval", "unit"]],
    hide_index=True,
    width="stretch",
)

st.subheader("How to read these charts")
st.write(
    "Each SHAP value reflects how much an individual patient's recorded clinical feature "
    "shifted their predicted log-odds of readmission relative to the average hospitalized cohort. "
    "Positive values increase estimated 30-day readmission risk, whereas negative values decrease risk. "
    "Odds ratios from the logistic model describe population-level relative associations per unit change "
    "after accounting for within-patient correlation."
)

tags_path = ROOT / "artifacts" / "feature_tags.json"
if tags_path.exists():
    st.header("5. Modifiable versus fixed signal")
    tags = load_json("feature_tags.json")
    mod_set = set(tags.get("modifiable", []))
    total_shap = float(imp["mean_abs_shap"].sum())
    mod_shap = float(imp[imp["feature"].isin(mod_set)]["mean_abs_shap"].sum())
    fixed_shap = total_shap - mod_shap

    mod_share = mod_shap / total_shap
    fixed_share = fixed_shap / total_shap

    fig5 = go.Figure(
        go.Bar(
            y=["Fixed features", "Modifiable features"],
            x=[fixed_share, mod_share],
            orientation="h",
            marker_color=[GREY, TEAL],
            text=[f"{fixed_share:.1%}", f"{mod_share:.1%}"],
            textposition="auto",
        )
    )
    fig5.update_layout(
        title="Share of TreeSHAP signal by feature mutability",
        xaxis_title="Share of total mean absolute SHAP",
        xaxis=dict(tickformat=".0%", range=[0, 1]),
        height=240,
    )
    figure(
        fig5,
        5,
        f"{mod_share:.0%} of the model's TreeSHAP signal comes from modifiable features that can change at discharge.",
    )
    st.caption(
        "Modifiable features include medications, discharge disposition, and HbA1c testing results. "
        "Fixed features reflect baseline clinical history and non-actionable demographics. "
        "These represent observational attribution shares and do not indicate causal effects."
    )

