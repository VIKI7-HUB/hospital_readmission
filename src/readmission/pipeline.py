"""Readmission risk pipeline runner."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd

from readmission.stages import (
    stage_calibrate,
    stage_data,
    stage_evaluate,
    stage_explain_global,
    stage_fairness_audit,
    stage_fairness_mitigation,
    stage_features,
    stage_odds_ratios,
    stage_score,
    stage_split,
    stage_threshold,
    stage_train,
)

ROOT = Path(__file__).resolve().parents[2]

STAGES = [
    ("data", stage_data),
    ("split", stage_split),
    ("features", stage_features),
    ("train", stage_train),
    ("score", stage_score),
    ("calibrate", stage_calibrate),
    ("threshold", stage_threshold),
    ("evaluate", stage_evaluate),
    ("explain", stage_explain_global),
    ("odds", stage_odds_ratios),
    ("fairness", stage_fairness_audit),
    ("mitigation", stage_fairness_mitigation),
]


def readme_table(path: str = "artifacts/model_comparison.csv") -> str:
    """Format model comparison table as Markdown."""
    csv_path = ROOT / path
    if not csv_path.exists():
        return "model_comparison.csv not found."
    df = pd.read_csv(csv_path)
    cols = [
        "model",
        "threshold",
        "accuracy",
        "precision",
        "recall",
        "roc_auc",
        "pr_auc",
        "brier",
    ]
    if "brier" not in df.columns and "brier_score" in df.columns:
        df["brier"] = df["brier_score"]
    avail_cols = [c for c in cols if c in df.columns]
    lines = ["| " + " | ".join(avail_cols) + " |", "|" + "---|" * len(avail_cols)]
    for _, r in df[avail_cols].iterrows():
        row_vals = [str(r["model"])] + [f"{float(r[c]):.3f}" for c in avail_cols[1:]]
        lines.append("| " + " | ".join(row_vals) + " |")
    return "\n".join(lines)


def run_pipeline(
    fast: bool = False,
    from_stage: str | None = None,
    only: str | None = None,
) -> None:
    if fast:
        os.environ["READMISSION_FAST"] = "1"

    stage_names = [name for name, _ in STAGES]
    if only:
        if only not in stage_names:
            raise ValueError(f"Unknown stage: {only}. Must be one of {stage_names}")
        active_stages = [(name, fn) for name, fn in STAGES if name == only]
    elif from_stage:
        if from_stage not in stage_names:
            raise ValueError(f"Unknown stage: {from_stage}. Must be one of {stage_names}")
        start_idx = stage_names.index(from_stage)
        active_stages = STAGES[start_idx:]
    else:
        active_stages = STAGES

    total_start = time.perf_counter()
    for name, stage_fn in active_stages:
        t0 = time.perf_counter()
        print(f"=== Stage: {name} ===")
        stage_fn()
        elapsed = time.perf_counter() - t0
        print(f"Stage {name} completed in {elapsed:.2f}s\n")

    total_elapsed = time.perf_counter() - total_start
    print(f"All stages completed in {total_elapsed:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hospital readmission pipeline runner")
    parser.add_argument("--fast", action="store_true", help="Run fast pipeline")
    parser.add_argument("--from-stage", type=str, help="Start from specified stage")
    parser.add_argument("--only", type=str, help="Run only specified stage")
    parser.add_argument(
        "--readme-table", action="store_true", help="Print model comparison Markdown table"
    )
    args = parser.parse_args()

    if args.readme_table:
        print(readme_table())
        return

    run_pipeline(fast=args.fast, from_stage=args.from_stage, only=args.only)


if __name__ == "__main__":
    main()
