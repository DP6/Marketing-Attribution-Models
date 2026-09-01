# Nova MAM (Marketing Attribution Models)

A **Nova MAM** é uma biblioteca de alta performance para Modelagem de Atribuição de Marketing (Marketing Attribution Models) e análise de jornadas de conversão de clientes. Ela foi completamente migrada e otimizada utilizando **Polars**, resultando em processamentos ordens de grandeza mais rápidos e uso extremamente eficiente de memória RAM, mantendo estrita paridade matemática com as regras de negócio legadas.

---

## 🚀 Principais Destaques

- **Performance Extrema com Polars:** Algoritmos 100% vetorizados e em nível de expressão, eliminando loops lentos e permitindo o processamento de bases com milhões de registros em poucos segundos.
- **Suporte Multiformato Nativo:** Suporta a ingestão transparente de três formatos de dados padrão de mercado (Sessões individuais, Jornadas lineares e Jornadas agrupadas com frequência).
- **JAToolbox Integrada:** Versão modernizada da DP6 Journey Analysis Toolbox para exploração estatística profunda de canais e transições de caminhos.
- **Modelos de Atribuição Avançados:** Heurísticas clássicas (Last Click, First Click, Linear, Position Based, Time Decay contínuo) e modelos algorítmicos robustos (Markov e Shapley).
- **Visualização Pronta para Negócios:** Geração automatizada de One Page Reports interativos em HTML e exportação estruturada em JSON para integração rápida com ferramentas de Business Intelligence (BI).

---

## 🛠️ Requisitos e Instalação

A biblioteca requer Python 3.12+ e as dependências listadas no `pyproject.toml`.

Para instalar em modo de desenvolvimento em seu ambiente virtual:

```bash
# Certifique-se de ativar o seu ambiente virtual
source .venv/bin/activate

# Instale o pacote e suas dependências
pip install -e .[dev]
```

---

## 📁 Estrutura de Arquivos

```
nova_mam/
├── mam/
│   ├── __init__.py
│   ├── core.py             # Orquestrador unificado da API (Classe principal MAM)
│   ├── preprocessing.py    # Pipeline de ingestão polars para os 3 formatos
│   ├── analysis.py         # Journey Analysis Toolbox (JAToolbox)
│   ├── reporting.py        # Gerador de relatórios HTML (Jinja2/Plotly) e JSON BI
│   ├── results.py          # Wrapper unificado de retorno dos resultados
│   └── models/
│       ├── __init__.py
│       ├── base.py         # Classe base para modelos
│       ├── heuristics.py   # Modelos: Last Click, First Click, Linear, Position Based, Time Decay
│       ├── markov.py       # Modelo Algorítmico baseado em Cadeias de Markov estável
│       └── shapley.py      # Modelo Algorítmico baseado em Teoria dos Jogos Cooperativos (Shapley)
```

---

## 📥 Guia de Ingestão de Dados (Os 3 Formatos)

O orquestrador principal `mam.core.MAM` detecta automaticamente ou configura a ingestão dos dados com base no parâmetro `format_type`.

### 1. Formato 1: Sessões Individuais (`format_type="session"`)
Cada linha representa um ponto de contato individual no tempo.
```python
import polars as pl
from mam.core import MAM

df = pl.DataFrame({
    "user_id": ["u1", "u1", "u1", "u2", "u2"],
    "datetime": ["2026-01-01 10:00:00", "2026-01-01 11:00:00", "2026-01-01 12:00:00", "2026-01-01 09:00:00", "2026-01-01 15:00:00"],
    "channel": ["Google_Search", "Meta_Ads", "Direct", "Organic_Search", "Email"],
    "conversion": [False, False, True, False, True]
})

mam = MAM(
    df=df,
    format_type="session",
    channels_colname="channel",
    journey_with_conv_colname="conversion",
    datetime_colname="datetime",
    user_id_colname="user_id"
)
```

### 2. Formato 2: Jornadas Lineares por Linha (`format_type="journey"`)
Cada linha representa uma jornada completa de um usuário, com os canais e tempos encadeados por um separador (ex: `" > "`).
```python
df = pl.DataFrame({
    "journey_id": ["j1", "j2"],
    "journey": ["Google_Search > Meta_Ads > Direct", "Organic_Search > Email"],
    "conversion": [True, True],
    "time_till_end": ["72.0 > 36.0 > 0.0", "120.0 > 0.0"] # tempos decrescentes (horas)
})

mam = MAM(
    df=df,
    format_type="journey",
    channels_colname="journey",
    journey_with_conv_colname="conversion",
    time_till_conv_colname="time_till_end"
)
```

