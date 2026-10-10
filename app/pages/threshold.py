import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import plotly.graph_objects as go
import streamlit as st
from loaders import load_json, load_table
from style import GREY, INK, RUST, TEAL, figure, setup, stat_row

from readmission.metrics import gains_table

setup("Threshold and capacity")

th = load_json("threshold.json")
sweep_raw = load_table("sweep.parquet")
test_preds = load_table("test_predictions.parquet")

operating_t = float(th["primary"]["threshold"])
default_t = round(operating_t, 2)

sweep = sweep_raw.copy()
sweep["threshold"] = sweep["threshold"].round(2)
total = sweep.iloc[0]["tn"] + sweep.iloc[0]["fp"] + sweep.iloc[0]["fn"] + sweep.iloc[0]["tp"]
sweep["recall"] = sweep["tp"] / (sweep["tp"] + sweep["fn"])
sweep["precision"] = sweep["tp"] / (sweep["tp"] + sweep["fp"]).replace(0, 1)
sweep["flagged_share"] = (sweep["tp"] + sweep["fp"]) / total
sweep["missed_per_1k"] = (sweep["fn"] / total) * 1000
sweep["false_alarms_per_1k"] = (sweep["fp"] / total) * 1000


@st.fragment
def render_threshold_and_cost() -> None:
    st.header("1. Choose a threshold")

    chosen_t = st.slider(
        "Operating threshold",
        min_value=0.02,
        max_value=0.60,
        value=default_t,
        step=0.01,
    )
    chosen_t = round(chosen_t, 2)

    row = sweep[sweep["threshold"] == chosen_t].iloc[0]

    stat_row(
        [
            ("Recall", f"{row['recall']:.1%}"),
            ("Precision", f"{row['precision']:.1%}"),
            ("Flagged share", f"{row['flagged_share']:.1%}"),
            ("Missed per 1k discharges", f"{row['missed_per_1k']:.1f}"),
            ("False alarms per 1k discharges", f"{row['false_alarms_per_1k']:.1f}"),
        ]
    )

    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=sweep["threshold"],
            y=sweep["recall"],
            mode="lines",
            name="Recall",
            line=dict(color=TEAL, width=2),
        )
    )
    fig1.add_trace(
        go.Scatter(
            x=sweep["threshold"],
            y=sweep["precision"],
            mode="lines",
            name="Precision",
            line=dict(color=RUST, width=2),
        )
    )
    fig1.add_vline(
        x=chosen_t,
        line=dict(dash="dot", color=INK, width=1.5),
        annotation_text=f"selected ({chosen_t:.2f})",
        annotation_position="top left",
    )
    fig1.add_vline(
        x=round(operating_t, 2),
        line=dict(dash="dot", color=GREY, width=1.5),
        annotation_text=f"operating ({operating_t:.3f})",
        annotation_position="bottom right",
    )
    fig1.update_layout(
        title="Recall and precision across decision thresholds",
        xaxis_title="Classification threshold",
        yaxis_title="Metric value",
        yaxis=dict(tickformat=".0%"),
        height=380,
        legend=dict(orientation="h", y=-0.22),
    )
    figure(
        fig1,
        1,
        "Recall and precision curves evaluated on test split across candidate thresholds.",
    )

    st.header("2. Cost of errors")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cost_fn = st.number_input(
            "Cost unit of a missed readmission (FN)",
            value=float(th.get("cost_fn", 5.0)),
            min_value=0.0,
            step=0.5,
        )
    with col_c2:
        cost_fp = st.number_input(
            "Cost unit of a false alarm (FP)",
            value=float(th.get("cost_fp", 1.0)),
            min_value=0.0,
            step=0.5,
        )

    st.caption("Costs are operational assumptions for scenario planning, not measured costs.")

    cost_per_1k = ((cost_fn * sweep["fn"] + cost_fp * sweep["fp"]) / total) * 1000
    min_idx = cost_per_1k.idxmin()
    min_t = sweep.loc[min_idx, "threshold"]
    min_cost = cost_per_1k.loc[min_idx]

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=sweep["threshold"],
            y=cost_per_1k,
            mode="lines",
            name="Expected cost per 1k",
            line=dict(color=TEAL, width=2),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=[min_t],
            y=[min_cost],
            mode="markers",
            marker=dict(size=10, color=RUST, symbol="diamond"),
            name=f"Minimum cost (@ t = {min_t:.2f})",
            hovertemplate=f"Optimal threshold: {min_t:.2f}<br>Expected cost: {min_cost:.1f} units<extra></extra>",
        )
    )
    fig2.update_layout(
        title="Expected cost per 1,000 discharges",
        xaxis_title="Classification threshold",
        yaxis_title="Total cost per 1k discharges",
        height=360,
        legend=dict(orientation="h", y=-0.22),
    )
    figure(
        fig2,
        2,
        "Expected misclassification cost per 1,000 hospital discharges across classification thresholds.",
    )


