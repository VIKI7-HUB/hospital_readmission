from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_pipeline_determinism_from_score():
    csv_path = ROOT / "artifacts" / "model_comparison.csv"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "readmission.pipeline",
            "--fast",
            "--from-stage",
            "score",
        ],
        cwd=ROOT,
        check=True,
    )
    bytes_1 = csv_path.read_bytes()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "readmission.pipeline",
            "--fast",
            "--from-stage",
            "score",
        ],
        cwd=ROOT,
        check=True,
    )
    bytes_2 = csv_path.read_bytes()

    assert bytes_1 == bytes_2