### 3. Formato 3: Jornadas Agrupadas com Frequência (`format_type="grouped_journey"`)
Caminhos agregados sem carimbo temporal, contendo uma coluna de peso/frequência (`occurrences`).
```python
df = pl.DataFrame({
    "journey": ["Google_Search > Meta_Ads", "Organic_Search > Direct"],
    "conversion": [True, False],
    "occurrences": [150, 430]
})

mam = MAM(
    df=df,
    format_type="grouped_journey",
    channels_colname="journey",
    journey_with_conv_colname="conversion",
    occurrences_colname="occurrences"
)
```

---

## 💰 Atribuição Baseada em Receita (Revenue Attribution)

Por padrão, a Nova MAM realiza a atribuição baseada na **quantidade de conversões** (onde cada jornada conversora tem valor constante de `1.0`). Porém, ela também suporta nativamente a atribuição baseada em **receita (valor financeiro/revenue)**.

Para habilitar isso, basta passar o nome da coluna contendo os valores de receita no parâmetro `conversion_value_colname` ao inicializar a classe `MAM`:

```python
import polars as pl
from mam.core import MAM

# DataFrame com coluna de receita (revenue)
df = pl.DataFrame({
    "journey_id": ["j1", "j2", "j3"],
    "journey": ["Google_Search > Meta_Ads > Direct", "Organic_Search > Email", "Direct"],
    "conversion": [True, False, True],
    "time_till_end": ["72.0 > 36.0 > 0.0", "120.0 > 0.0", "0.0"],
    "revenue": [150.00, 0.0, 300.00]  # Valores financeiros reais das conversões
})

# Inicializando o orquestrador mapeando a receita
mam = MAM(
    df=df,
    format_type="journey",
    channels_colname="journey",
    journey_with_conv_colname="conversion",
    time_till_conv_colname="time_till_end",
    conversion_value_colname="revenue"  # <--- Habilita atribuição por receita
)

# Ao rodar qualquer modelo, o crédito atribuído a cada canal será proporcional à receita total:
res_linear = mam.run_linear().to_polars()
print(res_linear)
```

### 📊 Relatórios Visuais e JSON com Suporte a Receita
Ao ativar a atribuição por receita, o método `generate_report(...)` detecta automaticamente esse contexto e ajusta dinamicamente a exibição do dashboard:
- **Novos Big Numbers:** Exibe um cartão adicional com a métrica de destaque **"Receita Total Atribuída"** (R$). O layout se expande automaticamente de 4 para 5 colunas.
- **Gráficos Monetários (Plotly):** O título do eixo X muda de "Conversões" para **"Receita Atribuída (R$)"**, formatando as legendas flutuantes e os textos sobre as barras como moeda brasileira (ex: `R$ 13.101,68`).
- **BI Export em JSON:** O arquivo bruto gerado no JSON incluirá a chave `"total_revenue"` dentro de `"metadata"`, ideal para carregar diretamente nos seus dashboards do Tableau, Power BI ou Looker Studio.

---

## 🔍 Journey Analysis Toolbox (JAToolbox)

A `JAToolbox` oferece ferramentas estatísticas poderosas para análise exploratória de touchpoints e caminhos de conversão, totalmente integrada com Polars (e com suporte automático a Pandas).

Há duas formas principais de utilizar a `JAToolbox`:

### 🔹 Opção 1: Diretamente através de uma instância do `MAM` (Recomendado)
Se você já instanciou o orquestrador `MAM`, você pode acessar a `JAToolbox` pré-configurada diretamente pela propriedade `.jatoolbox`:

```python
from mam import MAM

# 1. Instancia o orquestrador MAM normalmente
mam = MAM(df=df, format_type="journey", channels_colname="journey", journey_with_conv_colname="conversion")

# 2. Acessa a JAToolbox já pré-configurada com os dados unificados
jatoolbox = mam.jatoolbox
```

### 🔹 Opção 2: Instanciação Manual (Suporta Pandas e Polars)
Você também pode instanciar a `JAToolbox` de forma avulsa. Ela aceita DataFrames do Polars ou Pandas (convertendo de Pandas para Polars sob o capô automaticamente):

