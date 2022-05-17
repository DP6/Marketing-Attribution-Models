from typing import List, Dict, Any, Callable
import pytest

import pandas as pd
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
    .assign(session_id=_df.session_id.astype("str"))
)


@pytest.fixture
def model_fixture() -> MAM:
    """Fixture to create a model."""

    def factory(attribution_window=30) -> MAM:
        return MAM(
            df,
            attribution_window=attribution_window,
            channels_colname="source_medium",
            group_channels=True,
            group_channels_by_id_list=["user_pseudo_id"],
            group_timestamp_colname="event_time",
            journey_with_conv_colname="is_conversion",
            create_journey_id_based_on_conversion=True,
        )

    return factory
