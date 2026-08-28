# Plano Detalhado de Implementação: Nova MAM (Marketing Attribution Models)

Este plano técnico estabelece a arquitetura, o design de API e as estratégias de otimização de alta performance para a refatoração completa da biblioteca **MAM** e sua unificação com a **JAToolbox**. A arquitetura migra de uma infraestrutura baseada em Pandas/NumPy para **Polars**, atingindo capacidade de processamento de escala empresarial (200M+ linhas).

---

## 1. Visão Arquitetural e Objetivos do Projeto

A Nova MAM foi projetada como uma biblioteca Python moderna, modular, escalável e de alto desempenho, orientada aos seguintes pilares:

```
[ Camada de Entrada ] -> Três Formatos Suportados (Sessão, Jornada, Agrupado)
       │
       ▼
[ Preprocessing Engine (Polars) ] -> Ingestão, Categorização e Unificação
       │
       ├───────────────────────────────┐
       ▼                               ▼
[ Attribution Models ]        [ Journey Analysis (JAToolbox) ]
 ├── Heurísticas (Last, First,  ├── get_size, get_transitions
 │   Linear, Position, Decay)   ├── channels_by_tp, etc.
 └── Algorítmicos (Markov,      └── Otimizados com Expressões Polars
     Shapley)
       │
       ▼
[ AttributionResult (Output Único) ] -> Polars DF, Pandas DF, Dict, JSON
       │
       ├───────────────────────────────┐
       ▼                               ▼
[ Interactive HTML Report ]   [ JSON BI Export ] -> Looker, PowerBI, Tableau
 (Plotly + Vanilla CSS)
```

1. **Escalabilidade Extrema (Polars Core):** Todas as transformações, agrupamentos de jornadas e heurísticas de atribuição serão reescritas utilizando a API de expressões vetorizadas do **Polars**, eliminando loops Python (`.apply()`, lógicas com strings pesadas e recursões). Adotaremos o uso intensivo de `pl.Categorical` para representar canais de marketing e otimizar o consumo de memória em até 10x.
2. **Interface de Entrada Unificada (3 Formatos):** Um motor de pré-processamento inteligente unificará três estruturas distintas de base de dados para uma representação tabular padrão otimizada interna.
3. **Consistência de Saída (`AttributionResult`):** Todas as execuções de modelos produzirão um objeto comum padronizado para evitar quebras em pipelines de dados secundários.
4. **Unificação DX (MAM + JAToolbox):** Fusão nativa da Jatoolbox no ecossistema MAM sob o namespace `mam.analysis`, com funções rodando nativamente sobre estruturas Polars.
5. **Apresentação de Alto Impacto (HTML One-Pager):** Uma área visual para geração de reports corporativos interativos, rápidos e exportáveis em formatos amigáveis para plataformas de Business Intelligence (BI).

---

## 2. O Desafio dos Três Formatos de Entrada

Para resolver a principal necessidade do negócio de flexibilidade nas fontes de dados, projetamos uma **Representação Tabular Unificada Interna** e um **Motor de Pré-processamento** (`MAMPipeline`) em Polars que converte qualquer um dos três formatos abaixo para uma estrutura homogênea antes de qualquer cálculo matemático.

### 2.1 Detalhamento Técnico dos Formatos Aceitos

#### Formato 1: Cada Linha uma Sessão (Granularidade de Ponto de Contato)
* **Estrutura:** `datetime | user_id | channel | has_conversion`
* **Exemplo de Dados:**
  ```csv
  2026-01-01 01:00:00| user_123 | direct | false
  2026-01-01 02:00:00| user_123 | direct | false
  2026-01-01 03:00:00| user_123 | google_search | false
  2026-01-01 01:00:00| user_456 | meta_ads | false
  2026-01-01 02:00:00| user_456 | direct | false
  2026-01-01 03:00:00| user_456 | google_search | false
  2026-01-01 04:00:00| user_456 | google_search | true
  ```
* **Características:** O formato mais comum extraído diretamente de servidores de tracking web ou tabelas brutas de banco de dados (ex: Google BigQuery). Requer ordenamento cronológico e agrupamento por usuário. Permite reconstrução de caminhos e cálculo exato do tempo decorrido de cada ponto de contato até a conversão.

