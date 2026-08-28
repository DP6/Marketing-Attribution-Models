import pytest
import polars as pl
from mam.core import MAM


@pytest.fixture
def format_1_data():
    return pl.DataFrame(
        {
            "datetime": [
                "2026-01-01 01:00:00",
                "2026-01-01 02:00:00",
                "2026-01-01 03:00:00",
            ],
            "user_id": ["u1", "u1", "u1"],
            "channel": ["A", "B", "C"],
            "conversion": [False, False, True],
        }
    ).with_columns(pl.col("datetime").str.to_datetime())


@pytest.fixture
def format_2_data():
    return pl.DataFrame(
        {
            "journey_id": ["j1", "j2"],
            "journey": ["A > B > C", "A > C"],
            "conversion": [True, True],
            "time_till_end": ["7200 > 3600 > 0", "3600 > 0"],
        }
    )


@pytest.fixture
def format_3_data():
    return pl.DataFrame(
        {
            "journey": ["A > B > C", "A > C", "B > B"],
            "conversion": [True, True, False],
            "occurrences": [2, 1, 5],
        }
    )


def test_last_click(format_2_data):
    mam_instance = MAM(
        df=format_2_data,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_last_click()
    agg_df = result.to_polars()

    # Total conversões = 2, C is last in both, so C gets 2
    res_dict = dict(zip(agg_df["channels"], agg_df["attribution"]))
    assert res_dict.get("C") == 2.0


def test_first_click(format_2_data):
    mam_instance = MAM(
        df=format_2_data,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_first_click()
    agg_df = result.to_polars()

    res_dict = dict(zip(agg_df["channels"], agg_df["attribution"]))
    assert res_dict.get("A") == 2.0


def test_linear(format_2_data):
    mam_instance = MAM(
        df=format_2_data,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_linear()
    agg_df = result.to_polars()

    res_dict = dict(zip(agg_df["channels"], agg_df["attribution"]))
    # j1: A, B, C (1/3 each). j2: A, C (1/2 each)
    # A = 1/3 + 1/2 = 5/6 (0.8333)
    # B = 1/3
    # C = 1/3 + 1/2 = 5/6 (0.8333)
    assert abs(res_dict.get("A") - (1 / 3 + 1 / 2)) < 1e-5
    assert abs(res_dict.get("B") - 1 / 3) < 1e-5
    assert abs(res_dict.get("C") - (1 / 3 + 1 / 2)) < 1e-5


def test_position_based(format_2_data):
    mam_instance = MAM(
        df=format_2_data,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_position_based()
    agg_df = result.to_polars()
    res_dict = dict(zip(agg_df["channels"], agg_df["attribution"]))

    # j1 (A, B, C): A=0.4, B=0.2, C=0.4
    # j2 (A, C): A=0.5, C=0.5
    # Total A = 0.9, B = 0.2, C = 0.9
    assert abs(res_dict.get("A") - 0.9) < 1e-5
    assert abs(res_dict.get("B") - 0.2) < 1e-5
    assert abs(res_dict.get("C") - 0.9) < 1e-5


def test_time_decay(format_1_data):
    mam_instance = MAM(
        df=format_1_data,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
    )
    result = mam_instance.run_time_decay(half_life_hours=1.0)
    agg_df = result.to_polars()
    res_dict = dict(zip(agg_df["channels"], agg_df["attribution"]))

    # Only 1 conversion.
    # points: A (2 hours ago), B (1 hour ago), C (0 hours ago)
    # raw weights: A: 0.5^(2/1) = 0.25, B: 0.5^(1/1) = 0.5, C: 0.5^0 = 1.0
    # sum = 1.75
    # normalized: A = 0.25/1.75, B = 0.5/1.75, C = 1.0/1.75
    assert abs(res_dict.get("C") - 1.0 / 1.75) < 1e-5
    assert abs(res_dict.get("B") - 0.5 / 1.75) < 1e-5
    assert abs(res_dict.get("A") - 0.25 / 1.75) < 1e-5


def test_time_decay_format_3_fails(format_3_data):
    mam_instance = MAM(
        df=format_3_data,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        occurrences_colname="occurrences",
    )
    with pytest.raises(ValueError, match="ausência absoluta de dados temporais"):
        mam_instance.run_time_decay()
