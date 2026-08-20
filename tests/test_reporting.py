import os
import json
import pytest
import polars as pl
from mam.core import MAM

@pytest.fixture
def format_2_data():
    return pl.DataFrame({
        "journey_id": ["j1", "j2", "j3", "j4"],
        "journey": ["Direct > Google_Search > Meta_Ads", "Direct > Meta_Ads", "Google_Search > Direct", "Meta_Ads"],
        "conversion": [True, True, False, False],
        "time_till_end": ["10 > 5 > 0", "20 > 0", "15 > 0", "0"]
    })

@pytest.fixture
def format_3_data():
    return pl.DataFrame({
        "journey": ["Direct > Google_Search", "Meta_Ads > Direct", "Google_Search"],
        "conversion": [True, False, False],
        "occurrences": [10, 20, 5]
    })

def test_generate_report_with_time(format_2_data, tmp_path):
    # Setup filenames
    output_html = os.path.join(tmp_path, "report.html")
    output_json = os.path.join(tmp_path, "report_data.json")
    
    # Instantiate MAM
    mam_instance = MAM(
        df=format_2_data,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        time_till_conv_colname="time_till_end"
    )
    
    # Generate report running last_click and markov models
    models_to_run = ["last_click", "linear", "markov"]
    mam_instance.generate_report(
        models=models_to_run,
        output_html_path=output_html,
        output_json_path=output_json
    )
    
    # 1. Verify files exist
    assert os.path.exists(output_html)
    assert os.path.exists(output_json)
    
    # 2. Verify JSON structure and keys
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "metadata" in data
    assert data["metadata"]["total_journeys"] == 4
    assert data["metadata"]["total_conversions"] == 2
    
    assert "journey_statistics" in data
    assert "touchpoint_statistics" in data["journey_statistics"]
    assert "duration_statistics" in data["journey_statistics"]
    assert "top_conversion_paths" in data["journey_statistics"]
    
    # Since we have time duration data, duration statistics should be available
    assert data["journey_statistics"]["duration_statistics"]["available"] is True
    assert data["journey_statistics"]["duration_statistics"]["all"]["mean"] > 0
    
    assert "attribution_results" in data
    assert "last_click" in data["attribution_results"]
    assert "linear" in data["attribution_results"]
    assert "markov" in data["attribution_results"]
    
    assert "markov_specific_results" in data
    assert "transition_probabilities" in data["markov_specific_results"]
    assert "start_probabilities" in data["markov_specific_results"]
    assert "conversion_probabilities" in data["markov_specific_results"]
    assert "engagement_vs_conversion" in data["markov_specific_results"]
    
    # 3. Verify HTML contents
    with open(output_html, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "Relatório Executivo de Jornadas e Atribuição" in html_content
    assert "Análise de Pontos de Contato" in html_content
    assert "Análise de Tempo de Jornada (Duração)" in html_content
    assert "Top 10 Caminhos Mais Frequentes de Conversão" in html_content
    assert "Resultados dos Modelos de Atribuição" in html_content
    assert "Insights Detalhados do Modelo de Markov" in html_content


def test_generate_report_without_time(format_3_data, tmp_path):
    output_html = os.path.join(tmp_path, "report_no_time.html")
    output_json = os.path.join(tmp_path, "report_no_time.json")
    
    mam_instance = MAM(
        df=format_3_data,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="conversion",
        occurrences_colname="occurrences"
    )
    
    # Generate report with last_click model (Format 3 has no time duration data)
    mam_instance.generate_report(
        models=["last_click", "linear"],
        output_html_path=output_html,
        output_json_path=output_json
    )
    
    assert os.path.exists(output_html)
    assert os.path.exists(output_json)
    
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Check that duration statistics are NOT available
    assert data["journey_statistics"]["duration_statistics"]["available"] is False
    
    # Check HTML has warning message
    with open(output_html, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "Informações de Tempo Não Disponíveis" in html_content
    assert "O conjunto de dados de entrada fornecido" in html_content
