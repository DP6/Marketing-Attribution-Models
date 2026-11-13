"""
Injects one kind of bad input at random rows of clean data and checks that it is
reported with the right row count, and that clean data reports nothing.
"""

import datetime
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet

import numpy as np
import polars as pl
import pytest

from mam import check_data_quality

SEEDS = range(4)
CHANNELS = [f"ch_{i}" for i in range(8)]


def clean_sessions(rng, n_users=120):
    rows = []
    for user in range(n_users):
        start = datetime.datetime(2026, 1, 1) + datetime.timedelta(
            hours=int(rng.integers(0, 24 * 60))
        )
        touches = int(rng.integers(1, 6))
        converts = bool(rng.random() < 0.3)
        for i in range(touches):
            last = i == touches - 1
            rows.append(
                (
                    f"u{user}",
                    (start + datetime.timedelta(hours=3 * i)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    str(rng.choice(CHANNELS)),
                    converts and last,
                    round(float(rng.uniform(10, 500)), 2) if converts and last else 0.0,
                )
            )
    return pl.DataFrame(
        rows,
        schema=["user", "when", "channel", "converted", "revenue"],
        orient="row",
    )


def clean_journeys(rng):
    return sessions_to_journeys(clean_sessions(rng))


def sessions_to_journeys(sessions):
    """The same journeys in format 2: one row per user."""
    return (
        sessions.with_columns(pl.col("when").str.to_datetime())
        .sort("user", "when")
        .group_by("user", maintain_order=True)
        .agg(
            pl.col("channel"),
            ((pl.col("when").max() - pl.col("when")).dt.total_seconds() / 3600.0)
            .cast(pl.String)
            .alias("times"),
            pl.col("converted").any(),
            pl.col("revenue").sum(),
        )
        .select(
            pl.col("user").alias("id"),
            pl.col("channel").list.join(" > ").alias("path"),
            pl.col("times").list.join(" > "),
            "converted",
            "revenue",
        )
    )


def clean_grouped(rng):
    return journeys_to_grouped(clean_journeys(rng))


def journeys_to_grouped(journeys):
    """The same journeys in format 3: one row per path and conversion."""
    return (
        journeys.group_by("path", "converted", maintain_order=True)
        .agg(pl.len().cast(pl.Int64).alias("count"), pl.col("revenue").sum())
        .select("path", "count", "converted", "revenue")
    )


def check(df, fmt, **kwargs):
    if fmt == "session":
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
    if fmt == "journey":
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
    return check_data_quality(
        df,
        "grouped_journey",
        "path",
        "converted",
        occurrences_colname="count",
        conversion_value_colname="revenue",
        **kwargs,
    )


CLEAN = {"session": clean_sessions, "journey": clean_journeys, "grouped": clean_grouped}


def pick(rng, mask, k=None):
    """Chooses 1 to 5 distinct rows among those where mask is True."""
    candidates = np.flatnonzero(np.asarray(mask))
    k = int(rng.integers(1, 6)) if k is None else k
    return sorted(rng.choice(candidates, size=min(k, len(candidates)), replace=False))


def put(df, col, rows, value):
    mask = pl.Series(np.isin(np.arange(df.height), rows))
    value = value if isinstance(value, pl.Expr) else pl.lit(value)
    return df.with_columns(pl.when(mask).then(value).otherwise(pl.col(col)).alias(col))


def everywhere(df):
    return np.ones(df.height, bool)


def column(df, name):
    return df.get_column(name).to_numpy()


@dataclass
class Case:
    name: str
    fmt: str
    inject: Callable
    where: str = "errors"
    side: FrozenSet[str] = frozenset()
    kwargs: Dict = field(default_factory=dict)


def set_rows(col, value, rows_from=everywhere, check_name=None):
    def inject(df, rng):
        rows = pick(rng, rows_from(df))
        return put(df, col, rows, value), {check_name: len(rows)}

    return inject


def whole_column(col, expr, check_name):
    def inject(df, rng):
        return df.with_columns(expr.alias(col)), {check_name: df.height}

    return inject


def duplicate_rows(df, rng):
    rows = pick(rng, everywhere(df))
    return pl.concat([df, df[rows]]), {"duplicate_rows": 2 * len(rows)}


def converting(df):
    return column(df, "converted")


def converting_users(df):
    return df.select(pl.col("converted").any().over("user")).to_series().to_numpy()


def not_converting_users(df):
    return ~converting_users(df)


def touch_before_conversion(df):
    return converting_users(df) & ~converting(df)


def touch_after_conversion(df, rng):
    rows = pick(rng, converting(df))
    after = df[rows].with_columns(
        (pl.col("when").str.to_datetime() + pl.duration(hours=1))
        .dt.strftime("%Y-%m-%d %H:%M:%S")
        .alias("when"),
        pl.lit("ch_0").alias("channel"),
        pl.lit(False).alias("converted"),
        pl.lit(20.0).alias("revenue"),
    )
    return pl.concat([df, after]), len(rows)


def after_conversion_split(df, rng):
    bad, count = touch_after_conversion(df, rng)
    return bad, {"revenue_without_conversion": count}


def after_conversion_not_split(df, rng):
    bad, count = touch_after_conversion(df, rng)
    return bad, {"revenue_on_touch_in_converting_journey": count}


def channels_in_path(df):
    return df.get_column("path").str.split(" > ").list.len().to_numpy()


def single(df):
    return channels_in_path(df) == 1


def several(df):
    return channels_in_path(df) > 1


def times_with(transform):
    return pl.col("times").str.split(" > ").pipe(transform).list.join(" > ")


def duplicate_journey_ids(df, rng):
    rows = pick(rng, everywhere(df), k=2 * int(rng.integers(1, 4)))
    half = len(rows) // 2
    ids = df.get_column("id").to_list()
    for source, target in zip(rows[:half], rows[half:]):
        ids[target] = ids[source]
    return df.with_columns(pl.Series("id", ids)), {"duplicate_journey_id": 2 * half}


def missing_revenue(df, rng):
    return df.drop("revenue"), {"missing_columns": 0}


def no_rows(df, rng):
    return df.clear(), {"no_rows": 0}


def several_problems(df, rng):
    rows = rng.permutation(df.height)
    users, revenue, dates = rows[:3], rows[3:7], rows[7:12]
    bad = put(df, "user", users, None)
    bad = put(bad, "revenue", revenue, -5.0)
    bad = put(
        bad,
        "when",
        dates,
        pl.col("when").str.to_datetime().dt.strftime("%m/%d/%Y %H:%M:%S"),
    )
    return bad, {"null_user": 3, "negative_revenue": 4, "ambiguous_dates": 5}


CASES = [
    # Format 1, sessions
    Case(
        "null user",
        "session",
        set_rows("user", None, check_name="null_user"),
        side=frozenset({"duplicate_rows"}),
    ),
    Case(
        "null date",
        "session",
        set_rows("when", None, check_name="null_date"),
        side=frozenset({"duplicate_rows"}),
    ),
    Case(
        "slash dates",
        "session",
        set_rows(
            "when",
            pl.col("when").str.to_datetime().dt.strftime("%m/%d/%Y %H:%M:%S"),
            check_name="ambiguous_dates",
        ),
    ),
    Case(
        "dates with a time zone",
        "session",
        set_rows("when", pl.col("when") + pl.lit("Z"), check_name="ambiguous_dates"),
    ),
    Case(
        "dates that don't exist",
        "session",
        set_rows("when", "2026-02-30 10:00:00", check_name="invalid_dates"),
    ),
    Case(
        "dates as numbers",
        "session",
        whole_column(
            "when", pl.col("when").str.to_datetime().dt.epoch("s"), "invalid_date_type"
        ),
    ),
    Case(
        "null channel", "session", set_rows("channel", None, check_name="null_channel")
    ),
    Case(
        "blank channel",
        "session",
        set_rows("channel", "  ", check_name="empty_channel"),
    ),
    Case(
        "channels as numbers",
        "session",
        whole_column(
            "channel",
            pl.col("channel").str.slice(3).cast(pl.Int64),
            "invalid_channel_type",
        ),
    ),
    Case(
        "null flag",
        "session",
        set_rows("converted", None, check_name="null_conversion_flag"),
        side=frozenset({"revenue_without_conversion"}),
    ),
    Case(
        "flag 0/1 with a 2",
        "session",
        lambda df, rng: set_rows("converted", 2, check_name="invalid_conversion_flag")(
            df.with_columns(pl.col("converted").cast(pl.Int64)), rng
        ),
    ),
    Case(
        "flag as text",
        "session",
        whole_column(
            "converted",
            pl.when(pl.col("converted")).then(pl.lit("yes")).otherwise(pl.lit("no")),
            "invalid_conversion_flag",
        ),
    ),
    Case(
        "negative revenue",
        "session",
        set_rows("revenue", -5.0, check_name="negative_revenue"),
    ),
    Case(
        "NaN revenue",
        "session",
        set_rows("revenue", float("nan"), check_name="invalid_revenue"),
    ),
    Case(
        "infinite revenue",
        "session",
        set_rows("revenue", float("inf"), check_name="invalid_revenue"),
    ),
    Case(
        "null revenue on a conversion",
        "session",
        set_rows("revenue", None, converting, "null_revenue_on_conversion"),
    ),
    Case(
        "revenue on a user who never converts",
        "session",
        set_rows("revenue", 20.0, not_converting_users, "revenue_without_conversion"),
    ),
    Case(
        "revenue as text",
        "session",
        whole_column(
            "revenue", pl.col("revenue").cast(pl.String), "invalid_revenue_type"
        ),
    ),
    Case("exact duplicate rows", "session", duplicate_rows),
    Case(
        "revenue after the last conversion, split on conversion",
        "session",
        after_conversion_split,
        kwargs={"create_journey_id_based_on_conversion": True},
    ),
    Case("missing column", "session", missing_revenue),
    Case("no rows", "session", no_rows),
    Case("several problems at once", "session", several_problems),
    Case(
        "reserved channel name",
        "session",
        set_rows("channel", "(null)", check_name="reserved_channel_name"),
        where="warnings",
    ),
    Case(
        "revenue on a touch before the conversion",
        "session",
        set_rows(
            "revenue",
            20.0,
            touch_before_conversion,
            "revenue_on_touch_in_converting_journey",
        ),
        where="quality",
    ),
    Case(
        "revenue after the conversion, not split",
        "session",
        after_conversion_not_split,
        where="quality",
    ),
    Case(
        "zero revenue on a conversion",
        "session",
        set_rows("revenue", 0.0, converting, "zero_revenue_conversion"),
        where="quality",
    ),
    # Format 2, journeys
    Case("duplicate journey ids", "journey", duplicate_journey_ids),
    Case(
        "null journey id", "journey", set_rows("id", None, check_name="null_journey_id")
    ),
    Case("null path", "journey", set_rows("path", None, check_name="null_path")),
    Case(
        "blank path", "journey", set_rows("path", " ", single, "empty_channel_in_path")
    ),
    Case(
        "path ending in a separator",
        "journey",
        set_rows(
            "path", pl.col("path") + pl.lit(" > "), single, "empty_channel_in_path"
        ),
    ),
    Case(
        "a time missing",
        "journey",
        set_rows(
            "times",
            times_with(lambda t: t.list.slice(1)),
            several,
            "time_length_mismatch",
        ),
    ),
    Case(
        "times going up",
        "journey",
        set_rows(
            "times", times_with(lambda t: t.list.reverse()), several, "increasing_times"
        ),
    ),
    Case(
        "negative time",
        "journey",
        set_rows(
            "times",
            pl.col("times").str.replace(r"[^ >]+$", "-1.0"),
            check_name="negative_time",
        ),
    ),
    Case(
        "NaN time",
        "journey",
        set_rows(
            "times",
            pl.col("times").str.replace(r"[^ >]+$", "nan"),
            check_name="invalid_time_value",
        ),
    ),
    Case(
        "time as a word",
        "journey",
        set_rows(
            "times",
            pl.col("times").str.replace(r"[^ >]+$", "end"),
            check_name="invalid_time_value",
        ),
    ),
    Case(
        "times as numbers",
        "journey",
        whole_column("times", pl.lit(0.0), "invalid_time_type"),
    ),
    Case(
        "path as numbers",
        "journey",
        whole_column("path", pl.col("path").str.len_chars(), "invalid_path_type"),
    ),
    Case(
        "revenue on a journey with no conversion",
        "journey",
        set_rows(
            "revenue", 20.0, lambda df: ~converting(df), "revenue_without_conversion"
        ),
    ),
    Case(
        "null flag",
        "journey",
        set_rows("converted", None, check_name="null_conversion_flag"),
        side=frozenset({"revenue_without_conversion"}),
    ),
    Case(
        "reserved channel name",
        "journey",
        set_rows("path", "(inicio)", single, "reserved_channel_name"),
        where="warnings",
    ),
    # Format 3, grouped journeys
    Case(
        "fractional occurrences",
        "grouped",
        lambda df, rng: set_rows("count", 2.5, check_name="fractional_occurrences")(
            df.with_columns(pl.col("count").cast(pl.Float64)), rng
        ),
    ),
    Case(
        "zero occurrences",
        "grouped",
        set_rows("count", 0, check_name="non_positive_occurrences"),
    ),
    Case(
        "negative occurrences",
        "grouped",
        set_rows("count", -3, check_name="non_positive_occurrences"),
    ),
    Case(
        "null occurrences",
        "grouped",
        set_rows("count", None, check_name="null_occurrences"),
        side=frozenset({"duplicate_rows"}),
    ),
    Case(
        "occurrences as text",
        "grouped",
        whole_column(
            "count", pl.col("count").cast(pl.String), "invalid_occurrences_type"
        ),
    ),
    Case("exact duplicate rows", "grouped", duplicate_rows),
    Case(
        "revenue on a row with no conversion",
        "grouped",
        set_rows(
            "revenue", 20.0, lambda df: ~converting(df), "revenue_without_conversion"
        ),
    ),
    Case(
        "null path",
        "grouped",
        set_rows("path", None, check_name="null_path"),
        side=frozenset({"duplicate_rows"}),
    ),
    Case(
        "null flag",
        "grouped",
        set_rows("converted", None, check_name="null_conversion_flag"),
        side=frozenset({"duplicate_rows", "revenue_without_conversion"}),
    ),
]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.fmt}: {case.name}")
def test_injected_problem_is_reported_with_its_row_count(case, seed):
    rng = np.random.default_rng(seed)
    bad, expected = case.inject(CLEAN[case.fmt](rng), rng)

    report = check(bad, "session" if case.fmt == "session" else case.fmt, **case.kwargs)

    found = {problem.check: problem.rows for problem in getattr(report, case.where)}
    for name, rows in expected.items():
        assert found.get(name) == rows, str(report)
    if case.where == "errors":
        assert set(found) <= set(expected) | case.side, str(report)
    else:
        assert report.errors == [], str(report)
        assert report.ok


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("fmt", ["session", "journey", "grouped"])
def test_clean_random_data_reports_no_error_or_warning(fmt, seed):
    report = check(CLEAN[fmt](np.random.default_rng(seed)), fmt)

    assert report.errors == [], str(report)
    assert report.warnings == [], str(report)
