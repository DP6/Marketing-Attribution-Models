"""Spaces around channel names don't create new channels (I11, I20, I21).

Paths split on path_separator exactly as given; each channel is then trimmed.
"""

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from mam import MAM, check_data_quality
from tests.test_validation_in_mam import MODELS, build
from tests.test_validation_random import CLEAN, check


def journey_mam(paths, times=None, **kwargs):
    df = pl.DataFrame(
        {
            "journey_id": [f"j{i}" for i in range(len(paths))],
            "path": paths,
            "times": times or ["0.0"] * len(paths),
            "converted": [True] * len(paths),
        }
    )
    return MAM(
        df,
        format_type="journey",
        channels_colname="path",
        journey_with_conv_colname="converted",
        time_till_conv_colname="times",
        **kwargs,
    )


def channels(model):
    return (
        model.unified_df.sort("journey_id")["channels"]
        .cast(pl.List(pl.String))
        .to_list()
    )


@pytest.mark.parametrize("path", ["A > B", " A > B ", " A  >  B ", "A   > B"])
def test_journey_paths_split_the_same_whatever_the_spacing_around_names(path):
    model = journey_mam([path], times=["1.0 > 0.0"])

    assert channels(model) == [["A", "B"]]


@pytest.mark.parametrize("path", ["A>B", "A >B", "A> B"])
def test_paths_split_only_on_the_separator_as_given(path):
    model = journey_mam([path])

    assert channels(model) == [[path.strip()]]


def test_a_separator_with_spaces_keeps_its_bare_symbol_inside_names():
    model = journey_mam(["e-mail - paid-search"], times=["1 - 0"], path_separator=" - ")

    assert channels(model) == [["e-mail", "paid-search"]]


def test_journey_times_split_with_the_same_rule_as_the_path():
    model = journey_mam(["A > B"], times=[" 7200 >  0 "])

    assert model.unified_df["time_till_conv"].to_list() == [[7200.0, 0.0]]


def test_grouped_paths_split_the_same_whatever_the_spacing():
    df = pl.DataFrame(
        {"path": [" A  >  B ", "C"], "count": [3, 2], "converted": [True, False]}
    )
    model = MAM(
        df,
        format_type="grouped_journey",
        channels_colname="path",
        journey_with_conv_colname="converted",
        occurrences_colname="count",
    )

    assert channels(model) == [["A", "B"], ["C"]]


def test_session_channel_names_are_trimmed():
    df = pl.DataFrame(
        {
            "user_id": ["u1", "u1", "u2"],
            "datetime": [
                "2026-01-01 10:00:00",
                "2026-01-02 10:00:00",
                "2026-01-01 09:00:00",
            ],
            "channel": [" Email", "Search ", "Email"],
            "conversion": [False, True, True],
        }
    )
    model = MAM(
        df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
    )

    assert channels(model) == [["Email", "Search"], ["Email"]]
    totals = dict(
        model.run_last_click().to_polars().select("channels", "attribution").iter_rows()
    )
    assert totals == {"Search": 1.0, "Email": 1.0}


def test_custom_separator_keeps_the_default_one_inside_names():
    model = journey_mam(["A>x | B"], times=["1 | 0"], path_separator=" | ")

    assert channels(model) == [["A>x", "B"]]


def test_separator_made_of_spaces_is_used_as_given():
    model = journey_mam(["A B"], times=["1 0"], path_separator=" ")

    assert channels(model) == [["A", "B"]]


def test_quality_report_does_not_count_spacing_as_another_channel():
    df = pl.DataFrame(
        {
            "journey_id": ["j1", "j2"],
            "path": ["Email > Search", " Email  >  Search "],
            "converted": [True, False],
        }
    )
    report = check_data_quality(
        df,
        format_type="journey",
        channels_colname="path",
        journey_with_conv_colname="converted",
    )

    assert report.summary["channels"] == 2
    assert not [p for p in report.quality if p.check == "similar_channel_names"]


def respace(df, fmt, rng):
    """Writes the same data with messy spacing on about half of the rows."""
    rows = pl.Series(rng.random(df.height) < 0.5)
    if fmt == "session":
        messy = pl.lit(" ") + pl.col("channel") + pl.lit("  ")
        return df.with_columns(
            pl.when(rows).then(messy).otherwise("channel").alias("channel")
        )
    cols = ["path", "times"] if fmt == "journey" else ["path"]
    return df.with_columns(
        pl.when(rows)
        .then(pl.lit(" ") + pl.col(col).str.replace_all(" > ", "  >  ") + pl.lit(" "))
        .otherwise(col)
        .alias(col)
        for col in cols
    )


@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("fmt", ["session", "journey", "grouped"])
def test_messy_spacing_gives_the_same_report_and_results(fmt, seed):
    clean = CLEAN[fmt](np.random.default_rng(seed))
    messy = respace(clean, fmt, np.random.default_rng(seed + 100))

    assert check(messy, fmt).summary == check(clean, fmt).summary
    assert check(messy, fmt).quality == check(clean, fmt).quality
    for run in MODELS.values():
        assert_frame_equal(
            results(run(build(messy, fmt))), results(run(build(clean, fmt)))
        )


def results(result):
    frame = result.to_polars()
    return frame.with_columns(pl.col("channels").cast(pl.String)).sort("channels")
