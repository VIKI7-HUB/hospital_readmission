import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from loaders import load_json, load_table
from style import GREY, OKABE_ITO, RUST, TEAL, figure, setup

setup("Models")

mc = load_table("model_comparison.csv")
metrics = load_json("metrics.json")
champ = load_json("champion.json")
th = load_json("threshold.json")
curves_rel = load_table("curves_reliability.parquet")

champion_name = champ["model"]

st.header("1. Model comparison")

if "brier" not in mc.columns and "brier_score" in mc.columns:
    mc["brier"] = mc["brier_score"]

# Put champion first
mc["is_champ"] = mc["model"] == champion_name
mc_sorted = (
    pd.concat([mc[mc["is_champ"]], mc[~mc["is_champ"]]])
    .drop(columns=["is_champ"])
    .reset_index(drop=True)
)

cols = [
    "model",
    "threshold",
    "accuracy",
    "precision",
    "recall",
    "specificity",
    "f1",
    "f2",
    "roc_auc",
    "pr_auc",
    "brier",
]
table_df = mc_sorted[[c for c in cols if c in mc_sorted.columns]].copy()


def highlight_best(s: pd.Series) -> list[str]:
    if s.name in ("model", "threshold"):
        return ["" for _ in s]
    is_best = s == s.min() if s.name == "brier" else s == s.max()
    return ["font-weight: bold" if v else "" for v in is_best]


pct_cols = ["accuracy", "precision", "recall", "specificity", "f1", "f2"]
formatter = {c: "{:.1%}" for c in pct_cols if c in table_df.columns}
for c in ["threshold", "roc_auc", "pr_auc", "brier"]:
    if c in table_df.columns:
        formatter[c] = "{:.3f}"

styled_table = table_df.style.apply(highlight_best).format(formatter)
st.dataframe(styled_table, hide_index=True, width="stretch")
st.caption(
    "All models evaluated once on the held-out test split at the threshold chosen on validation data."
)

st.header("2. Why recall comes first")

p1 = (
    "For an acute-care inpatient hospital, a false negative represents a patient discharged "
    "without transitional support who unexpectedly decompensates and requires emergency "
    "readmission within 30 days. Conversely, a false positive represents an allocated post-discharge "
    "care call or medication review delivered to a patient who would not have returned."
)

operating_t = float(th["primary"]["threshold"])
target_recall = float(th.get("recall_target", 0.60))
p2 = (
    f"The operating threshold {operating_t:.3f} was chosen on validation data as the "
    f"highest-precision point that still catches at least {target_recall:.0%} of readmissions."
)

champ_row = mc[mc["model"] == champion_name].iloc[0]
r_test = float(champ_row["recall"])
p_test = float(champ_row["precision"])
fn_test = int(champ_row["fn"])
fp_test = int(champ_row["fp"])
p3 = (
    f"On the test split this gives recall {r_test:.1%} and precision {p_test:.1%}. "
    f"{fn_test:,} readmitted patients were missed and {fp_test:,} patients were flagged "
    "without being readmitted."
)

st.write(p1)
st.write(p2)
st.write(p3)

col_c1, col_c2 = st.columns(2)

# Fig 1: ROC curves
with col_c1:
    fig_roc = go.Figure()
    fig_roc.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=1,
        y1=1,
        line=dict(dash="dot", color=GREY, width=1.2),
    )
    for idx, (m_name, m_data) in enumerate(metrics.items()):
        roc = m_data["curves"]["roc"]
        is_champ = m_name == champion_name
        color = TEAL if is_champ else OKABE_ITO[idx % len(OKABE_ITO)]
        fig_roc.add_trace(
            go.Scatter(
                x=roc["false_positive_rate"],
                y=roc["true_positive_rate"],
                mode="lines",
                name=f"{m_name} (AUC {m_data['roc_auc']:.3f})",
                line=dict(color=color, width=3 if is_champ else 1.5),
                customdata=roc["thresholds"],
                hovertemplate=f"<b>{m_name}</b><br>FPR: %{{x:.3f}}<br>TPR: %{{y:.3f}}<br>Threshold: %{{customdata:.3f}}<extra></extra>",
            )
        )
    fig_roc.update_layout(
        title="Receiver Operating Characteristic (ROC)",
        xaxis_title="False positive rate",
        yaxis_title="True positive rate",
        height=380,
        legend=dict(orientation="h", y=-0.25),
    )
    figure(
        fig_roc,
        1,
        "ROC curves across all candidate models evaluated on held-out test data. Champion shown thicker.",
    )