#### Formato 2: Cada Linha uma Jornada (Granularidade de Usuário/Caminho Completo)
* **Estrutura:** `start_time | end_time | journey_id | journey | has_conversion | time_till_end`
* **Exemplo de Dados:**
  ```csv
  2026-01-01 01:00:00 | 2026-01-01 03:00:00 | user_123_0 | 'direct > direct > google_search' | false | '7200 > 3600 > 0'
  2026-01-01 01:00:00 | 2026-01-01 05:00:00 | user_456_0 | 'meta_ads > direct > google_search > google_search' | true | '10800 > 7200 > 3600 > 0'
  ```
* **Características:** Comum em relatórios consolidados de plataformas como Google Analytics (Top Conversion Paths). As interações e tempos de jornada estão compactados em strings separadas por um delimitador (ex: `" > "`). Requer conversão de strings para estruturas vetoriais (`pl.List`).

#### Formato 3: Cada Linha uma Jornada Agrupada (Granularidade de Tipo de Caminho/Frequências)
* **Estrutura:** `journey | has_conversion | occurrences`
* **Exemplo de Dados:**
  ```csv
  'direct > direct > google_search' | false | 2
  'meta_ads > direct > google_search > google_search' | true | 1
  ```
* **Características:** Altamente comprimido. Ideal para bases gigantescas onde bilhões de sessões são sumarizadas em milhares de caminhos exclusivos com seus respectivos contadores de ocorrência (`occurrences`). Este formato **não possui carimbo de data/tempo** associado a cada sessão individual, o que impossibilita o cálculo exato de modelos dependentes de tempo linear (como o Time Decay), a menos que preenchido com aproximações.

---

### 2.2 Representação Interna Unificada (Esquema Polars do Core)

Para garantir que todos os modelos matemáticos (heurísticos e algorítmicos) rodem sob um único conjunto de expressões lógicas, o módulo de pré-processamento convertará o input do usuário para o seguinte **DataFrame Interno de Referência**:

| Nome da Coluna | Tipo Polars | Descrição |
| :--- | :--- | :--- |
| `journey_id` | `pl.Utf8` | Identificador único de jornada para indexação. |
| `channels` | `pl.List(pl.Categorical)` | Lista cronológica dos canais de pontos de contato. |
| `time_till_conv` | `pl.List(pl.Float64)` | Diferença de tempo (em horas) de cada ponto até o fim da jornada. |
| `has_conversion` | `pl.Boolean` | Flag indicativa se a jornada resultou em conversão. |
| `weight` | `pl.Int64` | Multiplicador de ocorrências (1 para Formatos 1 e 2; Valor dinâmico para Formato 3). |

---

### 2.3 Estratégias de Pré-processamento e Ingestão em Polars

Abaixo detalhamos como as transformações de ingestão de cada formato serão implementadas no módulo `mam.preprocessing` usando expressões nativas do Polars:

#### pipeline_format_1_to_unified
1. **Ordenamento e Indexação:**
   ```python
   lf = (
       df.lazy()
       .with_columns(pl.col(datetime_col).str.to_datetime())
       .sort([user_id_col, datetime_col])
   )
   ```
2. **Geração de Journey ID (Segmentação por Conversão):**
   Se o usuário desejar fragmentar a história de sessões de um usuário em múltiplas jornadas após cada conversão:
   ```python
   lf = lf.with_columns(
       # Shift de conversão para acumular a partir do primeiro passo pós-conversão anterior
       pl.col(has_conv_col).shift(1).fill_null(False).cum_sum().over(user_id_col).alias("journey_idx")
   ).with_columns(
       pl.concat_str([pl.col(user_id_col), pl.lit("_J"), pl.col("journey_idx")]).alias("journey_id")
   )
   ```
3. **Agregação em Listas:**
   Agrupamos por `journey_id` e calculamos o `time_till_conv` para cada ponto de contato como a diferença em horas até o último carimbo temporal da jornada.
   ```python
   unified_df = (
       lf.group_by("journey_id")
       .agg([
           pl.col(channel_col).alias("channels"),
           # Diferença temporal em horas até a última interação da jornada
           (((pl.col(datetime_col).max() - pl.col(datetime_col)).dt.total_seconds() / 3600.0)).alias("time_till_conv"),
           pl.col(has_conv_col).any().alias("has_conversion"),
           pl.lit(1, dtype=pl.Int64).alias("weight")
       ])
   )
   ```

