from marketing_attribution_models import MAM
import pandas as pd 
import pytest

att = None
df_agg = None
conv_value = None
df_journey = None

def setup_module(module):
    global df_agg, att, conv_value, df_journey
    conv_value = 3
    df_agg = pd.DataFrame(
                    {'channels_agg': ["A", "A > B",
                                        "A > B > C", "B",
                                        "B > A","B > C > A",
                                        "C","C > A",
                                        "C > B > A"],
                    'conversion_value': [conv_value for i in range(9)]})
    att = MAM(df_agg, 
                conversion_value='conversion_value', 
                channels_colname='channels_agg')
    
    att.attribution_first_click()
    att.attribution_last_click()
    att.attribution_last_click_non('A')
    att.attribution_linear()
    att.attribution_position_based()
    att.attribution_time_decay(decay_over_time=0.5, frequency=1)
    att.attribution_markov()
    att.attribution_shapley()
    df_journey = att.as_pd_dataframe()


def test_journey_results():
    results = []
    df_journey_test = df_journey.copy()
    df_journey_test['size'] = df_journey_test[ 'channels_agg'].str.split(' > ').apply(len)
    for col in [col for col in df_journey_test.columns if col not in ['channels_agg', 'converted_agg', 'conversion_value', 'size']]:
        df_journey_test[col] = df_journey_test[ col].str.split(' > ').apply(len)
        results.append(all((df_journey_test[ col] == df_journey_test[ 'size']).values))
    assert all(results)


def test_agg_results():
    res_value = df_agg['conversion_value'].sum()
    model_results_df = att.group_by_channels_models
    model_results_df = model_results_df[[col for col in model_results_df.columns if col != 'channels']]
    assert all((model_results_df.sum().round() == res_value).values)

def test_att_first():
    colname = 'attribution_first_click_heuristic'
    df_journey_test = df_journey.copy()
    assert all(df_journey_test[ colname].str.split(' > ').apply(lambda x: float(x[0]) == conv_value).values)


def test_att_last():
    colname = 'attribution_last_click_heuristic'
    df_journey_test = df_journey.copy()
    assert all(df_journey_test[ colname].str.split(' > ').apply(lambda x: float(x[-1]) == conv_value).values)


def test_att_last_non():
    colname = 'attribution_last_click_non_A_heuristic'
    df_journey_test = df_journey.copy()
    non_list = ['B > C > A', 'C > A', 'C > B > A']
    df_journey_test = df_journey_test[ df_journey_test[ 'channels_agg'].apply(lambda x: x in non_list)]
    assert all(df_journey_test[colname].str.split(' > ').apply(lambda x: float(x[-1]) == 0).values)


def test_att_linear():
    colname = 'attribution_linear_heuristic'
    df_journey_test = df_journey.copy()
    assert all(df_journey_test[ colname].str.split(' > ').apply(lambda x: float(x[0]) == (conv_value / len(x))).values)


def test_att_position_based():
    colname = 'attribution_position_based_0.4_0.2_0.4_heuristic'
    df_journey_test = df_journey.copy()
    df_test = df_journey_test[ df_journey_test[ 'channels_agg'].apply(lambda x: len(x) == 3)]
    assert all(df_test[colname].str.split(' > ').apply(lambda x: float(x[0]) == (conv_value * 0.4)).values)
    df_test = df_journey_test[ df_journey_test[ 'channels_agg'].apply(lambda x: len(x) == 2)]
    assert all(df_test[colname].str.split(' > ').apply(lambda x: float(x[0]) == (conv_value * 0.5)).values)


# def test_att_time():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'


# def test_att_markov():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'


# def test_att_shapley():
#     colname = 'attribution_time_decay0.5_freq1_heuristic'

if __name__ == '__main__':
    setup_module(None)
    print(df_journey)
    colname = 'attribution_first_click_heuristic'
    df_journey_test = df_journey.copy()
    print(df_journey_test[ colname].str.split(' > ').apply(lambda x: float(x[0])).values)
    print(all(df_journey_test[ colname].str.split(' > ').apply(lambda x: float(x[0]) == conv_value).values))