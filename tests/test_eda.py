import pandas as pd

from readmission import eda


def _df():
    return pd.DataFrame(
        {
            "grp": ["a"] * 100 + ["b"] * 50,
            "step": ["x"] * 80 + ["y"] * 70,
            "readmit_30": [1] * 20 + [0] * 80 + [1] * 25 + [0] * 25,
        }
    )


def test_rate_table_values():
    t = eda.rate_table(_df(), "grp").set_index("grp")
    assert t.loc["a", "n"] == 100 and t.loc["a", "positives"] == 20
    assert abs(t.loc["a", "rate"] - 0.2) < 1e-12
    assert t.loc["a", "lo"] < 0.2 < t.loc["a", "hi"]


def test_sankey_links_conserve_counts():
    labels, source, target, value = eda.sankey_links(_df(), ["grp", "step"])
    assert sum(value) == 150
    assert len(source) == len(target) == len(value)
    assert set(labels) >= {"a", "b", "x", "y"}