#### pipeline_format_2_to_unified
1. **Processamento Vetorizado de String para Lista:**
   Convertemos as representações textuais agrupadas de canais e durações diretamente para colunas do tipo `List` usando a eficiência da engine Polars:
   ```python
   unified_df = (
       df.lazy()
       .with_columns([
           pl.col(journey_col).str.split(separator).cast(pl.List(pl.Categorical)).alias("channels"),
           pl.col(time_col).str.split(separator).cast(pl.List(pl.Float64)).alias("time_till_conv"),
           pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
           pl.lit(1, dtype=pl.Int64).alias("weight")
       ])
       .select(["journey_id", "channels", "time_till_conv", "has_conversion", "weight"])
   )
   ```

#### pipeline_format_3_to_unified
1. **Geração de Dummy ID e Atribuição de Pesos de Frequência:**
   Como as linhas já estão consolidadas por caminho, geramos um ID de jornada sequencial e mapeamos o contador `occurrences` diretamente para o `weight`:
   ```python
   unified_df = (
       df.lazy()
       .with_row_index("journey_idx")
       .with_columns([
           pl.concat_str([pl.lit("path_"), pl.col("journey_idx")]).alias("journey_id"),
           pl.col(journey_col).str.split(separator).cast(pl.List(pl.Categorical)).alias("channels"),
           # Inicializa time_till_conv como uma lista de nulos (impede o uso do Time Decay)
           pl.col(journey_col).str.split(separator).list.eval(pl.repeat(pl.lit(None, dtype=pl.Float64), pl.element().len())).alias("time_till_conv"),
           pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
           pl.col(occurrences_col).cast(pl.Int64).alias("weight")
       ])
       .select(["journey_id", "channels", "time_till_conv", "has_conversion", "weight"])
   )
   ```

---

## 3. Arquitetura Modular e Design de API

Para sanar a dor de "Ecossistema Fragmentado", a estrutura do pacote foi reprojetada do zero, consolidando a MAM e a JAToolbox sob um único pipeline integrado.

### 3.1 Árvore do Repositório Proposta
```
nova_mam/
├── pyproject.toml               # Dependências modernas (Polars, Plotly, Jinja2, Pytest, SciPy)
├── README.md                    # Documentação do pacote
├── mam/
│   ├── __init__.py              # Exportações limpas do ecossistema
│   ├── core.py                  # Classe central MAM que orquestra a execução
│   ├── preprocessing.py         # Módulo de pipelines de ingestão e normalização (Formatos 1, 2, 3)
│   ├── results.py               # Classe de entrega padronizada AttributionResult
│   ├── analysis.py              # Jatoolbox integrada e otimizada (EDA de Jornadas)
│   ├── reporting.py             # Motor de geração de HTML Report (Jinja2) e exportações JSON/BI
│   └── models/
│       ├── __init__.py          # Exportação de classes de modelos
│       ├── base.py              # Classe Abstrata / Contrato Rígido (BaseModel)
│       ├── heuristics.py        # Implementação Polars (First, Last, Linear, Position, Decay)
│       ├── markov.py            # Cadeias de Markov de alta performance (Álgebra Linear vetorizada)
│       └── shapley.py           # Shapley Value otimizado combinatório
└── tests/
    ├── conftest.py              # Fixtures comuns e geradores de dados sintéticos (200M+ linhas)
    ├── test_preprocessing.py    # Testes unitários de ingestão
    ├── test_heuristics.py       # Validações matemáticas das heurísticas
    ├── test_markov.py           # Validações das propriedades Markovianas e Removal Effect
    ├── test_shapley.py          # Verificações combinatórias do Shapley
    └── test_analysis.py         # Validações de consistência do módulo JAToolbox
```

---

### 3.2 Design de Classes e Assinaturas de API

#### Classe Central: `MAM` (`mam.core`)
Representa a interface de usuário simplificada de alto nível para processar dados de atribuição.

