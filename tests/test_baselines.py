import pandas as pd

from readmission import baselines as B


def test_charlson_points():
    assert B.charlson_points(["428", "250.41", "V45"]) == 3
    assert B.charlson_points(["196.1", "410.01"]) == 7
    assert B.charlson_points(["Unknown", "250.00"]) == 0


def test_lace_score_components():
    df = pd.DataFrame(
        {
            "time_in_hospital": [1, 8, 15],
            "admission_type_id": [1, 3, 1],
            "diag_1": ["428", "250.00", "197"],
            "diag_2": ["Unknown"] * 3,
            "diag_3": ["Unknown"] * 3,
            "number_emergency": [0, 6, 1],
        }
    )
    assert list(B.lace_score(df)) == [5, 9, 16]
