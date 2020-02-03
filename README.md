# Marketing Attribution Models

## 1 - Sobre a Classe
Classe em Python desenvolvida para soluções de problemas de atribuição voltadas para o marketing


## 2 - Sobre Atribuição Multicanal

### a) Tipos de Modelos

#### Heurísticos

- Last Interaction:
    - Modelo padrão de atribuição tanto do Google Analytics, quanto de ferramentas de mídia como Google Ads e Facebook Business manager;
    - Atribui todo o resultado da conversão para o último ponto de contato;
- Last non-Direct Click
    - Todo o tráfego direto é ignorado, e 100% do crédito da venda vai para o último canal por meio do qual o cliente chegou ao site antes de concluir a conversão
- First Interaction
    - Atribui todo o resultado da conversão para o primeiro ponto de contato;
- Linear
    - Cada ponto de contato no caminho de conversão;
- Time Decay
    - Os pontos de contato mais próximos em termos de tempo da venda ou conversão recebem a maior parte do crédito. 
- Position Based
    - No modelo de atribuição Com base na posição, 40% do crédito é atribuído a cada primeira e última interação, e os 20% de crédito restantes são distribuídos uniformemente para as interações intermediárias.

#### Probabilisticos

##### Shapley Value:

Método não paramétrico, isto é, não assume nenhuma distribuição para os dados.

O Shapley value por definição não considera a ordem dos canais, mas sim a contribuição da presença dele na jornada. 
Para levar isso em consideração é preciso aumentar a ordem do numero de combinações. 
Além disso, podemos calcular a contribuição de canais combinados, o que também aumenta a ordem das combinações.

Exemplo de cenários possiveis:

Exemplo 1:

- **A** > B > B > C 

- B > **A** > B > C 

- B > C > **A** > B

- B > C > D > **A**



Podemos calcular a contribuição marginal do canal **B quando *antecedido* pelo canal A**. 

Diferente das cadeias de Markov, os resultados são construídos usando jornadas *existentes* e não simuladas.

Disso vem a dificuldade em usar um método que considere a *ordem dos canais* para um grande número n, pois, além das $2^n$ interações para o cálculo do Shapley Value de um determinado canal i, **precisamos da *observação* do canal i em todas as possíveis posições.**




**Contras**
- Limita o número de pontos de contato uma vez que as combinações são $2^n$
- Se não ordenado, o Shapley value considera que a contribuição de um canal A é a mesma se seguido por B ou por C;
- Se ordenado, o número de combinações cresce MUITO e as jornadas devem estar disponíveis;
- Canais que estão poucos presentes ou presentes em jornadas longas vão ter pequenas contribuições;

#### Markov Chain:
  - Calcula a probabilidade de transição entre canais e é possivel calcular o **efeito de remoção**;
  - Memory free: Probabilidade de transição depende apenas do estado anterior;
  - Mede a probabilidade de continuar no mesmo estado, no caso de mídia, a probabilidade do próximo ponto de contato ser o mesmo canal anterior;


