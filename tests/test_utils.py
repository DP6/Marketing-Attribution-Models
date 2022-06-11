import pytest
from typing import Tuple, Any

from utils import load_sample_dataframe, generate_sample_dataframe


def test_load_sample_dataframe():
    df = load_sample_dataframe()
    assert df.shape[0] == 16
    assert df.columns == [
        "user_pseudo_id",
        "session_id",
        "event_time",
        "user_id",
        "is_conversion",
        "source_medium",
    ]


def test_generate_sample_dataframe():
    pass