```python
class MAM:
    def __init__(
        self,
        df: Union[pl.DataFrame, pd.DataFrame],
        format_type: str,  # "session", "journey", "grouped_journey"
        channels_colname: str,
        journey_with_conv_colname: str,
        datetime_colname: Optional[str] = None,
        user_id_colname: Optional[str] = None,
        time_till_conv_colname: Optional[str] = None,
        occurrences_colname: Optional[str] = None,
        create_journey_id_based_on_conversion: bool = False,
        path_separator: str = " > ",
        verbose: bool = False
    ):
        """
        Orquestrador central de atribuições. Automatiza a conversão de formatos de 
        entrada baseados em Polars para o Esquema Unificado Interno do core.
        """
        self.verbose = verbose
        self.sep = path_separator
        
        # Conversão de Pandas para Polars sob o capô, garantindo alta performance imediata
        if isinstance(df, pd.DataFrame):
            self._df = pl.from_pandas(df)
        else:
            self._df = df
            
        # Execução do pipeline correspondente de ingestão
        self.unified_df = self._ingest_data(
            format_type,
            channels_colname,
            journey_with_conv_colname,
            datetime_colname,
            user_id_colname,
            time_till_conv_colname,
            occurrences_colname,
            create_journey_id_based_on_conversion
        )

    def _ingest_data(self, format_type, **kwargs) -> pl.DataFrame:
        # Direciona para os pipelines especializados do mam.preprocessing
        ...

    def run_last_click(self) -> AttributionResult:
        ...

    def run_first_click(self) -> AttributionResult:
        ...

    def run_linear(self) -> AttributionResult:
        ...

    def run_position_based(self) -> AttributionResult:
        ...

    def run_time_decay(self, half_life_hours: float = 168.0) -> AttributionResult:
        ...

    def run_markov(self, transition_to_same_state: bool = False) -> AttributionResult:
        ...

    def run_shapley(self, max_size: int = 4, value_column: str = "conv_rate") -> AttributionResult:
        ...
```

#### Classe Base de Modelos: `BaseModel` (`mam.models.base`)
Interface estrita para garantir conformidade de contratos de desenvolvimento de modelos.

```python
from abc import ABC, abstractmethod

class BaseModel(ABC):
    @abstractmethod
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Executa os cálculos matemáticos sobre o DataFrame interno unificado.
        Retorna o DataFrame enriquecido com os pesos de atribuição por linha.
        """
        pass

    @abstractmethod
    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Agrupa os resultados agregando o valor total convertido ponderado por canal.
        """
        pass
```

#### Objeto de Saída Padronizado: `AttributionResult` (`mam.results`)
Uma classe rica e flexível que unifica as saídas do modelo eliminando a fragmentação ("inconsistência de saídas").

```python
class AttributionResult:
    def __init__(self, raw_df: pl.DataFrame, aggregated_df: pl.DataFrame, model_metadata: dict):
        self._raw_df = raw_df             # Resultados em nível de jornada individual
        self._aggregated_df = aggregated_df # Resultados somarizados por canal
        self.metadata = model_metadata

    def to_polars(self) -> pl.DataFrame:
        """Retorna o resultado agregado em formato Polars DataFrame."""
        return self._aggregated_df

    def to_pandas(self) -> pd.DataFrame:
        """Retorna o resultado em formato Pandas DataFrame para retrocompatibilidade."""
        return self._aggregated_df.to_pandas()

    def to_dict(self) -> dict:
        """Estrutura os dados para formato amigável de dicionário Python."""
        return self._aggregated_df.to_dict(as_series=False)

    def to_raw_polars(self) -> pl.DataFrame:
        """Retorna o resultado granular por jornada em formato Polars."""
        return self._raw_df

    def plot(self) -> None:
        """Gera visualização do resultado deste modelo específico usando Plotly."""
        ...
```

---

## 4. Algoritmos de Atribuição Modernizados em Polars

O motor matemático de cada modelo foi reprojetado para usufruir ao máximo das capacidades de computação vetorizada e lazy-evaluation do Polars.

### 4.1 Heurísticas Vetorizadas

#### Last Click
O canal que recebe 100% de atribuição é o último da lista.
* **Expressão Polars Otimizada:**
  ```python
  df.with_columns(
      pl.col("channels").list.last().alias("attribution_channel"),
      (pl.col("has_conversion").cast(pl.Float64) * pl.col("weight")).alias("attribution_value")
  ).group_by("attribution_channel").agg(pl.col("attribution_value").sum().alias("attribution"))
  ```

