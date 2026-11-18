"""Shapley on random valid data."""

# Totals match the truth, raw adds up to the aggregate, the three input formats
# agree, and renaming channels changes nothing.

import datetime

import numpy as np
import polars as pl
import pytest

from mam import MAM

SEEDS = range(4)
CHANNELS = [f"ch_{i}" for i in range(9)]
VALUE_COLUMNS = ["conv_rate", "conversions", "conversion_value", "total_sequences"]


def random_journeys(seed, n=300):
    """Journeys with repeats, up to 9 distinct channels and ~30% conversions."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        length = int(rng.geometric(0.35))
        path = list(rng.choice(CHANNELS, length, p=np.r_[0.3, np.full(8, 0.7 / 8)]))
        for k in range(1, length):
            if rng.random() < 0.3:
                path[k] = path[k - 1]
        converts = bool(rng.random() < 0.3)
        value = round(float(rng.lognormal(4, 1)), 2) if converts else 0.0
        rows.append((f"j{i}", path, converts, value))
    return rows


def format_2(rows, rename=None):
    rename = rename or {}
    return pl.DataFrame(
        {
            "id": [j for j, *_ in rows],
            "path": [" > ".join(rename.get(c, c) for c in p) for _, p, _, _ in rows],
            "converted": [c for *_, c, _ in rows],
            "revenue": [v for *_, v in rows],
        }
    )


def format_1(rows):
    out = []
    t0 = datetime.datetime(2026, 1, 1)
    for j, path, converts, value in rows:
        for k, ch in enumerate(path):
            last = k == len(path) - 1
            out.append(
                (
                    j,
                    (t0 + datetime.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M:%S"),
                    ch,
                    converts and last,
                    value if last else 0.0,
                )
            )
    return pl.DataFrame(
        out, schema=["user", "when", "channel", "converted", "revenue"], orient="row"
    )


def format_3(rows):
    return (
        format_2(rows)
        .group_by("path", "converted")
        .agg(pl.len().alias("n"), pl.col("revenue").sum())
    )


def build(fmt, df, revenue):
    rv = "revenue" if revenue else None
    if fmt == "f1":
        return MAM(
            df,
            "session",
            "channel",
            "converted",
            datetime_colname="when",
            user_id_colname="user",
            conversion_value_colname=rv,
        )
    if fmt == "f2":
        return MAM(
            df,
            "journey",
            "path",
            "converted",
            user_id_colname="id",
            conversion_value_colname=rv,
        )
    return MAM(
        df,
        "grouped_journey",
        "path",
        "converted",
        occurrences_colname="n",
        conversion_value_colname=rv,
    )


def credit(frame, value="attribution"):
    return dict(frame.select("channels", value).iter_rows())


def assert_same_credit(a, b):
    assert set(a) == set(b)
    for k in a:
        assert a[k] == pytest.approx(b[k], rel=1e-9, abs=1e-9), k


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("value_column", VALUE_COLUMNS)
@pytest.mark.parametrize("revenue", [True, False], ids=["revenue", "count"])
def test_totals_and_raw_match(seed, value_column, revenue):
    rows = random_journeys(seed)
    truth = sum(v for *_, c, v in rows if c) if revenue else sum(c for *_, c, _ in rows)
    result = build("f2", format_2(rows), revenue).run_shapley(
        max_size=4, value_column=value_column
    )
    agg = credit(result.to_polars())
    raw = result.to_raw_polars()
    assert sum(agg.values()) == pytest.approx(truth)
    assert raw["attribution_value"].sum() == pytest.approx(truth)
    raw_credit = credit(
        raw.group_by("channels").agg(pl.col("attribution_value").sum()),
        "attribution_value",
    )
    for ch, v in agg.items():
        assert raw_credit.get(ch, 0.0) == pytest.approx(v, abs=1e-9)
    assert all(np.isfinite(raw["attribution_value"].to_numpy()))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("revenue", [True, False], ids=["revenue", "count"])
def test_the_three_formats_agree(seed, revenue):
    rows = random_journeys(seed)
    results = {
        fmt: credit(build(fmt, make(rows), revenue).run_shapley(max_size=3).to_polars())
        for fmt, make in (("f1", format_1), ("f2", format_2), ("f3", format_3))
    }
    assert_same_credit(results["f1"], results["f2"])
    assert_same_credit(results["f3"], results["f2"])


@pytest.mark.parametrize("seed", SEEDS)
def test_renaming_channels_changes_nothing(seed):
    rows = random_journeys(seed)
    rng = np.random.default_rng(seed + 100)
    new_names = [f"x{n}" for n in rng.permutation(len(CHANNELS))]
    rename = dict(zip(CHANNELS, new_names))
    before = credit(
        build("f2", format_2(rows), True).run_shapley(max_size=3).to_polars()
    )
    after = credit(
        build("f2", format_2(rows, rename), True).run_shapley(max_size=3).to_polars()
    )
    assert_same_credit({rename[k]: v for k, v in before.items()}, after)