```python
from mam import JAToolbox

# Inicializando com um DataFrame que já possui listas de canais
jatoolbox = JAToolbox(df=df_unificado, channels_col="channels")
```

Se os seus dados estiverem brutos (não unificados), a `JAToolbox` é capaz de realizar o pré-processamento interno automático no próprio construtor:

```python
from mam import JAToolbox

# Inicializando e pré-processando dados brutos do Formato 2 (journey) de forma transparente
jatoolbox = JAToolbox(
    df=df_bruto,
    format_type="journey",
    channels_col="jornada_original",
    journey_with_conv_colname="conversao_original",
    time_till_conv_colname="tempo_para_conversao"
)
```

### 📈 Exemplos de Análise Estatística
Uma vez obtida ou instanciada a sua `JAToolbox`, você pode realizar diversas análises exploratórias:

```python
# 1. Obter o tamanho das jornadas (quantidade de touchpoints por linha)
tamanhos = jatoolbox.get_size()

# 2. Obter a contagem ponderada (volume real) de aparições por canal
contagens = jatoolbox.get_tps_counts()

# 3. Obter transições ponto a ponto (matriz de transição detalhada)
transicoes = jatoolbox.get_transitions(count=True, norm=True)

# 4. Obter a distribuição de canais por posição da jornada (estágios/etapas de conversão)
estagios_df = jatoolbox.channels_by_tp(max_journey_size=5)
```

---

## 📊 Executando os Modelos de Atribuição

Cada modelo de atribuição é instanciado e executado através de métodos simples que retornam um objeto `AttributionResult`.

### 🔹 Modelos Heurísticos
```python
# Last Click (Atribui 100% ao último ponto de contato)
res_last = mam.run_last_click()

# First Click (Atribui 100% ao primeiro ponto de contato)
res_first = mam.run_first_click()

# Linear (Distribui o valor igualmente entre todos os canais)
res_linear = mam.run_linear()

# Position Based (Atribui 40% ao primeiro, 40% ao último e divide 20% no meio)
res_position = mam.run_position_based()

# Time Decay (Decaimento contínuo baseado em meia-vida exponencial - requer dados temporais)
res_decay = mam.run_time_decay(half_life_hours=168.0)
```

### 🔹 Modelos Algorítmicos

#### Cadeias de Markov
Calcula a probabilidade de conversão e atribui pesos a cada canal usando a taxa de efeito de remoção (Removal Effect).
```python
res_markov = mam.run_markov(transition_to_same_state=False)

# Metadados adicionais do modelo
matriz_transicao = res_markov.metadata["transition_matrix"]
efeito_remocao = res_markov.metadata["removal_effect"]
```

#### Valor de Shapley
Aplica conceitos de Teoria dos Jogos Cooperativos para avaliar a contribuição marginal de cada canal nas combinações de jornadas. Ele conta com **normalização por jornada**, evitando a inflação artificial em caminhos com touchpoints repetidos.
```python
res_shapley = mam.run_shapley(max_size=4, value_column="conv_rate")

# Tabela de conversão agrupada de coalizões gerada
conv_table = res.metadata["conv_table"]
```

---

## 📈 Geração de Relatórios Visuais e BI

Você pode facilmente gerar relatórios ricos e interativos em HTML, além de exportar dados consolidados em formato JSON ideal para ferramentas de Business Intelligence (BI):

```python
# Gera um One-Page Report em HTML interativo com Plotly e exporta os dados limpos para BI em JSON
mam.generate_report(
    models=["last_click", "first_click", "linear", "position_based", "time_decay", "markov", "shapley"],
    output_html_path="relatorio_atribuicao.html",
    output_json_path="exportacao_bi.json"
)
```

---

## 🧪 Testes de Validação e Estabilidade

A biblioteca é exaustivamente testada por meio de testes unitários integrados e de um validador de migração ponta a ponta.

### Executando Testes Unitários:
```bash
pytest
```

### Executando a Validação Matemática e de Regressão:
O script `validate_migration.py` executa o código legado de forma assíncrona ao lado da Nova MAM em um dataset sintético de grande escala, provando a estrita paridade matemática das heurísticas e calculando o ganho de velocidade (speedup):

```bash
python validate_migration.py
```

---

## 📄 Licença e Contribuição

Projeto licenciado nos termos internos da DP6. Todas as contribuições devem aderir às convenções descritas no manifesto técnico e passar em 100% da suíte de testes automáticos livres de deprecation warnings.
