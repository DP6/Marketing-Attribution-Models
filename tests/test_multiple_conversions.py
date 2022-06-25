import numpy as np
import pandas as pd


def test_last_click(model_fixture_multiple_conversions):
    model = model_fixture_multiple_conversions()
    result: pd.Series = model.attribution_last_click()[0]
    assert result.equals(
        pd.Series(
            {0: [0, 0, 1], 1: [0, 0], 2: [0, 0, 1], 3: [0, 0, 1], 4: [0, 0, 0, 1], 5: [0,0,2]}
        )
    )
