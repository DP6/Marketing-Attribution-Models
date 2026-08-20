import polars as pl
from mam.core import MAM

def main():
    print("🚀 Iniciando a geração do Segundo One Page Report de Exemplo...")
    
    # 1. Carregar o segundo chunk de dados reais (Format 1 Chunk 1)
    data_path = "data/format_1_chunk_1.csv"
    print(f"📖 Carregando os dados de '{data_path}'...")
    df = pl.read_csv(data_path)
    
    print(f"📊 Dados carregados: {len(df):,} linhas de pontos de contato.")
    
    # 2. Instanciar o orquestrador MAM
    print("⚙️ Inicializando o orquestrador MAM para o Bloco 2...")
    mam_instance = MAM(
        df=df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
        create_journey_id_based_on_conversion=True
    )
    
    # 3. Gerar o One Page Report e Exportação de Dados JSON
    print("📈 Rodando os modelos 'last_click' e 'markov' e compilando as visualizações para o Relatório 2...")
    report_data = mam_instance.generate_report(
        models=["last_click", "markov"],
        output_html_path="example_report_2.html",
        output_json_path="example_report_data_2.json"
    )
    
    print("\n✨ Processo Concluído com Sucesso!")
    print("🖥️  Segundo relatório interativo gerado: 'example_report_2.html'")
    print("📊 Segundos dados brutos em JSON gerados: 'example_report_data_2.json'")
    
    # Exibe alguns KPIs de exemplo do JSON gerado
    meta = report_data["metadata"]
    print("\n📊 Resumo das Jornadas Processadas no Exemplo 2:")
    print(f"  • Total de Jornadas: {meta['total_journeys']:,}")
    print(f"  • Total de Conversões: {meta['total_conversions']:,}")
    print(f"  • Taxa de Conversão: {meta['conversion_rate']}%")

if __name__ == "__main__":
    main()
