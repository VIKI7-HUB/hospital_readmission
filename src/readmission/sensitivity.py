"""Sensitivity check: first encounter per patient."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score

from readmission.features import MODEL_FEATURES
from readmission.model_registry import MODEL_REGISTRY, FittedReadmissionModel
from readmission.scoring import frame_for_encounters

ROOT = Path(__file__).resolve().parents[2]


def run_sensitivity() -> dict:
    """Fit champion model on first encounters only and evaluate on test first encounters."""
    with (ROOT / "configs" / "config.yaml").open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    champ_data = json.loads((ROOT / "artifacts" / "champion.json").read_text(encoding="utf-8"))
    champion = champ_data.get("champion") or champ_data.get("model")

    best_params_all = json.loads(
        (ROOT / "artifacts" / "best_params.json").read_text(encoding="utf-8")
    )
    champ_params = best_params_all[champion].get("parameters", best_params_all[champion])

    split = json.loads((ROOT / "artifacts" / "split.json").read_text(encoding="utf-8"))

    clean = pd.read_parquet(
        ROOT / "artifacts" / "clean.parquet",
        columns=["encounter_id", "patient_nbr", "readmit_30"],
    )

    first_enc = clean.groupby("patient_nbr")["encounter_id"].min().to_dict()
    first_enc_set = set(first_enc.values())

    train_first_ids = [eid for eid in split["train"] if eid in first_enc_set]
    test_first_ids = [eid for eid in split["test"] if eid in first_enc_set]

    train_frame = frame_for_encounters(train_first_ids)
    test_frame = frame_for_encounters(test_first_ids)

    feature_cols = [c for c in MODEL_FEATURES if c in train_frame.columns]
    train_x = train_frame[feature_cols]
    train_y = train_frame["y_true"].astype(int)

    test_x = test_frame[feature_cols]
    test_y = test_frame["y_true"].astype(int)

    spec = MODEL_REGISTRY[champion]
    preprocessor = spec.preprocessor()
    train_values = preprocessor.fit_transform(train_x)

    seed = int(config["models"]["seed"])
    estimator = spec.factory(champ_params, seed, train_y, config, False)
    estimator.fit(train_values, train_y)
    first_model = FittedReadmissionModel(estimator, preprocessor, False)

    first_test_preds = first_model.predict_proba(test_x)[:, 1]
    roc_auc_first = float(roc_auc_score(test_y, first_test_preds))
    pr_auc_first = float(average_precision_score(test_y, first_test_preds))

    scores_test = pd.read_parquet(ROOT / "artifacts" / "scores" / f"{champion}__test.parquet")
    scores_first = scores_test[scores_test["encounter_id"].isin(test_first_ids)]
    scores_merged = (
        test_frame[["encounter_id", "y_true"]]
        .reset_index(drop=True)
        .merge(scores_first, on="encounter_id")
    )
    roc_auc_orig = float(roc_auc_score(scores_merged["y_true_x"], scores_merged["p_raw"]))

    pr_auc_orig = float(
        average_precision_score(scores_merged["y_true_x"], scores_merged["p_raw"])
    )

    result = {
        "model": champion,
        "n_train_total": len(split["train"]),
        "n_train_first": len(train_first_ids),
        "n_test_total": len(split["test"]),
        "n_test_first": len(test_first_ids),
        "first_encounters_only": {
            "roc_auc": roc_auc_first,
            "pr_auc": pr_auc_first,
        },
        "all_encounters_champion": {
            "roc_auc": roc_auc_orig,
            "pr_auc": pr_auc_orig,
        },
    }

    (ROOT / "artifacts" / "sensitivity.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Sensitivity check: train={len(train_first_ids)}/{len(split['train'])}, "
        f"test={len(test_first_ids)}/{len(split['test'])}"
    )
    print(
        f"First-only model on test first: ROC-AUC={roc_auc_first:.4f}, PR-AUC={pr_auc_first:.4f}"
    )
    print(
        f"All-encs champion on test first: ROC-AUC={roc_auc_orig:.4f}, PR-AUC={pr_auc_orig:.4f}"
    )
    return result
