import polars as pl
import pytest
from mam.preprocessing import MAMPipeline


def test_small_format_1_df(small_format_1_df):
    assert isinstance(small_format_1_df, pl.DataFrame)
    assert small_format_1_df.shape == (7, 4)
    assert list(small_format_1_df.columns) == [
        "datetime",
        "user_id",
        "channel",
        "has_conversion",
    ]
    assert small_format_1_df["has_conversion"].dtype == pl.Boolean


def test_small_format_2_df(small_format_2_df):
    assert isinstance(small_format_2_df, pl.DataFrame)
    assert small_format_2_df.shape == (3, 6)
    assert list(small_format_2_df.columns) == [
        "start_time",
        "end_time",
        "journey_id",
        "journey",
        "has_conversion",
        "time_till_end",
    ]


def test_small_format_3_df(small_format_3_df):
    assert isinstance(small_format_3_df, pl.DataFrame)
    assert small_format_3_df.shape == (4, 3)
    assert list(small_format_3_df.columns) == [
        "journey",
        "has_conversion",
        "occurrences",
    ]


def test_bulk_generators(bulk_data_generator):
    # Test generation of Format 1
    df1 = bulk_data_generator["format_1"](100)
    assert isinstance(df1, pl.DataFrame)
    assert df1.shape[0] == 100
    assert list(df1.columns) == ["datetime", "user_id", "channel", "has_conversion"]

    # Test generation of Format 2
    df2 = bulk_data_generator["format_2"](20)
    assert isinstance(df2, pl.DataFrame)
    assert df2.shape[0] == 20
    assert list(df2.columns) == [
        "start_time",
        "end_time",
        "journey_id",
        "journey",
        "has_conversion",
        "time_till_end",
    ]

    # Test generation of Format 3
    df3 = bulk_data_generator["format_3"](10)
    assert isinstance(df3, pl.DataFrame)
    assert df3.shape[0] == 10
    assert list(df3.columns) == ["journey", "has_conversion", "occurrences"]


# --- Phase 2: Preprocessing Pipeline Tests ---


def test_pipeline_format_1_preprocessing(small_format_1_df):
    """Test preprocessing on Format 1 (Sessions / Touchpoints)."""
    unified_df = MAMPipeline.preprocess(
        df=small_format_1_df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
    )

    # Schema check
    assert isinstance(unified_df, pl.DataFrame)
    expected_cols = {
        "journey_id",
        "channels",
        "time_till_conv",
        "has_conversion",
        "weight",
    }
    assert set(unified_df.columns) == expected_cols

    # Type checks
    assert unified_df["journey_id"].dtype == pl.String
    assert isinstance(unified_df["channels"].dtype, pl.List)
    assert unified_df["channels"].dtype.inner == pl.Categorical
    assert isinstance(unified_df["time_till_conv"].dtype, pl.List)
    assert unified_df["time_till_conv"].dtype.inner == pl.Float64
    assert unified_df["has_conversion"].dtype == pl.Boolean
    assert unified_df["weight"].dtype == pl.Int64

    # Data consistency checks
    # There are 3 unique user_ids: user_1, user_2, user_3
    assert unified_df.shape[0] == 3

    # Check user_1 (which has a conversion)
    user_1_row = unified_df.filter(pl.col("journey_id") == "user_1")
    assert user_1_row.shape[0] == 1
    assert user_1_row["has_conversion"][0] is True
    assert user_1_row["weight"][0] == 1

    # Check chronological order of channels for user_1
    assert list(user_1_row["channels"][0]) == ["direct", "google_search", "meta_ads"]
    # Check time_till_conv calculations (max time is 03:00, offsets are 2h and 1h)
    assert list(user_1_row["time_till_conv"][0]) == [2.0, 1.0, 0.0]


def test_pipeline_format_1_segmentation(small_format_1_df):
    """Test session grouping with segmentation based on conversions (create_journey_id_based_on_conversion=True)."""
    # Create a user with multiple conversions in their timeline
    custom_df = pl.DataFrame(
        [
            {
                "datetime": "2026-01-01 01:00:00",
                "user_id": "user_split",
                "channel": "direct",
                "has_conversion": False,
            },
            {
                "datetime": "2026-01-01 02:00:00",
                "user_id": "user_split",
                "channel": "google_search",
                "has_conversion": True,
            },
            {
                "datetime": "2026-01-01 03:00:00",
                "user_id": "user_split",
                "channel": "meta_ads",
                "has_conversion": False,
            },
            {
                "datetime": "2026-01-01 04:00:00",
                "user_id": "user_split",
                "channel": "email",
                "has_conversion": True,
            },
        ]
    ).with_columns(pl.col("datetime").str.to_datetime())

    unified_df = MAMPipeline.preprocess(
        df=custom_df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
        create_journey_id_based_on_conversion=True,
    )

    # It should result in two separate journey records: user_split_J0 and user_split_J1
    assert unified_df.shape[0] == 2
    assert set(unified_df["journey_id"]) == {"user_split_J0", "user_split_J1"}

    # J0 should have ['direct', 'google_search']
    j0_row = unified_df.filter(pl.col("journey_id") == "user_split_J0")
    assert list(j0_row["channels"][0]) == ["direct", "google_search"]
    assert j0_row["has_conversion"][0] is True

    # J1 should have ['meta_ads', 'email']
    j1_row = unified_df.filter(pl.col("journey_id") == "user_split_J1")
    assert list(j1_row["channels"][0]) == ["meta_ads", "email"]
    assert j1_row["has_conversion"][0] is True


