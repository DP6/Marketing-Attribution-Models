import datetime

import pandas as pd
import polars as pl
import pytest

from mam import MAM, check_data_quality


def session_df(**overrides):
    data = {
        "user": ["u1", "u1", "u2", "u3", "u3"],
        "when": [
            "2026-01-01 10:00:00",
            "2026-01-02 10:00:00",
            "2026-01-03 10:00:00",
            "2026-01-04 10:00:00",
            "2026-01-05 10:00:00",
        ],
        "channel": ["Email", "Search", "Search", "Direct", "Email"],
        "converted": [False, True, False, False, True],
        "revenue": [0.0, 100.0, 0.0, 0.0, 50.0],
    }
    data.update(overrides)
    return pl.DataFrame(data)


def check_session(df, **kwargs):
    return check_data_quality(
        df,
        "session",
        "channel",
        "converted",
        datetime_colname="when",
        user_id_colname="user",
        conversion_value_colname="revenue",
        **kwargs,
    )


def journey_df(**overrides):
    data = {
        "id": ["j1", "j2", "j3"],
        "path": ["Email > Search", "Search", "Direct > Email"],
        "times": ["24.0 > 0.0", "0.0", "24.0 > 0.0"],
        "converted": [True, False, True],
        "revenue": [100.0, 0.0, 50.0],
    }
    data.update(overrides)
    return pl.DataFrame(data)


def check_journey(df, **kwargs):
    return check_data_quality(
        df,
        "journey",
        "path",
        "converted",
        user_id_colname="id",
        time_till_conv_colname="times",
        conversion_value_colname="revenue",
        **kwargs,
    )


def grouped_df(**overrides):
    data = {
        "path": ["Email > Search", "Search", "Direct > Email"],
        "count": [3, 5, 2],
        "converted": [True, False, True],
        "revenue": [300.0, 0.0, 100.0],
    }
    data.update(overrides)
    return pl.DataFrame(data)


def check_grouped(df, **kwargs):
    return check_data_quality(
        df,
        "grouped_journey",
        "path",
        "converted",
        occurrences_colname="count",
        conversion_value_colname="revenue",
        **kwargs,
    )


def checks(problems):
    return {problem.check for problem in problems}


# Summary


def test_session_summary_counts_the_dataset():
    summary = check_session(session_df()).summary

    assert summary["rows"] == 5
    assert summary["unique_users"] == 3
    assert summary["journeys"] == 3
    assert summary["channels"] == 3
    assert summary["conversions"] == 2
    assert summary["revenue"] == 150.0
    assert summary["first_date"] == datetime.datetime(2026, 1, 1, 10)
    assert summary["last_date"] == datetime.datetime(2026, 1, 5, 10)


def test_session_summary_counts_journeys_split_on_conversion():
    df = session_df(converted=[True, True, False, False, True])

    report = check_session(df, create_journey_id_based_on_conversion=True)

    assert report.summary["unique_users"] == 3
    assert report.summary["journeys"] == 4


def test_journey_summary_counts_the_dataset():
    summary = check_journey(journey_df()).summary

    assert summary["rows"] == 3
    assert summary["journeys"] == 3
    assert summary["channels"] == 3
    assert summary["conversions"] == 2
    assert summary["revenue"] == 150.0


def test_grouped_summary_weights_by_occurrences():
    summary = check_grouped(grouped_df()).summary

    assert summary["rows"] == 3
    assert summary["journeys"] == 10
    assert summary["channels"] == 3
    assert summary["conversions"] == 5
    assert summary["revenue"] == 400.0


def test_summary_counts_conversions_without_a_revenue_column():
    report = check_data_quality(
        session_df(),
        "session",
        "channel",
        "converted",
        datetime_colname="when",
        user_id_colname="user",
    )

    assert report.summary["conversions"] == 2
    assert "revenue" not in report.summary


