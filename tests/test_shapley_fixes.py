"""
Shapley on valid data: which channels enter the game, raw = aggregated, totals,
options and the conversion table schema.
"""

import itertools
import math

import polars as pl
import pytest

from mam import MAM
from mam.models.shapley import ShapleyModel


def journeys(rows, revenue=True):
    """rows: (path, converts, revenue). Format 2 with one id per journey."""
    data = {
        "journey_id": [str(i + 1) for i in range(len(rows))],
        "path": [p for p, _, _ in rows],
        "converted": [c for _, c, _ in rows],
    }
    if revenue:
        data["revenue"] = [float(v) for _, _, v in rows]
    return MAM(
        pl.DataFrame(data),
        "journey",
        "path",
        "converted",
        conversion_value_colname="revenue" if revenue else None,
    )


def per_channel(frame, value="attribution"):
    return {c: round(v, 9) for c, v in frame.select("channels", value).iter_rows()}


def raw_per_channel(result):
    raw = result.to_raw_polars()
    totals = raw.group_by("channels").agg(pl.col("attribution_value").sum())
    return per_channel(totals, "attribution_value")


WALKTHROUGH = [
    ("A", True, 100),
    ("B", True, 200),
    ("B > C", False, 0),
    ("D > C > A", True, 300),
]


def test_walkthrough_example():
    result = journeys(WALKTHROUGH).run_shapley()
    expected = {"A": 300.0, "B": 200.0, "C": 50.0, "D": 50.0}
    assert per_channel(result.to_polars()) == expected
    assert raw_per_channel(result) == expected


# max_size keeps the most recent channels ------------------------------------


def test_max_size_keeps_the_most_recent_channels_not_the_last_names():
    result = journeys([("Zeta > Alpha > Beta > Gamma > Delta", True, 100)]).run_shapley(
        max_size=4
    )
    credit = per_channel(result.to_polars())
    assert credit.get("Zeta", 0.0) == 0.0
    assert credit["Alpha"] == pytest.approx(25.0)
    assert result.metadata["conv_table"]["combinations"].to_list() == [
        "Alpha > Beta > Delta > Gamma"
    ]


def test_recency_counts_the_last_appearance_of_a_channel():
    # A > B > C > A > D: distinct by last appearance is B, C, A, D; keep 3 -> C, A, D
    result = journeys([("A > B > C > A > D", True, 90)]).run_shapley(max_size=3)
    credit = per_channel(result.to_polars())
    assert credit.get("B", 0.0) == 0.0
    assert {k: credit[k] for k in "ACD"} == {"A": 30.0, "C": 30.0, "D": 30.0}


def test_walkthrough_with_max_size_two_drops_the_oldest_touch():
    result = journeys(WALKTHROUGH).run_shapley(max_size=2)
    combos = set(result.metadata["conv_table"]["combinations"])
    assert "A > C" in combos
    assert per_channel(result.to_polars()).get("D", 0.0) == 0.0


def test_renaming_channels_does_not_change_attribution():
    rows = [
        ("E > D > C > B > A", True, 100),
        ("A > B", True, 40),
        ("D > E", False, 0),
        ("C", True, 10),
    ]
    rename = {"A": "z", "B": "y", "C": "x", "D": "w", "E": "v"}
    renamed = [
        (" > ".join(rename[c] for c in p.split(" > ")), conv, val)
        for p, conv, val in rows
    ]
    before = per_channel(journeys(rows).run_shapley(max_size=3).to_polars())
    after = per_channel(journeys(renamed).run_shapley(max_size=3).to_polars())
    assert {rename[c]: v for c, v in before.items()} == after


# raw = aggregated -------------------------------------------------------------


@pytest.mark.parametrize(
    "rows",
    [
        [("A > A > A > B", True, 1)],
        [("B > B > A", True, 1)],
        [
            ("A", True, 100),
            ("B", True, 200),
            ("B > C", False, 0),
            ("D > A > C > A", True, 300),
        ],
    ],
    ids=["AAAB", "BBA", "walkthrough-repeat"],
)
def test_raw_adds_up_to_the_aggregate_when_channels_repeat(rows):
    result = journeys(rows).run_shapley()
    assert raw_per_channel(result) == per_channel(result.to_polars())


def test_each_touch_of_a_repeated_channel_gets_an_equal_part():
    raw = journeys([("A > A > A > B", True, 1)]).run_shapley().to_raw_polars()
    assert raw["attribution_value"].to_list() == pytest.approx([1 / 6] * 3 + [0.5])


# negative contributions --------------------------------------------------------


