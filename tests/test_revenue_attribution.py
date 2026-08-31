import polars as pl
import pytest
import os
import json
from mam.core import MAM
from mam.preprocessing import MAMPipeline


@pytest.fixture
def format_1_revenue_df():
    """Format 1 (Sessions / Touchpoints) with a revenue column."""
    data = [
        {
            "datetime": "2026-01-01 01:00:00",
            "user_id": "user_1",
            "channel": "direct",
            "has_conversion": False,
            "revenue": 0.0,
        },
        {
            "datetime": "2026-01-01 02:00:00",
            "user_id": "user_1",
            "channel": "google_search",
            "has_conversion": False,
            "revenue": 0.0,
        },
        {
            "datetime": "2026-01-01 03:00:00",
            "user_id": "user_1",
            "channel": "meta_ads",
            "has_conversion": True,
            "revenue": 150.0,  # Revenue on the converting session
        },
        {
            "datetime": "2026-01-01 01:30:00",
            "user_id": "user_2",
            "channel": "meta_ads",
            "has_conversion": False,
            "revenue": 0.0,
        },
        {
            "datetime": "2026-01-01 02:30:00",
            "user_id": "user_2",
            "channel": "direct",
            "has_conversion": False,
            "revenue": 0.0,
        },
        {
            "datetime": "2026-01-01 04:00:00",
            "user_id": "user_3",
            "channel": "email",
            "has_conversion": False,
            "revenue": 0.0,
        },
        {
            "datetime": "2026-01-01 05:00:00",
            "user_id": "user_3",
            "channel": "organic_search",
            "has_conversion": True,
            "revenue": 300.0,  # Revenue on the converting session
        },
    ]
    return pl.DataFrame(data).with_columns(pl.col("datetime").str.to_datetime())


@pytest.fixture
def format_2_revenue_df():
    """Format 2 (Journeys) with a revenue column."""
    data = [
        {
            "start_time": "2026-01-01 01:00:00",
            "end_time": "2026-01-01 03:00:00",
            "journey_id": "user_1_0",
            "journey": "direct > google_search > meta_ads",
            "has_conversion": True,
            "time_till_end": "2.0 > 1.0 > 0.0",
            "revenue": 150.0,
        },
        {
            "start_time": "2026-01-01 01:30:00",
            "end_time": "2026-01-01 02:30:00",
            "journey_id": "user_2_0",
            "journey": "meta_ads > direct",
            "has_conversion": False,
            "time_till_end": "1.0 > 0.0",
            "revenue": 0.0,
        },
        {
            "start_time": "2026-01-01 04:00:00",
            "end_time": "2026-01-01 05:00:00",
            "journey_id": "user_3_0",
            "journey": "email > organic_search",
            "has_conversion": True,
            "time_till_end": "1.0 > 0.0",
            "revenue": 300.0,
        },
    ]
    return pl.DataFrame(data)


def test_preprocessing_revenue_format_1(format_1_revenue_df):
    """Test that Format 1 preprocessing maps and aggregates the revenue correctly."""
    unified_df = MAMPipeline.preprocess(
        df=format_1_revenue_df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
        conversion_value_colname="revenue",
    )

    assert "conversion_value" in unified_df.columns
    # Check that revenue has been summed per user journey
    user_1_row = unified_df.filter(pl.col("journey_id") == "user_1")
    assert user_1_row["conversion_value"][0] == 150.0

    user_2_row = unified_df.filter(pl.col("journey_id") == "user_2")
    assert user_2_row["conversion_value"][0] == 0.0

    user_3_row = unified_df.filter(pl.col("journey_id") == "user_3")
    assert user_3_row["conversion_value"][0] == 300.0


def test_preprocessing_revenue_format_2(format_2_revenue_df):
    """Test that Format 2 preprocessing maps and converts the revenue correctly."""
    unified_df = MAMPipeline.preprocess(
        df=format_2_revenue_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        user_id_colname="journey_id",
        time_till_conv_colname="time_till_end",
        conversion_value_colname="revenue",
    )

    assert "conversion_value" in unified_df.columns
    # Check that revenue values are preserved
    user_1_row = unified_df.filter(pl.col("journey_id") == "user_1_0")
    assert user_1_row["conversion_value"][0] == 150.0

    user_2_row = unified_df.filter(pl.col("journey_id") == "user_2_0")
    assert user_2_row["conversion_value"][0] == 0.0


