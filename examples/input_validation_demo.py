"""
How MAM behaves on a dataset with problems, and the recommended way to run it.

Builds a simulated session dataset with problems a client export often has, runs
MAM on it, then checks it with check_data_quality, fixes it step by step and runs
the models. Prints a Markdown report with the code of each step and its real output:

    python examples/input_validation_demo.py > examples/input_validation_demo.md
"""

import datetime
import inspect
import warnings

import numpy as np
import polars as pl

from mam import MAM, InputValidationError, check_data_quality

ARGS = dict(
    format_type="session",
    channels_colname="channel",
    journey_with_conv_colname="conversion",
    datetime_colname="datetime",
    user_id_colname="user_id",
    conversion_value_colname="revenue",
)


def clean_dataset():
    rng = np.random.default_rng(7)
    channels = ["Search", "Email", "Social", "Display", "Direct"]
    rows = []
    for user in range(300):
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
                    start + datetime.timedelta(hours=5 * i),
                    str(rng.choice(channels)),
                    converts and last,
                    round(float(rng.uniform(20, 400)), 2) if converts and last else 0.0,
                )
            )
    return pl.DataFrame(
        rows,
        schema=["user_id", "datetime", "channel", "conversion", "revenue"],
        orient="row",
    )


def plant_problems(clean):
    raw = clean.with_columns(
        pl.col("datetime").dt.strftime("%m/%d/%Y %H:%M:%S")
    )  # dates written month first
    row = np.arange(raw.height)
    touch_rows = np.flatnonzero(
        raw.select(
            pl.col("conversion").any().over("user_id") & ~pl.col("conversion")
        ).to_series()
    )  # touches of converting users that aren't the conversion
    never_convert = (
        raw.filter(~pl.col("conversion").any().over("user_id"))["user_id"]
        .unique()
        .sort()[:3]
    )
    raw = raw.with_columns(
        pl.when(
            pl.col("user_id").is_in(never_convert.implode())
            & (pl.int_range(pl.len()).over("user_id") == 0)
        )
        .then(35.0)
        .otherwise(pl.col("revenue"))
        .alias("revenue"),  # revenue on users who never convert
        pl.when(pl.Series(np.isin(row, touch_rows[[3, 25, 60]])))
        .then(pl.lit("email"))
        .otherwise(pl.col("channel"))
        .alias("channel"),  # another spelling of Email
    )
    raw = raw.with_columns(
        pl.when(pl.Series(np.isin(row, touch_rows[[10, 40, 90]])))
        .then(pl.lit("(null)"))
        .otherwise(pl.col("channel"))
        .alias("channel"),  # a name Markov uses internally
        pl.when(pl.Series(np.isin(row, [200, 201])))
        .then(None)
        .otherwise(pl.col("user_id"))
        .alias("user_id"),  # rows with no user
    )
    return pl.concat([raw, raw[[5, 6, 60]]])  # rows exported twice


def step_1_straight_into_mam(raw):
    try:
        MAM(raw, **ARGS)
    except InputValidationError as error:
        print(f"InputValidationError: {error}")


def step_2_check_first(raw):
    report = check_data_quality(raw, **ARGS)
    print(report)
    print(f"\nreport.ok = {report.ok}")


def step_3_fix_the_errors(raw):
    fixed = (
        raw.unique(maintain_order=True)  # rows exported twice
        .filter(pl.col("user_id").is_not_null())  # rows with no user
        .with_columns(
            pl.col("datetime").str.to_datetime("%m/%d/%Y %H:%M:%S")
        )  # state the date order
        .with_columns(
            pl.when(~pl.col("conversion").any().over("user_id"))
            .then(0.0)
            .otherwise(pl.col("revenue"))
            .alias("revenue")
        )  # revenue on users who never convert
    )
    print(check_data_quality(fixed, **ARGS))
    model = MAM(fixed, **ARGS)  # runs, and warns about "(null)"
    print("\nMarkov:")
    print(model.run_markov().to_polars())
    return fixed


def step_4_fix_the_warning_and_the_quality_finding(fixed):
    final = fixed.with_columns(
        pl.when(pl.col("channel") == "(null)")
        .then(pl.lit("Unknown"))  # reserved name
        .otherwise(pl.col("channel").str.to_titlecase())  # 'email' to 'Email'
        .alias("channel")
    )
    print(check_data_quality(final, **ARGS))
    model = MAM(final, **ARGS)  # runs with no warning
    print("\nMarkov:")
    print(model.run_markov().to_polars())


def run(step, *args):
    """Prints the step's code and its output, including warnings, as Markdown."""
    print("```python")
    print(inspect.getsource(step).rstrip())
    print("```\n\nOutput:\n\n```text")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", UserWarning)
        result = step(*args)
    for warning in caught:
        if issubclass(warning.category, UserWarning):
            print(f"\nUserWarning: {warning.message}")
    print("```\n")
    return result


def main():
    pl.Config.set_tbl_rows(20)
    raw = plant_problems(clean_dataset())

    print("# How MAM behaves on a dataset with problems\n")
    print(
        "Generated by `python examples/input_validation_demo.py`. Every output below is the "
        "real output of the code above it, so rerun the script to check it.\n"
    )
    print(
        f"A simulated session dataset of {raw.height} rows and 300 users, with problems "
        "planted:\n\n"
        "| Problem | Where it is reported |\n|---|---|\n"
        "| Dates written month first, on every row | `MAM` error |\n"
        "| 3 rows exported twice | `MAM` error |\n"
        "| 2 rows with no user | `MAM` error |\n"
        "| Revenue on the first touch of 3 users who never convert | `MAM` error |\n"
        '| 3 converting-journey touches named `"(null)"`, a name Markov uses internally '
        "| `MAM` warning |\n"
        '| 3 converting-journey touches named `"email"` | quality function only |\n'
    )
    print("```text")
    print(raw.head(5))
    print("```\n")

    print("## 1. Straight into MAM: it stops and lists every error\n")
    run(step_1_straight_into_mam, raw)
    print(
        "The warning about `(null)` isn't shown yet, because the errors stop the run first.\n"
    )

    print("## 2. Recommended: check the data first\n")
    run(step_2_check_first, raw)

    print("## 3. Fix the errors: MAM runs and warns\n")
    fixed = run(step_3_fix_the_errors, raw)
    print(
        "`(null)` gets no credit in Markov although its touches are in converting journeys, "
        "and `email` is counted apart from `Email`.\n"
    )

    print("## 4. Fix the warning and the quality finding: a clean run\n")
    run(step_4_fix_the_warning_and_the_quality_finding, fixed)
    print(
        "The touches renamed `Unknown` now get credit in Markov, and `Email` is one channel.\n"
    )


if __name__ == "__main__":
    main()