#### First Click
O canal introdutor recebe 100% de atribuição.
* **Expressão Polars Otimizada:**
  ```python
  df.with_columns(
      pl.col("channels").list.first().alias("attribution_channel"),
      (pl.col("has_conversion").cast(pl.Float64) * pl.col("weight")).alias("attribution_value")
  ).group_by("attribution_channel").agg(pl.col("attribution_value").sum().alias("attribution"))
  ```

#### Linear
O valor da conversão é dividido igualmente entre todos os canais da jornada.
* **Expressão Polars Otimizada:**
  ```python
  df.with_columns([
      pl.col("channels").list.len().alias("journey_len"),
      (pl.col("has_conversion").cast(pl.Float64) * pl.col("weight")).alias("total_value")
  ]).with_columns(
      (pl.col("total_value") / pl.col("journey_len")).alias("split_value")
  ).explode("channels").group_by("channels").agg(pl.col("split_value").sum().alias("attribution"))
  ```

#### Position Based
Atribui 40% ao primeiro ponto, 40% ao último ponto e distribui os 20% restantes igualmente entre os canais intermediários.
* **Estratégia Polars:**
  Através de expressões nativas, criaremos uma coluna de pesos vetoriais baseada no comprimento da lista de canais:
  * Comprimento 1: `[1.0]`
  * Comprimento 2: `[0.5, 0.5]`
  * Comprimento $N \ge 3$: `[0.4] + [0.2 / (N - 2)] * (N - 2) + [0.4]`
  Esta lógica é calculada em nível de expressão, explodindo canais e pesos em paralelo para gerar somas rápidas.

#### Time Decay
Usa a coluna `time_till_conv` para calcular o declínio exponencial de crédito com base na meia-vida especificada (ex: 7 dias).

> **Diretriz de Validação Estrita (Dados Ausentes):**
> Caso todos os valores da coluna `time_till_conv` sejam `null` (como ocorre nativamente no Formato 3 - Jornadas Agrupadas), o modelo **deve interromper a execução e lançar um erro descritivo** (`ValueError`), declarando explicitamente que o cálculo do Time Decay não é possível devido à ausência absoluta de dados temporais na base de entrada.

* **Expressão Polars Otimizada:**
  O Polars permite explodir colunas correspondentes de listas em paralelo de forma eficiente:
  ```python
  exploded_df = df.select([
      pl.col("has_conversion"),
      pl.col("weight"),
      pl.col("channels").explode(),
      pl.col("time_till_conv").explode().alias("hours")
  ])
  
  # Aplicação da fórmula de decaimento exponencial
  decayed_df = exploded_df.with_columns(
      (0.5 ** (pl.col("hours") / half_life_hours)).alias("raw_decay_weight")
  )
  
  # Normalização dos pesos de decaimento dentro da jornada
  # para que a soma dos pesos de uma única jornada de conversão equivalha ao valor unitário
  ...
  ```

---

### 4.2 Algorítmicos de Alta Performance

#### Cadeias de Markov
Atualmente, as transições são formadas por laços iterativos pesados. O novo design implementará as transições gerando listas pareadas e explodindo-as com agrupamentos de alta velocidade:

1. **Construção de Caminhos Estendidos:**
   Adicionamos o marcador `(inicio)` e o nó final (`(conversion)` ou `(null)`) às listas de canais de forma vetorizada usando `pl.concat_list`.
2. **Criação de Pares de Transição:**
   Dada uma lista de canais `["(inicio)", "Direct", "Organic", "(conversion)"]`, criamos uma lista deslocada e zipamos as duas colunas:
   ```python
   # Extração eficiente de transições orig -> dest no Polars
   transitions_df = (
       df.with_columns([
           pl.col("channels").list.slice(0, pl.col("channels").list.len() - 1).alias("orig_list"),
           pl.col("channels").list.slice(1).alias("dest_list")
       ])
       .explode(["orig_list", "dest_list"])
       .group_by(["orig_list", "dest_list"])
       .agg(pl.col("weight").sum().alias("transition_count"))
   )
   ```
3. **Resolução de Matrizes via NumPy/SciPy:**
   A matriz obtida de transição será convertida para uma matriz de estados absorventes esparsa de alta eficiência e as probabilidade resolvidas via álgebra linear pura utilizando fatorações LU ou inversas matriciais da biblioteca `scipy.linalg`. O cálculo do **Removal Effect** será paralelizado via threads internas.

