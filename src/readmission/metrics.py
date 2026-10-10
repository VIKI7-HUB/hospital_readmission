from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


def _div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def confusion_counts(y, p, t: float, w=None) -> tuple[float, float, float, float]:
    """Return tp, fp, tn, fn at threshold t. Optional row weights w."""
    y = np.asarray(y).astype(int)
    pred = (np.asarray(p) >= t).astype(int)
    w = np.ones(len(y)) if w is None else np.asarray(w, dtype=float)
    tp = float(w[(pred == 1) & (y == 1)].sum())
    fp = float(w[(pred == 1) & (y == 0)].sum())
    tn = float(w[(pred == 0) & (y == 0)].sum())
    fn = float(w[(pred == 0) & (y == 1)].sum())
    return tp, fp, tn, fn


def threshold_metrics(y, p, t: float, w=None) -> dict:
    tp, fp, tn, fn = confusion_counts(y, p, t, w)
    precision = _div(tp, tp + fp)
    recall = _div(tp, tp + fn)
    total = tp + fp + tn + fn
    return {
        "threshold": float(t),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": _div(tp + tn, total),
        "precision": precision,
        "recall": recall,
        "specificity": _div(tn, tn + fp),
        "npv": _div(tn, tn + fn),
        "f1": _div(2 * precision * recall, precision + recall),
        "f2": _div(5 * precision * recall, 4 * precision + recall),
        "flag_rate": _div(tp + fp, total),
    }


def ranking_metrics(y, p, w=None) -> dict:
    y = np.asarray(y).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, p, sample_weight=w)),
        "pr_auc": float(average_precision_score(y, p, sample_weight=w)),
        "brier": float(brier_score_loss(y, p, sample_weight=w)),
    }


def sweep(y, p, grid=None) -> pd.DataFrame:
    grid = np.round(np.arange(0.02, 0.60 + 1e-9, 0.01), 3) if grid is None else grid
    return pd.DataFrame([threshold_metrics(y, p, t) for t in grid])


def roc_points(y, p) -> pd.DataFrame:
    fpr, tpr, thr = roc_curve(y, p)
    return pd.DataFrame({"fpr": fpr, "tpr": tpr, "threshold": thr})


def pr_points(y, p) -> pd.DataFrame:
    prec, rec, thr = precision_recall_curve(y, p)
    thr = np.append(thr, np.nan)
    return pd.DataFrame({"precision": prec, "recall": rec, "threshold": thr})


def reliability_points(y, p, n_bins: int = 10) -> pd.DataFrame:
    """Quantile bins of predicted risk with mean predicted and observed rate."""
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    df["bin"] = pd.qcut(df["p"], q=n_bins, duplicates="drop")
    out = df.groupby("bin", observed=True).agg(
        mean_pred=("p", "mean"), observed=("y", "mean"), n=("y", "size")
    )
    return out.reset_index(drop=True)


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    ph = k / n
    denom = 1 + z**2 / n
    centre = (ph + z**2 / (2 * n)) / denom
    spread = z * np.sqrt(ph * (1 - ph) / n + z**2 / (4 * n**2)) / denom
    return (float(centre - spread), float(centre + spread))


def gains_table(y, p, n_bins: int = 10) -> pd.DataFrame:
    """Rows sorted by risk; cumulative share of readmissions captured by top x percent."""
    df = pd.DataFrame({"y": np.asarray(y).astype(int), "p": np.asarray(p)})
    df = df.sort_values("p", ascending=False, kind="mergesort").reset_index(drop=True)
    n, pos = len(df), df["y"].sum()
    cuts = np.unique(np.ceil(np.linspace(0, n, n_bins + 1)).astype(int))[1:]
    rows = []
    for c in cuts:
        captured = df["y"].iloc[:c].sum()
        rows.append(
            {
                "top_share": c / n,
                "captured": int(captured),
                "recall": captured / pos,
                "precision": captured / c,
                "lift": (captured / c) / (pos / n),
            }
        )
    return pd.DataFrame(rows)


def net_benefit(y, p, thresholds) -> pd.DataFrame:
    y = np.asarray(y).astype(int)
    p = np.asarray(p)
    n = len(y)
    prev = y.mean()
    rows = []
    for t in thresholds:
        flagged = p >= t
        tp = (flagged & (y == 1)).sum()
        fp = (flagged & (y == 0)).sum()
        odds = t / (1 - t)
        rows.append(
            {
                "threshold": float(t),
                "model": tp / n - fp / n * odds,
                "treat_all": prev - (1 - prev) * odds,
                "treat_none": 0.0,
            }
        )
    return pd.DataFrame(rows)


def patient_bootstrap(
    y, p, patient_codes, stat_fn, n_boot: int = 1000, seed: int = 42
) -> pd.DataFrame:
    """Resample whole patients. stat_fn(y, p, w) -> dict of numbers; w are row weights."""
    y = np.asarray(y)
    p = np.asarray(p)
    codes = np.asarray(patient_codes)
    uniq, inv = np.unique(codes, return_inverse=True)
    n_pat = len(uniq)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, n_pat, n_pat), minlength=n_pat)
        draws.append(stat_fn(y, p, counts[inv].astype(float)))
    return pd.DataFrame(draws)


def interval(draws: pd.DataFrame, level: float = 0.95) -> pd.DataFrame:
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    return pd.DataFrame(
        {
            "mean": draws.mean(),
            "lower": draws.quantile(lo),
            "upper": draws.quantile(hi),
        }
    )


def paired_bootstrap(
    y, p_a, p_b, patient_codes, stat_fn, n_boot: int = 1000, seed: int = 42
) -> pd.DataFrame:
    """Same patient resamples for two models. stat_fn(y, p, w) -> dict. Returns a minus b per statistic."""
    y = np.asarray(y)
    p_a, p_b = np.asarray(p_a), np.asarray(p_b)
    uniq, inv = np.unique(np.asarray(patient_codes), return_inverse=True)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        w = counts[inv].astype(float)
        a, b = stat_fn(y, p_a, w), stat_fn(y, p_b, w)
        rows.append({k: a[k] - b[k] for k in a})
    return pd.DataFrame(rows)


def difference_summary(diff: pd.DataFrame) -> pd.DataFrame:
    """Mean difference, 95 percent interval and share of resamples where a beats b."""
    out = interval(diff)
    out["share_a_better"] = (diff > 0).mean()
    return out