# Fig 2: Precision-Recall curves
with col_c2:
    fig_pr = go.Figure()
    pos_rate = float(champ_row["tp"] + champ_row["fn"]) / (
        champ_row["tp"] + champ_row["fp"] + champ_row["tn"] + champ_row["fn"]
    )
    fig_pr.add_hline(
        y=pos_rate,
        line=dict(dash="dot", color=GREY, width=1.2),
        annotation_text="no skill",
        annotation_position="bottom right",
    )
    for idx, (m_name, m_data) in enumerate(metrics.items()):
        pr = m_data["curves"]["precision_recall"]
        is_champ = m_name == champion_name
        color = TEAL if is_champ else OKABE_ITO[idx % len(OKABE_ITO)]
        fig_pr.add_trace(
            go.Scatter(
                x=pr["recall"],
                y=pr["precision"],
                mode="lines",
                name=f"{m_name} (PR-AUC {m_data['pr_auc']:.3f})",
                line=dict(color=color, width=3 if is_champ else 1.5),
                customdata=pr["thresholds"] + [pr["thresholds"][-1]],
                hovertemplate=f"<b>{m_name}</b><br>Recall: %{{x:.3f}}<br>Precision: %{{y:.3f}}<extra></extra>",
            )
        )
    fig_pr.update_layout(
        title="Precision-Recall curves",
        xaxis_title="Recall",
        yaxis_title="Precision",
        height=380,
        legend=dict(orientation="h", y=-0.25),
    )
    figure(
        fig_pr,
        2,
        "Precision-recall curves across candidate models. Horizontal line marks test positive prevalence.",
    )

col_d1, col_d2 = st.columns(2)

# Fig 3: Reliability diagram
with col_d1:
    fig_rel = go.Figure()
    fig_rel.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=0.6,
        y1=0.6,
        line=dict(dash="dot", color=GREY, width=1.2),
    )
    raw_rel = curves_rel[curves_rel["stage"] == "raw"]
    cal_rel = curves_rel[curves_rel["stage"] == "calibrated"]

    if not raw_rel.empty:
        fig_rel.add_trace(
            go.Scatter(
                x=raw_rel["mean_predicted_probability"],
                y=raw_rel["observed_rate"],
                mode="lines+markers",
                name="Raw probabilities",
                line=dict(color=RUST, width=1.5),
                marker=dict(size=7),
            )
        )
    if not cal_rel.empty:
        fig_rel.add_trace(
            go.Scatter(
                x=cal_rel["mean_predicted_probability"],
                y=cal_rel["observed_rate"],
                mode="lines+markers",
                name="Calibrated probabilities",
                line=dict(color=TEAL, width=2),
                marker=dict(size=8),
            )
        )
    fig_rel.update_layout(
        title=f"Reliability diagram ({champion_name})",
        xaxis_title="Mean predicted risk",
        yaxis_title="Observed readmission fraction",
        height=360,
        legend=dict(orientation="h", y=-0.25),
    )
    figure(
        fig_rel,
        3,
        f"Calibration curve for {champion_name} before and after isotonic/sigmoid calibration on validation data.",
    )

# Fig 4: Confusion matrix
with col_d2:
    tn = int(champ_row["tn"])
    fp = int(champ_row["fp"])
    fn = int(champ_row["fn"])
    tp = int(champ_row["tp"])

    z_matrix = [[tn, fp], [fn, tp]]
    text_matrix = [
        [
            f"TN: {tn:,}<br>({tn / (tn + fp):.1%})",
            f"FP: {fp:,}<br>({fp / (tn + fp):.1%})",
        ],
        [
            f"FN: {fn:,}<br>({fn / (fn + tp):.1%})",
            f"TP: {tp:,}<br>({tp / (fn + tp):.1%})",
        ],
    ]
    fig_cm = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=["Predicted: Not readmitted", "Predicted: Readmitted"],
            y=["Actual: Not readmitted", "Actual: Readmitted"],
            text=text_matrix,
            texttemplate="%{text}",
            colorscale=[[0, "#fbfaf6"], [1, "#1f6f78"]],
            showscale=False,
        )
    )
    fig_cm.update_layout(
        title=f"Confusion matrix ({champion_name} @ t = {operating_t:.3f})",
        height=360,
        yaxis=dict(autorange="reversed"),
    )
    figure(
        fig_cm,
        4,
        f"Test confusion counts and row-wise sensitivities at operating threshold {operating_t:.3f}.",
    )

st.header("3. Model choice")

val_ap = float(champ["validation_average_precision"])
best_ap = float(champ["best_validation_average_precision"])
diff_ap = best_ap - val_ap
reason = champ.get("reason", "")

st.write(
    f"The selected champion model is **{champion_name}**. Under the simpler-model selection "
    f"hierarchy, the model was chosen because its validation PR-AUC ({val_ap:.4f}) is within "
    f"0.005 of the top-scoring gradient boosting architecture ({best_ap:.4f}, a difference of "
    f"{diff_ap:.4f}). {reason} Random forest was preferred as it achieves parity discrimination "
    "with fewer tuning dependencies and reliable out-of-bag variance reduction."
)
