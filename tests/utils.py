from typing import List, Dict, Any, Callable
import pytest

from random import sample, randrange
import datetime
from datetime import timedelta

import pandas as pd
import numpy as np
from marketing_attribution_models import MAM


_df = None


def get_intermediate(df):
    global _df
    _df = df
    return df


def random_date(start, end) -> datetime.datetime:
    """
    This function will return a random datetime between two datetime
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


def load_sample_dataframe() -> pd.DataFrame:
    return (
        pd.read_csv("data/test_dataset.csv")
        .pipe(get_intermediate)
        .assign(event_time=pd.to_datetime(_df.event_time))
        .assign(is_conversion_purchase=_df.is_conversion_purchase.astype("bool"))
        .assign(session_id=_df.session_id.astype("str"))
    )


def generate_sample_dataframe(
    n_users: int = 10000,
    avg_journey_length: int = 5,
    prob_conversion: float = 0.10,
    conversion_col_name: str = "is_conversion_purchase",
) -> pd.DataFrame:
    """
    Generates a sample dataframe with a given number of users and a given average journey length.
    """
    users = np.linspace(1, n_users, n_users).astype("int")
    data = {
        "user_pseudo_id": [],
        "session_id": [],
        "event_time": [],
        "user_id": [],
        conversion_col_name: [],
        "source_medium": [],
    }
    for user in users:
        journey_length = np.random.normal(avg_journey_length, avg_journey_length / 10)
        for i in range(int(journey_length)):
            data["user_pseudo_id"].append(user)
            data["session_id"].append(np.random.randint(1, n_users * 2))
            if i == 0:
                data["event_time"].append(
                    random_date(
                        datetime.datetime(2022, 1, 1), datetime.datetime(2022, 12, 31)
                    )
                )
            else:
                data["event_time"].append(
                    data["event_time"][-1] + timedelta(days=np.random.randint(1, 7))
                )
            data["user_id"].append(np.random.randint(1, n_users * 2))
            data[conversion_col_name].append(
                False
                if i + 1 < journey_length
                else np.random.choice(
                    [True, False], p=[prob_conversion, 1 - prob_conversion]
                )
            )
            data["source_medium"].append(
                np.random.choice(
                    ["crm", "social", "google_ads", "direct", "afiliados", "seo"]
                )
            )
    return pd.DataFrame.from_dict(data)