def test_report_lists_the_expected_type_of_each_column():
    expected = check_session(session_df()).expected_types

    assert set(expected) == {"channel", "converted", "when", "user", "revenue"}
    assert "ISO" in expected["when"]


# Clean data


@pytest.mark.parametrize(
    "report",
    [
        check_session(session_df()),
        check_journey(journey_df()),
        check_grouped(grouped_df()),
    ],
    ids=["session", "journey", "grouped_journey"],
)
def test_clean_data_has_no_findings(report):
    assert report.errors == []
    assert report.warnings == []
    assert report.quality == []
    assert report.ok


# What only the quality function reports


def test_similar_channel_names_are_reported_together():
    df = session_df(channel=["Email", "email ", "Search", "Paid-Search", "paid_search"])

    finding = next(
        p for p in check_session(df).quality if p.check == "similar_channel_names"
    )

    assert "'Email', 'email'" in finding.message
    assert "'Paid-Search', 'paid_search'" in finding.message
    assert "Search'," not in finding.message.replace("Paid-Search',", "")


def test_zero_revenue_on_a_conversion_is_reported():
    report = check_session(session_df(revenue=[0.0, 0.0, 0.0, 0.0, 50.0]))

    finding = next(p for p in report.quality if p.check == "zero_revenue_conversion")
    assert finding.rows == 1
    assert report.errors == []


def test_revenue_before_a_conversion_is_quality_not_error():
    report = check_session(session_df(revenue=[10.0, 100.0, 0.0, 0.0, 50.0]))

    finding = next(
        p for p in report.quality if p.check == "revenue_on_touch_in_converting_journey"
    )
    assert finding.rows == 1
    assert report.errors == []


def test_future_dates_are_reported():
    future = str(datetime.datetime.now().year + 30) + "-01-01 10:00:00"
    df = session_df(
        when=[
            "2026-01-01 10:00:00",
            "2026-01-02 10:00:00",
            "2026-01-03 10:00:00",
            "2026-01-04 10:00:00",
            future,
        ]
    )

    finding = next(p for p in check_session(df).quality if p.check == "future_dates")

    assert finding.rows == 1


def test_dates_far_from_the_rest_are_reported():
    days = [
        datetime.datetime(2026, 1, 1) + datetime.timedelta(days=i) for i in range(30)
    ]
    days[0] = datetime.datetime(1996, 1, 1)
    df = pl.DataFrame(
        {
            "user": [f"u{i}" for i in range(30)],
            "when": days,
            "channel": ["Email"] * 30,
            "converted": [False] * 30,
            "revenue": [0.0] * 30,
        }
    )

    finding = next(p for p in check_session(df).quality if p.check == "far_dates")

    assert finding.rows == 1
    assert "1996" in finding.message


def test_tied_timestamps_are_counted():
    df = session_df(
        when=["2026-01-01", "2026-01-01", "2026-01-03", "2026-01-04", "2026-01-05"]
    )

    finding = next(p for p in check_session(df).quality if p.check == "tied_timestamps")

    assert finding.rows == 2
    assert "full timestamps" in finding.message


def test_same_timestamp_on_different_users_is_not_a_tie():
    df = session_df(
        when=["2026-01-01", "2026-01-02", "2026-01-01", "2026-01-04", "2026-01-05"]
    )

    assert "tied_timestamps" not in checks(check_session(df).quality)


def test_outliers_are_counted_per_variable():
    n = 40
    df = pl.DataFrame(
        {
            # 1 to 4 touches, so the IQR is not 0, and one journey with 60
            "path": [" > ".join(["Email"] * (1 + i % 4)) for i in range(n - 1)]
            + [" > ".join(["Email"] * 60)],
            "count": [1] * n,
            "converted": [True] * n,
            "revenue": [100.0 + i for i in range(n - 1)] + [100000.0],
        }
    )

    finding = next(p for p in check_grouped(df).quality if p.check == "outliers")

    assert "conversion_value: 1" in finding.message
    assert "n_steps: 1" in finding.message


