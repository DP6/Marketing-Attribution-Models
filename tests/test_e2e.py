import os
import json
import polars as pl
from mam.core import MAM
from mam.analysis import JAToolbox


def test_e2e_analyst_workflow(tmp_path):
    """
    Simula o fluxo de trabalho real e completo de um analista (Fase 6 E2E):
    1. Ingestão e Pré-processamento de dados brutos (Sessões - Formato 1).
    2. Análise exploratória de jornadas (EDA) com JAToolbox.
    3. Execução de múltiplos modelos de atribuição (Heurísticos e Algorítmicos).
    4. Geração do relatório executivo interativo em HTML e exportação de dados estruturados para BI.
    """
    # 1. SETUP DE DADOS SINTÉTICOS (Formato 1: Sessões/Touchpoints Individuais)
    # 4 usuários, múltiplos touchpoints ao longo do tempo, gerando conversões reais e jornadas ricas.
    raw_data = pl.DataFrame(
        {
            "datetime": [
                "2026-06-01 09:00:00",
                "2026-06-01 10:00:00",  # User 1: Direct -> Google -> Conv
                "2026-06-02 11:00:00",
                "2026-06-02 12:00:00",
                "2026-06-02 13:00:00",  # User 2: Meta -> Email -> Direct -> Conv
                "2026-06-03 14:00:00",
                "2026-06-03 15:00:00",  # User 3: Direct -> Meta -> No Conv
                "2026-06-04 16:00:00",  # User 4: Organic -> Conv
            ],
            "user_id": ["u1", "u1", "u2", "u2", "u2", "u3", "u3", "u4"],
            "channel": [
                "Direct",
                "Google_Search",
                "Meta_Ads",
                "Email",
                "Direct",
                "Direct",
                "Meta_Ads",
                "Organic_Search",
            ],
            "has_conversion": [False, True, False, False, True, False, False, True],
        }
    ).with_columns(pl.col("datetime").str.to_datetime())

    # 2. INGESTÃO E PRÉ-PROCESSAMENTO
    # Instancia o orchestrador central MAM com criação dinâmica de journey_id com base nas marcas de conversão
    mam = MAM(
        df=raw_data,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
        create_journey_id_based_on_conversion=True,
    )

    # Verifica se os dados unificados foram criados com sucesso
    unified = mam.unified_df
    assert "journey_id" in unified.columns
    assert "channels" in unified.columns
    assert "has_conversion" in unified.columns
    assert "time_till_conv" in unified.columns
    assert "weight" in unified.columns

    # 3. ANÁLISE EXPLORATÓRIA DE JORNADAS (EDA VIA JATOOLBOX)
    # Simula o analista extraindo insights exploratórios rápidos usando os métodos de JAToolbox otimizados em Polars
    ja = JAToolbox()

    # Tamanho das jornadas
    journey_sizes = ja.get_size(df=unified, channels_col="channels")
    assert sorted(journey_sizes.to_list()) == [1, 2, 2, 3]

    # Transições de canal
    transitions_df = ja.get_transitions(df=unified, channels_col="channels")
    assert "orig_list" in transitions_df.columns
    assert "dest_list" in transitions_df.columns
    assert "count" in transitions_df.columns

    # 4. EXECUÇÃO DE MÚLTIPLOS MODELOS
    # Executa Last Click, Linear, Markov e Shapley
    result_last = mam.run_last_click()
    result_linear = mam.run_linear()
    result_markov = mam.run_markov()
    result_shapley = mam.run_shapley()

    # Validações dos retornos
    df_last = result_last.to_polars()
    df_linear = result_linear.to_polars()
    df_markov = result_markov.to_polars()
    df_shapley = result_shapley.to_polars()

    assert df_last["attribution"].sum() == 3.0  # u1 (1 conv), u2 (1 conv), u4 (1 conv)
    assert df_linear["attribution"].sum() == 3.0
    assert abs(df_markov["attribution"].sum() - 3.0) < 1e-5
    assert abs(df_shapley["attribution"].sum() - 3.0) < 1e-5

    # 5. REPORTING E EXPORTAÇÃO
    # Define os caminhos de saída no diretório temporário do teste
    output_html = os.path.join(tmp_path, "executive_dashboard.html")
    output_json = os.path.join(tmp_path, "bi_raw_data.json")

    # Gera o relatório executivo completo
    mam.generate_report(
        models=["last_click", "linear", "markov", "shapley"],
        output_html_path=output_html,
        output_json_path=output_json,
    )

    # 6. VERIFICAÇÕES DE SAÍDA E SUCESSO DE ARQUIVOS
    assert os.path.exists(output_html)
    assert os.path.exists(output_json)

    # Lê o JSON exportado para garantir consistência estrutural
    with open(output_json, "r", encoding="utf-8") as f:
        export_data = json.load(f)

    assert "metadata" in export_data
    assert "journey_statistics" in export_data
    assert "attribution_results" in export_data
    assert "markov_specific_results" in export_data

    # Garante que os números batem
    assert export_data["metadata"]["total_journeys"] == 4
    assert export_data["metadata"]["total_conversions"] == 3

    # Verifica o HTML para certificar que as seções principais foram incluídas
    with open(output_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert "Relatório Executivo de Jornadas e Atribuição" in html_content
    assert "Análise de Pontos de Contato" in html_content
    assert "Resultados dos Modelos de Atribuição" in html_content
    assert "Insights Detalhados do Modelo de Markov" in html_content
