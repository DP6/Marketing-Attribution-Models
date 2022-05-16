import pytest

import pandas as pd
import numpy as np

from marketing_attribution_models import MAM

_df = None


def get_intermediate(df):
    global _df
    _df = df
    return df


df = (
    pd.read_csv("data/test_dataset.csv")
    .pipe(get_intermediate)
    .assign(event_time=pd.to_datetime(_df.event_time))
    .assign(is_conversion=_df.is_conversion.astype("bool"))
)

model = MAM(
    df,
    attribution_window=30,
    channels_colname="source_medium",
    group_channels=True,
    group_channels_by_id_list=["user_pseudo_id"],
    group_timestamp_colname="event_time",
    journey_with_conv_colname="is_conversion",
    create_journey_id_based_on_conversion=True,
)


def test_dataframe_formation(model=model):
    """
    Checa algumas entradas no dataframe formado pelo modelo.
    """
    df_example: pd.DataFrame = model.as_pd_dataframe().query("journey_id == 'id:A_J:0'")
    assert df_example.channels_agg.equals(
        pd.Series({0: "direct > google_ads > direct"})
    )


def test_first_click(model=model):
    result: pd.Series = model.attribution_first_click()[0]
    assert result.equals(
        {0: [1, 0, 0], 1: [0, 0], 2: [1, 0, 0], 3: [1, 0, 0], 4: [1, 0, 0]}
    )
