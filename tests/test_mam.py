import pandas as pd
from marketing_attribution_models import MAM



#####################
## Setup Variables ##
#####################

CONV_VALUE = 3
DF_AGG = pd.DataFrame(
    {
        "channels_agg": [
            "A",
            "A > B",
            "A > B > C",
            "B",
            "B > A",
            "B > C > A",
            "C",
            "C > A",
            "C > B > A",
        ],
        "conversion_value": [CONV_VALUE for i in range(9)],
    }
)
ATT = MAM(DF_AGG, conversion_value="conversion_value", channels_colname="channels_agg")

ATT.attribution_first_click()
ATT.attribution_last_click()
ATT.attribution_last_click_non("A")
ATT.attribution_linear()
ATT.attribution_position_based()
ATT.attribution_time_decay(decay_over_time=0.5, frequency=1)
ATT.attribution_markov()
ATT.attribution_shapley()
DF_JOURNEY = ATT.as_pd_dataframe()


###########
## Tests ##
###########


def test_as_pd_dataframe_len():
    """
    Test function that will check if the len returned
    on self.as_pd_dataframe() results will be the same
    len as the number of channels
    """

    results = []  # Results variable
    df_journey_test = DF_JOURNEY.copy()
    df_journey_test["size"] = (
        df_journey_test["channels_agg"].str.split(" > ").apply(len)
    )

    # For loop on model results columns
    column_list = [
        col
        for col in df_journey_test.columns
        if col not in ["channels_agg", "converted_agg", "conversion_value", "size"]
    ]
    for col in column_list:
        df_journey_test[col] = df_journey_test[col].str.split(" > ").apply(len)
        results.append(all((df_journey_test[col] == df_journey_test["size"]).values))
    assert all(results)


def test_agg_results():
    """
    Test function that will check if the sum of
    the model results are the same as the total
    of conversions present when creating the MAM
    object.
    """

    res_value = DF_AGG["conversion_value"].sum()
    model_results_df = ATT.group_by_channels_models
    model_results_df = model_results_df[
        [col for col in model_results_df.columns if col != "channels"]
    ]
    assert all((model_results_df.sum().round() == res_value).values)


def test_att_first():
    """
    Test function to validate the first click method
    results.
    """

    colname = "attribution_first_click_heuristic"
    df_journey_test = DF_JOURNEY.copy()
    assert all(
        df_journey_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[0]) == CONV_VALUE)
        .values
    )


def test_att_last():
    """
    Test function to validate the last click method
    results.
    """

    colname = "attribution_last_click_heuristic"
    df_journey_test = DF_JOURNEY.copy()
    assert all(
        df_journey_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[-1]) == CONV_VALUE)
        .values
    )


def test_att_last_non():
    """
    Test function to validate the last click non method
    results.
    """

    colname = "attribution_last_click_non_A_heuristic"
    df_journey_test = DF_JOURNEY.copy()
    non_list = ["B > C > A", "C > A", "C > B > A"]
    df_journey_test = df_journey_test[
        df_journey_test["channels_agg"].apply(lambda x: x in non_list)
    ]
    assert all(
        df_journey_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[-1]) == 0)
        .values
    )


def test_att_linear():
    """
    Test function to validate the linear method
    results.
    """

    colname = "attribution_linear_heuristic"
    df_journey_test = DF_JOURNEY.copy()
    assert all(
        df_journey_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[0]) == (CONV_VALUE / len(x)))
        .values
    )


def test_att_position_based():
    """
    Test function to validate the position based method
    results.
    """

    colname = "attribution_position_based_0.4_0.2_0.4_heuristic"
    df_journey_test = DF_JOURNEY.copy()
    df_test = df_journey_test[
        df_journey_test["channels_agg"].apply(lambda x: len(x) == 3)
    ]
    assert all(
        df_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[0]) == (CONV_VALUE * 0.4))
        .values
    )
    df_test = df_journey_test[
        df_journey_test["channels_agg"].apply(lambda x: len(x) == 2)
    ]
    assert all(
        df_test[colname]
        .str.split(" > ")
        .apply(lambda x: float(x[0]) == (CONV_VALUE * 0.5))
        .values
    )


print(DF_JOURNEY)
# def test_att_time():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'


# def test_att_markov():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'


# def test_att_shapley():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'
