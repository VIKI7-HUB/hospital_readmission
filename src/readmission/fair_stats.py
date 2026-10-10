from __future__ import annotations

import numpy as np
import pandas as pd

from readmission.metrics import wilson

MIN_POSITIVES = 100


def group_table(
    df: pd.DataFrame,
    group_col: str,
    threshold: float,
    y_col: str = "y_true",
    p_col: str = "p_cal",
) -> pd.DataFrame:
    """Per-group counts and rates at one threshold, with Wilson intervals."""
    rows = []
    for name, g in df.groupby(group_col, observed=True):
        y = g[y_col].to_numpy().astype(int)
        flagged = (g[p_col].to_numpy() >= threshold).astype(int)
        tp = int(((flagged == 1) & (y == 1)).sum())
        fp = int(((flagged == 1) & (y == 0)).sum())
        pos, neg = int(y.sum()), int((y == 0).sum())
        tpr_lo, tpr_hi = wilson(tp, pos)
        fpr_lo, fpr_hi = wilson(fp, neg)
        rows.append(
            {
                "group": name,
                "n": len(g),
                "positives": pos,
                "selection_rate": flagged.mean(),
                "tpr": tp / pos if pos else np.nan,
                "tpr_lo": tpr_lo,
                "tpr_hi": tpr_hi,
                "fpr": fp / neg if neg else np.nan,
                "fpr_lo": fpr_lo,
                "fpr_hi": fpr_hi,
                "precision": tp / (tp + fp) if (tp + fp) else np.nan,
                "mean_pred": g[p_col].mean(),
                "observed": y.mean(),
                "underpowered": pos < MIN_POSITIVES,
            }
        )
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def _weighted_rate(y, flagged, w, mask, kind: str) -> float:
    m = mask & (y == 1) if kind == "tpr" else mask & (y == 0)
    den = w[m].sum()
    return float((w[m] * flagged[m]).sum() / den) if den > 0 else np.nan


def gap_interval(
    df: pd.DataFrame,
    group_col: str,
    group_a: str,
    group_ref: str,
    threshold: float,
    kind: str = "tpr",
    patient_col: str = "patient_nbr",
    n_boot: int = 1000,
    seed: int = 42,
) -> dict:
    """Gap (a minus reference) in percentage points with a patient-level bootstrap interval."""
    y = df["y_true"].to_numpy().astype(int)
    flagged = (df["p_cal"].to_numpy() >= threshold).astype(int)
    grp = df[group_col].to_numpy()
    uniq, inv = np.unique(df[patient_col].to_numpy(), return_inverse=True)
    ma, mr = grp == group_a, grp == group_ref
    ones = np.ones(len(df))
    point = (
        _weighted_rate(y, flagged, ones, ma, kind) - _weighted_rate(y, flagged, ones, mr, kind)
    ) * 100
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        w = counts[inv].astype(float)
        draws.append(
            (_weighted_rate(y, flagged, w, ma, kind) - _weighted_rate(y, flagged, w, mr, kind))
            * 100
        )
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {
        "group": group_a,
        "reference": group_ref,
        "metric": kind,
        "gap_pp": float(point),
        "lower_pp": float(lo),
        "upper_pp": float(hi),
        "crosses_zero": bool(lo <= 0 <= hi),
    }


def disparity_summary(table: pd.DataFrame) -> dict:
    """Summary over groups that are not underpowered."""
    t = table[~table["underpowered"]]
    if len(t) < 2:
        return {}
    ref_rate = t["selection_rate"].max()
    return {
        "tpr_difference": float(t["tpr"].max() - t["tpr"].min()),
        "fpr_difference": float(t["fpr"].max() - t["fpr"].min()),
        "equalized_odds_difference": float(
            max(t["tpr"].max() - t["tpr"].min(), t["fpr"].max() - t["fpr"].min())
        ),
        "demographic_parity_difference": float(
            t["selection_rate"].max() - t["selection_rate"].min()
        ),
        "selection_rate_ratio": float(t["selection_rate"].min() / ref_rate) if ref_rate else np.nan,
    }


def group_thresholds(
    val: pd.DataFrame,
    group_col: str,
    target_tpr: float,
    fallback: float,
    grid=None,
    min_positives: int = MIN_POSITIVES,
) -> dict:
    """Per-group threshold: the highest threshold whose validation TPR is at least target_tpr.
    Groups with too few positives keep the fallback threshold."""
    grid = np.round(np.arange(0.01, 0.80 + 1e-9, 0.005), 3) if grid is None else grid
    out = {}
    for name, g in val.groupby(group_col, observed=True):
        y = g["y_true"].to_numpy().astype(int)
        p = g["p_cal"].to_numpy()
        if y.sum() < min_positives:
            out[name] = float(fallback)
            continue
        ok = [t for t in grid if ((p >= t) & (y == 1)).sum() / y.sum() >= target_tpr]
        out[name] = float(max(ok)) if ok else float(grid.min())
    return out


def apply_group_thresholds(
    df: pd.DataFrame, group_col: str, thresholds: dict, fallback: float
) -> np.ndarray:
    t = df[group_col].map(thresholds).fillna(fallback).to_numpy(dtype=float)
    return (df["p_cal"].to_numpy() >= t).astype(int)


def reweighing_weights(group, y) -> np.ndarray:
    """Kamiran and Calders weights: P(group) * P(y) / P(group, y), so group and label are independent."""
    d = pd.DataFrame({"g": np.asarray(group), "y": np.asarray(y).astype(int)})
    n = len(d)
    p_g = d["g"].map(d["g"].value_counts() / n)
    p_y = d["y"].map(d["y"].value_counts() / n)
    joint = d.groupby(["g", "y"])["y"].transform("size") / n
    return (p_g * p_y / joint).to_numpy()
