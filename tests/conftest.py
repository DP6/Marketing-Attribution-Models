import pytest
import polars as pl
import numpy as np
import datetime

# Setup random seed for reproducibility
np.random.seed(42)


@pytest.fixture
def sample_channels():
    return ["direct", "google_search", "meta_ads", "email", "organic_search"]


@pytest.fixture
def small_format_1_df():
    """
    Format 1: Every row is a session / touchpoint.
    datetime | user_id | channel | has_conversion
    """
    data = [
        {
            "datetime": "2026-01-01 01:00:00",
            "user_id": "user_1",
            "channel": "direct",
            "has_conversion": False,
        },
        {
            "datetime": "2026-01-01 02:00:00",
            "user_id": "user_1",
            "channel": "google_search",
            "has_conversion": False,
        },
        {
            "datetime": "2026-01-01 03:00:00",
            "user_id": "user_1",
            "channel": "meta_ads",
            "has_conversion": True,
        },
        {
            "datetime": "2026-01-01 01:30:00",
            "user_id": "user_2",
            "channel": "meta_ads",
            "has_conversion": False,
        },
        {
            "datetime": "2026-01-01 02:30:00",
            "user_id": "user_2",
            "channel": "direct",
            "has_conversion": False,
        },
        {
            "datetime": "2026-01-01 04:00:00",
            "user_id": "user_3",
            "channel": "email",
            "has_conversion": False,
        },
        {
            "datetime": "2026-01-01 05:00:00",
            "user_id": "user_3",
            "channel": "organic_search",
            "has_conversion": True,
        },
    ]
    return pl.DataFrame(data).with_columns(pl.col("datetime").str.to_datetime())


@pytest.fixture
def small_format_2_df():
    """
    Format 2: Every row is a complete user journey.
    start_time | end_time | journey_id | journey | has_conversion | time_till_end
    """
    data = [
        {
            "start_time": "2026-01-01 01:00:00",
            "end_time": "2026-01-01 03:00:00",
            "journey_id": "user_1_0",
            "journey": "direct > google_search > meta_ads",
            "has_conversion": True,
            "time_till_end": "2.0 > 1.0 > 0.0",
        },
        {
            "start_time": "2026-01-01 01:30:00",
            "end_time": "2026-01-01 02:30:00",
            "journey_id": "user_2_0",
            "journey": "meta_ads > direct",
            "has_conversion": False,
            "time_till_end": "1.0 > 0.0",
        },
        {
            "start_time": "2026-01-01 04:00:00",
            "end_time": "2026-01-01 05:00:00",
            "journey_id": "user_3_0",
            "journey": "email > organic_search",
            "has_conversion": True,
            "time_till_end": "1.0 > 0.0",
        },
    ]
    return pl.DataFrame(data).with_columns(
        [
            pl.col("start_time").str.to_datetime(),
            pl.col("end_time").str.to_datetime(),
        ]
    )


@pytest.fixture
def small_format_3_df():
    """
    Format 3: Every row is an aggregated path.
    journey | has_conversion | occurrences
    """
    data = [
        {
            "journey": "direct > google_search > meta_ads",
            "has_conversion": True,
            "occurrences": 120,
        },
        {
            "journey": "direct > google_search > meta_ads",
            "has_conversion": False,
            "occurrences": 300,
        },
        {"journey": "meta_ads > direct", "has_conversion": False, "occurrences": 450},
        {
            "journey": "email > organic_search",
            "has_conversion": True,
            "occurrences": 80,
        },
    ]
    return pl.DataFrame(data)