NEGATIVE = WALKTHROUGH + [("C > C > C > B", True, 50)]


def test_negative_contribution_keeps_the_journey_value_in_raw():
    result = journeys(NEGATIVE).run_shapley()
    agg = per_channel(result.to_polars())
    assert agg == {"A": 300.0, "B": 275.0, "C": 25.0, "D": 50.0}
    assert raw_per_channel(result) == agg
    raw = result.to_raw_polars()
    j5 = raw.filter(pl.col("journey_id") == "5")
    assert j5["attribution_value"].sum() == pytest.approx(50.0)


def test_near_cancelling_journey_does_not_blow_up():
    rows = [
        ("A", True, 1),
        ("B", False, 0),
        ("A > B", False, 0),
        ("B > B > B > A", True, 1),
    ]
    raw = journeys(rows).run_shapley().to_raw_polars()
    assert raw["attribution_value"].abs().max() <= 2.0
    assert raw["attribution_value"].sum() == pytest.approx(2.0)


# totals --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value_column", ["conv_rate", "conversions", "conversion_value", "total_sequences"]
)
@pytest.mark.parametrize("revenue", [True, False], ids=["revenue", "count"])
def test_every_value_column_returns_the_true_total_in_both_outputs(
    value_column, revenue
):
    rows = NEGATIVE + [("A > B > A", False, 0), ("D", True, 70), ("A > D", True, 5)]
    truth = sum(v for _, c, v in rows if c) if revenue else sum(c for _, c, _ in rows)
    result = journeys(rows, revenue=revenue).run_shapley(value_column=value_column)
    assert result.to_polars()["attribution"].sum() == pytest.approx(truth)
    assert result.to_raw_polars()["attribution_value"].sum() == pytest.approx(truth)


def test_revenue_on_non_converting_rows_is_not_credited():
    unified = pl.DataFrame(
        {
            "journey_id": ["1", "2", "3"],
            "channels": [["A", "B"], ["B", "A"], ["C"]],
            "has_conversion": [True, False, False],
            "weight": [1, 1, 1],
            "conversion_value": [100.0, 50.0, 30.0],
        }
    )
    model = ShapleyModel()
    raw = model.calculate(unified)
    agg = model.get_aggregated_results(unified)
    assert agg["attribution"].sum() == pytest.approx(100.0)
    assert raw["attribution_value"].sum() == pytest.approx(100.0)