render_threshold_and_cost()


@st.fragment
def render_followup_capacity() -> None:
    st.header("3. Follow-up capacity")

    contact_share_pct = st.slider(
        "Care team follow-up capacity (% of all discharged patients)",
        min_value=5,
        max_value=50,
        value=20,
        step=1,
    )
    contact_frac = contact_share_pct / 100.0

    gt = gains_table(test_preds["y_true"], test_preds["probability_calibrated"], n_bins=20)
    closest_idx = (gt["top_share"] - contact_frac).abs().idxmin()
    row_gt = gt.loc[closest_idx]

    stat_row(
        [
            ("Share of all readmissions captured", f"{row_gt['recall']:.1%}"),
            ("Precision in contacted cohort", f"{row_gt['precision']:.1%}"),
            ("Encounter lift over baseline", f"{row_gt['lift']:.2f}x"),
        ]
    )

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig3 = go.Figure()
        fig3.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            line=dict(dash="dot", color=GREY, width=1.2),
        )
        fig3.add_trace(
            go.Scatter(
                x=gt["top_share"],
                y=gt["recall"],
                mode="lines+markers",
                name="Model capture",
                line=dict(color=TEAL, width=2),
                marker=dict(size=6),
            )
        )
        fig3.add_trace(
            go.Scatter(
                x=[row_gt["top_share"]],
                y=[row_gt["recall"]],
                mode="markers",
                marker=dict(size=10, color=RUST),
                name=f"Selected capacity ({contact_share_pct}%)",
                hovertemplate=f"Contacted: {row_gt['top_share']:.1%}<br>Captured: {row_gt['recall']:.1%}<extra></extra>",
            )
        )
        fig3.update_layout(
            title="Cumulative capture curve",
            xaxis_title="Share of discharges contacted",
            yaxis_title="Share of readmissions captured",
            xaxis=dict(tickformat=".0%"),
            yaxis=dict(tickformat=".0%"),
            height=360,
            legend=dict(orientation="h", y=-0.25),
        )
        figure(
            fig3,
            3,
            "Cumulative readmission capture curve relative to random uniform outreach.",
        )

    with col_g2:
        fig4 = go.Figure()
        fig4.add_hline(
            y=1.0,
            line=dict(dash="dot", color=GREY, width=1.2),
            annotation_text="baseline lift (1.0x)",
            annotation_position="bottom right",
        )
        fig4.add_trace(
            go.Scatter(
                x=gt["top_share"],
                y=gt["lift"],
                mode="lines+markers",
                name="Lift",
                line=dict(color=TEAL, width=2),
                marker=dict(size=6),
            )
        )
        fig4.add_trace(
            go.Scatter(
                x=[row_gt["top_share"]],
                y=[row_gt["lift"]],
                mode="markers",
                marker=dict(size=10, color=RUST),
                name=f"Selected lift ({row_gt['lift']:.2f}x)",
                hovertemplate=f"Contacted: {row_gt['top_share']:.1%}<br>Lift: {row_gt['lift']:.2f}x<extra></extra>",
            )
        )
        fig4.update_layout(
            title="Lift curve by outreach share",
            xaxis_title="Share of discharges contacted",
            yaxis_title="Lift multiplier",
            xaxis=dict(tickformat=".0%"),
            height=360,
            legend=dict(orientation="h", y=-0.25),
        )
        figure(
            fig4,
            4,
            "Lift multiplier over average discharge population readmission rate by contact fraction.",
        )


render_followup_capacity()