#### b) Sobre MCF Data-Driven Attribution
- Baseado na teoria dos jogos chamada Shapley Value;
- Utiliza os dados do relatório [Multi-Channel Funnels](https://support.google.com/analytics/answer/1191180);
- Classificação dos canais utilizada é com base no [Default Channel Grouping](https://support.google.com/analytics/answer/6010097)
  -  Limitação de 15 Channel Groupings, sem incluir os Default Channel Grouping;
- Lookback Window padrão de 30 dias;
- Número máximo de 4 interações;
- Trafego direto que ocorreu em até 24h de uma campanha, é removido;
- Leva em consideração a posição de impacto do canal;


## Referências
- [Attribution Models in Marketing](https://data-science-blog.com/blog/2019/04/18/attribution-models-in-marketing/)
- [Attribution Theory: The Two Best Models for Algorithmic Marketing Attribution – Implemented in Apache Spark and R](http://datafeedtoolbox.com/attribution-theory-the-two-best-models-for-algorithmic-marketing-attribution-implemented-in-apache-spark-and-r/)
- [Game Theory Attribution: The Model You’ve Probably Never Heard Of](https://clearcode.cc/blog/game-theory-attribution/)
- [Marketing Channel Attribution With Markov Models In R](https://www.bounteous.com/insights/2016/06/30/marketing-channel-attribution-markov-models-r/?ns=l)
- [Multi-Channel Funnels Data-Driven Attribution](https://support.google.com/analytics/topic/3180362?hl=en&ref_topic=3205717)
- [Marketing Multi-Channel Attribution model with R (part 1: Markov chains concept)](https://analyzecore.com/2016/08/03/attribution-model-r-part-1/)
- [Marketing Multi-Channel Attribution model with R (part 2: practical issues)](https://analyzecore.com/2017/05/31/marketing-multi-channel-attribution-model-r-part-2-practical-issues/)
- [ml-book/shapley](https://christophm.github.io/interpretable-ml-book/shapley.html)
- [Overview of Attribution modeling in MCF](https://support.google.com/analytics/answer/1662518?hl=en)

## 3 - Importando a Classe


```python
>> pip install marketing_attribution_models
```


```python
from marketing_attribution_models import MAM
```

## 4 - Demonstração

### **Criando o objeto MAM**

**A criação do objeto MAM** é baseado em **dois formatos de Data Frame** e que é guiado pelo parâmetro group_channels:

*   **group_channels = True**. Espera-se receber uma base na qual **cada linha seria uma sessão da jornada do usuário**.
  * Esse data frame deve conter colunas representando ID do Usuário, indicação booleana se houve ou não transação durante a sessão, timestamp da sessão e o canal na qual o usuário gerou a sessão;
*   **group_channels = False**. Recebe a base na qual a **jornada já foi agrupada** e que cada linha representa uma jornada completa de determinado usuário até a conversão. Para os usuários do Google Analytics, essa base pode ser gerada através da exportação do relatório de Top Conversion Paths na aba de Conversions.
  * Nesse caso a coluna de canais e time_till_conv_colname receberiam em cada linha uma jornada separada por um separador, ' > ' como padrão e que pode ser alterado no parâmetro path_separator.

No nosso caso, iremos apresentar um exemplo na qual as jornadas ainda não estão agrupadas, que cada linha representa uma jornada e que ainda não temos um ID de Cada Jornada.

**Ponto de Atenção:**
A classe já contempla uma função representada pelo parâmetro create_journey_id_based_on_conversion, que caso seja True, será criado um ID da Jornada baseado nas colunas de ID do Usuário, passada no parâmetro group_channels_id_list e a coluna que representa se houve ou não conversão, passada no parâmetro journey_with_conv_colname.

Nesse caso, serão ordenadas as sessões de cada usuário e a cada transação será criado um novo ID da Jornada. Entretanto, **encorajamos que seja criado um ID da Jornada com base no conhecimento de negócio de cada base explorada**. Podendo criar condições expecíficas de tempo para que haja uma quebra de jornada, como por explempo se identificado que a jornada média de determidado negócio dura 1 semana até a conversão, podemos adotar um critério que se determinado usuário não interagir com o site por uma semana, sua jornada será quebrada, pois pode haver uma quebra de interesse.



Exemplificando como seria a configuração dos parametros no cenário descrito acima com group_channels = True. 

1. Deve ser passado o **Pandas Data Frame** contendo a base de dados a ser analisada;
2. Indicar o formato da base em **group_channels**=True
3. Nome da coluna que contem os agrupamentos de canais em **channels_colname**;
4. Coluna Booleana indicando se houve ou não conversão na sessão em **journey_with_conv_colname**;
5. Lista contendo os nomes das colunas que representam o ID da Jornada, podendo ser uma combinação de colunas em **group_channels_by_id_list**. Mas nesse caso como estamos indicando que iremos criar um ID da Jornada no parâmetro **create_journey_id_based_on_conversion = True**, basta indicar a coluna de ID do Usuário; 
6. Coluna representando a data em que ocorreu a sessão em **group_timestamp_colname**. Coluna que pode receber além dos dias do ano, o horário em que a sessão ocorreu;
7. Por fim, em nosso caso, indicamos que iremos gerar um ID da Jornada a partir das colunas indicadas nos parâmetros group_channels_by_id_list e journey_with_conv_colname, em **create_journey_id_based_on_conversion** = True



```python
attributions = MAM(df,
    group_channels=True,
    channels_colname = 'channels',
    journey_with_conv_colname= 'has_transaction',
    group_channels_by_id_list=['user_id'],
    group_timestamp_colname = 'visitStartTime',
    create_journey_id_based_on_conversion = True)
```

Para fins exploratórios e de aprendizado, implementamos uma forma de gerar uma **base de dados aleatória** através do parâmetro **random_df=True**. Não sendo necessário o preenchimento dos demais.


```python
attributions = MAM(random_df=True)
```

Assim que o objeto foi criado, podemos checar como ficou a **base após a criação do journey_id e o agrupamento das sessões** em joranadas através do **atributo .DataFrame.**


```python
attributions.DataFrame
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>journey_id</th>
      <th>channels_agg</th>
      <th>time_till_conv_agg</th>
      <th>converted_agg</th>
      <th>conversion_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>id:0_J:0</td>
      <td>Facebook</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>1</th>
      <td>id:0_J:1</td>
      <td>Google Search</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>2</th>
      <td>id:0_J:10</td>
      <td>Google Search &gt; Organic &gt; Email Marketing</td>
      <td>72.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>3</th>
      <td>id:0_J:11</td>
      <td>Organic</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>4</th>
      <td>id:0_J:12</td>
      <td>Email Marketing &gt; Facebook</td>
      <td>432.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>20341</th>
      <td>id:9_J:5</td>
      <td>Direct &gt; Facebook</td>
      <td>120.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>20342</th>
      <td>id:9_J:6</td>
      <td>Google Search &gt; Google Search &gt; Google Search</td>
      <td>48.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>20343</th>
      <td>id:9_J:7</td>
      <td>Organic &gt; Organic &gt; Google Search &gt; Google Search</td>
      <td>480.0 &gt; 480.0 &gt; 288.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>20344</th>
      <td>id:9_J:8</td>
      <td>Direct &gt; Organic</td>
      <td>168.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <th>20345</th>
      <td>id:9_J:9</td>
      <td>Google Search &gt; Organic &gt; Google Search &gt; Emai...</td>
      <td>528.0 &gt; 528.0 &gt; 408.0 &gt; 240.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
  </tbody>
</table>
<p>20346 rows × 5 columns</p>
</div>



Esse **atributo é atualizado para cada modelo gerado** e nos casos dos resultados heurísticos, será adicionado uma coluna contendo a atribuição dada por determinado modelo no final.

**Atenção:**
Os cálculos dos modelos não são calculados com base no parâmetro .DataFrame, caso ele seja alterado, os resultados não serão afetados.


```python
attributions.attribution_last_click()
attributions.DataFrame
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>journey_id</th>
      <th>channels_agg</th>
      <th>time_till_conv_agg</th>
      <th>converted_agg</th>
      <th>conversion_value</th>
      <th>attribution_last_click_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>id:0_J:0</td>
      <td>Instagram &gt; Direct &gt; Google Search &gt; Organic &gt;...</td>
      <td>2568.0 &gt; 2112.0 &gt; 2064.0 &gt; 576.0 &gt; 240.0 &gt; 96....</td>
      <td>True</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 1</td>
    </tr>
    <tr>
      <th>1</th>
      <td>id:0_J:1</td>
      <td>Organic &gt; Organic &gt; Google Search &gt; Direct</td>
      <td>1848.0 &gt; 1752.0 &gt; 1272.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 1</td>
    </tr>
    <tr>
      <th>2</th>
      <td>id:0_J:2</td>
      <td>Organic &gt; Email Marketing &gt; Organic</td>
      <td>720.0 &gt; 504.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 1</td>
    </tr>
    <tr>
      <th>3</th>
      <td>id:0_J:3</td>
      <td>Organic</td>
      <td>0.0</td>
      <td>False</td>
      <td>1</td>
      <td>0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>id:100_J:0</td>
      <td>Direct &gt; Facebook &gt; Youtube &gt; Google Search &gt; ...</td>
      <td>6576.0 &gt; 6432.0 &gt; 5304.0 &gt; 4896.0 &gt; 4632.0 &gt; 4...</td>
      <td>False</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 ...</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>1648</th>
      <td>id:98_J:0</td>
      <td>Organic &gt; Direct &gt; Facebook &gt; Google Search &gt; ...</td>
      <td>5064.0 &gt; 4920.0 &gt; 3024.0 &gt; 1752.0 &gt; 1536.0 &gt; 1...</td>
      <td>False</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0</td>
    </tr>
    <tr>
      <th>1649</th>
      <td>id:99_J:0</td>
      <td>Facebook &gt; Youtube &gt; Google Search &gt; Organic &gt;...</td>
      <td>6864.0 &gt; 6120.0 &gt; 4824.0 &gt; 4224.0 &gt; 4056.0 &gt; 3...</td>
      <td>False</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0</td>
    </tr>
    <tr>
      <th>1650</th>
      <td>id:9_J:0</td>
      <td>Email Marketing &gt; Organic &gt; Direct &gt; Google Se...</td>
      <td>2208.0 &gt; 1560.0 &gt; 1032.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 1</td>
    </tr>
    <tr>
      <th>1651</th>
      <td>id:9_J:1</td>
      <td>Organic &gt; Organic &gt; Google Search &gt; Google Search</td>
      <td>2472.0 &gt; 2352.0 &gt; 2160.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 1</td>
    </tr>
    <tr>
      <th>1652</th>
      <td>id:9_J:2</td>
      <td>Direct &gt; Organic &gt; Instagram &gt; Direct &gt; Facebo...</td>
      <td>1680.0 &gt; 1440.0 &gt; 792.0 &gt; 408.0 &gt; 72.0 &gt; 0.0</td>
      <td>False</td>
      <td>1</td>
      <td>0 &gt; 0 &gt; 0 &gt; 0 &gt; 0 &gt; 0</td>
    </tr>
  </tbody>
</table>
<p>1653 rows × 6 columns</p>
</div>



Como trabalhamos com um grande volume de dados, sabemos que não é possivel avaliar os resultados atribuídos para cada jornada que resultou em uma transação. Assim, através da consulta do **atributo group_by_channels_models trazemos os resultados dos modelos agrupados por cada canal**. 

**Atenção:**
Os resultados agrupados não se sobrescrevem caso o mesmo modelo seja calculado mais de uma vez e ambos resultados estarão presentes no atributo group_by_channels_models.


```python
attributions.group_by_channels_models
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_last_click_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>2133</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>1033</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>3168</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>1073</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>4255</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>1028</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>6322</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>1093</td>
    </tr>
  </tbody>
</table>
</div>



E como acontece com o .DataFrame, o **group_by_channels_models também é atualizado para cada novo modelo rodado** e sem a limitação de não trazer os resultados algorítimicos


```python
attributions.attribution_shapley()
attributions.group_by_channels_models
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_last_click_heuristic</th>
      <th>attribution_shapley_size4_conv_rate_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>109</td>
      <td>74.926849</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>54</td>
      <td>70.558428</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>160</td>
      <td>160.628945</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>65</td>
      <td>110.649352</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>193</td>
      <td>202.179519</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>64</td>
      <td>72.982433</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>315</td>
      <td>265.768549</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>58</td>
      <td>60.305925</td>
    </tr>
  </tbody>
</table>
</div>



### **Sobre os modelos**

Todos os modelos heurísticos apresentam o mesmo comportamento quanto à atualização dos **atributos .DataFrame e .group_by_channels_models** e também quanto ao **output do método** que irá retornar uma **tupla contendo dois pandas Series**.


```python
attribution_first_click = attributions.attribution_first_click()
```

**O primeiro output** da tupla corresponde aos resultados na **granularidade de jornada**, similar ao resultado encontrado no .DataFrame


```python
attribution_first_click[0]
```




    0                          [1, 0, 0, 0, 0]
    1                                      [1]
    2              [1, 0, 0, 0, 0, 0, 0, 0, 0]
    3                                   [1, 0]
    4                                      [1]
                           ...                
    20512                               [1, 0]
    20513                            [1, 0, 0]
    20514    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    20515                            [1, 0, 0]
    20516                         [1, 0, 0, 0]
    Length: 20517, dtype: object



**Já o segundo** corresponde aos resultados na **granularidade de canal**, similar ao resultado encontrado no .DataFrame


```python
attribution_first_click[1]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_first_click_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>2078</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>1095</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>3177</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>1066</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>4259</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>1007</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>6361</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>1062</td>
    </tr>
  </tbody>
</table>
</div>



#### **Customização dos modelos**

Dentre os modelos presentes na classe apenas o Last Click, o First Click e Linear não possuem parametros customizáveis além do **parametro group_by_channels_models**, que recebe um **valor booleano** e que caso **falso**, **não irá retornar os resultados dos modelos agrupados por canais**.

##### **Modelo Last Click Non** 

Foi criado para replicar o comportamento padrão do Google Analytics na qual o **tráfego Direto é sobreposto** caso ocorra após alguma interação de outra origem dentro de determinado período.

Por padrão o parâmetro but_not_this_channel recebe o valor 'Direct', mas pode ser alterado para outros canais / valores de acordo com os seus canais e agrupamentos.




```python
attributions.attribution_last_click_non(but_not_this_channel='Direct')[1]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_last_click_non_Direct_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>11</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>60</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>172</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>69</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>224</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>67</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>350</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>65</td>
    </tr>
  </tbody>
</table>
</div>



##### **Modelo Position Based** 

Pode receber uma lista no parâmetro **list_positions_first_middle_last** determinando os percentuais que serão atribuídos para o ínicio, meio e fim da jornada de acordo com o contexto de negócio do seu cliente/dado. E que **por padrão** é distribuído com os percentuáis **40% para o canal introdutor, 20% distribuído para os canais intermediários e 40% para o conversor.**


```python
attributions.attribution_position_based(list_positions_first_middle_last=[0.3, 0.3, 0.4])[1]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_position_based_0.3_0.3_0.4_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>95.685085</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>57.617191</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>145.817501</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>56.340693</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>193.282305</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>54.678557</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>288.148896</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>55.629772</td>
    </tr>
  </tbody>
</table>
</div>



##### **Modelo Time Decay** 

Pode ser curtomizado quanto ao **percentual de decaimento** no parâmetro **decay_over_time** e quanto ao **tempo em horas na qual esse percentual será aplicado** no parâmetro **frequency**.

Contudo, vale salientar que caso haja mais pontos de contato entre os espaços de tempo do decaimento, o valor será distribuído igualmente para esses canais;

Exemplo de funcionamento do modelo:
- **Canais:** Facebook > Organic > Paid Search
- **Tempo até a Conversão:** 14 > 12 > 0
- **Frequência do decaimento:** 7
- **Resultados atribuídos:**
  - 25% para Facebook;
  - 25% para Organic;
  - 50% para Paid Search;



```python
attributions.attribution_time_decay(
    decay_over_time=0.6,
    frequency=7)[1]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_time_decay0.6_freq7_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>108.679538</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>54.425914</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>159.592216</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Google Display</td>
      <td>64.350107</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>192.838884</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>64.611414</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>314.920082</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Youtube</td>
      <td>58.581845</td>
    </tr>
  </tbody>
</table>
</div>



##### **Markov Chains**

**Modelo de Atribuição** baseado em **Cadeias de Markov** nos auxilia a solucionar o problema de atribuição de mídia com uma **abordagem algorítimica** baseada em dados que calcula a probabilidade de transição entre canais.

Esse modelo se comporta como os demais quanto a atualização do .DataFrame e do .group_by_channels_models, além de **retornar uma tupla** com os dois primeiros resultados representando os mesmos descritos anteriormente nos modelos heurísticos. Contudo, obtemos dois outputs, a **matriz de transição** e o **removal effect**.

Como parâmetro de entrada temos, a princípio, como indicar se irá ser considerado ou não a probabilidade de transição para o mesmo estado.


```python
attribution_markov = attributions.attribution_markov(transition_to_same_state=False)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>channels</th>
      <th>attribution_markov_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>2305.324362</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Email Marketing</td>
      <td>1237.400774</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Facebook</td>
      <td>3273.918832</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Youtube</td>
      <td>1231.183938</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Google Search</td>
      <td>4035.260685</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Instagram</td>
      <td>1205.949095</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Organic</td>
      <td>5358.270644</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Google Display</td>
      <td>1213.691671</td>
    </tr>
  </tbody>
</table>
</div>



Essa configuração **não afeta os resultados agregados** e que são atribuídos para cada canal, **mas sim os valores observados na matriz de transição**. E como inficamos **transition_to_same_state=False** a linha diagonal, que representa a auto-transição, aparece zerada.


```python
ax, fig = plt.subplots(figsize=(15,10))
sns.heatmap(attribution_markov[2].round(3), cmap="YlGnBu", annot=True, linewidths=.5)
```




    <matplotlib.axes._subplots.AxesSubplot at 0x7f97052ab320>




![png](readme-images/output_37_1.png)


**Removal Effect**, quarto output dos resultados attribution_markov, é dada pela razão entre a diferença da probabilidade total de conversão e a probabilidade de conversão sem o canal, e a probabilidade total de conversão original.


```python
ax, fig = plt.subplots(figsize=(2,5))
sns.heatmap(attribution_markov[3].round(3), cmap="YlGnBu", annot=True, linewidths=.5)
```




    <matplotlib.axes._subplots.AxesSubplot at 0x7f9705bb17b8>




![png](readme-images/output_39_1.png)


##### **Shapley Value**

Por fim, temos o segundo modelo algorítmico da classe MAM o **Shapley Value**, conceito vindo da **Teoria dos Jogos**, para distribuir a contribuição de cada jogador em um jogo de cooperação.

Modelo atribui os créditos das conversões calculando a contribuição de cada canal presente na jornada, utilizando combinações de jornadas com e sem o canal em questão. 

Parâmetro **size limita quantidade de canais únicos na jornada**, por **padrão** é definido como os **4 últimos**. Isso ocorre pois o número de iterações aumenta exponencialmente com o número de canais. Da ordem de 2N, sendo N o número de canais.   

A metodologia do cálculo das contribuições marginais pode variar através do **parâmetro order**, que por padrão calcula a contribuição da **combinação dos canais independende da ordem em que aparecem** nas diferentes jornadas.



```python
attributions.attribution_shapley(size=4, order=True, values_col='conv_rate')[0]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>combinations</th>
      <th>conversions</th>
      <th>total_sequences</th>
      <th>conversion_value</th>
      <th>conv_rate</th>
      <th>attribution_shapley_size4_conv_rate_order_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>909</td>
      <td>926</td>
      <td>909</td>
      <td>0.981641</td>
      <td>[909.0]</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Direct &gt; Email Marketing</td>
      <td>27</td>
      <td>28</td>
      <td>27</td>
      <td>0.964286</td>
      <td>[13.948270234099155, 13.051729765900845]</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Direct &gt; Email Marketing &gt; Facebook</td>
      <td>5</td>
      <td>5</td>
      <td>5</td>
      <td>1.000000</td>
      <td>[1.6636366232390172, 1.5835883671498818, 1.752...</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Direct &gt; Email Marketing &gt; Facebook &gt; Google D...</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2563402919193473, 0.2345560799963515, 0.259...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Direct &gt; Email Marketing &gt; Facebook &gt; Google S...</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2522517802130265, 0.2401286956930936, 0.255...</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>1278</th>
      <td>Youtube &gt; Organic &gt; Google Search &gt; Google Dis...</td>
      <td>1</td>
      <td>2</td>
      <td>1</td>
      <td>0.500000</td>
      <td>[0.2514214624662836, 0.24872101523605275, 0.24...</td>
    </tr>
    <tr>
      <th>1279</th>
      <td>Youtube &gt; Organic &gt; Google Search &gt; Instagram</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2544401477637237, 0.2541071889956603, 0.253...</td>
    </tr>
    <tr>
      <th>1280</th>
      <td>Youtube &gt; Organic &gt; Instagram</td>
      <td>4</td>
      <td>4</td>
      <td>4</td>
      <td>1.000000</td>
      <td>[1.2757196742326997, 1.4712839059493295, 1.252...</td>
    </tr>
    <tr>
      <th>1281</th>
      <td>Youtube &gt; Organic &gt; Instagram &gt; Facebook</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2357631944623868, 0.2610913781266248, 0.247...</td>
    </tr>
    <tr>
      <th>1282</th>
      <td>Youtube &gt; Organic &gt; Instagram &gt; Google Search</td>
      <td>3</td>
      <td>3</td>
      <td>3</td>
      <td>1.000000</td>
      <td>[0.7223482210689489, 0.7769049003203142, 0.726...</td>
    </tr>
  </tbody>
</table>
<p>1275 rows × 6 columns</p>
</div>



Por fim, parâmetro na qual o Shapley Value será calculado pode ser alterado em **values_col**, que por padrão utiliza a **taxa de conversão** que é uma forma de **considerarmos as não conversões no cálculo do modelo**. Contudo, também podemos considerar no cálculo o total de conversões ou o valor gerados pelas conversões, como demostrado abaixo. 


```python
attributions.attribution_shapley(size=3, order=False, values_col='conversions')[0]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>combinations</th>
      <th>conversions</th>
      <th>total_sequences</th>
      <th>conversion_value</th>
      <th>conv_rate</th>
      <th>attribution_shapley_size3_conversions_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Direct</td>
      <td>11</td>
      <td>18</td>
      <td>18</td>
      <td>0.611111</td>
      <td>[11.0]</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Direct &gt; Email Marketing</td>
      <td>4</td>
      <td>5</td>
      <td>5</td>
      <td>0.800000</td>
      <td>[2.0, 2.0]</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Direct &gt; Email Marketing &gt; Google Search</td>
      <td>1</td>
      <td>2</td>
      <td>2</td>
      <td>0.500000</td>
      <td>[-3.1666666666666665, -7.666666666666666, 11.8...</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Direct &gt; Email Marketing &gt; Organic</td>
      <td>4</td>
      <td>6</td>
      <td>6</td>
      <td>0.666667</td>
      <td>[-7.833333333333333, -10.833333333333332, 22.6...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Direct &gt; Facebook</td>
      <td>3</td>
      <td>4</td>
      <td>4</td>
      <td>0.750000</td>
      <td>[-8.5, 11.5]</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>75</th>
      <td>Instagram &gt; Organic &gt; Youtube</td>
      <td>46</td>
      <td>123</td>
      <td>123</td>
      <td>0.373984</td>
      <td>[5.833333333333332, 34.33333333333333, 5.83333...</td>
    </tr>
    <tr>
      <th>76</th>
      <td>Instagram &gt; Youtube</td>
      <td>2</td>
      <td>4</td>
      <td>4</td>
      <td>0.500000</td>
      <td>[2.0, 0.0]</td>
    </tr>
    <tr>
      <th>77</th>
      <td>Organic</td>
      <td>64</td>
      <td>92</td>
      <td>92</td>
      <td>0.695652</td>
      <td>[64.0]</td>
    </tr>
    <tr>
      <th>78</th>
      <td>Organic &gt; Youtube</td>
      <td>8</td>
      <td>11</td>
      <td>11</td>
      <td>0.727273</td>
      <td>[30.5, -22.5]</td>
    </tr>
    <tr>
      <th>79</th>
      <td>Youtube</td>
      <td>11</td>
      <td>15</td>
      <td>15</td>
      <td>0.733333</td>
      <td>[11.0]</td>
    </tr>
  </tbody>
</table>
<p>79 rows × 6 columns</p>
</div>



### Visualização
E agora que temos os resultados atribuídos pelos diferentes modelos guardados em nosso objeto **.group_by_channels_models** de acordo com o nosso contexto de negócio podemos plotar um gráfico e comparar os resultados.


```python
attributions.plot()
```




    <matplotlib.axes._subplots.AxesSubplot at 0x7f9705c6f048>




![png](readme-images/output_45_1.png)


Caso queira selecionar apenas os modelos algorítimicos, podemos especifica-lo no **parâmetro model_type**.


```python
attributions.plot(model_type='algorithmic')
```




    <matplotlib.axes._subplots.AxesSubplot at 0x7f9704d3b470>




![png](readme-images/output_47_1.png)

