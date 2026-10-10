"""Odds ratios for the logistic regression baseline with clustered covariance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from readmission.features import MODEL_FEATURES

ROOT = Path(__file__).resolve().parents[2]


def odds_table(train_frame: pd.DataFrame, y: pd.Series, patient: pd.Series) -> pd.DataFrame:
    """Fit cluster-adjusted logistic regression and return formatted odds ratios table."""
    caps_path = ROOT / "artifacts" / "caps.json"
    caps: dict[str, float] = (
        json.loads(caps_path.read_text(encoding="utf-8")) if caps_path.exists() else {}
    )

    num_cols = [
        c for c in train_frame.select_dtypes(include="number").columns if c in MODEL_FEATURES
    ]
    sd_dict: dict[str, float] = {}
    x_num_dfs: list[pd.DataFrame] = []

    for col in num_cols:
        series = train_frame[col].astype(float)
        if col in caps:
            series = series.clip(upper=caps[col])
        mean_val = float(series.mean())
        sd_val = float(series.std())
        sd_dict[col] = sd_val
        denom = sd_val if sd_val > 0 else 1.0
        x_num_dfs.append(pd.DataFrame({col: (series - mean_val) / denom}, index=train_frame.index))

    cat_cols = [c for c in train_frame.columns if c in MODEL_FEATURES and c not in num_cols]
    ref_dict: dict[str, str] = {}
    x_cat_dfs: list[pd.DataFrame] = []
    dummy_to_source: dict[str, str] = {}

    for col in cat_cols:
        series = train_frame[col].fillna("Missing").astype(str)
        counts = series.value_counts()
        rare = counts[counts < 50].index
        if len(rare) > 0:
            series = series.replace(rare, "Other")
        levels = sorted(series.unique().tolist())
        ref_level = levels[0]
        ref_dict[col] = ref_level

        dummies = pd.get_dummies(series, prefix=col, drop_first=True, dtype=float)
        for d_col in dummies.columns:
            dummy_to_source[d_col] = col
        x_cat_dfs.append(dummies)

    all_parts = x_num_dfs + x_cat_dfs
    x_mat = pd.concat(all_parts, axis=1)
    x_mat = sm.add_constant(x_mat, has_constant="add")

    try:
        model = sm.Logit(y, x_mat)
        res = model.fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": patient})
    except Exception:
        zero_var = [
            c
            for c in x_mat.columns
            if c != "const" and (x_mat[c].std() == 0 or np.isnan(x_mat[c].std()))
        ]
        if zero_var:
            x_mat = x_mat.drop(columns=zero_var)
            model = sm.Logit(y, x_mat)
            res = model.fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": patient})
        else:
            raise

    params = res.params
    conf = res.conf_int()
    pvals = res.pvalues

    records: list[dict[str, Any]] = []
    for term in params.index:
        if term == "const":
            continue
        coef = float(params[term])
        odds_ratio = float(np.exp(np.clip(coef, -50, 50)))
        lower_raw = conf.loc[term, 0]
        upper_raw = conf.loc[term, 1]
        lower = (
            float(np.exp(lower_raw)) if np.isfinite(lower_raw) and lower_raw < 100 else float("nan")
        )
        upper = (
            float(np.exp(upper_raw)) if np.isfinite(upper_raw) and upper_raw < 100 else float("nan")
        )
        pval = float(pvals[term]) if np.isfinite(pvals[term]) else float("nan")

        if term in num_cols:
            source_feature = term
            unit = f"per +1 SD (SD = {sd_dict[term]:.2f})"
        else:
            source_feature = dummy_to_source.get(term, term)
            unit = f"versus {ref_dict.get(source_feature, 'reference')}"

        records.append(
            {
                "term": term,
                "source_feature": source_feature,
                "odds_ratio": odds_ratio,
                "lower": lower,
                "upper": upper,
                "p_value": pval,
                "unit": unit,
            }
        )

    return pd.DataFrame(records)
