"""
Outliers in check_data_quality (#109): journeys far from the rest on steps, duration
or revenue are found, listed and can be removed whole.

The data is the shared random base with outlier journeys planted at random users.
"""

import datetime

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from mam import check_data_quality
from tests.test_validation_in_mam import MODELS, build
from tests.test_validation_random import (
    CHANNELS,
    check,
    clean_sessions,
    journeys_to_grouped,
    sessions_to_journeys,
)

SEEDS = range(4)
FORMATS = ["session", "journey", "grouped"]
VARIABLES = ["n_steps", "duration", "conversion_value"]


def planted(seed, k=None):
    """
    Sessions with k journeys planted far out on each variable, on different users:
    40 extra touches, a first touch 3000 hours earlier, revenue 1000 times higher.
    """
    rng = np.random.default_rng(seed)
    sessions = clean_sessions(rng)
    k = int(rng.integers(1, 6)) if k is None else k
    users = sessions.get_column("user").unique(maintain_order=True).to_list()
    converting = (
        sessions.filter("converted").get_column("user").unique(maintain_order=True)
    )
    on_revenue = [str(u) for u in rng.choice(converting.to_list(), k, replace=False)]
    others = [u for u in users if u not in on_revenue]
    chosen = [str(u) for u in rng.choice(others, 2 * k, replace=False)]
    on_steps, on_duration = chosen[:k], chosen[k:]

    first = (
        sessions.with_columns(pl.col("when").str.to_datetime())
        .group_by("user")
        .agg(pl.col("when").min())
    )
    first_touch = dict(first.iter_rows())
    extra = []
    for user in on_steps:
        for i in range(40):
            when = first_touch[user] - datetime.timedelta(seconds=i + 1)
            extra.append((user, when, str(rng.choice(CHANNELS)), False, 0.0))
    for user in on_duration:
        when = first_touch[user] - datetime.timedelta(hours=3000)
        extra.append((user, when, str(rng.choice(CHANNELS)), False, 0.0))
    extra = pl.DataFrame(
        extra, schema=["user", "when", "channel", "converted", "revenue"], orient="row"
    ).with_columns(pl.col("when").dt.strftime("%Y-%m-%d %H:%M:%S"))

    sessions = pl.concat([sessions, extra]).with_columns(
        pl.when(pl.col("converted") & pl.col("user").is_in(on_revenue))
        .then(pl.col("revenue") * 1000)
        .otherwise(pl.col("revenue"))
        .alias("revenue")
    )
    return sessions, {
        "n_steps": set(on_steps),
        "duration": set(on_duration),
        "conversion_value": set(on_revenue),
    }


def in_format(sessions, fmt):
    if fmt == "session":
        return sessions
    journeys = sessions_to_journeys(sessions)
    return journeys if fmt == "journey" else journeys_to_grouped(journeys)


def cuts(report):
    return {cut.variable: cut for cut in report.outliers}


def flagged(report, variable):
    table = report.outlier_journeys
    return set(
        table.filter(pl.col("outlier_on").str.contains(variable))
        .get_column("journey_id")
        .to_list()
    )


# The planted journeys are found


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["session", "journey"])
def test_planted_outliers_are_found(fmt, seed):
    sessions, expected = planted(seed)
    report = check(in_format(sessions, fmt), fmt)

    for variable in VARIABLES:
        assert flagged(report, variable) == expected[variable], variable
        assert cuts(report)[variable].journeys == len(expected[variable])


@pytest.mark.parametrize("seed", SEEDS)
def test_planted_long_journeys_are_found_in_grouped_paths(seed):
    sessions, expected = planted(seed)
    report = check(in_format(sessions, "grouped"), "grouped")

    assert cuts(report)["n_steps"].journeys == len(expected["n_steps"])
    assert "duration" not in cuts(report)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["session", "journey"])
def test_zscore_finds_a_single_planted_journey(fmt, seed):
    sessions, expected = planted(seed, k=1)
    report = check(in_format(sessions, fmt), fmt, outlier_method="zscore")

    for variable in VARIABLES:
        assert flagged(report, variable) == expected[variable], variable
        assert cuts(report)[variable].method == "zscore"


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_clean_data_has_cut_offs_but_no_outliers(fmt, seed):
    df = in_format(clean_sessions(np.random.default_rng(seed)), fmt)
    report = check(df, fmt)

    assert report.outliers
    assert all(cut.journeys == 0 for cut in report.outliers)
    assert report.outlier_journeys.is_empty()
    assert "outliers" not in [p.check for p in report.quality]