#### Shapley Value
O cálculo de Shapley Value é intrinsecamente exponencial ($2^N$ permutações para $N$ canais). Para torná-lo viável na casa de milhões de linhas:
1. **Agregação em Coalizões (Redução de Escala):**
   Agrupamos e sumarizamos de forma preliminar os caminhos unificados do Polars em conjuntos únicos de coalizão de canais em milissegundos.
2. **Filtragem de Atribuições pelo tamanho da Janela (`max_size`):**
   Limitamos a análise aos últimos $k$ canais de conversão para manter as combinações combinatórias abaixo do limite exponencial instável.
3. **Cálculo Combinatório Vetorizado:**
   As contribuições marginais de cada canal serão calculadas usando representações de bits das coalizões (vetores de flags binárias), acelerando em até 100x a lógica sequencial antiga baseada em loops aplicados à strings.

---

## 5. Integração do Journey Analysis (JAToolbox)

O módulo de análise exploratória (`mam.analysis`) unifica todas as ferramentas de exploração de trajetórias de clientes em uma única classe analítica de alto desempenho rodando sobre o motor Polars.

### Mapeamento e Otimização de Métodos da JAToolbox

Todas as antigas operações baseadas em strings pesadas e lógicas individuais por linha com lamba da JAToolbox serão substituídas por operações vetorizadas de listas no Polars:

| Método Original JAToolbox | Nova Assinatura Polars / MAM | Estratégia de Refatoração de Desempenho |
| :--- | :--- | :--- |
| `get_size(j)` | `pl.col("channels").list.len()` | Cálculo de metadado de comprimento de lista nativa sem efetuar divisão de string. |
| `get_first_tp(j)` | `pl.col("channels").list.first()` | Acesso direto ao primeiro indexador da lista interna do Polars. |
| `get_last_tp(j)` | `pl.col("channels").list.last()` | Acesso direto à ponta final da lista (`list.last()`). |
| `get_nth_tp(j, n)` | `pl.col("channels").list.get(n)` | Resgate vetorial otimizado por índice sem realizar splits iterativos. |
| `get_intermediate_tp(j, r)` | `pl.col("channels").list.slice(r[0], r[1]-r[0])` | Operação de fatiamento de lista ultra rápida nativa do motor Polars. |
| `get_tps_counts(j)` | `pl.col("channels").list.eval(pl.element().value_counts())` | Contagem de valores únicos estruturada dentro das células da lista do Polars. |
| `skip_tp(j, tp)` | `pl.col("channels").list.eval(pl.element().filter(pl.element() != tp))` | Filtro condicional ultra rápido dentro de contextos vetoriais. |
| `check_tp(j, tp)` | `pl.col("channels").list.contains(tp)` | Avaliação booleana nativa de pertinência de elemento em lista. |
| `get_duration(ts, r)` | Operação vetorizada de tempo | Diferença aritmética direta baseada em indexação de listas de floats pré-calculados. |
| `get_transitions(j)` | `pl.col("channels").list.zip()` | Criação de listas de tuplas unidas de transição e explosão por linha. |
| `channels_by_tp(df, j)` | Group-by por indexadores de listas | Agrupamento estatístico multidimensional de canais em cada nível de etapa do funil. |

---

## 6. Reporting, Visualização e Exportabilidade

O módulo `mam.reporting` foi desenhado sob a perspectiva de gerar insumos ricos e robustos, facilitando a tomada de decisão empresarial.

```
       [ AttributionResult / Core MAM ]
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│  report_raw_data.json│  │ One Page HTML Report │
│ (Mapeamento de BI)   │  │ (Dashboard Completo) │
│ - Distribuição Tempo │  │ - Comparativo Modelos│
│ - Matriz Transições  │  │ - Top Conversões     │
│ - Top 10 Caminhos    │  │ - Matriz de Markov   │
└──────────────────────┘  └──────────────────────┘
```

