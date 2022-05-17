import pytest

import pandas as pd
from pandas.testing import assert_series_equal
import numpy as np

from marketing_attribution_models import MAM


def test_dataframe_formation_converted(model_fixture):
    """
    Checa algumas entradas no dataframe formado pelo modelo.
    """
    # user A has one session too old, which will be excluded
    model = model_fixture()
    df_example: pd.DataFrame = model.as_pd_dataframe().query("journey_id == 'id:A_J:0'")
    assert df_example.channels_agg.equals(
        pd.Series({0: "direct > google_ads > direct"})
    )
    assert df_example.sessions_agg.equals(pd.Series({0: ["2", "3", "4"]}))
    assert df_example.time_till_conv_agg.equals(pd.Series({0: "2.0 > 1.0 > 0.0"}))
    assert "1" not in model.original_df.session_id.values


def test_dataframe_formation_not_converted(model_fixture):
    """
    Checa algumas entradas no dataframe formado pelo modelo.
    """
    df_not_converted: pd.DataFrame = (
        model_fixture().as_pd_dataframe().query("journey_id == 'id:B_J:0'")
    )
    assert df_not_converted.channels_agg.equals(pd.Series({1: "seo > direct"}))
    assert df_not_converted.sessions_agg.equals(pd.Series({1: ["5", "6"]}))
    assert not df_not_converted.converted_agg.values


def test_first_click(model_fixture):
    result: pd.Series = model_fixture().attribution_first_click()[0]
    assert result.equals(
        pd.Series(
            {0: [1, 0, 0], 1: [0, 0], 2: [1, 0, 0], 3: [1, 0, 0], 4: [1, 0, 0, 0]}
        )
    )


def test_last_click(model_fixture):
    result: pd.Series = model_fixture().attribution_last_click()[0]
    assert result.equals(
        pd.Series(
            {0: [0, 0, 1], 1: [0, 0], 2: [0, 0, 1], 3: [0, 0, 1], 4: [0, 0, 0, 1]}
        )
    )


def test_last_click_non_direct(model_fixture):
    result: pd.Series = model_fixture().attribution_last_click_non(
        but_not_this_channel="direct"
    )[0]
    assert result.equals(
        pd.Series(
            {0: [0, 1, 0], 1: [0, 0], 2: [0, 1, 0], 3: [1, 0, 0], 4: [0, 0, 1, 0]}
        )
    )


def test_linear(model_fixture):
    result: pd.Series = model_fixture().attribution_linear()[0]
    assert result.equals(
        pd.Series(
            {
                0: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                1: [0.0, 0.0],
                2: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                3: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333],
                4: [0.25, 0.25, 0.25, 0.25],
            }
        )
    )


def test_tim_decay(model_fixture):
    model: MAM = model_fixture()
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
            }
        ),
    )