def generate_bulk_format_1(num_rows: int) -> pl.DataFrame:
    """Generates bulk data in Format 1 (Sessions)."""
    channels = ["direct", "google_search", "meta_ads", "email", "organic_search"]

    # Generate user IDs
    num_users = max(1, num_rows // 4)
    user_pool = [f"user_{i}" for i in range(num_users)]
    user_ids = np.random.choice(user_pool, size=num_rows)

    # Generate random datetimes starting from 2026-01-01
    base_time = datetime.datetime(2026, 1, 1)
    seconds_offsets = np.random.randint(
        0, 30 * 24 * 3600, size=num_rows
    )  # within 30 days
    datetimes = [
        base_time + datetime.timedelta(seconds=int(offset))
        for offset in seconds_offsets
    ]

    # Generate channels
    channel_choices = np.random.choice(channels, size=num_rows)

    # Generate conversion flags
    has_conversion = np.random.choice([True, False], size=num_rows, p=[0.05, 0.95])

    df = pl.DataFrame(
        {
            "datetime": datetimes,
            "user_id": user_ids,
            "channel": channel_choices,
            "has_conversion": has_conversion,
        }
    )

    # Sort chronologically by user and time to mimic real web tracking
    return df.sort(["user_id", "datetime"])


def generate_bulk_format_2(num_journeys: int) -> pl.DataFrame:
    """Generates bulk data in Format 2 (Journeys)."""
    channels = ["direct", "google_search", "meta_ads", "email", "organic_search"]

    base_time = datetime.datetime(2026, 1, 1)

    journey_ids = [f"j_{i}" for i in range(num_journeys)]
    has_conversion = np.random.choice([True, False], size=num_journeys, p=[0.08, 0.92])

    start_times = []
    end_times = []
    journeys = []
    time_till_ends = []

    for i in range(num_journeys):
        path_length = np.random.randint(1, 6)  # journey lengths 1 to 5
        path_channels = np.random.choice(channels, size=path_length)
        journey_str = " > ".join(path_channels)
        journeys.append(journey_str)

        # Generate timeline
        j_start = base_time + datetime.timedelta(
            seconds=int(np.random.randint(0, 30 * 24 * 3600))
        )
        durations = sorted(
            np.random.randint(0, 48 * 3600, size=path_length), reverse=True
        )  # up to 48 hours
        # Convert seconds to hours till end
        time_till_end_str = " > ".join([f"{d / 3600.0:.2f}" for d in durations])
        time_till_ends.append(time_till_end_str)

        j_end = j_start + datetime.timedelta(seconds=int(durations[0]))
        start_times.append(j_start)
        end_times.append(j_end)

    return pl.DataFrame(
        {
            "start_time": start_times,
            "end_time": end_times,
            "journey_id": journey_ids,
            "journey": journeys,
            "has_conversion": has_conversion,
            "time_till_end": time_till_ends,
        }
    )


def generate_bulk_format_3(num_paths: int) -> pl.DataFrame:
    """Generates bulk data in Format 3 (Grouped Journeys)."""
    channels = ["direct", "google_search", "meta_ads", "email", "organic_search"]

    journeys = []
    has_conversions = []
    occurrences = []

    # We want unique paths
    seen_paths = set()
    while len(seen_paths) < num_paths:
        path_length = np.random.randint(1, 6)
        path_channels = np.random.choice(channels, size=path_length)
        journey_str = " > ".join(path_channels)
        conv = bool(np.random.choice([True, False], p=[0.1, 0.9]))

        path_key = (journey_str, conv)
        if path_key not in seen_paths:
            seen_paths.add(path_key)
            journeys.append(journey_str)
            has_conversions.append(conv)
            occurrences.append(int(np.random.randint(1, 1000)))

    return pl.DataFrame(
        {
            "journey": journeys,
            "has_conversion": has_conversions,
            "occurrences": occurrences,
        }
    )


@pytest.fixture
def bulk_data_generator():
    """
    Returns a helper dict of functions to generate larger bulk datasets.
    Can be used by performance and stress tests.
    """
    return {
        "format_1": generate_bulk_format_1,
        "format_2": generate_bulk_format_2,
        "format_3": generate_bulk_format_3,
    }
