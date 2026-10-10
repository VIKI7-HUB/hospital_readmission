from readmission import textgen as TG


def test_risk_sentence_template():
    s = TG.describe_risk(
        [("number_inpatient", "2", 0.4), ("time_in_hospital", "9", 0.2), ("age", "70-80", -0.1)],
        {"number_inpatient": "Prior inpatient stays"},
    )
    assert s.startswith(
        "Higher risk mainly because of: Prior inpatient stays (2); Time in hospital (9)."
    )
    assert "Lower risk because of: Age (70-80)." in s
    assert TG.describe_risk([("x", "1", -0.2)]).startswith("No feature pushes")
