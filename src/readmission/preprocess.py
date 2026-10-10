"""Preprocessing builders for linear and tree models."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    OrdinalEncoder,
    StandardScaler,
)


def build_linear_preprocessor() -> ColumnTransformer:
    """Build a train-fitted impute, scale, and one-hot transformation."""
    numeric = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=0.01,
                    sparse_output=True,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, make_column_selector(dtype_include="number")),
            (
                "categorical",
                categorical,
                make_column_selector(dtype_include=["object", "string", "category"]),
            ),
        ],
        remainder="drop",
    )


def build_tree_preprocessor() -> ColumnTransformer:
    """Build a train-fitted ordinal encoder with passthrough numeric values."""
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            (
                "encoder",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-1,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", "passthrough", make_column_selector(dtype_include="number")),
            (
                "categorical",
                categorical,
                make_column_selector(dtype_include=["object", "string", "category"]),
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
