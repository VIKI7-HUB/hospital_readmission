"""Model explanation methods and feature contributions."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from readmission.features import MODEL_FEATURES

ROOT = Path(__file__).resolve().parents[2]


def source_feature(column_name: str, source_features: list[str]) -> str:
    """Map an encoded column name back to the original source feature name."""
    remainder = column_name.split("__", 1)[-1]
    matches = [f for f in source_features if remainder.startswith(f)]
    if not matches:
        return remainder
    return max(matches, key=len)


def contributions_matrix(
    model_name: str, frame: pd.DataFrame
) -> tuple[pd.DataFrame, float | np.ndarray, np.ndarray]:
    """Compute per-original-feature contributions, base value, and raw margin."""
    model_path = ROOT / "artifacts" / "models" / f"{model_name}.joblib"
    model = joblib.load(model_path)
    feature_cols = [c for c in MODEL_FEATURES if c in frame.columns]
    raw_x = frame[feature_cols]

    if model_name == "random_forest":
        import shap

        x_trans = model.preprocessor.transform(raw_x)
        transformed_cols = list(model.preprocessor.get_feature_names_out())
        explainer = shap.TreeExplainer(model.estimator)
        if len(x_trans) > 100:
            chunks = np.array_split(x_trans, 4)
            res = joblib.Parallel(n_jobs=4)(
                joblib.delayed(explainer.shap_values)(chunk, check_additivity=False)
                for chunk in chunks
            )
            sv = np.concatenate(res, axis=0)
        else:
            sv = explainer.shap_values(x_trans, check_additivity=False)
        raw_shap = sv[:, :, 1] if isinstance(sv, np.ndarray) and sv.ndim == 3 else sv[1]
        exp_val = explainer.expected_value
        base_val = float(exp_val[1]) if hasattr(exp_val, "__len__") else float(exp_val)
        raw_margin = model.estimator.predict_proba(x_trans)[:, 1]

    elif model_name == "xgboost":
        import xgboost

        x_trans = model.preprocessor.transform(raw_x)
        transformed_cols = list(model.preprocessor.get_feature_names_out())
        dmat = xgboost.DMatrix(x_trans)
        contribs_raw = model.estimator.get_booster().predict(dmat, pred_contribs=True)
        raw_shap = contribs_raw[:, :-1]
        base_val = contribs_raw[:, -1]
        raw_margin = model.estimator.get_booster().predict(dmat, output_margin=True)

    elif model_name == "lightgbm":
        x_trans = model.preprocessor.transform(raw_x)
        transformed_cols = list(model.preprocessor.get_feature_names_out())
        contribs_raw = model.estimator.booster_.predict(x_trans, pred_contrib=True)
        raw_shap = contribs_raw[:, :-1]
        base_val = contribs_raw[:, -1]
        raw_margin = model.estimator.booster_.predict(x_trans, raw_score=True)

    elif model_name == "catboost":
        import catboost

        from readmission.model_registry import catboost_frame

        values, cat_cols = catboost_frame(raw_x)
        pool = catboost.Pool(values, cat_features=cat_cols)
        contribs_raw = model.estimator.get_feature_importance(pool, type="ShapValues")
        raw_shap = contribs_raw[:, :-1]
        base_val = contribs_raw[:, -1]
        raw_margin = model.estimator.predict(pool, prediction_type="RawFormulaVal")
        transformed_cols = list(values.columns)

    elif model_name == "logistic_regression":
        x_trans = model.preprocessor.transform(raw_x)
        transformed_cols = list(model.preprocessor.get_feature_names_out())
        if hasattr(x_trans, "toarray"):
            x_trans = x_trans.toarray()
        coef = model.estimator.coef_[0]
        intercept = model.estimator.intercept_[0]
        mean_x = np.asarray(x_trans.mean(axis=0)).ravel()
        raw_shap = (x_trans - mean_x) * coef
        base_val = float(intercept + np.dot(mean_x, coef))
        raw_margin = np.asarray(model.estimator.decision_function(x_trans))

    else:
        raise ValueError(f"Unsupported model for explanation: {model_name}")

    col_to_src = [source_feature(col, feature_cols) for col in transformed_cols]
    contrib_df = pd.DataFrame(0.0, index=frame.index, columns=feature_cols)
    for j, src in enumerate(col_to_src):
        if src in contrib_df.columns:
            contrib_df[src] += raw_shap[:, j]

    return contrib_df, base_val, np.asarray(raw_margin, dtype=float)
