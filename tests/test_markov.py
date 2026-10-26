import polars as pl
import pandas as pd
from mam.core import MAM
from mam.results import AttributionResult
from mam.models.markov import MarkovModel


def test_markov_format_2(small_format_2_df):
    mam_instance = MAM(
        df=small_format_2_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_markov(transition_to_same_state=False)

    # Verificar se o retorno é um AttributionResult
    assert isinstance(result, AttributionResult)

    # DataFrame agregado
    agg_df = result.to_polars()
    assert isinstance(agg_df, pl.DataFrame)
    assert "channels" in agg_df.columns
    assert "attribution" in agg_df.columns

    # Verificar se a soma das atribuições é igual ao total de conversões
    # No small_format_2_df, user_1_0 (True) e user_3_0 (True) converteram -> total 2 conversões
    total_attributions = agg_df["attribution"].sum()
    assert abs(total_attributions - 2.0) < 1e-5

    # Metadados
    metadata = result.metadata
    assert metadata["model_type"] == "algorithmic"
    assert metadata["model_name"] == "markov"

    # Matriz de Transição
    trans_matrix = metadata["transition_matrix"]
    assert isinstance(trans_matrix, pd.DataFrame)
    assert "(inicio)" in trans_matrix.columns
    assert "(null)" in trans_matrix.columns
    assert "(conversion)" in trans_matrix.columns

    # Estados absorventes devem ter probabilidade 1.0 de transitar para si mesmos
    assert trans_matrix.loc["(null)", "(null)"] == 1.0
    assert trans_matrix.loc["(conversion)", "(conversion)"] == 1.0

    # Efeito de Remoção
    removal_effect = metadata["removal_effect"]
    assert isinstance(removal_effect, pd.DataFrame)
    assert "removal_effect" in removal_effect.columns


def test_markov_format_3(small_format_3_df):
    mam_instance = MAM(
        df=small_format_3_df,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        occurrences_colname="occurrences",
    )
    result = mam_instance.run_markov(transition_to_same_state=False)
    agg_df = result.to_polars()

    # No small_format_3_df:
    # direct > google_search > meta_ads (True, 120 occurrences) -> 120 conv
    # email > organic_search (True, 80 occurrences) -> 80 conv
    # Total conv = 200
    assert abs(agg_df["attribution"].sum() - 200.0) < 1e-5


def test_markov_transition_to_same_state(small_format_3_df):
    # Testar com transição para o mesmo estado permitida
    mam_instance = MAM(
        df=small_format_3_df,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        occurrences_colname="occurrences",
    )
    result_same = mam_instance.run_markov(transition_to_same_state=True)
    result_no_same = mam_instance.run_markov(transition_to_same_state=False)

    assert (
        result_same.to_polars()["attribution"].sum()
        == result_no_same.to_polars()["attribution"].sum()
    )


def test_markov_transition_counts_format_3():
    # Contagens ponderadas por occurrences, sem auto-transições (Search > Search)
    df = pl.DataFrame(
        {
            "journey": [
                "Search > Direct",
                "Search > Direct",
                "Social > Search > Search > Direct",
                "Display",
                "Display > Social",
            ],
            "has_conversion": [True, False, True, True, False],
            "occurrences": [3, 7, 2, 4, 5],
        }
    )
    mam_instance = MAM(
        df=df,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        occurrences_colname="occurrences",
    )
    matrix, _, names = MarkovModel()._build_transition_matrix(mam_instance.unified_df)
    counts = pd.DataFrame(matrix, index=names, columns=names)

    expected = {
        ("(inicio)", "Display"): 9,
        ("(inicio)", "Search"): 10,
        ("(inicio)", "Social"): 2,
        ("Direct", "(null)"): 7,
        ("Direct", "(conversion)"): 5,
        ("Display", "Social"): 5,
        ("Display", "(conversion)"): 4,
        ("Search", "Direct"): 12,
        ("Social", "Search"): 2,
        ("Social", "(null)"): 5,
        ("(null)", "(null)"): 1,
        ("(conversion)", "(conversion)"): 1,
    }
    for (orig, dest), value in expected.items():
        assert counts.loc[orig, dest] == value
    assert counts.values.sum() == sum(expected.values())
