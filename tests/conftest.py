from typing import List, Dict, Any, Callable
import pytest

from marketing_attribution_models import MAM
from utils import load_sample_dataframe, generate_sample_dataframe


@pytest.fixture
def model_fixture() -> Callable:
    """Fixture to create a model."""

    def factory(attribution_window=30, should_sample=False, **kargs) -> MAM:
        df = load_sample_dataframe()
        if should_sample:
            n = len(df.user_pseudo_id.unique())
            sample_df = generate_sample_dataframe(**kargs)
        else:
            sample_df = df
        return MAM(
            sample_df,
            attribution_window=attribution_window,
            channels_colname="source_medium",
            group_channels=True,
            group_channels_by_id_list=["user_pseudo_id"],
            group_timestamp_colname="event_time",
            journey_with_conv_colname="is_conversion_purchase",
            create_journey_id_based_on_conversion=True,
        )

    return factory
