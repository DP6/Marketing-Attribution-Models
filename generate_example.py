import polars as pl
import numpy as np
from mam.core import MAM

np.random.seed(42)

# Generate 2000 converting journeys
num_conversions = 2000
num_non_conversions = 1000  # Total 3000 journeys

# Revenue values and their probabilities (smaller values are more frequent)
revenue_values = [10, 25, 50, 75, 100]
probabilities = [0.45, 0.25, 0.15, 0.10, 0.05]

# Sample revenues
revenues = np.random.choice(revenue_values, size=num_conversions, p=probabilities)

# Sample channels
channels_pool = ["google_ads", "facebook_ads", "organic_search", "email", "direct"]

data = []

# Generate converting journeys
for i in range(num_conversions):
    # Length of journey: minimum 1, some reaching up to 15
    path_len = int(
        np.random.choice(
            range(1, 16),
            p=[
                0.15,
                0.15,
                0.12,
                0.10,
                0.10,
                0.08,
                0.07,
                0.06,
                0.05,
                0.04,
                0.03,
                0.02,
                0.015,
                0.01,
                0.005,
            ],
        )
    )

    path_channels = np.random.choice(channels_pool, size=path_len, replace=True)
    journey_str = " > ".join(path_channels)

    # Generate time offsets decreasing down to 0.0
    if path_len > 1:
        times_list = sorted(
            [float(np.random.randint(1, 350)) for _ in range(path_len - 1)],
            reverse=True,
        )
        times_list.append(0.0)
    else:
        times_list = [0.0]

    times_str = " > ".join([f"{t:.1f}" for t in times_list])

    data.append(
        {
            "journey_id": f"user_conv_{i}",
            "journey": journey_str,
            "has_conversion": True,
            "time_till_end": times_str,
            "revenue": float(revenues[i]),
        }
    )

# Generate non-converting journeys
for i in range(num_non_conversions):
    path_len = int(
        np.random.choice(
            range(1, 11), p=[0.20, 0.20, 0.15, 0.15, 0.10, 0.08, 0.05, 0.04, 0.02, 0.01]
        )
    )

    path_channels = np.random.choice(channels_pool, size=path_len, replace=True)
    journey_str = " > ".join(path_channels)

    # Generate times till end (strictly descending)
    times_list = sorted(
        [float(np.random.randint(1, 350)) for _ in range(path_len)], reverse=True
    )
    times_str = " > ".join([f"{t:.1f}" for t in times_list])

    data.append(
        {
            "journey_id": f"user_non_conv_{i}",
            "journey": journey_str,
            "has_conversion": False,
            "time_till_end": times_str,
            "revenue": 0.0,
        }
    )

df = pl.DataFrame(data)

# Initialize MAM
mam = MAM(
    df=df,
    format_type="journey",
    channels_colname="journey",
    journey_with_conv_colname="has_conversion",
    user_id_colname="journey_id",
    time_till_conv_colname="time_till_end",
    conversion_value_colname="revenue",
)

# Run models and generate report
report_data = mam.generate_report(
    models=["markov", "first_click", "last_click"],
    output_html_path="example_report.html",
    output_json_path="example_report_raw_data.json",
)

# Summarize and print total values to console
print(f"Total Conversions: {num_conversions}")
print(f"Total Revenue Generated: {sum(revenues)}")
for m in ["markov", "first_click", "last_click"]:
    print(
        f"Model {m} Attributed Sum: {sum(report_data['attribution_results'][m]['attributions'])}"
    )
