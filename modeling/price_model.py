"""Train and use a reproducible Ontario house-price estimation model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


CATEGORICAL_FEATURES = ["city", "property_type"]
NUMERIC_FEATURES = ["bedrooms", "days_on_market", "sale_year", "sale_month"]
MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


@dataclass(frozen=True)
class PriceModel:
    """Fitted estimator and held-out validation statistics."""

    pipeline: Pipeline
    mean_absolute_error: float
    r2_score: float
    prediction_margin: float
    training_rows: int


@dataclass(frozen=True)
class PriceEstimate:
    """Point estimate and validation-informed range."""

    predicted_price: float
    lower_bound: float
    upper_bound: float


def prepare_model_data(data: pd.DataFrame) -> pd.DataFrame:
    """Create model features from clean transaction data."""
    required = {
        "city",
        "property_type",
        "bedrooms",
        "days_on_market",
        "sale_date",
        "sale_price",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Model data is missing columns: {', '.join(sorted(missing))}")

    prepared = data.copy()
    prepared["sale_date"] = pd.to_datetime(prepared["sale_date"], errors="coerce")
    prepared["sale_year"] = prepared["sale_date"].dt.year
    prepared["sale_month"] = prepared["sale_date"].dt.month
    prepared = prepared.dropna(subset=MODEL_FEATURES + ["sale_price"])
    prepared = prepared[prepared["sale_price"] > 0]
    return prepared


def train_price_model(
    data: pd.DataFrame,
    random_state: int = 42,
) -> PriceModel:
    """Fit a random-forest model and calculate held-out validation metrics."""
    prepared = prepare_model_data(data)
    if len(prepared) < 50:
        raise ValueError("At least 50 valid transactions are required for training")

    features = prepared[MODEL_FEATURES]
    target = prepared["sale_price"]
    train_x, test_x, train_y, test_y = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=random_state,
    )

    preprocessor = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=240,
                    min_samples_leaf=4,
                    max_features=0.8,
                    n_jobs=-1,
                    random_state=random_state,
                ),
            ),
        ]
    )
    pipeline.fit(train_x, train_y)
    predictions = pipeline.predict(test_x)
    absolute_errors = np.abs(test_y.to_numpy() - predictions)

    return PriceModel(
        pipeline=pipeline,
        mean_absolute_error=float(mean_absolute_error(test_y, predictions)),
        r2_score=float(r2_score(test_y, predictions)),
        prediction_margin=float(np.quantile(absolute_errors, 0.8)),
        training_rows=len(prepared),
    )


def estimate_price(
    model: PriceModel,
    *,
    city: str,
    property_type: str,
    bedrooms: int,
    days_on_market: int,
    valuation_date: pd.Timestamp,
) -> PriceEstimate:
    """Estimate a price and an empirical 80% error range."""
    valuation_date = pd.Timestamp(valuation_date)
    features = pd.DataFrame(
        [
            {
                "city": city,
                "property_type": property_type,
                "bedrooms": bedrooms,
                "days_on_market": days_on_market,
                "sale_year": valuation_date.year,
                "sale_month": valuation_date.month,
            }
        ]
    )
    predicted_price = float(model.pipeline.predict(features)[0])
    return PriceEstimate(
        predicted_price=predicted_price,
        lower_bound=max(0.0, predicted_price - model.prediction_margin),
        upper_bound=predicted_price + model.prediction_margin,
    )
