import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import streamlit as st

st.set_page_config(page_title="Readmission risk", layout="wide")

pages = [
    st.Page("pages/overview.py", title="Overview", default=True),
    st.Page("pages/data_quality.py", title="Data quality"),
    st.Page("pages/exploration.py", title="Exploration"),
    st.Page("pages/models.py", title="Models"),
    st.Page("pages/threshold.py", title="Threshold and capacity"),
    st.Page("pages/explainability.py", title="Explainability"),
    st.Page("pages/fairness.py", title="Fairness"),
    st.Page("pages/patient_risk.py", title="Patient risk"),
]
st.navigation(pages).run()
