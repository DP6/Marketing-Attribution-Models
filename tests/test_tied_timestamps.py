"""Touches of a user at the same timestamp (usually dates without time).

MAM can't know their real order. When a conversion is tied with another touch and journeys
are split at conversions, that order decides which journey the touch (and its revenue)
belongs to, so MAM stops. Other ties keep the order of the input rows, in MAM and in
check_data_quality alike, so the same data always gives the same journeys.
"""

import polars as pl
import pytest

from mam import MAM, InputValidationError, check_data_quality

SESSION = dict(
    format_type="session",
    channels_colname="channel",
    journey_with_conv_colname="converted",
    datetime_colname="when",
    user_id_colname="user",
)


def sessions(rows):
    """rows: (user, when, channel, converted[, revenue])"""
    columns = ["user", "when", "channel", "converted", "revenue"][: len(rows[0])]
    return pl.DataFrame([dict(zip(columns, row)) for row in rows])


def problem(errors, check):
    return next((p for p in errors if p.check == check), None)


TOUCH_TIED_WITH_CONVERSION = [
    ("u1", "2026-01-01", "Email", False),
    ("u1", "2026-01-02", "Search", False),
    ("u1", "2026-01-02", "Direct", True),
    ("u2", "2026-01-03", "Email", True),
]


def test_a_conversion_tied_with_a_touch_stops_mam_when_journeys_split_at_conversions():
    df = sessions(TOUCH_TIED_WITH_CONVERSION)

    with pytest.raises(InputValidationError) as raised:
        MAM(df, create_journey_id_based_on_conversion=True, **SESSION)

    found = problem(raised.value.problems, "tied_conversion")
    assert found is not None and found.rows == 2
    assert "full timestamps" in found.message


def test_the_quality_report_has_the_same_error():
    report = check_data_quality(
        sessions(TOUCH_TIED_WITH_CONVERSION),
        create_journey_id_based_on_conversion=True,
        **SESSION,
    )

    assert not report.ok
    assert problem(report.errors, "tied_conversion").rows == 2


def test_without_splitting_at_conversions_the_tie_does_not_change_the_journey():
    model = MAM(sessions(TOUCH_TIED_WITH_CONVERSION), **SESSION)

    assert model.unified_df.height == 2


def test_ties_between_touches_that_do_not_convert_are_not_an_error():
    df = sessions(
        [
            ("u1", "2026-01-01", "Email", False),
            ("u1", "2026-01-01", "Search", False),
            ("u1", "2026-01-02", "Direct", True),
        ]
    )

    model = MAM(df, create_journey_id_based_on_conversion=True, **SESSION)

    assert model.unified_df.height == 1


def test_revenue_on_a_touch_tied_with_the_conversion_stops_mam():
    """Which journey gets that revenue depends on an order the data doesn't have."""
    df = sessions(
        [
            ("u1", "2026-01-01", "Email", False, 0.0),
            ("u1", "2026-01-02", "Search", False, 30.0),
            ("u1", "2026-01-02", "Direct", True, 100.0),
        ]
    )

    with pytest.raises(InputValidationError, match="full timestamps"):
        MAM(
            df,
            create_journey_id_based_on_conversion=True,
            conversion_value_colname="revenue",
            **SESSION,
        )


def tied_users(users):
    """Each user: three touches on the same day, in a known order, then a conversion.
    Rows go round by round (every user's 1st touch, then every 2nd...), so the input is
    not sorted by user and the sort has to move the tied rows."""
    order = ["C", "A", "B"]
    rows = []
    for step in range(3):
        rows += [
            (f"u{u:06d}", "2026-01-01", (order[u % 3 :] + order[: u % 3])[step], False)
            for u in range(users)
        ]
    rows += [(f"u{u:06d}", "2026-01-02", "D", True) for u in range(users)]
    return sessions(rows), {
        f"u{u:06d}": order[u % 3 :] + order[: u % 3] + ["D"] for u in range(users)
    }


def test_tied_touches_keep_the_order_of_the_input_rows():
    """Large enough for polars to sort in parallel, where an unstable sort reorders ties."""
    df, expected = tied_users(60000)

    model = MAM(df, **SESSION)

    got = dict(
        model.unified_df.select(
            "journey_id", pl.col("channels").cast(pl.List(pl.String))
        ).iter_rows()
    )
    assert got == expected


def test_the_report_counts_the_journeys_mam_builds_on_tied_data():
    df, _ = tied_users(2000)
    df = df.with_columns(pl.col("when").str.replace("2026-01-02", "2026-01-01"))
    df = df.filter(~pl.col("converted")).vstack(
        df.filter(pl.col("converted")).with_columns(pl.lit("2026-01-05").alias("when"))
    )

    report = check_data_quality(
        df, create_journey_id_based_on_conversion=True, **SESSION
    )
    model = MAM(df, create_journey_id_based_on_conversion=True, **SESSION)

    assert report.ok
    assert report.summary["journeys"] == model.unified_df.height


def test_the_tie_finding_says_the_row_order_is_used():
    df = sessions(
        [
            ("u1", "2026-01-01", "Email", False),
            ("u1", "2026-01-01", "Search", False),
            ("u1", "2026-01-02", "Direct", True),
        ]
    )

    finding = problem(check_data_quality(df, **SESSION).quality, "tied_timestamps")

    assert finding.rows == 2
    assert "order of the rows" in finding.message
