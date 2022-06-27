from typing import Tuple, Any

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal, assert_frame_equal


def test_last_click_multiple_conversions(model_fixture_multiple_conversions):
    model = model_fixture_multiple_conversions()
    result: pd.Series = model.attribution_last_click()[0]
    assert result.equals(
        pd.Series(
            {
                0: [0, 0, 1],
                1: [0, 0],
                2: [0, 0, 1],
                3: [0, 0, 1],
                4: [0, 0, 0, 1],
                5: [0, 0, 2],
            }
        )
    )


def test_first_click_multiple_conversions(model_fixture_multiple_conversions):
    model = model_fixture_multiple_conversions()
    result: pd.Series = model.attribution_first_click()[0]
    assert result.equals(
        pd.Series(
            {
                0: [1, 0, 0],
                1: [0, 0],
                2: [1, 0, 0],
                3: [1, 0, 0],
                4: [1, 0, 0, 0],
                5: [2, 0, 0],
            }
        )
    )


def test_last_click_non_direct_multiple_conversions(model_fixture_multiple_conversions):
    model = model_fixture_multiple_conversions()
    result: pd.Series = model.attribution_last_click_non(but_not_this_channel="direct")[
        0
    ]
    assert result.equals(
        pd.Series(
            {
                0: [0, 1, 0],
                1: [0, 0],
                2: [0, 1, 0],
                3: [1, 0, 0],
                4: [0, 0, 1, 0],
                5: [0, 2, 0],
            }
        )
    )


def test_linear_multiple_conversions(model_fixture_multiple_conversions):
    result: pd.Series = model_fixture_multiple_conversions().attribution_linear()[0]
    assert result.equals(
        pd.Series(
            {
                0: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                1: [0.0, 0.0],
                2: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                3: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                4: [0.25, 0.25, 0.25, 0.25],
                5: [0.6666666666666666, 0.6666666666666666, 0.6666666666666666],
            }
        )
    )


def test_time_decay_multiple_conversions(model_fixture_multiple_conversions):
    model = model_fixture_multiple_conversions()
    result: pd.Series = model.attribution_time_decay()[0]
    assert_series_equal(
        result,
        pd.Series(
            {
                0: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                1: [np.nan, np.nan],
                2: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                3: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                4: [
                    0.010309278350515464,
                    0.32989690721649484,
                    0.32989690721649484,
                    0.32989690721649484,
                ],
                5: [0.6666666666666666, 0.6666666666666666, 0.6666666666666666],
            }
        ),
    )


def test_markov_transition_matrix_multiple_conversions(
    model_fixture_multiple_conversions,
):
    model = model_fixture_multiple_conversions()
    result: Tuple[Any] = model.attribution_markov(
        transition_to_same_state=True, conversion_value_type="integer"
    )
    assert_frame_equal(
        result[2],
        pd.DataFrame.from_dict(
            {
                "(inicio)": {
                    "(inicio)": 0.0,
                    "crm": 0.0,
                    "direct": 0.0,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 0.0,
                    "(conversion)": 0.0,
                },
                "crm": {
                    "(inicio)": 0.0,
                    "crm": 0.0,
                    "direct": 0.21428571428571427,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 0.0,
                    "(conversion)": 0.0,
                },
                "direct": {
                    "(inicio)": 0.7142857142857143,
                    "crm": 1.0,
                    "direct": 0.14285714285714285,
                    "google_ads": 1.0,
                    "seo": 1.0,
                    "(null)": 0.0,
                    "(conversion)": 0.0,
                },
                "google_ads": {
                    "(inicio)": 0.0,
                    "crm": 0.0,
                    "direct": 0.07142857142857142,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 0.0,
                    "(conversion)": 0.0,
                },
                "seo": {
                    "(inicio)": 0.2857142857142857,
                    "crm": 0.0,
                    "direct": 0.07142857142857142,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 0.0,
                    "(conversion)": 0.0,
                },
                "(null)": {
                    "(inicio)": 0.0,
                    "crm": 0.0,
                    "direct": 0.07142857142857142,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 1.0,
                    "(conversion)": 0.0,
                },
                "(conversion)": {
                    "(inicio)": 0.0,
                    "crm": 0.0,
                    "direct": 0.42857142857142855,
                    "google_ads": 0.0,
                    "seo": 0.0,
                    "(null)": 0.0,
                    "(conversion)": 1.0,
                },
            }
        ),
        check_like=True,
    )


def test_markov_removal_effect_matrix_multiple_conversion(
    model_fixture_multiple_conversions,
):
    model = model_fixture_multiple_conversions()
    result: Tuple[Any] = model.attribution_markov(
        transition_to_same_state=True, conversion_value_type="integer"
    )
    assert_frame_equal(
        result[3],
        pd.DataFrame.from_dict(
            data={
                "removal_effect": {
                    "crm": 0.30,
                    "google_ads": 0.125,
                    "seo": 0.375,
                    "direct": 1.0,
                }
            }
        ),
        check_like=True,
    )
