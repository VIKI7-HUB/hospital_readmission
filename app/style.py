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
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=13, color=INK),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        colorway=OKABE_ITO,
        xaxis=dict(gridcolor=RULE, zeroline=False, linecolor=INK, ticks="outside"),
        yaxis=dict(gridcolor=RULE, zeroline=False, linecolor=INK, ticks="outside"),
        margin=dict(l=60, r=20, t=40, b=50),
        legend=dict(orientation="h", y=-0.22),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
)
pio.templates.default = "paper"

CSS = """
h1, h2, h3 { font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif; font-weight: 600; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
.block-container { padding-top: 2rem; max-width: 1200px; }
"""


def setup(title: str) -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    st.title(title)


def figure(fig: go.Figure, number: int, caption: str) -> None:
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Fig. {number}. {caption}")


def stat_row(items: list[tuple[str, str]]) -> None:
    for col, (label, value) in zip(st.columns(len(items)), items, strict=False):
        col.metric(label, value)