def test_no_conversions_returns_every_channel_with_zero():
    rows = [(p, False, 0) for p, _, _ in WALKTHROUGH]
    result = journeys(rows).run_shapley()
    assert per_channel(result.to_polars()) == {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
    assert result.to_raw_polars()["attribution_value"].sum() == 0.0


def test_no_conversions_in_the_report_is_not_an_error(tmp_path):
    rows = [(p, False, 0) for p, _, _ in WALKTHROUGH]
    out = journeys(rows).generate_report(
        models=["shapley"],
        output_html_path=str(tmp_path / "r.html"),
        output_json_path=str(tmp_path / "r.json"),
    )
    shapley = out["attribution_results"]["shapley"]
    assert "error" not in shapley
    assert sorted(shapley["channels"]) == ["A", "B", "C", "D"]
    assert shapley["attributions"] == [0.0] * 4


# Shapley values match the definition ---------------------------------------------


def brute_force_shapley(players, value):
    """Average marginal contribution over every arrival order."""
    credit = dict.fromkeys(players, 0.0)
    orders = list(itertools.permutations(players))
    for order in orders:
        group = ()
        for p in order:
            before = value(tuple(sorted(group)))
            group = group + (p,)
            credit[p] += value(tuple(sorted(group))) - before
    return {p: v / len(orders) for p, v in credit.items()}


def test_shares_match_the_arrival_order_definition():
    rows = NEGATIVE + [
        ("A > B > D", True, 80),
        ("A > B", False, 0),
        ("B > D", True, 20),
    ]
    model_result = journeys(rows).run_shapley()
    table = model_result.metadata["conv_table"]
    rates = {
        tuple(c.split(" > ")): r
        for c, r in table.select("combinations", "conv_rate").iter_rows()
    }
    for combo, alloc, total in table.select(
        "combinations", "attribution", "conversion_value"
    ).iter_rows():
        players = combo.split(" > ")
        phi = brute_force_shapley(players, lambda g: rates.get(g, 0.0))
        s = sum(phi.values())
        assert alloc == pytest.approx([phi[p] / s * total for p in players])


# options and schema --------------------------------------------------------------


@pytest.mark.parametrize("max_size", [0, -1, 2.5, True, "4"])
def test_invalid_max_size_is_rejected(max_size):
    with pytest.raises(ValueError, match="max_size"):
        journeys(WALKTHROUGH).run_shapley(max_size=max_size)


@pytest.mark.parametrize("value_column", ["custom_value", "revenue", ""])
def test_unknown_value_column_is_rejected(value_column):
    with pytest.raises(ValueError, match="value_column"):
        journeys(WALKTHROUGH).run_shapley(value_column=value_column)


def test_max_size_none_keeps_every_channel():
    result = journeys([("A > B > C > D > E", True, 10)]).run_shapley(max_size=None)
    assert per_channel(result.to_polars()) == {c: 2.0 for c in "ABCDE"}


def test_channel_name_containing_the_separator_stays_whole():
    df = pl.DataFrame(
        {
            "user": ["u1", "u1", "u2"],
            "when": [
                "2026-01-01 10:00:00",
                "2026-01-01 11:00:00",
                "2026-01-01 10:00:00",
            ],
            "channel": ["Paid > Search", "Email", "Paid > Search"],
            "converted": [False, True, True],
        }
    )
    m = MAM(
        df,
        "session",
        "channel",
        "converted",
        datetime_colname="when",
        user_id_colname="user",
    )
    result = m.run_shapley()
    credit = per_channel(result.to_polars())
    assert set(credit) == {"Paid > Search", "Email"}
    assert sum(credit.values()) == pytest.approx(2.0)


@pytest.mark.parametrize("name", ["A\x1fB", "1:A1:B", "A:B"])
def test_channel_name_never_collides_with_a_set_of_channels(name):
    # One channel whose name looks like the set {A, B} must stay its own set.
    rows = [(name, True, 0), ("A > B", True, 0), ("A", True, 0)]
    result = journeys(rows, revenue=False).run_shapley()
    assert per_channel(result.to_polars()) == {name: 1.0, "A": 2.0, "B": 0.0}
    assert result.to_raw_polars()["attribution_value"].sum() == pytest.approx(3.0)


def test_conversion_table_schema():
    result = journeys(WALKTHROUGH).run_shapley()
    table = result.metadata["conv_table"]
    assert table.columns == [
        "combinations",
        "conversions",
        "total_sequences",
        "conv_rate",
        "conversion_value",
        "attribution",
    ]
    assert table.schema["attribution"] == pl.List(pl.Float64)
    assert table["combinations"].to_list() == ["A", "A > C > D", "B"]
    assert result.metadata["model_name"] == "shapley_size4_conv_rate"


def test_twelve_channels_are_fast_enough():
    import time

    path = " > ".join(f"ch{i:02d}" for i in range(12))
    rows = [(path, True, 1)] + [(f"ch{i:02d}", True, 1) for i in range(12)]
    start = time.perf_counter()
    result = journeys(rows).run_shapley(max_size=12)
    assert time.perf_counter() - start < 5.0
    assert result.to_polars()["attribution"].sum() == pytest.approx(13.0)
    assert math.isfinite(result.to_polars()["attribution"].sum())


@pytest.mark.filterwarnings("ignore::UserWarning")
@pytest.mark.parametrize("max_size", [None, 21])
def test_too_many_channels_stops_with_a_clear_error(max_size):
    path = " > ".join(f"ch{i:02d}" for i in range(21))
    with pytest.raises(ValueError, match="max_size"):
        journeys([(path, True, 1)]).run_shapley(max_size=max_size)


def test_long_journey_is_fine_with_a_small_max_size():
    path = " > ".join(f"ch{i:02d}" for i in range(20))
    result = journeys([(path, True, 1)]).run_shapley(max_size=5)
    assert result.to_polars()["attribution"].sum() == pytest.approx(1.0)


def test_total_sequences_values_sets_that_never_converted():
    # {A}: 10 journeys, none convert; {B}: 10, 5 convert; {A, B}: 10, 2 convert.
    # With total_sequences every set is worth 10, so A and B split {A, B} 50/50.
    rows = (
        [("A", False, 0)] * 10
        + [("B", True, 1)] * 5
        + [("B", False, 0)] * 5
        + [("A > B", True, 1)] * 2
        + [("A > B", False, 0)] * 8
    )
    result = journeys(rows, revenue=False).run_shapley(value_column="total_sequences")
    table = result.metadata["conv_table"]
    row = table.filter(pl.col("combinations") == "A > B")
    assert row["attribution"].to_list() == [pytest.approx([1.0, 1.0])]
    assert per_channel(result.to_polars()) == {"A": 1.0, "B": 6.0}
