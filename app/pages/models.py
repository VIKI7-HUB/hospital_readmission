import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

import streamlit as st
from style import setup

setup("Models")
st.write("In progress.")
