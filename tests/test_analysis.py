import pytest
import polars as pl
from mam.core import MAM
from mam.analysis import JAToolbox


@pytest.fixture
def preprocessed_df(small_format_2_df):
    mam_instance = MAM(
        df=small_format_2_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        time_till_conv_colname="time_till_end"
    )
    return mam_instance.unified_df


def test_jatoolbox_get_size(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    sizes = jt.get_size()
    assert isinstance(sizes, pl.Series)
    assert sizes.to_list() == [3, 2, 2]


def test_jatoolbox_get_first_and_last_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    firsts = jt.get_first_tp()
    lasts = jt.get_last_tp()
    assert firsts.to_list() == ["direct", "meta_ads", "email"]
    assert lasts.to_list() == ["meta_ads", "direct", "organic_search"]


def test_jatoolbox_get_nth_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    
    # Índice 1 é válido para todas as jornadas (tamanho >= 2)
    n1 = jt.get_nth_tp(1)
    assert n1.to_list() == ["google_search", "direct", "organic_search"]

    # Índice 2 está fora de alcance para as jornadas 2 e 3 (tamanho 2)
    with pytest.raises(ValueError, match="out of range"):
        jt.get_nth_tp(2)

    # Com last_if_out=True deve retornar o último elemento se estiver fora de alcance
    n2_last = jt.get_nth_tp(2, last_if_out=True)
    assert n2_last.to_list() == ["meta_ads", "direct", "organic_search"]


def test_jatoolbox_get_intermediate_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    sub = jt.get_intermediate_tp((0, 2))
    assert sub.to_list() == [["direct", "google_search"], ["meta_ads", "direct"], ["email", "organic_search"]]


def test_jatoolbox_get_tps_counts(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    counts = jt.get_tps_counts()
    
    assert isinstance(counts, pl.DataFrame)
    # total de ocorrências de cada canal (todas as jornadas têm peso 1):
    # direct: 2, meta_ads: 2, google_search: 1, email: 1, organic_search: 1
    res_dict = dict(zip(counts["channels"], counts["count"]))
    assert res_dict["direct"] == 2
    assert res_dict["meta_ads"] == 2
    assert res_dict["google_search"] == 1


def test_jatoolbox_skip_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    skipped_df = jt.skip_tp("direct")
    
    # A primeira jornada ['direct', 'google_search', 'meta_ads'] deve virar ['google_search', 'meta_ads']
    # A segunda ['meta_ads', 'direct'] deve virar ['meta_ads']
    # A terceira ['email', 'organic_search'] deve continuar idêntica
    channels_list = skipped_df["channels"].to_list()
    assert channels_list[0] == ["google_search", "meta_ads"]
    assert channels_list[1] == ["meta_ads"]
    assert channels_list[2] == ["email", "organic_search"]


def test_jatoolbox_skip_tp_group(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    skipped_df = jt.skip_tp_group(["direct", "meta_ads"])
    
    channels_list = skipped_df["channels"].to_list()
    assert channels_list[0] == ["google_search"]
    assert channels_list[1] == []
    assert channels_list[2] == ["email", "organic_search"]


def test_jatoolbox_check_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    has_direct = jt.check_tp("direct")
    assert has_direct.to_list() == [True, True, False]


def test_jatoolbox_check_tp_group(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    checks = jt.check_tp_group(["direct", "email"])
    
    assert isinstance(checks, pl.DataFrame)
    assert checks["direct"].to_list() == [True, True, False]
    assert checks["email"].to_list() == [False, False, True]


def test_jatoolbox_get_tp_counts(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    direct_counts = jt.get_tp_counts("direct")
    assert direct_counts.to_list() == [1, 1, 0]


def test_jatoolbox_get_duration(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    duration = jt.get_duration((0, -1))
    assert duration.to_list() == [2.0, 1.0, 1.0]


def test_jatoolbox_translate_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    translated_df = jt.translate_tp({"direct": "DIR", "meta_ads": "FB"})
    
    channels_list = translated_df["channels"].to_list()
    assert channels_list[0] == ["DIR", "google_search", "FB"]
    assert channels_list[1] == ["FB", "DIR"]


def test_jatoolbox_get_transitions(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    transitions = jt.get_transitions()
    
    assert isinstance(transitions, pl.DataFrame)
    # Transições presentes:
    # direct -> google_search (1)
    # google_search -> meta_ads (1)
    # meta_ads -> direct (1)
    # email -> organic_search (1)
    assert transitions.height == 4
    for row in transitions.iter_rows(named=True):
        assert row["count"] == 1


def test_jatoolbox_channels_by_tp(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    stages = jt.channels_by_tp(3)
    
    assert isinstance(stages, pl.DataFrame)
    assert "channels" in stages.columns
    assert "tp_1" in stages.columns
    assert "tp_2" in stages.columns
    assert "tp_3" in stages.columns


def test_jatoolbox_tps_by_channel(preprocessed_df):
    jt = JAToolbox(df=preprocessed_df)
    by_channel = jt.tps_by_channel()
    
    assert isinstance(by_channel, pl.DataFrame)
    assert "Channel" in by_channel.columns
    assert "Count" in by_channel.columns


def test_jatoolbox_with_pandas_df():
    # Cria um DataFrame do Pandas já com listas de canais
    import pandas as pd
    pandas_df = pd.DataFrame({
        "channels": [["direct", "google_search", "meta_ads"], ["meta_ads", "direct"], ["email", "organic_search"]],
        "time_till_conv": [[2.0, 1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
        "weight": [1, 1, 1]
    })
    
    # Testa instanciação direta com Pandas
    jt = JAToolbox(df=pandas_df, channels_col="channels")
    assert isinstance(jt.df, pl.DataFrame)
    
    # Testa operações simples
    sizes = jt.get_size()
    assert sizes.to_list() == [3, 2, 2]


def test_jatoolbox_internal_preprocessing(small_format_2_df):
    # Instancia JAToolbox com dados brutos do formato 2 e ativa pré-processamento automático
    jt = JAToolbox(
        df=small_format_2_df,
        format_type="journey",
        channels_col="journey",
        journey_with_conv_colname="has_conversion",
        time_till_conv_colname="time_till_end"
    )
    
    # No formato unificado, as colunas padrão passam a ser configuradas
    assert jt.channels_col == "channels"
    assert jt.time_col == "time_till_conv"
    assert jt.weight_col == "weight"
    
    sizes = jt.get_size()
    assert sizes.to_list() == [3, 2, 2]


def test_mam_property_jatoolbox(small_format_2_df):
    # Instancia MAM normalmente
    mam = MAM(
        df=small_format_2_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        time_till_conv_colname="time_till_end"
    )
    
    # Acessa a JAToolbox pela propriedade exposta no MAM
    jt = mam.jatoolbox
    assert isinstance(jt, JAToolbox)
    
    sizes = jt.get_size()
    assert sizes.to_list() == [3, 2, 2]