# The same journeys give the same answer in every format


@pytest.mark.parametrize("seed", SEEDS)
def test_formats_agree_on_cut_offs_and_counts(seed):
    sessions, _ = planted(seed)
    reports = {fmt: cuts(check(in_format(sessions, fmt), fmt)) for fmt in FORMATS}

    shared = {
        "n_steps": FORMATS,
        "duration": ["session", "journey"],
        "conversion_value": ["session", "journey"],
    }
    for variable, formats in shared.items():
        first = reports[formats[0]][variable]
        for fmt in formats[1:]:
            other = reports[fmt][variable]
            assert (other.lower, other.journeys) == pytest.approx(
                (first.lower, first.journeys)
            ), (variable, fmt)
            assert other.upper == pytest.approx(first.upper), (variable, fmt)
            assert other.share_journeys == pytest.approx(first.share_journeys)
            assert other.share_conversions == pytest.approx(first.share_conversions)
            assert other.share_revenue == pytest.approx(first.share_revenue)


@pytest.mark.parametrize("seed", SEEDS)
def test_occurrences_count_as_journeys(seed):
    sessions, _ = planted(seed)
    grouped = in_format(sessions, "grouped")
    one_per_row = (
        grouped.with_columns(
            (pl.col("revenue") / pl.col("count")).alias("revenue"),
            pl.int_ranges(0, pl.col("count")).alias("copy"),
        )
        .explode("copy")
        .drop("copy")
        .with_columns(pl.lit(1, dtype=pl.Int64).alias("count"))
    )

    a, b = check(one_per_row, "grouped"), check(grouped, "grouped")

    assert len(a.outliers) == len(b.outliers)
    for left, right in zip(a.outliers, b.outliers):
        assert left.variable == right.variable
        assert left.journeys == right.journeys
        assert (left.lower, left.upper) == pytest.approx((right.lower, right.upper))
        assert left.share_journeys == pytest.approx(right.share_journeys)
        assert left.share_conversions == pytest.approx(right.share_conversions)
        assert left.share_revenue == pytest.approx(right.share_revenue)


# What the report says about them


@pytest.mark.parametrize("seed", SEEDS)
def test_shares_of_journeys_conversions_and_revenue(seed):
    sessions, expected = planted(seed)
    report = check(sessions, "session")
    journeys = sessions.group_by("user").agg(
        pl.col("converted").any(), pl.col("revenue").sum()
    )

    for variable, users in expected.items():
        out = journeys.filter(pl.col("user").is_in(list(users)))
        cut = cuts(report)[variable]
        assert cut.share_journeys == pytest.approx(out.height / journeys.height)
        assert cut.share_conversions == pytest.approx(
            out["converted"].sum() / journeys["converted"].sum()
        )
        assert cut.share_revenue == pytest.approx(
            out["revenue"].sum() / journeys["revenue"].sum()
        )


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", ["session", "journey"])
def test_examples_are_flagged_journeys(fmt, seed):
    sessions, expected = planted(seed)
    report = check(in_format(sessions, fmt), fmt)

    for variable in VARIABLES:
        examples = cuts(report)[variable].examples
        assert 1 <= len(examples) <= 5
        assert set(examples) <= expected[variable]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_quality_finding_counts_each_journey_once(fmt, seed):
    sessions, _ = planted(seed)
    df = in_format(sessions, fmt)
    report = check(df, fmt)
    finding = next(p for p in report.quality if p.check == "outliers")

    if fmt == "grouped":
        rows = report.outlier_journeys.get_column("journey_id").str.slice(5)
        weights = df.get_column("count").gather(rows.cast(pl.Int64))
        assert finding.rows == weights.sum()
    else:
        assert finding.rows == report.outlier_journeys.height
    assert "Outliers" in str(report)


@pytest.mark.parametrize("seed", SEEDS)
def test_a_higher_threshold_flags_fewer_journeys(seed):
    sessions, _ = planted(seed)
    counts = [
        check(sessions, "session", outlier_threshold=t).outlier_journeys.height
        for t in (1.0, 3.0, 1e6)
    ]

    assert counts[0] >= counts[1] >= counts[2]
    assert counts[2] == 0


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_ids_are_the_journey_ids_of_mam(fmt, seed):
    sessions, _ = planted(seed)
    df = in_format(sessions, fmt)
    ids = set(build(df, fmt).unified_df.get_column("journey_id").to_list())

    assert set(check(df, fmt).outlier_journeys.get_column("journey_id")) <= ids


