from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from readmission.explain import contributions_matrix, source_feature
from readmission.scoring import frame_for_encounters

ROOT = Path(__file__).resolve().parents[1]


def test_source_feature_mapping():
    features = [
        "discharge_group",
        "time_in_hospital",
        "diag_1_category",
        "age",
        "age_mid",
    ]
    assert source_feature("cat__discharge_group_Home", features) == "discharge_group"
    assert source_feature("num__time_in_hospital", features) == "time_in_hospital"
    assert source_feature("diag_1_category_Circulatory", features) == "diag_1_category"
    assert source_feature("age_mid", features) == "age_mid"


def test_contributions_additivity():
    champion = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))[
        "model"
    ]
    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    test_ids = split["test"]
    rng = np.random.RandomState(42)
    sample_ids = rng.choice(test_ids, size=50, replace=False).tolist()
    frame = frame_for_encounters(sample_ids)
    contribs, base, margin = contributions_matrix(champion, frame)
    max_error = np.abs(contribs.sum(axis=1) + base - margin).max()
    assert max_error < 1e-4, f"Additivity error {max_error} exceeds 1e-4 for {champion}"


def test_explain_rows_sentence():
    from readmission.explain import explain_rows, top_sentence

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))
    test_ids = split["test"][:5]
    frame = frame_for_encounters(test_ids)
    res = explain_rows(frame)
    assert len(res["contribs"]) == 5
    assert len(res["values"]) == 5
    for idx in range(len(frame)):
        sentence = top_sentence(res["contribs"].iloc[idx], res["values"].iloc[idx])
        assert sentence.startswith("Higher risk mainly because of") or sentence.startswith(
            "No feature pushes"
        ), f"Unexpected sentence format: {sentence}"
