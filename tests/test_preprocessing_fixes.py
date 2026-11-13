"""
Inputs that are valid but used to break the preprocessing or change its result
(C17, C19, C24, C25, I7). Each one runs on the shared random data and must give the
same results as the plain input.
"""

import datetime
import decimal

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from mam import MAM, JAToolbox, check_data_quality
from tests.test_validation_in_mam import ARGS, MODELS, build
from tests.test_validation_random import CLEAN, check

SEEDS = range(3)


def results(result):
    frame = result.to_polars()
    return frame.with_columns(pl.col("channels").cast(pl.String)).sort("channels")


def same_results(df, expected_df, fmt, models=MODELS, **kwargs):
    for name, run in models.items():
        assert_frame_equal(
            results(run(build(df, fmt, **kwargs))),
            results(run(build(expected_df, fmt))),
            check_exact=False,
        ), name


# C17: format 1 kept whole seconds only


@pytest.mark.parametrize("seed", SEEDS)
def test_session_times_keep_fractions_of_a_second(seed):
    rng = np.random.default_rng(seed)
    clean = CLEAN["session"](rng)
    millis = pl.Series(rng.integers(0, 1000, clean.height)).cast(pl.String).str.zfill(3)
    df = clean.with_columns(pl.col("when") + pl.lit(".") + millis)

    unified = build(df, "session").unified_df
    stamps = df.with_columns(
        pl.col("when").str.to_datetime("%Y-%m-%d %H:%M:%S%.f", time_unit="us")
    )
    expected = (
        stamps.sort("user", "when")
        .group_by("user")
        .agg(((pl.col("when").max() - pl.col("when")).dt.total_microseconds() / 3.6e9))
        .sort("user")
    )
    got = unified.sort("journey_id")["time_till_conv"].to_list()
    for got_times, want_times in zip(got, expected["when"].to_list()):
        assert got_times == pytest.approx(want_times, abs=1e-9)


def test_session_and_journey_formats_agree_on_time_decay_with_milliseconds():
    session = pl.DataFrame(
        {
            "user": ["u1", "u1", "u1"],
            "when": [
                "2026-01-01 10:00:00.250",
                "2026-01-01 10:00:01.750",
                "2026-01-01 10:00:03.000",
            ],
            "channel": ["A", "B", "C"],
            "converted": [False, False, True],
            "revenue": [0.0, 0.0, 100.0],
        }
    )
    journey = pl.DataFrame(
        {
            "id": ["u1"],
            "path": ["A > B > C"],
            "times": [f"{2.75 / 3600} > {1.25 / 3600} > 0.0"],
            "converted": [True],
            "revenue": [100.0],
        }
    )
    decay = lambda m: m.run_time_decay(half_life_hours=1 / 3600)  # noqa: E731
    assert_frame_equal(
        results(decay(build(session, "session"))),
        results(decay(build(journey, "journey"))),
        check_exact=False,
    )


# C19: a user column named journey_idx clashed with MAM's own index


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["session", "journey", "grouped"])
def test_a_column_named_journey_idx_changes_nothing(fmt, seed):
    clean = CLEAN[fmt](np.random.default_rng(seed))
    df = clean.with_columns(pl.lit(7).alias("journey_idx"))

    assert check(df, fmt).errors == []
    same_results(df, clean, fmt)


def test_session_split_on_conversion_ignores_a_column_named_journey_idx():
    clean = CLEAN["session"](np.random.default_rng(0))
    df = clean.with_columns(pl.lit("x").alias("journey_idx"))
    split = {"create_journey_id_based_on_conversion": True}

    assert_frame_equal(
        build(df, "session", **split).unified_df.sort("journey_id"),
        build(clean, "session", **split).unified_df.sort("journey_id"),
    )


# C24: Decimal revenue (BigQuery NUMERIC) crashed format 1 on polars 1.0


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["session", "journey", "grouped"])
def test_decimal_revenue_gives_the_same_results(fmt, seed):
    clean = CLEAN[fmt](np.random.default_rng(seed))
    exact = [decimal.Decimal(f"{value:.2f}") for value in clean["revenue"]]
    df = clean.with_columns(pl.Series("revenue", exact, dtype=pl.Decimal(18, 2)))

    assert check(df, fmt).errors == []
    same_results(df, clean, fmt)


def test_decimal_revenue_with_nulls_on_touches():
    df = pl.DataFrame(
        {
            "user": ["u1", "u1", "u2"],
            "when": [
                "2026-01-01 10:00:00",
                "2026-01-02 10:00:00",
                "2026-01-01 09:00:00",
            ],
            "channel": ["Email", "Search", "Email"],
            "converted": [False, True, True],
            "revenue": [None, decimal.Decimal("10.50"), decimal.Decimal("4.25")],
        },
        schema_overrides={"revenue": pl.Decimal(18, 2)},
    )

    unified = build(df, "session").unified_df.sort("journey_id")
    assert unified["conversion_value"].to_list() == [10.5, 4.25]


# C25: a Categorical path (pandas 'category') was refused in formats 2 and 3


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["journey", "grouped"])
def test_categorical_path_gives_the_same_results(fmt, seed):
    clean = CLEAN[fmt](np.random.default_rng(seed))
    df = clean.with_columns(pl.col("path").cast(pl.Categorical))

    report = check(df, fmt)
    assert report.errors == [], str(report)
    assert report.summary == check(clean, fmt).summary
    same_results(df, clean, fmt)


def test_pandas_category_path_works():
    clean = CLEAN["journey"](np.random.default_rng(0))
    df = clean.to_pandas().astype({"path": "category"})

    same_results(df, clean, "journey")


# I7: format 2 demanded a time column even for models that don't use it


@pytest.mark.parametrize("seed", SEEDS)
def test_journey_without_times_runs_every_model_but_time_decay(seed):
    clean = CLEAN["journey"](np.random.default_rng(seed))
    df = clean.drop("times")
    no_time_args = {"time_till_conv_colname": None}

    args = {**ARGS["journey"], **no_time_args}
    report = check_data_quality(df, **args)
    assert report.errors == [], str(report)
    same_results(df, clean, "journey", **no_time_args)
    with pytest.raises(ValueError, match="Time Decay"):
        build(df, "journey", **no_time_args).run_time_decay()


def test_journey_without_times_behaves_like_grouped_journeys():
    df = pl.DataFrame(
        {"id": ["j1", "j2"], "path": ["A > B", "C"], "converted": [True, False]}
    )

    model = MAM(df, "journey", "path", "converted", user_id_colname="id")

    assert model.unified_df.sort("journey_id")["time_till_conv"].to_list() == [
        [None, None],
        [None],
    ]
    JAToolbox(df, "journey", "path", "converted", user_id_colname="id")


def test_a_time_column_that_was_named_but_is_missing_is_still_an_error():
    df = CLEAN["journey"](np.random.default_rng(0)).drop("times")

    report = check(df, "journey")  # ARGS name the column 'times'
    assert [p.check for p in report.errors] == ["missing_columns"]


def test_old_default_time_column_name_is_still_used():
    clean = CLEAN["journey"](np.random.default_rng(0))
    df = clean.rename({"times": "time_till_end"})

    unified = build(df, "journey", time_till_conv_colname=None).unified_df
    assert (
        unified["time_till_conv"].list.eval(pl.element().is_null()).list.any().sum()
        == 0
    )
