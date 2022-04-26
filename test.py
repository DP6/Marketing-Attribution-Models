import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from marketing_attribution_models import MAM

pd.set_option("display.float_format", lambda x: "%.3f" % x)
pd.set_option("max_colwidth", None)

df = pd.read_csv("/home/luanfernandes/Downloads/sessions.csv")
df = df.drop(
    columns=[
        "page_referrer",
        "page_location",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
    ]
)
df.event_time = pd.to_datetime(df.event_time)
df.is_conversion = df.is_conversion.astype(bool)
df.user_pseudo_id = df.user_pseudo_id.astype("str")

df.head()

DP_tribution = MAM(
    df,
    attribution_window=30,
    channels_colname="source_medium",
    group_channels=True,
    group_channels_by_id_list=["user_pseudo_id"],
    group_timestamp_colname="event_time",
    journey_with_conv_colname="is_conversion",
    create_journey_id_based_on_conversion=True,
)

DP_tribution.as_pd_dataframe()

DP_tribution.attribution_last_click()
