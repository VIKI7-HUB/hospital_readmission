"""Validation-only threshold selection checks."""

import inspect

import numpy as np

from readmission.calibrate import select_operating_threshold


def test_operating_threshold_uses_validation_scores_only() -> None:
    """The selector accepts validation labels and scores, not test data."""
    parameters = inspect.signature(select_operating_threshold).parameters
    assert set(parameters) == {"y_true", "probabilities", "recall_target"}

    validation_target = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    validation_scores = np.array([0.95, 0.85, 0.2, 0.9, 0.88, 0.7, 0.6, 0.1])
    selected = select_operating_threshold(validation_target, validation_scores, recall_target=2 / 3)

    assert selected["threshold"] == 0.85
    assert selected["precision"] == 0.5
    assert selected["recall"] == 2 / 3
    assert selected["recall_target_met"] is True
