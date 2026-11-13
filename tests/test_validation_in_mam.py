import warnings

import numpy as np
import polars as pl
import pytest

from mam import MAM, InputValidationError, JAToolbox, check_data_quality
from tests.test_validation_random import CASES, CLEAN, SEEDS, check

ARGS = {
    "session": dict(
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="converted",
        datetime_colname="when",
        user_id_colname="user",
        conversion_value_colname="revenue",
    ),
    "journey": dict(
        format_type="journey",
        channels_colname="path",
        journey_with_conv_colname="converted",
        user_id_colname="id",
        time_till_conv_colname="times",
        conversion_value_colname="revenue",
    ),
    "grouped": dict(
        format_type="grouped_journey",
        channels_colname="path",
        journey_with_conv_colname="converted",
        occurrences_colname="count",
        conversion_value_colname="revenue",
    ),
}

MODELS = {
    "last_click": lambda m: m.run_last_click(),
    "first_click": lambda m: m.run_first_click(),
    "linear": lambda m: m.run_linear(),
    "position_based": lambda m: m.run_position_based(),
    "markov": lambda m: m.run_markov(),
    "shapley": lambda m: m.run_shapley(),
}


def build(df, fmt, **kwargs):
    args = {**ARGS[fmt], **kwargs}
    if "revenue" not in df.columns:
        args.pop("conversion_value_colname")
    return MAM(df, **args)


def total_credit(result):
    frame = result.to_polars()
    return sum(
        frame.get_column(col).sum()
        for col in frame.columns
        if col.startswith("attribution")
    )


ERROR_CASES = [
    case for case in CASES if case.where == "errors" and case.name != "missing column"
]
OTHER_CASES = [case for case in CASES if case.where != "errors"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize(
    "case", ERROR_CASES, ids=lambda case: f"{case.fmt}: {case.name}"
)
def test_mam_stops_on_every_error_the_quality_function_reports(case, seed):
    rng = np.random.default_rng(seed)
    bad, _ = case.inject(CLEAN[case.fmt](rng), rng)
    expected = check(bad, case.fmt, **case.kwargs).errors

    with pytest.raises(InputValidationError) as raised:
        build(bad, case.fmt, **case.kwargs)

    assert raised.value.problems == expected


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize(
    "case", OTHER_CASES, ids=lambda case: f"{case.fmt}: {case.name}"
)
def test_mam_runs_on_warnings_and_quality_findings(case, seed):
    rng = np.random.default_rng(seed)
    bad, _ = case.inject(CLEAN[case.fmt](rng), rng)
    report = check(bad, case.fmt, **case.kwargs)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = build(bad, case.fmt, **case.kwargs)

    assert [str(w.message) for w in caught if issubclass(w.category, UserWarning)] == [
        problem.message for problem in report.warnings
    ]
    model.run_linear()


def test_mam_reports_a_missing_column():
    df = CLEAN["session"](np.random.default_rng(0)).drop("user")

    with pytest.raises(InputValidationError, match="Missing columns: 'user'"):
        build(df, "session")


def test_jatoolbox_stops_on_the_same_errors():
    df = CLEAN["journey"](np.random.default_rng(0))
    df = df.with_columns(pl.lit("j1").alias("id"))

    with pytest.raises(InputValidationError, match="must be unique"):
        args = {**ARGS["journey"], "channels_col": "path"}
        args.pop("channels_colname")
        args.pop("conversion_value_colname")
        JAToolbox(df, **args)


@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("fmt", ["session", "journey", "grouped"])
def test_clean_random_data_runs_every_model(fmt, seed):
    df = CLEAN[fmt](np.random.default_rng(seed))
    report = check(df, fmt)
    model = build(df, fmt)

    assert model.unified_df.height == (
        report.summary["journeys"] if fmt != "grouped" else report.summary["rows"]
    )
    for name, run in MODELS.items():
        credit = total_credit(run(model))
        assert credit == pytest.approx(report.summary["revenue"], rel=1e-6), name


def test_conversion_flag_as_0_and_1_works_in_session_format():
    df = CLEAN["session"](np.random.default_rng(0))
    as_numbers = df.with_columns(pl.col("converted").cast(pl.Int64))

    def credit(data):
        result = build(data, "session").run_linear().to_polars()
        return dict(zip(result["channels"].cast(pl.String), result["attribution"]))

    assert credit(as_numbers) == pytest.approx(credit(df))


def test_iso_dates_with_and_without_fractions_are_read():
    df = pl.DataFrame(
        {
            "user": ["u1", "u1", "u1"],
            "when": [
                "2026-01-05 10:00:00.000",
                "2026-01-05T11:00:00",
                "2026-01-05 12:00",
            ],
            "channel": ["Email", "Search", "Direct"],
            "converted": [False, False, True],
            "revenue": [0.0, 0.0, 10.0],
        }
    )

    unified = build(df, "session").unified_df

    assert unified.get_column("time_till_conv").to_list() == [[2.0, 1.0, 0.0]]


def long_journey(unique_channels):
    path = " > ".join(f"c{i:02d}" for i in range(unique_channels))
    return MAM(
        pl.DataFrame(
            {"path": [path, "c00"], "converted": [True, False], "count": [1, 1]}
        ),
        "grouped_journey",
        "path",
        "converted",
        occurrences_colname="count",
    )


def test_shapley_warns_when_a_long_journey_has_no_size_limit():
    with pytest.warns(UserWarning, match="16 unique channels"):
        long_journey(16).run_shapley(max_size=None)


@pytest.mark.parametrize("unique_channels, max_size", [(16, 4), (16, 15), (15, None)])
def test_shapley_does_not_warn_when_journeys_are_limited(unique_channels, max_size):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        long_journey(unique_channels).run_shapley(max_size=max_size)


def test_mam_stops_on_session_without_date_or_user_with_the_report_message():
    df = pl.DataFrame({"channel": ["Email", "Search"], "converted": [False, True]})
    report = check_data_quality(df, "session", "channel", "converted")

    with pytest.raises(InputValidationError) as raised:
        MAM(df, "session", "channel", "converted")

    assert raised.value.problems == report.errors


def test_warnings_point_at_the_users_call():
    df = pl.DataFrame(
        {
            "journey_id": ["j1", "j2"],
            "path": ["(null) > Search", "Email"],
            "converted": [True, False],
        }
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        MAM(df, "journey", "path", "converted")

    assert caught and {w.filename for w in caught} == {__file__}
