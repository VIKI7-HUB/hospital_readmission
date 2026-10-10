from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

INK = "#1c1f23"
PAPER = "#fbfaf6"
TEAL = "#1f6f78"
RUST = "#b5523b"
GREY = "#8a8f98"
RULE = "#e4e1d8"
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]

pio.templates["paper"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=16, color=INK),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        colorway=OKABE_ITO,
        xaxis=dict(
            gridcolor=RULE,
            zeroline=False,
            linecolor=INK,
            ticks="outside",
            title=dict(font=dict(size=17)),
            tickfont=dict(size=15),
        ),
        yaxis=dict(
            gridcolor=RULE,
            zeroline=False,
            linecolor=INK,
            ticks="outside",
            title=dict(font=dict(size=17)),
            tickfont=dict(size=15),
        ),
        margin=dict(l=60, r=20, t=40, b=50),
        legend=dict(orientation="h", y=-0.22, font=dict(size=15)),
        hoverlabel=dict(bgcolor="white", font_size=14),
        height=460,
    )
)
pio.templates.default = "paper"

CSS = """
body, p, label, .stMarkdown p, [data-testid="stMarkdownContainer"] p { font-size: 17px; }
h1 { font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif; font-weight: 600; font-size: 40px !important; }
h2 { font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif; font-weight: 600; font-size: 30px !important; }
h3 { font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif; font-weight: 600; font-size: 24px !important; }
.stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaption"] { font-size: 15px !important; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
.block-container { padding-top: 2rem; max-width: 1200px; }
[data-testid="stDataFrame"], .stTable, [data-testid="stTable"] { font-size: 16px !important; }
[data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span { font-size: 16px; }
.stTable th, .stTable td, [data-testid="stTable"] th, [data-testid="stTable"] td {
    font-size: 16px !important;
    padding: 10px !important;
}
"""

NAV_CSS = """
section[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 100% !important; }
header[data-testid="stHeader"] {
    border-bottom: 1px solid #e4e1d8;
    background: transparent !important;
}
header[data-testid="stHeader"] a {
    color: #1c1f23 !important;
    background: transparent !important;
    background-color: transparent !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    text-decoration: none !important;
    box-shadow: none !important;
}
header[data-testid="stHeader"] a:hover {
    background: transparent !important;
    background-color: transparent !important;
}
header[data-testid="stHeader"] a[aria-current="page"] {
    border-bottom: 2px solid #1f6f78 !important;
    color: #1c1f23 !important;
    background: transparent !important;
    background-color: transparent !important;
}
header[data-testid="stHeader"] a span {
    color: #1c1f23 !important;
}
"""


def setup(title: str) -> None:
    st.markdown(f"<style>{CSS}\n{NAV_CSS}</style>", unsafe_allow_html=True)
    st.title(title)


def figure(fig: go.Figure, number: int, caption: str) -> None:
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Fig. {number}. {caption}")


def stat_row(items: list[tuple[str, str]]) -> None:
    for col, (label, value) in zip(st.columns(len(items)), items, strict=False):
        col.metric(label, value)