def test_pipeline_format_2_preprocessing(small_format_2_df):
    """Test preprocessing on Format 2 (Journeys)."""
    unified_df = MAMPipeline.preprocess(
        df=small_format_2_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        user_id_colname="journey_id",
        time_till_conv_colname="time_till_end",
    )

    # Schema check
    assert isinstance(unified_df, pl.DataFrame)
    expected_cols = {
        "journey_id",
        "channels",
        "time_till_conv",
        "has_conversion",
        "weight",
    }
    assert set(unified_df.columns) == expected_cols

    # Type checks
    assert unified_df["journey_id"].dtype == pl.String
    assert isinstance(unified_df["channels"].dtype, pl.List)
    assert unified_df["channels"].dtype.inner == pl.Categorical
    assert isinstance(unified_df["time_till_conv"].dtype, pl.List)
    assert unified_df["time_till_conv"].dtype.inner == pl.Float64
    assert unified_df["has_conversion"].dtype == pl.Boolean
    assert unified_df["weight"].dtype == pl.Int64

    # Rows count
    assert unified_df.shape[0] == 3

    # Row contents check
    user_1_row = unified_df.filter(pl.col("journey_id") == "user_1_0")
    assert list(user_1_row["channels"][0]) == ["direct", "google_search", "meta_ads"]
    assert list(user_1_row["time_till_conv"][0]) == [2.0, 1.0, 0.0]
    assert user_1_row["has_conversion"][0] is True
    assert user_1_row["weight"][0] == 1


def test_pipeline_format_3_preprocessing(small_format_3_df):
    """Test preprocessing on Format 3 (Grouped Journeys / Frequencies)."""
    unified_df = MAMPipeline.preprocess(
        df=small_format_3_df,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        occurrences_colname="occurrences",
    )

    # Schema check
    assert isinstance(unified_df, pl.DataFrame)
    expected_cols = {
        "journey_id",
        "channels",
        "time_till_conv",
        "has_conversion",
        "weight",
    }
    assert set(unified_df.columns) == expected_cols

    # Type checks
    assert unified_df["journey_id"].dtype == pl.String
    assert isinstance(unified_df["channels"].dtype, pl.List)
    assert unified_df["channels"].dtype.inner == pl.Categorical
    assert isinstance(unified_df["time_till_conv"].dtype, pl.List)
    assert unified_df["time_till_conv"].dtype.inner == pl.Float64
    assert unified_df["has_conversion"].dtype == pl.Boolean
    assert unified_df["weight"].dtype == pl.Int64

    # Rows count
    assert unified_df.shape[0] == 4

    # Check that journey_ids are sequential path_X
    assert sorted(list(unified_df["journey_id"])) == [
        "path_0",
        "path_1",
        "path_2",
        "path_3",
    ]

    # Check weights match occurrences
    first_path = unified_df.filter(pl.col("journey_id") == "path_0")
    assert list(first_path["channels"][0]) == ["direct", "google_search", "meta_ads"]
    assert first_path["weight"][0] == 120
    assert first_path["has_conversion"][0] is True

    # Check that time_till_conv are all null (None) of matching length
    assert list(first_path["time_till_conv"][0]) == [None, None, None]


def test_pandas_compatibility(small_format_1_df):
    """Verify that Pandas DataFrame inputs are accepted, converted and successfully processed."""
    pandas_df = small_format_1_df.to_pandas()

    unified_df = MAMPipeline.preprocess(
        df=pandas_df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
    )

    assert isinstance(unified_df, pl.DataFrame)
    assert unified_df.shape[0] == 3


def test_invalid_arguments_handling(small_format_1_df):
    """Verify that MAMPipeline raises proper errors for invalid inputs/configurations."""
    # Invalid DataFrame type
    with pytest.raises(
        TypeError, match="df must be either a Polars or Pandas DataFrame"
    ):
        MAMPipeline.preprocess(
            df="not_a_df",
            format_type="session",
            channels_colname="channel",
            journey_with_conv_colname="has_conversion",
        )

    # Invalid format type
    with pytest.raises(ValueError, match="Unknown format_type"):
        MAMPipeline.preprocess(
            df=small_format_1_df,
            format_type="invalid_format",
            channels_colname="channel",
            journey_with_conv_colname="has_conversion",
        )

    # Missing datetime or user_id for sessions
    with pytest.raises(
        ValueError, match="datetime_colname and user_id_colname are required"
    ):
        MAMPipeline.preprocess(
            df=small_format_1_df,
            format_type="session",
            channels_colname="channel",
            journey_with_conv_colname="has_conversion",
        )
