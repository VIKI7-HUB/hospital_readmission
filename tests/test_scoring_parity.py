import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from readmission.scoring import frame_for_encounters, predict_raw

ROOT = Path(__file__).resolve().parents[1]


def test_page_scoring_path_reproduces_stored_predictions():
    stored = pd.read_parquet(ROOT / "artifacts" / "test_predictions.parquet").sample(
        25, random_state=0
    )
    with (ROOT / "artifacts" / "champion.json").open(encoding="utf-8") as f:
        d = json.load(f)
        champion = d.get("champion") or d.get("model")

    frame = frame_for_encounters(stored["encounter_id"].tolist())
    cal = joblib.load(ROOT / "artifacts" / "models" / "calibrators" / f"{champion}.joblib")
    got = pd.Series(
        cal.predict(predict_raw(champion, frame)),
        index=frame["encounter_id"].to_numpy(),
    )
    want = stored.set_index("encounter_id")["p_cal"]
    assert np.abs(got.reindex(want.index).to_numpy() - want.to_numpy()).max() < 1e-6
