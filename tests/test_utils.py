import pytest
from typing import Tuple, Any

from tests.utils import load_sample_dataframe, generate_sample_dataframe


def test_load_sample_dataframe():
    df = load_sample_dataframe()
    assert df.shape[0] == 16
    assert list(df.columns) == [
        "user_pseudo_id",
        "session_id",
        "event_time",
        "user_id",
        "is_conversion_purchase",
        "source_medium",
    ]


def test_generate_sample_dataframe():
    N = 10000
    df = generate_sample_dataframe(N)
    assert df.user_pseudo_id.nunique() == N
