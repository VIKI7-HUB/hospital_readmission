from __future__ import annotations

import plotly.graph_objects as go
from style import GREY, INK, RUST, TEAL


def dot_whisker(
    labels,
    values,
    lows,
    highs,
    hollow=None,
    x_title="",
    fmt=".0%",
    reference=None,
    height=320,
    title="",
    log_x=False,
):
    """Horizontal dots with intervals. hollow marks small-sample groups; reference draws a dotted line."""
    hollow = hollow if hollow is not None else [False] * len(labels)
    values, lows, highs = list(values), list(lows), list(highs)
    fig = go.Figure(
        go.Scatter(
            x=values,
            y=[str(label) for label in labels],
            mode="markers",
            marker=dict(
                size=9,
                color=TEAL,
                symbol=["circle-open" if h else "circle" for h in hollow],
                line=dict(width=1.5, color=TEAL),
            ),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[hi - v for v, hi in zip(values, highs, strict=False)],
                arrayminus=[v - lo for v, lo in zip(values, lows, strict=False)],
                color=GREY,
                thickness=1.2,
                width=4,
            ),
            hovertemplate="%{y}<br>%{x:" + fmt + "}<extra></extra>",
        )
    )
    if reference is not None:
        fig.add_vline(x=reference, line=dict(dash="dot", color=RUST, width=1.2))
    fig.update_xaxes(tickformat=fmt, title=x_title, type="log" if log_x else "linear")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title=title, height=height, showlegend=False)
    return fig


def interval_chart(table, label_col, title, x_title="Readmitted within 30 days", height=320):
    """Readmission rate per level with Wilson intervals. table comes from eda.rate_table."""
    fig = dot_whisker(
        table[label_col],
        table["rate"],
        table["lo"],
        table["hi"],
        x_title=x_title,
        height=height,
        title=title,
    )
    fig.update_traces(
        customdata=table[["n", "positives"]].to_numpy(),
        hovertemplate="%{y}<br>rate %{x:.1%}<br>n = %{customdata[0]:,}, "
        "readmitted = %{customdata[1]:,}<extra></extra>",
    )
    return fig


def waterfall_chart(
    base: float,
    margin: float,
    contribs,
    labels_map: dict[str, str],
    height: int = 400,
) -> go.Figure:
    """Waterfall plot breaking down encounter risk into baseline log-odds and feature adjustments."""
    abs_c = contribs.abs().sort_values(ascending=False)
    top8_feats = abs_c.head(8).index.tolist()
    other_sum = float(contribs.drop(index=top8_feats).sum())

    wf_names = (
        ["Average patient"]
        + [labels_map.get(f, f) for f in top8_feats]
        + ["Other features", "This patient"]
    )
    wf_values = [base] + [float(contribs[f]) for f in top8_feats] + [other_sum, margin]
    wf_measures = ["absolute"] + ["relative"] * (len(top8_feats) + 1) + ["total"]

    fig = go.Figure(
        go.Waterfall(
            orientation="h",
            measure=wf_measures,
            y=wf_names,
            x=wf_values,
            connector=dict(line=dict(color=GREY, width=1)),
            decreasing=dict(marker=dict(color=TEAL)),
            increasing=dict(marker=dict(color=RUST)),
            totals=dict(marker=dict(color=INK)),
        )
    )
    fig.update_layout(
        title="Top TreeSHAP contributions to encounter log-odds",
        xaxis_title="Contribution to log-odds",
        height=height,
        yaxis=dict(autorange="reversed"),
    )
    return fig