### 6.1 Geração de Dados para BI (`report_raw_data.json`)
As saídas serão agregadas de forma consistente em um arquivo estruturado único para fácil importação nas plataformas corporativas de visualização (Looker, PowerBI, Tableau). O JSON conterá:
- **`model_comparisons`**: Valores absolutos e percentuais de atribuição de cada canal por modelo.
- **`transition_matrix`**: Matriz de transições refinada (em formato de lista plana para fácil consumo em tabelas).
- **`top_conversion_paths`**: Os 10 caminhos mais representativos que resultaram em conversões.
- **`duration_statistics`**: Distribuição de tempo médio das jornadas por canal introdutor.

---

### 6.2 O One Page Report Interativo (HTML + Vanilla CSS + Plotly)
Em vez de depender de dependências que demandam renderização lenta no navegador, usaremos o motor de templates **Jinja2** com estilização estruturada em **Vanilla CSS** para entregar um painel moderno, interativo e fluido.

#### Estratégia Visual (Fidelity Design):
- **Paleta de Cores Estilo "Dark Mode" Executivo:** Cores sóbrias e elegantes com transições de hover suaves, garantindo alto contraste e leitura executiva.
- **Gráficos Dinâmicos Plotly:** Gráficos de barra de múltiplos modelos agrupados, heatmap interativo para visualização de transições de Markov, histograma interativo para distribuição do tamanho e duração das jornadas e um fluxograma em estilo Sankey Diagram para ilustrar os caminhos de conversão mais populares.
- **Responsividade Nativa:** Painel estruturado com CSS Grid e Flexbox, proporcionando visualização otimizada para telas mobile ou monitores de alta resolução.

---

## 7. Estratégia de Validação e Qualidade (Shift-Left Testing)

Adotaremos a prática de **Shift-Left Testing**, projetando testes de regressão e estresse desde o primeiro dia de codificação para certificar a estabilidade operacional e consistência de ponta a ponta.

### 7.1 Pipeline de Testes Propostos (`pytest`)

1. **Testes de Pré-processamento e Ingestão (`tests/test_preprocessing.py`):**
   - Garantir que as lógicas de ingestão para os três formatos distintos processem os insumos sintéticos e os transformem em estruturas idênticas.
   - Validar que a geração automática de `journey_id` com base em marcas de conversão segmente e agrupe as sequências temporais de maneira idêntica à versão histórica da biblioteca MAM.

2. **Testes Matemáticos Comparativos (`tests/test_heuristics.py` & `tests/test_markov.py`):**
   - Comparar a precisão decimal dos resultados heurísticos e de Markov da nova biblioteca orientada a Polars com as saídas geradas pela versão histórica baseada em Pandas.
   - Validar que a soma de todas as atribuições equivale de forma estrita à soma total de conversões reais ocorridas nas bases testadas.

3. **Testes de Estresse e Carga com Volume Massivo (`tests/test_stress.py`):**
   - Criar scripts de geração de dados capazes de construir uma base massiva controlada com **200 milhões de registros** (Formatos 1, 2 e 3).
   - Validar se a ingestão e os processamentos dos modelos heurísticos rodam sem atingir picos críticos de consumo de memória RAM, respeitando o limite físico do ambiente.

### 7.2 Scripts Auxiliares de Validação de Transição
Para certificar a transição perfeita e garantir que não ocorram regressões comportamentais, criaremos um script de validação de compatibilidade (`validate_migration.py`) que executará simultaneamente as duas versões das classes (MAM Legado vs Nova MAM Polars) sob uma base comum para alertar em caso de divergências nos dados finais ou estouro nos tempos tolerados de execução.

---

## 8. Conclusão e Próximos Passos

O plano apresentado redefine estruturalmente a biblioteca MAM, transformando um ecossistema fragmentado e lento em uma ferramenta unificada de excelente usabilidade e performance.

### Cronograma de Ação Recomendado:
1. **Fase 1:** Criação do ambiente de testes (`pytest`), validações iniciais de setup e geração dos datasets sintéticos e massivos.
2. **Fase 2:** Escrita do módulo `mam.preprocessing` com suporte nativo em Polars para os três formatos de base.
3. **Fase 3:** Implementação dos modelos heurísticos e algorítmicos orientados à performance.
4. **Fase 4:** Unificação e modernização das ferramentas JAToolbox sob o escopo `mam.analysis`.
5. **Fase 5:** Codificação do gerador de relatórios visuais (One Page Report HTML e JSON para exportação de BI).
6. **Fase 6:** Testes integrados Finais, otimizações finais de performance e documentação completa da API.
