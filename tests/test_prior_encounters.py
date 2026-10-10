import pandas as pd

from readmission.features import prior_encounter_count


def test_prior_count_ignores_later_encounters():
    df = pd.DataFrame(
        {"patient_nbr": [1, 1, 1, 2], "encounter_id": [30, 10, 20, 5], "x": [0, 0, 0, 0]}
    )
    first = prior_encounter_count(df)
    assert list(first) == [2, 0, 1, 0]
    changed = df.copy()
    changed.loc[0, "x"] = 99
    assert list(prior_encounter_count(changed)) == list(first)