def test_outliers_are_not_reported_on_small_or_regular_data():
    assert "outliers" not in checks(check_session(session_df()).quality)


# It reports everything and leaves the data alone


def test_every_problem_is_reported_at_once():
    df = pl.DataFrame(
        {
            "user": ["u1", None, "u3", "u3", "u3"],
            "when": ["01/05/2026 10:00:00"] * 5,
            "channel": ["Email", "email", None, "(null)", "(null)"],
            "converted": [True, False, False, True, True],
            "revenue": [-1.0, 10.0, 0.0, 0.0, 0.0],
        }
    )

    report = check_session(df)

    assert {
        "null_user",
        "ambiguous_dates",
        "null_channel",
        "negative_revenue",
        "revenue_without_conversion",
        "duplicate_rows",
    } <= checks(report.errors)
    assert "reserved_channel_name" in checks(report.warnings)
    assert "similar_channel_names" in checks(report.quality)
    assert not report.ok


def test_summary_survives_columns_of_the_wrong_type():
    df = session_df(
        converted=["no", "yes", "no", "no", "yes"], revenue=["0", "100", "0", "0", "50"]
    )

    report = check_session(df)

    assert report.summary["rows"] == 5
    assert report.summary["unique_users"] == 3
    assert report.summary["conversions"] is None
    assert report.summary["revenue"] is None
    assert {"invalid_conversion_flag", "invalid_revenue_type"} <= checks(report.errors)


def test_missing_column_is_reported_and_the_rest_still_checked():
    df = session_df(channel=["Email", None, "Search", "Search", "Search"]).drop(
        "revenue"
    )

    report = check_session(df)

    assert "missing_columns" in checks(report.errors)
    assert "null_channel" in checks(report.errors)
    assert report.summary["unique_users"] == 3


def test_empty_dataframe_is_reported():
    report = check_session(session_df().clear())

    assert "no_rows" in checks(report.errors)
    assert report.summary["rows"] == 0


def test_input_data_is_not_changed():
    df = session_df(channel=[" Email", "Search", "Search", "Direct", "Email"])
    before = df.clone()

    check_session(df)

    assert df.equals(before)


def test_pandas_input_is_accepted():
    report = check_session(session_df().to_pandas())

    assert isinstance(session_df().to_pandas(), pd.DataFrame)
    assert report.summary["rows"] == 5
    assert report.ok


def test_unknown_format_raises():
    with pytest.raises(ValueError, match="Unknown format_type"):
        check_data_quality(session_df(), "banana", "channel", "converted")


def test_report_prints_summary_and_findings():
    text = str(check_session(session_df(revenue=[0.0, 0.0, 0.0, 0.0, 50.0])))

    assert "rows: 5" in text
    assert "unique_users: 3" in text
    assert "zero_revenue_conversion" in text


def test_a_clean_report_means_mam_runs():
    report = check_session(session_df())

    model = MAM(
        session_df(),
        "session",
        "channel",
        "converted",
        datetime_colname="when",
        user_id_colname="user",
        conversion_value_colname="revenue",
    )

    assert report.ok
    assert model.unified_df.height == report.summary["journeys"]


def test_session_without_date_or_user_column_is_an_error_as_in_mam():
    df = pl.DataFrame({"channel": ["Email", "Search"], "converted": [False, True]})

    report = check_data_quality(df, "session", "channel", "converted")

    assert not report.ok
    assert [p.check for p in report.errors] == ["missing_arguments"]
    assert "datetime_colname and user_id_colname" in report.errors[0].message


def test_expected_types_list_only_the_columns_in_use():
    df = pl.DataFrame(
        {
            "journey_id": ["j1", "j2"],
            "path": ["Email > Search", "Search"],
            "converted": [True, False],
        }
    )

    report = check_data_quality(df, "journey", "path", "converted")

    assert None not in report.expected_types
    assert set(report.expected_types) == {"converted", "path", "journey_id"}
    assert "None:" not in str(report)
