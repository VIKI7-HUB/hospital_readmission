import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts import dot_whisker
from loaders import load_json, load_table
from style import GREY, RUST, TEAL, figure, setup, stat_row

setup("Fairness")

audit_df = load_table("fairness_audit.csv")
gaps_df = load_table("fairness_gaps.csv")
summary_json = load_json("fairness_summary.json")
mitigation_df = load_table("fairness_mitigation.csv")
thresholds_grp = load_json("fairness_thresholds.json")
metrics_json = load_json("metrics.json")
champion_json = load_json("champion.json")

champ_name = champion_json["model"]
champ_metrics = metrics_json[champ_name]
overall_recall = float(champ_metrics["recall"])
overall_fpr = float(champ_metrics["fp"]) / (
    float(champ_metrics["fp"]) + float(champ_metrics["tn"])
)
operating_t = float(summary_json.get("threshold", champ_metrics["threshold"]))

underpowered_set = set(audit_df[audit_df["positives"] < 100]["group"].tolist())


@st.fragment
def render_fairness_dashboard() -> None:
    attribute = st.radio(
        "Sensitive attribute",
        ["age_band", "gender", "race"],
        horizontal=True,
    )

    sub_audit = audit_df[audit_df["attribute"] == attribute].copy()
    sub_gaps = gaps_df[gaps_df["attribute"] == attribute].copy()
    sub_mit = mitigation_df[mitigation_df["attribute"] == attribute].copy()
    attr_summary = summary_json.get(attribute, {})

    # 1. Group sizes
    st.header("1. Group sizes")
    display_sizes = sub_audit[["group", "n", "positives", "underpowered"]].copy()
    display_sizes["underpowered"] = display_sizes["underpowered"].map(
        {True: "Yes", False: "No"}
    )
    st.dataframe(display_sizes, hide_index=True, width="stretch")

    # 2. Who is found
    st.header("2. Who is found")
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        fig1 = dot_whisker(
            sub_audit["group"],
            sub_audit["tpr"],
            sub_audit["tpr_lo"],
            sub_audit["tpr_hi"],
            hollow=sub_audit["underpowered"].astype(bool).tolist(),
            reference=overall_recall,
            x_title="True positive rate (recall)",
            fmt=".1%",
            title=f"True positive rate (recall) by {attribute}",
        )
        figure(
            fig1,
            1,
            f"True positive rate across {attribute} groups at operating threshold {operating_t:.3f}. Dotted line marks overall recall.",
        )

    with col_f2:
        fig2 = dot_whisker(
            sub_audit["group"],
            sub_audit["fpr"],
            sub_audit["fpr_lo"],
            sub_audit["fpr_hi"],
            hollow=sub_audit["underpowered"].astype(bool).tolist(),
            reference=overall_fpr,
            x_title="False positive rate",
            fmt=".1%",
            title=f"False positive rate by {attribute}",
        )
        figure(
            fig2,
            2,
            f"False positive rate across {attribute} groups at operating threshold {operating_t:.3f}. Dotted line marks overall FPR.",
        )

    # 3. Gaps
    st.header("3. Gaps")
    if not sub_gaps.empty:
        display_gaps = sub_gaps[
            ["group", "reference", "metric", "gap_pp", "lower_pp", "upper_pp"]
        ].copy()
        display_gaps.columns = [
            "Group",
            "Reference",
            "Metric",
            "Gap (pp)",
            "Lower 95%",
            "Upper 95%",
        ]
        st.dataframe(display_gaps, hide_index=True, width="stretch")

        for _, r in sub_gaps.iterrows():
            if r["group"] in underpowered_set:
                continue
            cross_str = (
                "the interval includes zero."
                if r["crosses_zero"]
                else "the interval does not include zero."
            )
            sentence = (
                f"{r['metric'].upper()} gap, {r['group']} versus {r['reference']}: "
                f"{r['gap_pp']:+.1f} points (95% interval {r['lower_pp']:+.1f} to {r['upper_pp']:+.1f}); "
                f"{cross_str}"
            )
            st.write(sentence)

    if attr_summary:
        tpr_diff = attr_summary.get("tpr_difference", 0.0) * 100
        fpr_diff = attr_summary.get("fpr_difference", 0.0) * 100
        eq_odds = attr_summary.get("equalized_odds_difference", 0.0) * 100
        dp_diff = attr_summary.get("demographic_parity_difference", 0.0) * 100
        sr_ratio = attr_summary.get("selection_rate_ratio", 0.0)

        stat_row(
            [
                ("TPR difference", f"{tpr_diff:.1f} pp"),
                ("FPR difference", f"{fpr_diff:.1f} pp"),
                ("Equalized odds diff", f"{eq_odds:.1f} pp"),
                ("Demographic parity diff", f"{dp_diff:.1f} pp"),
                ("Selection-rate ratio", f"{sr_ratio:.2f}"),
            ]
        )
        st.caption(
            "The selection-rate ratio is a screening heuristic from employment settings (EEOC four-fifths rule), "
            "not a clinical performance standard."
        )

    # 4. Calibration by group
    st.header("4. Calibration by group")
    fig3 = go.Figure()
    fig3.add_trace(
        go.Bar(
            x=sub_audit["group"],
            y=sub_audit["mean_pred"],
            name="Mean predicted risk",
            marker_color=TEAL,
        )
    )
    fig3.add_trace(
        go.Bar(
            x=sub_audit["group"],
            y=sub_audit["observed"],
            name="Observed readmission rate",
            marker_color=RUST,
        )
    )
    fig3.update_layout(
        barmode="group",
        title=f"Risk calibration by {attribute}",
        yaxis=dict(tickformat=".1%"),
        height=360,
        legend=dict(orientation="h", y=-0.22),
    )
    figure(
        fig3,
        3,
        f"Comparison of mean predicted risk and observed 30-day readmission rate across {attribute} groups.",
    )

    # 5. Group-specific thresholds
    st.header("5. Group-specific thresholds")
    grp_th_dict = thresholds_grp.get(attribute, {})
    if grp_th_dict:
        th_table = pd.DataFrame(
            [{"Group": g, "Mitigated threshold": f"{val:.3f}"} for g, val in grp_th_dict.items()]
        )
        st.dataframe(th_table, hide_index=True, width="stretch")

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        if not sub_mit.empty:
            fig4 = go.Figure()
            comp_metrics = ["recall", "fpr", "equalized_odds_difference"]
            base_row = sub_mit[sub_mit["variant"] == "base"]
            mit_row = sub_mit[sub_mit["variant"] == "group_threshold"]

            if not base_row.empty and not mit_row.empty:
                b_vals = [base_row[m].iloc[0] for m in comp_metrics]
                m_vals = [mit_row[m].iloc[0] for m in comp_metrics]
                fig4.add_trace(
                    go.Bar(
                        x=["Recall", "FPR", "Equalized odds diff"],
                        y=b_vals,
                        name="Base model",
                        marker_color=GREY,
                    )
                )
                fig4.add_trace(
                    go.Bar(
                        x=["Recall", "FPR", "Equalized odds diff"],
                        y=m_vals,
                        name="Group threshold",
                        marker_color=TEAL,
                    )
                )
                fig4.update_layout(
                    barmode="group",
                    title="Base versus group-specific thresholding",
                    yaxis=dict(tickformat=".1%"),
                    height=360,
                    legend=dict(orientation="h", y=-0.22),
                )
                figure(
                    fig4,
                    4,
                    f"Performance and disparity comparison between base model and group-specific thresholds on {attribute}.",
                )

    with col_m2:
        if not sub_mit.empty:
            fig5 = go.Figure()
            fig5.add_trace(
                go.Scatter(
                    x=sub_mit["equalized_odds_difference"],
                    y=sub_mit["recall"],
                    mode="markers+text",
                    text=sub_mit["variant"],
                    textposition="top center",
                    marker=dict(size=12, color=[GREY, TEAL]),
                )
            )
            fig5.update_layout(
                title="Recall versus disparity tradeoff",
                xaxis_title="Equalized odds difference",
                yaxis_title="Overall recall",
                xaxis=dict(tickformat=".1%"),
                yaxis=dict(tickformat=".1%"),
                height=360,
            )
            figure(
                fig5,
                5,
                f"Tradeoff between overall test recall and equalized odds disparity under group mitigation on {attribute}.",
            )

    if not sub_mit.empty:
        base_sub = sub_mit[sub_mit["variant"] == "base"]
        mit_sub = sub_mit[sub_mit["variant"] == "group_threshold"]
        if not base_sub.empty and not mit_sub.empty:
            b_tpr_diff = float(base_sub["tpr_difference"].iloc[0])
            m_tpr_diff = float(mit_sub["tpr_difference"].iloc[0])
            b_prec = float(base_sub["precision"].iloc[0])
            m_prec = float(mit_sub["precision"].iloc[0])

            delta_tpr = (m_tpr_diff - b_tpr_diff) * 100
            delta_prec = (m_prec - b_prec) * 100

            if delta_tpr <= 0:
                summary_sentence = (
                    f"Group-specific thresholding reduced the TPR disparity by {abs(delta_tpr):.1f} percentage points "
                    f"(from {b_tpr_diff * 100:.1f} pp to {m_tpr_diff * 100:.1f} pp), with a change in precision of "
                    f"{delta_prec:+.1f} percentage points (from {b_prec:.1%} to {m_prec:.1%})."
                )
            else:
                summary_sentence = (
                    f"Group-specific thresholding changed the TPR disparity by {delta_tpr:+.1f} percentage points "
                    f"(from {b_tpr_diff * 100:.1f} pp to {m_tpr_diff * 100:.1f} pp), with a change in precision of "
                    f"{delta_prec:+.1f} percentage points."
                )
            st.write(summary_sentence)

    # 6. Limits
    st.header("6. Limits")
    st.write(
        "- Small sample groups with low positive counts (< 100) are flagged and excluded from definitive performance conclusions."
    )
    st.write(
        "- Race and gender categories reflect administrative hospital records and may not represent self-reported identity."
    )
    st.write(
        "- Group-specific thresholds require sensitive demographic attributes at decision time, which may face legal or clinical governance restrictions."
    )
    st.write(
        "- The dataset represents hospital inpatient encounters from 1999 to 2008 and reflects clinical practice from that decade."
    )


render_fairness_dashboard()
