from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def _require(name: str) -> Path:
    path = ARTIFACTS / name
    if not path.exists():
        st.error(f"Missing artifacts/{name}. Run `make pipeline` first.")
        st.stop()
    return path


@st.cache_data(show_spinner=False)
def load_json(name: str) -> dict:
    return json.loads(_require(name).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_table(name: str, columns: list[str] | None = None) -> pd.DataFrame:
    path = _require(name)
    if name.endswith(".parquet"):
        return pd.read_parquet(path, columns=columns)
    return pd.read_csv(path, usecols=columns)
