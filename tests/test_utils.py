import pytest
from typing import Tuple, Any


def test_load_sample_dataframe(load_sample_dataframe_fixture):
    df = load_sample_dataframe_fixture()
    assert df.shape[0] == 16
    assert df.columns == [
        "user_pseudo_id",
        "session_id",
        "event_time",
        "user_id",
        "is_conversion",
        "source_medium",
    ]


def test_generate_sample_dataframe(generate_sample_dataframe_fixture):
    df = generate_sample_dataframe_fixture()
    assert df.user_pseudo_id.nunique() == 1000000