@pytest.mark.parametrize("seed", SEEDS)
def test_ids_follow_split_on_conversion(seed):
    sessions, expected = planted(seed)
    split = dict(create_journey_id_based_on_conversion=True)
    ids = set(build(sessions, "session", **split).unified_df["journey_id"].to_list())
    report = check(sessions, "session", **split)

    found = set(report.outlier_journeys.get_column("journey_id"))
    assert found and found <= ids
    assert {i.split("_J")[0] for i in flagged(report, "n_steps")} == expected["n_steps"]


# Removing them


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_remove_outliers_drops_whole_journeys_and_keeps_the_rest(fmt, seed):
    sessions, expected = planted(seed)
    df = in_format(sessions, fmt)
    report = check(df, fmt)

    kept = report.remove_outliers(df)

    ids = report.outlier_journeys.get_column("journey_id")
    if fmt == "grouped":
        rows = ids.str.slice(5).cast(pl.UInt32)
        wanted = (
            df.with_row_index("i").filter(~pl.col("i").is_in(rows.to_list())).drop("i")
        )
    else:
        key = "user" if fmt == "session" else "id"
        wanted = df.filter(~pl.col(key).is_in(ids.to_list()))
        everyone = set().union(*expected.values())
        assert set(ids) == everyone
    assert_frame_equal(kept, wanted)
    assert kept.height < df.height


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_every_model_runs_without_the_outliers(fmt, seed):
    sessions, _ = planted(seed)
    df = in_format(sessions, fmt)
    kept = check(df, fmt).remove_outliers(df)
    model = build(kept, fmt)

    for run in MODELS.values():
        assert run(model).to_polars().height > 0


def test_remove_outliers_works_on_pandas():
    sessions, _ = planted(0)
    report = check(sessions.to_pandas(), "session")

    kept = report.remove_outliers(sessions.to_pandas())

    assert type(kept).__name__ == "DataFrame" and hasattr(kept, "iloc")
    assert len(kept) == report.remove_outliers(sessions).height


def test_remove_outliers_refuses_other_data():
    sessions, _ = planted(0)
    report = check(sessions, "session")

    with pytest.raises(ValueError, match="same data"):
        report.remove_outliers(sessions.head(10))


# What isn't measured and what isn't accepted


def test_no_duration_without_times():
    sessions, _ = planted(0)
    journeys = in_format(sessions, "journey").drop("times")
    report = check_data_quality(
        journeys,
        "journey",
        "path",
        "converted",
        user_id_colname="id",
        conversion_value_colname="revenue",
    )

    assert set(cuts(report)) == {"n_steps", "conversion_value"}


def test_no_cut_off_on_small_data():
    df = in_format(clean_sessions(np.random.default_rng(0), n_users=10), "journey")

    assert check(df, "journey").outliers == []


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(outlier_method="median"),
        dict(outlier_threshold=0),
        dict(outlier_threshold=-1),
    ],
)
def test_bad_outlier_arguments_are_refused(kwargs):
    with pytest.raises(ValueError):
        check(clean_sessions(np.random.default_rng(0)), "session", **kwargs)


def mostly_single_touch():
    """80 journeys with one touch, 15 with two, 5 with three: Q1 = Q3 = 1 touch."""
    paths = ["Email"] * 80 + ["Email > Search"] * 15 + ["Email > Search > Direct"] * 5
    return pl.DataFrame(
        {
            "journey_id": [f"j{i}" for i in range(len(paths))],
            "path": paths,
            "converted": [i % 2 == 0 for i in range(len(paths))],
        }
    )


def test_iqr_does_not_cut_a_measure_without_spread():
    """With Q1 = Q3 every journey off that value would be an outlier: the rule can't
    separate them, so that measure gets no cut and nothing is removed for it."""
    df = mostly_single_touch()

    report = check_data_quality(df, "journey", "path", "converted")

    assert "n_steps" not in cuts(report)
    assert report.outlier_journeys.is_empty()
    assert report.remove_outliers(df).height == df.height
    assert "outliers" not in [p.check for p in report.quality]


def test_the_report_says_which_measures_have_no_spread_and_what_to_use():
    report = check_data_quality(mostly_single_touch(), "journey", "path", "converted")

    note = next(p for p in report.quality if p.check == "outliers_without_spread")
    assert "n_steps" in note.message and "zscore" in note.message


def test_zscore_still_cuts_a_measure_without_iqr_spread():
    report = check_data_quality(
        mostly_single_touch(), "journey", "path", "converted", outlier_method="zscore"
    )

    assert "n_steps" in cuts(report)
    assert "outliers_without_spread" not in [p.check for p in report.quality]
