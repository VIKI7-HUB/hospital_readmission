"""Tests for patient-level splitting and training-only caps."""

import pandas as pd

from readmission.split import (
    apply_caps,
    assert_no_overlap,
    fit_caps,
    patient_split,
)


def _synthetic_frame() -> pd.DataFrame:
    patient_ids = list(range(100))
    return pd.DataFrame(
        {
            "encounter_id": [patient * 10 + visit for patient in patient_ids for visit in (1, 2)],
            "patient_nbr": [patient for patient in patient_ids for _ in (1, 2)],
            "readmit_30": [patient % 2 for patient in patient_ids for _ in (1, 2)],
        }
    )


def test_split_has_no_patient_overlap() -> None:
    frame = _synthetic_frame()
    train, validation, test = patient_split(frame, seed=17)

    assert_no_overlap(frame, train, validation, test)


def test_split_proportions_are_within_two_percentage_points() -> None:
    frame = _synthetic_frame()
    train, validation, test = patient_split(frame, seed=17)
    achieved = [len(index) / len(frame) for index in (train, validation, test)]

    expected_ratios = (0.70, 0.10, 0.20)
    assert all(
        abs(actual - expected) <= 0.02
        for actual, expected in zip(achieved, expected_ratios, strict=True)
    )


def test_caps_use_training_rows_only_when_test_values_change() -> None:
    train = pd.DataFrame({"number_inpatient": [0, 1, 2, 3, 4, 5]})
    test = pd.DataFrame({"number_inpatient": [6, 7]})
    frame = pd.concat([train, test], ignore_index=True)
    train_index = frame.index[: len(train)]
    test_index = frame.index[len(train) :]

    train_caps = fit_caps(frame.loc[train_index], ["number_inpatient"])
    frame.loc[test_index, "number_inpatient"] = [1_000_000, 2_000_000]
    train_caps_after_test_change = fit_caps(frame.loc[train_index], ["number_inpatient"])

    assert train_caps == train_caps_after_test_change
    assert train_caps["number_inpatient"] == 4.95
    capped = apply_caps(frame.loc[test_index], train_caps)
    assert capped["number_inpatient"].max() == 4.95
    assert frame.loc[test_index, "number_inpatient"].max() == 2_000_000


def test_split_is_repeatable_for_same_seed() -> None:
    frame = _synthetic_frame()
    first = patient_split(frame, seed=29)
    second = patient_split(frame, seed=29)

    assert all(left.equals(right) for left, right in zip(first, second, strict=True))
