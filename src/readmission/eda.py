from __future__ import annotations

import pandas as pd

from readmission.metrics import wilson


def rate_table(df: pd.DataFrame, col: str, target: str = "readmit_30") -> pd.DataFrame:
    """Readmission rate per level of col with Wilson 95 percent intervals."""
    g = df.groupby(col, observed=True)[target].agg(n="size", positives="sum").reset_index()
    g["rate"] = g["positives"] / g["n"]
    bounds = g.apply(lambda r: wilson(r["positives"], r["n"]), axis=1, result_type="expand")
    g["lo"], g["hi"] = bounds[0], bounds[1]
    return g


def sankey_links(df: pd.DataFrame, cols: list[str]):
    """Node labels and link arrays for a Plotly Sankey across consecutive columns."""
    labels: list[str] = []
    index: dict[tuple[str, str], int] = {}

    def node(col: str, val) -> int:
        key = (col, str(val))
        if key not in index:
            index[key] = len(labels)
            labels.append(str(val))
        return index[key]

    source, target, value = [], [], []
    for a, b in zip(cols[:-1], cols[1:], strict=False):
        counts = df.groupby([a, b], observed=True).size().reset_index(name="n")
        for _, r in counts.iterrows():
            source.append(node(a, r[a]))
            target.append(node(b, r[b]))
            value.append(int(r["n"]))
    return labels, source, target, value