def test_heuristic_models_revenue_attribution(format_2_revenue_df):
    """Test that all heuristic models attribute values based on revenue."""
    mam = MAM(
        df=format_2_revenue_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        user_id_colname="journey_id",
        time_till_conv_colname="time_till_end",
        conversion_value_colname="revenue",
    )

    # Sum of input revenues = 150 + 300 = 450
    expected_total_revenue = 450.0

    # 1. Last Click
    res_last = mam.run_last_click().to_polars()
    assert res_last["attribution"].sum() == expected_total_revenue
    # For user_1_0 (revenue 150): last channel is meta_ads
    # For user_3_0 (revenue 300): last channel is organic_search
    assert res_last.filter(pl.col("channels") == "meta_ads")["attribution"][0] == 150.0
    assert res_last.filter(pl.col("channels") == "organic_search")["attribution"][0] == 300.0

    # 2. First Click
    res_first = mam.run_first_click().to_polars()
    assert res_first["attribution"].sum() == expected_total_revenue
    # For user_1_0 (revenue 150): first channel is direct
    # For user_3_0 (revenue 300): first channel is email
    assert res_first.filter(pl.col("channels") == "direct")["attribution"][0] == 150.0
    assert res_first.filter(pl.col("channels") == "email")["attribution"][0] == 300.0

    # 3. Linear
    res_linear = mam.run_linear().to_polars()
    assert res_linear["attribution"].sum() == expected_total_revenue
    # user_1_0 has 3 channels: direct, google_search, meta_ads. Each gets 150/3 = 50.0
    # user_3_0 has 2 channels: email, organic_search. Each gets 300/2 = 150.0
    assert res_linear.filter(pl.col("channels") == "direct")["attribution"][0] == 50.0
    assert res_linear.filter(pl.col("channels") == "google_search")["attribution"][0] == 50.0
    assert res_linear.filter(pl.col("channels") == "meta_ads")["attribution"][0] == 50.0
    assert res_linear.filter(pl.col("channels") == "email")["attribution"][0] == 150.0
    assert res_linear.filter(pl.col("channels") == "organic_search")["attribution"][0] == 150.0

    # 4. Position Based (40/20/40)
    res_pb = mam.run_position_based().to_polars()
    assert res_pb["attribution"].sum() == expected_total_revenue

    # 5. Time Decay
    res_td = mam.run_time_decay().to_polars()
    assert abs(res_td["attribution"].sum() - expected_total_revenue) < 1e-5


def test_algorithmic_models_revenue_attribution(format_2_revenue_df):
    """Test that algorithmic models attribute values based on revenue."""
    mam = MAM(
        df=format_2_revenue_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        user_id_colname="journey_id",
        time_till_conv_colname="time_till_end",
        conversion_value_colname="revenue",
    )

    expected_total_revenue = 450.0

    # 1. Markov
    res_markov = mam.run_markov().to_polars()
    assert abs(res_markov["attribution"].sum() - expected_total_revenue) < 1e-5

    # 2. Shapley
    res_shapley = mam.run_shapley(value_column="conversion_value").to_polars()
    assert abs(res_shapley["attribution"].sum() - expected_total_revenue) < 1e-5


def test_reporting_revenue_metric(format_2_revenue_df, tmp_path):
    """Test that generate_report includes total_revenue in output JSON metadata."""
    mam = MAM(
        df=format_2_revenue_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        user_id_colname="journey_id",
        time_till_conv_colname="time_till_end",
        conversion_value_colname="revenue",
    )

    output_html = os.path.join(tmp_path, "dashboard.html")
    output_json = os.path.join(tmp_path, "raw_data.json")

    mam.generate_report(
        models=["last_click", "linear"],
        output_html_path=output_html,
        output_json_path=output_json,
    )

    # Verify files generated
    assert os.path.exists(output_html)
    assert os.path.exists(output_json)

    # Verify JSON structure and total_revenue value
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "metadata" in data
    assert "total_revenue" in data["metadata"]
    assert data["metadata"]["total_revenue"] == 450.0

    # Verify that model attribution values are based on revenue
    assert "attribution_results" in data
    assert "last_click" in data["attribution_results"]
    assert sum(data["attribution_results"]["last_click"]["attributions"]) == 450.0
