import numpy as np
from synth import frame, n

from readmission import fair_stats as F


def test_group_table_matches_manual_tpr():
    df = frame()
    t = F.group_table(df, "grp", 0.2).set_index("group")
    a = df[df.grp == "A"]
    tpr = ((a.p_cal >= 0.2) & (a.y_true == 1)).sum() / (a.y_true == 1).sum()
    assert abs(t.loc["A", "tpr"] - tpr) < 1e-12
    assert t.loc["C", "underpowered"] and not t.loc["A", "underpowered"]


def test_gap_interval_contains_point():
    r = F.gap_interval(frame(), "grp", "B", "A", 0.2, "tpr", n_boot=200)
    assert r["lower_pp"] <= r["gap_pp"] <= r["upper_pp"]
    assert F.gap_interval(frame(), "grp", "B", "A", 0.2, "fpr", n_boot=50)["metric"] == "fpr"


def test_disparity_summary_consistent():
    s = F.disparity_summary(F.group_table(frame(), "grp", 0.2))
    assert s["equalized_odds_difference"] >= max(s["tpr_difference"], s["fpr_difference"]) - 1e-12
    assert 0 <= s["selection_rate_ratio"] <= 1


def test_group_thresholds_reach_target_and_fallback():
    df = frame()
    thr = F.group_thresholds(df, "grp", 0.6, 0.2)
    assert thr["C"] == 0.2
    flagged = F.apply_group_thresholds(df, "grp", thr, 0.2)
    for g in ("A", "B"):
        m = ((df.grp == g) & (df.y_true == 1)).to_numpy()
        assert flagged[m].mean() >= 0.58


def test_reweighing_makes_group_and_label_independent():
    rng = np.random.default_rng(1)
    g = rng.choice(["a", "b"], n, p=[0.7, 0.3])
    yy = (rng.random(n) < np.where(g == "a", 0.08, 0.2)).astype(int)
    w = F.reweighing_weights(g, yy)
    rate = {k: w[(g == k) & (yy == 1)].sum() / w[g == k].sum() for k in ("a", "b")}
    assert abs(rate["a"] - rate["b"]) < 1e-9 and abs(w.sum() - n) < 1e-6


def test_mitigated_recall_within_five_percentage_points_of_base():
    from pathlib import Path

    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    df = pd.read_csv(root / "artifacts" / "fairness_mitigation.csv")
    for attr in df["attribute"].unique():
        sub = df[df["attribute"] == attr].set_index("variant")
        base_recall = float(sub.loc["base", "recall"])
        mitigated_recall = float(sub.loc["group_threshold", "recall"])
        assert abs(mitigated_recall - base_recall) <= 0.05, (
            f"Recall difference {abs(mitigated_recall - base_recall):.4f} for {attr} exceeds 0.05"
        )
