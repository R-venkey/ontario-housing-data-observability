import pandas as pd

from ingestion.sample_data_generator import generate_sample_data
from modeling.price_model import estimate_price, prepare_model_data, train_price_model
from transformations.bronze_to_silver import clean_housing_data


def sample_training_data() -> pd.DataFrame:
    return clean_housing_data(
        generate_sample_data(start_date="2024-01-01", months=8, seed=7)
    )


def test_model_training_produces_useful_validation_metrics() -> None:
    model = train_price_model(sample_training_data())

    assert model.training_rows > 1_000
    assert model.mean_absolute_error > 0
    assert model.mean_absolute_error < 200_000
    assert model.r2_score > 0.75
    assert model.prediction_margin >= model.mean_absolute_error


def test_price_estimate_returns_ordered_positive_range() -> None:
    model = train_price_model(sample_training_data())

    estimate = estimate_price(
        model,
        city="Toronto",
        property_type="Detached",
        bedrooms=4,
        days_on_market=20,
        valuation_date=pd.Timestamp("2025-06-01"),
    )

    assert 500_000 < estimate.predicted_price < 2_000_000
    assert 0 < estimate.lower_bound < estimate.predicted_price
    assert estimate.upper_bound > estimate.predicted_price


def test_prepare_model_data_requires_model_columns() -> None:
    data = pd.DataFrame({"city": ["Toronto"]})

    try:
        prepare_model_data(data)
    except ValueError as error:
        assert "missing columns" in str(error)
    else:
        raise AssertionError("Expected missing model columns to raise ValueError")
