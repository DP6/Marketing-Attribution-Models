# Marketing Attribution Models

<div align="center">
<img src="https://raw.githubusercontent.com/DP6/templates-centro-de-inovacoes/main/public/images/centro_de_inovacao_dp6.png" height="100px" />
</div>

<p align="center">
  <a href="#badge">
    <img alt="semantic-release" src="https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg">
  </a>
  <a href="https://www.codacy.com/gh/DP6/Marketing-Attribution-Models/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=DP6/Marketing-Attribution-Models&amp;utm_campaign=Badge_Grade">
    <img src="https://app.codacy.com/project/badge/Grade/0d6e5f753b2b4289aa27cc572b474773"/>
  </a>
</p>
  
## 1. About the Class  
Python Class created to address problems regarding Digital Marketing Attribution.  
  
## 2. About Multi-Channel Attribution  
While browsing online, an user has multiple touchpoints before converting, which could lead to ever so longer and more complex journeys.  
  
*How to duly credit conversions and optmize investment on media?*  
  
To adress this, we apply **Attribution Models**.  
  
### 2.1 Attribution Models  
**Heuristic Models**:  
  
- **Last Interaction**:  
- Default attribution in Gogle Analytics and other media platforms such as Google Ads and Facebook Business manager;  
- Only the last touchpoint is credited for the conversion.  
  
- **Last Click Non-Direct**:  
- All direct traffic is ignored and so 100% of the result goes to the last channel through which the client got to the website before converting.  
  
- **First Interaction**:  
- The result is wholly attributed to the first touchpoint.  
  
- **Linear**:  
- Every touchpoint is equally credited.  
  
- **Time Decay**:  
- The more recent a touchpoint is, the more credit it gets.  
- **Position Based**:  
- In this model, 40% of the result is attributed to the last touchpoint, another 40% to the first and the remaining 20% is equally distributed among the midway channels.  
  
**Algotithmic Models**  
  
**Shapley Value**  
  
Used in Game Theory, this value is an estimation of the contribution of each individual player in a cooperative game.  
  
Conversions are credited to the channels by a process of permutating the journeys. In each permutation a channel is given out to estimate how essencial it is overall.  
  
**As an example**, let's look at the following hypotherical journey:  
  
Organic Search > Facebook > Direct > **$19** (as revenue)  
  
To obtain each channel's Shapley Value, we first need to consider all conversion values for the component permutations of this given journey.  
  
  
> Organic Search > **$7**  
  
> Facebook > **$6**  
  
> Direct > **$4**  
  
> Organic Search > Facebook > **$15**  
  
> Organic Search > Direct > **$7**  
  
> Facebook > Direct > **$9**  
  
> Organic Search > Facebook > Direct > **$19**  
  
The number of component joneys increases exponentially the more distinct channels you have: The rate is 2^n (2 to the power of n) for **n channels**.  
  
In other words, with 3 distinct touchpoints there are 8 permutations. **With over 15, for instance, this process is unfeasible**.  
  
By default, the order of the touchpoints isn't taken into consideration when calculating the Shapley Value, only their presence or lack there of. In order to do so, the number of permutations **increases**.  
  
With that in mind, note that it is pretty difficult to use this model when considering the order of interactions. For n channels, not only there are 2^n permutations of a given channel **i**, but also **every permutation containing i in a different position**.  
  
**Some issues and limitations of Shapley Value**  
  
- The number of distinct channels is limited by the exponential nature of the permutations.  
- When not considering the order of the touchpoints, the contribution estimated for channel A is considered the same being it preceded by B or C.  
- If the order is taken into account, the number of combinations skyrockets and if any combination does not exist among the observations the model considers that journey as existent with zero conversions.  
- Touchpoints that are unfrequent or are only present in longer journeys have their contribution underestimated.  
  
  
**Markov Chains**
A Markov Chain is a particular Stochastic process in which the probability distribution of any next state depends only on what the current state is, disregarding any preceeding states and their sequence.

In multichannel attriution, we can use the Markov Chains to calculate the probability of interaction between pairs of media channels with the **Transition Matrix**.

In regard to each channel's contribution in conversions, the **Removal Effect** comes in: For each jorney a given channel is removed and a conversion probability is calculated.

The value attributed to a channel, then, is obtained by the ratio of the difference between the probability of conversion in general and the probability once said channel is removed over the general probability again. 

In other words, the bigger a channel's removal effect, the larger their contribution is. 

**When working with Markovian Processes there are no restrictions due to the quantity or order of channels. Their sequence, itself, is a fundamental part of the algorithm.

### 2.2 References
- [Attribution Models in Marketing](https://data-science-blog.com/blog/2019/04/18/attribution-models-in-marketing/)
- [Attribution Theory: The Two Best Models for Algorithmic Marketing Attribution – Implemented in Apache Spark and R](http://datafeedtoolbox.com/attribution-theory-the-two-best-models-for-algorithmic-marketing-attribution-implemented-in-apache-spark-and-r/)
- [Game Theory Attribution: The Model You’ve Probably Never Heard Of](https://clearcode.cc/blog/game-theory-attribution/)
- [Marketing Channel Attribution With Markov Models In R](https://www.bounteous.com/insights/2016/06/30/marketing-channel-attribution-markov-models-r/?ns=l)
- [Multi-Channel Funnels Data-Driven Attribution](https://support.google.com/analytics/topic/3180362?hl=en&ref_topic=3205717)
- [Marketing Multi-Channel Attribution model with R (part 1: Markov chains concept)](https://analyzecore.com/2016/08/03/attribution-model-r-part-1/)
- [Marketing Multi-Channel Attribution model with R (part 2: practical issues)](https://analyzecore.com/2017/05/31/marketing-multi-channel-attribution-model-r-part-2-practical-issues/)
- [ml-book/shapley](https://christophm.github.io/interpretable-ml-book/shapley.html)
- [Overview of Attribution modeling in MCF](https://support.google.com/analytics/answer/1662518?hl=en)

## 3. Importing the Class
```python
>> pip install marketing_attribution_models
```
```python
from marketing_attribution_models import MAM
```

## 4. Demonstration
### Creation of the MAM Object
When **creating a MAM Object** two Data Frame **templates** can be used as input depending on what is the value of the parameter *group_channels*. 

- ***group_channels* = True**: The input Data Frame has **one session** of each user's jorney **per row**.
  - The values required in each row (in other words, the required columns) are some **distinct** user identification, a **boolean** indication of convertion or lack there of and the session's **source channel**.
- ***group_channels* = False**: The input Data Frame has **the whole journey** of each user **per row**. In case you use Google Analytics, this template can be obtained by downloading the *Top Conversion Paths* report.    
  - In this case, both the channels and time to conversion columns are agregated by journey with each touchpoint being separated by '**>**' (the bigger than sign) by default. A different separator can be set in the *path_separator* parameter.

For this demostration we'll be using a Data Frame in which the journeys are **not yet grouped**, with each row as a different session and without an unique journey id.

> **Note:** The MAM Class has a built in parameter for journey id creation, *create_journey_id_based_on_conversion*, that if **True**, an id is created based on the user id, input in the *group_channels_id_list* parameter, and the column indicating wether there is a conversion or not, whose name is defined by the *journey_with_conv_colname* parameter.

In this scenario, all sessions from each distinct user will be ordered and for every conversion a new journey id is created. However, we **highly encourage** that this journey id creation is customized based on **knowledge specific to the business in hand** and exploratory conclusions. For instance if in a given business it is noted that the average journey duration is about a week, a new critereon may be defined so that once any user doesn't have any interaction for seven days the journey breaks under the assumption there was a loss of interest. 

As for the parameters now, here's how they're configured for our *group_ channels* = True scenario:

1. A **Pandas DataFrame** is input as a database;
2. The *group_channels* parameter is set to True;
3. The name of the column containing the channels in the original DataFrame is informed though the *channels_colname* parameter;
4. The name of the boolean column that determines wether there is a conversion or not is informed through the *journey_with_conv_colname* parameter;
5. The list containing the names of the columns used to compose the journey id is informed through the *group_channels_by_id_list*. Although the list could be longer, we're creating this id based on conversions (see item 7), so the user id alone is enough.
6. The start time of each session is informed in the *group_timestamp_colname* parameter as the name of said column in the original Data Frame. It can be a date or a timestamp.
7. And finally, in our scenario, we want to generate a journey id based on the columns already indicated on the parameters *group_channels_by_id_list* and *journey_with_conv_colname* by setting *create_journey_id_based_on_conversion* as **True**.

```python
attributions = MAM(df,
    group_channels=True,
    channels_colname = 'channels',
    journey_with_conv_colname= 'has_transaction',
    group_channels_by_id_list=['user_id'],
    group_timestamp_colname = 'visitStartTime',
    create_journey_id_based_on_conversion = True)
```

In order to explore and understand the capabilities of MAM, a "Random DataFrame Generator" was implemented through the use of ***random_df*** parameter when set to **True**.

```python
attributions = MAM(random_df=True)
```
    
After the Object MAM is created, we can check out our database now with the addition of our **journey_id** and with sessions grouped in **journeys** using the **attriute *".DataFrame"***.

```python
attributions.DataFrame
```
<table>
  <thead>
    <tr>
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
      <td>0</td>
      <td>id:0_J:0</td>
      <td>Facebook</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>1</td>
      <td>id:0_J:1</td>
      <td>Google Search</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>2</td>
      <td>id:0_J:10</td>
      <td>Google Search &gt; Organic &gt; Email Marketing</td>
      <td>72.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>3</td>
      <td>id:0_J:11</td>
      <td>Organic</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>4</td>
      <td>id:0_J:12</td>
      <td>Email Marketing &gt; Facebook</td>
      <td>432.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <td>20341</td>
      <td>id:9_J:5</td>
      <td>Direct &gt; Facebook</td>
      <td>120.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20342</td>
      <td>id:9_J:6</td>
      <td>Google Search &gt; Google Search &gt; Google Search</td>
      <td>48.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20343</td>
      <td>id:9_J:7</td>
      <td>Organic &gt; Organic &gt; Google Search &gt; Google Search</td>
      <td>480.0 &gt; 480.0 &gt; 288.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20344</td>
      <td>id:9_J:8</td>
      <td>Direct &gt; Organic</td>
      <td>168.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20345</td>
      <td>id:9_J:9</td>
      <td>Google Search &gt; Organic &gt; Google Search &gt; Emai...</td>
      <td>528.0 &gt; 528.0 &gt; 408.0 &gt; 240.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
  </tbody>
</table>


This attribute is **updated** for **every attribution model** generated. Only in the case of heuristic models, a new column is appended containing the attribution value given by said model.

>**Note:** The attribute *.DataFrame* does not interfere with any model calculations. Should it be altered by usage, the following results aren't affected.

```python
attributions.attribution_last_click()
attributions.DataFrame
```

<table>
  <thead>
    <tr>
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
      <td>0</td>
      <td>id:0_J:0</td>
      <td>Facebook</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>1</td>
      <td>id:0_J:1</td>
      <td>Google Search</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>2</td>
      <td>id:0_J:10</td>
      <td>Google Search &gt; Organic &gt; Email Marketing</td>
      <td>72.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>3</td>
      <td>id:0_J:11</td>
      <td>Organic</td>
      <td>0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>4</td>
      <td>id:0_J:12</td>
      <td>Email Marketing &gt; Facebook</td>
      <td>432.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <td>20341</td>
      <td>id:9_J:5</td>
      <td>Direct &gt; Facebook</td>
      <td>120.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20342</td>
      <td>id:9_J:6</td>
      <td>Google Search &gt; Google Search &gt; Google Search</td>
      <td>48.0 &gt; 24.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20343</td>
      <td>id:9_J:7</td>
      <td>Organic &gt; Organic &gt; Google Search &gt; Google Search</td>
      <td>480.0 &gt; 480.0 &gt; 288.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20344</td>
      <td>id:9_J:8</td>
      <td>Direct &gt; Organic</td>
      <td>168.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
    <tr>
      <td>20345</td>
      <td>id:9_J:9</td>
      <td>Google Search &gt; Organic &gt; Google Search &gt; Emai...</td>
      <td>528.0 &gt; 528.0 &gt; 408.0 &gt; 240.0 &gt; 0.0</td>
      <td>True</td>
      <td>1</td>
    </tr>
  </tbody>
</table>


Usually the volume of data worked with is extensive, so it is impractical or even impossible to analyse results attributed to **each** journey with transaction. With the attribute ***group_by_channels_models***, however, all results can be seen grouped by channel.

>**Note**: Grouped results **do not overwrite** each other in case the same model is used in two distinct instances. Both (or even more) of them are shown in "*group_by_channels_models*".

```python
attributions.group_by_channels_models
```

<table>
  <thead>
    <tr>
      <th>channels</th>
      <th>attribution_last_click_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Direct</td>
      <td>2133</td>
    </tr>
    <tr>
      <td>Email Marketing</td>
      <td>1033</td>
    </tr>
    <tr>
      <td>Facebook</td>
      <td>3168</td>
    </tr>
    <tr>
      <td>Google Display</td>
      <td>1073</td>
    </tr>
    <tr>
      <td>Google Search</td>
      <td>4255</td>
    </tr>
    <tr>
      <td>Instagram</td>
      <td>1028</td>
    </tr>
    <tr>
      <td>Organic</td>
      <td>6322</td>
    </tr>
    <tr>
      <td>Youtube</td>
      <td>1093</td>
    </tr>
  </tbody>
</table>


As with the *.DataFrame* attribute, *group_by_channels_models* is also updated for every model used **without the limitation** of not displaying algorithmic results.

```python
attributions.attribution_shapley()
attributions.group_by_channels_models
```

<table>
  <thead>
    <tr>
      <th></th>
      <th>channels</th>
      <th>attribution_last_click_heuristic</th>
      <th>attribution_shapley_size4_conv_rate_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>109</td>
      <td>74.926849</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>54</td>
      <td>70.558428</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>160</td>
      <td>160.628945</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Google Display</td>
      <td>65</td>
      <td>110.649352</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>193</td>
      <td>202.179519</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>64</td>
      <td>72.982433</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>315</td>
      <td>265.768549</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Youtube</td>
      <td>58</td>
      <td>60.305925</td>
    </tr>
  </tbody>
</table>


### About the Models

All heuristic models behave the same when using the attributes *.DataFrame* and *.group_by_channels_models*, as explained before, and the **output** of all heuristic **model's methods** return a **tuple** containing two **pandas Series**.

```python
attribution_first_click = attributions.attribution_first_click()
```

The **first** Series of the tuple are the results in a **journey granularity**, similar to the observed in the *.DataFrame* attribute


```python
attribution_first_click[0]
```

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
```

The **second** one contains the results with a **channel granularity**, as seen in the **.group_by_channels_models** attribute.    

```python
attribution_first_click[1]
```

<table>
  <thead>
    <tr>
      <th></th>
      <th>channels</th>
      <th>attribution_first_click_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>2078</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>1095</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>3177</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Google Display</td>
      <td>1066</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>4259</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>1007</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>6361</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Youtube</td>
      <td>1062</td>
    </tr>
  </tbody>
</table>


#### Customizing Models

Of all models present in the Object MAM, only Last Click, First Click and Linear have **no customizable parameters** but *group_by_channels_models*, which has a **boolean value** that when set to **False** the model doesn't return the attribution goruped by channels.

##### Last Click Non- Model 

Created to replicate Google Analytics' default attriution (*Last Click Non Direct*) in which **Direct traffic** is **overwritten** in case previous interations have a specific traffic source other than Direct itself in a given timespan (6 months by default).

If unspecified, the parameter *but_not_this_channel* is set to *'Direct'*, but it can be set to any other channel of interest to the business.

```python
attributions.attribution_last_click_non(but_not_this_channel='Direct')[1]
```

<table>
  <thead>
    <tr>
      <th>channels</th>
      <th>attribution_last_click_non_Direct_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>11</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>60</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>172</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Google Display</td>
      <td>69</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>224</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>67</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>350</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Youtube</td>
      <td>65</td>
    </tr>
  </tbody>
</table>

##### Position Based Model 

This model has a parameter *list_positions_first_middle_last* in which the weights respective to the positions of channels in each journey can me specified according to **business related** decisions. The default distribution of the parameter is **40%** for the **introducing** channel, **40%** for the **converting / last** channel and **20%** for the **intermidiate** ones.

```python
attributions.attribution_position_based(list_positions_first_middle_last=[0.3, 0.3, 0.4])[1]
```

<table>
  <thead>
    <tr>
      <th></th>
      <th>channels</th>
      <th>attribution_position_based_0.3_0.3_0.4_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>95.685085</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>57.617191</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>145.817501</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Google Display</td>
      <td>56.340693</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>193.282305</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>54.678557</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>288.148896</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Youtube</td>
      <td>55.629772</td>
    </tr>
  </tbody>
</table>


##### **Time Decay Model** 

There are two customizable settings: The **decay rate**, throght the *decay_over_time** parameter, and the time (in hours) **between each decaiment** through the *frequency* parameter.

It is worth noting, however, that in case there is more than one touchpoint between frequency intervals the conversion value will be equally distributed among these channels.

As an example:
- **Channels:** Facebook > Organic > Paid Search
- **Time between touchpoints:** 14 > 12 > 0
- **Decay Frequence:** 7
- **Results:**
  - 25% goes to Facebook;
  - 25% goes to Organic;
  - 50% goes to Paid Search;
  
```python
attributions.attribution_time_decay(
    decay_over_time=0.6,
    frequency=7)[1]
```

<table>
  <thead>
    <tr>
      <th></th>
      <th>channels</th>
      <th>attribution_time_decay0.6_freq7_heuristic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>108.679538</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>54.425914</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>159.592216</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Google Display</td>
      <td>64.350107</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>192.838884</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>64.611414</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>314.920082</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Youtube</td>
      <td>58.581845</td>
    </tr>
  </tbody>
</table>


##### Markov Chains

Uppon being called, this model returns a tuple with **four** components. The first two (indexed 0 and 1) are just like with the heuristic models, with the representation of the *.DataFrame* and *.group_by_channels_models* respectively. As for the third and fourth components (indexed 2 and 3) the results are the **transition matrix** and the **removal effect table**.

To start off, it is possible to indicate if same **state transitions** are considered or not (*e.g.* Direct to Direct).

```python
attribution_markov = attributions.attribution_markov(transition_to_same_state=False)
```

<table>
  <thead>
    <tr>
      <th></th>
      <th>channels</th>
      <th>attribution_markov_algorithmic</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td>Direct</td>
      <td>2305.324362</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Email Marketing</td>
      <td>1237.400774</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Facebook</td>
      <td>3273.918832</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Youtube</td>
      <td>1231.183938</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Google Search</td>
      <td>4035.260685</td>
    </tr>
    <tr>
      <td>5</td>
      <td>Instagram</td>
      <td>1205.949095</td>
    </tr>
    <tr>
      <td>6</td>
      <td>Organic</td>
      <td>5358.270644</td>
    </tr>
    <tr>
      <td>7</td>
      <td>Google Display</td>
      <td>1213.691671</td>
    </tr>
  </tbody>
</table>


This configuration **does not affect** the overall attributed results for each channel, but the values observed in the **transition matrix**. Because we set *transition_to_same_state* to **False**, the diagonal, indicating states transitioning to themselves, is nulled.

```python
ax, fig = plt.subplots(figsize=(15,10))
sns.heatmap(attribution_markov[2].round(3), cmap="YlGnBu", annot=True, linewidths=.5)
```

![png](readme-images/output_37_1.png)

**Removal Effect**, the fourth *attribution_markov* output, is obtained by the ratio of the difference between the probability of conversion in general and the probability once said channel is removed over the general probability again.

```python
ax, fig = plt.subplots(figsize=(2,5))
sns.heatmap(attribution_markov[3].round(3), cmap="YlGnBu", annot=True, linewidths=.5)
```

![png](readme-images/output_39_1.png)

##### Shapley Value

Finally, the second algorith model of **MAM** whose concept comes from **Game Theory**. The objective here is to distribute the contribution of each player (in our case, channel) in a game of cooperation calculated using combinations of journeys with and without a given channel.

The parameter **size** defines a limit of how **long** a **chain of channels** is in every journey. By default, it's value is set to **4**, meaning only the **four last channels preceding a conversion** are considered.

The calculation method of marginal contributions of each channel can vary with the ***order*** parameter. By default it is set to **False**, which means the contribution is calculated disregarding the order of each channel in the journeys.

```python
attributions.attribution_shapley(size=4, order=True, values_col='conv_rate')[0]
```

<table>
  <thead>
    <tr>
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
      <td>0</td>
      <td>Direct</td>
      <td>909</td>
      <td>926</td>
      <td>909</td>
      <td>0.981641</td>
      <td>[909.0]</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Direct &gt; Email Marketing</td>
      <td>27</td>
      <td>28</td>
      <td>27</td>
      <td>0.964286</td>
      <td>[13.948270234099155, 13.051729765900845]</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Direct &gt; Email Marketing &gt; Facebook</td>
      <td>5</td>
      <td>5</td>
      <td>5</td>
      <td>1.000000</td>
      <td>[1.6636366232390172, 1.5835883671498818, 1.752...</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Direct &gt; Email Marketing &gt; Facebook &gt; Google D...</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2563402919193473, 0.2345560799963515, 0.259...</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Direct &gt; Email Marketing &gt; Facebook &gt; Google S...</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2522517802130265, 0.2401286956930936, 0.255...</td>
    </tr>
    <tr>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <td>1278</td>
      <td>Youtube &gt; Organic &gt; Google Search &gt; Google Dis...</td>
      <td>1</td>
      <td>2</td>
      <td>1</td>
      <td>0.500000</td>
      <td>[0.2514214624662836, 0.24872101523605275, 0.24...</td>
    </tr>
    <tr>
      <td>1279</td>
      <td>Youtube &gt; Organic &gt; Google Search &gt; Instagram</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2544401477637237, 0.2541071889956603, 0.253...</td>
    </tr>
    <tr>
      <td>1280</td>
      <td>Youtube &gt; Organic &gt; Instagram</td>
      <td>4</td>
      <td>4</td>
      <td>4</td>
      <td>1.000000</td>
      <td>[1.2757196742326997, 1.4712839059493295, 1.252...</td>
    </tr>
    <tr>
      <td>1281</td>
      <td>Youtube &gt; Organic &gt; Instagram &gt; Facebook</td>
      <td>1</td>
      <td>1</td>
      <td>1</td>
      <td>1.000000</td>
      <td>[0.2357631944623868, 0.2610913781266248, 0.247...</td>
    </tr>
    <tr>
      <td>1282</td>
      <td>Youtube &gt; Organic &gt; Instagram &gt; Google Search</td>
      <td>3</td>
      <td>3</td>
      <td>3</td>
      <td>1.000000</td>
      <td>[0.7223482210689489, 0.7769049003203142, 0.726...</td>
    </tr>
  </tbody>
</table>


Finally, the parameter indicating what metric is used to calculate the Shapley Value is **values_col**, which by default is set to *conversion rate*. In doing so, journeys **without conversions** are taken into acount. 

It is possible, however, to consider only **literal conversions** when using the model as seen below.

```python
attributions.attribution_shapley(size=3, order=False, values_col='conversions')[0]
```

<table>
  <thead>
    <tr>
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
      <td>0</td>
      <td>Direct</td>
      <td>11</td>
      <td>18</td>
      <td>18</td>
      <td>0.611111</td>
      <td>[11.0]</td>
    </tr>
    <tr>
      <td>1</td>
      <td>Direct &gt; Email Marketing</td>
      <td>4</td>
      <td>5</td>
      <td>5</td>
      <td>0.800000</td>
      <td>[2.0, 2.0]</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Direct &gt; Email Marketing &gt; Google Search</td>
      <td>1</td>
      <td>2</td>
      <td>2</td>
      <td>0.500000</td>
      <td>[-3.1666666666666665, -7.666666666666666, 11.8...</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Direct &gt; Email Marketing &gt; Organic</td>
      <td>4</td>
      <td>6</td>
      <td>6</td>
      <td>0.666667</td>
      <td>[-7.833333333333333, -10.833333333333332, 22.6...</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Direct &gt; Facebook</td>
      <td>3</td>
      <td>4</td>
      <td>4</td>
      <td>0.750000</td>
      <td>[-8.5, 11.5]</td>
    </tr>
    <tr>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <td>75</td>
      <td>Instagram &gt; Organic &gt; Youtube</td>
      <td>46</td>
      <td>123</td>
      <td>123</td>
      <td>0.373984</td>
      <td>[5.833333333333332, 34.33333333333333, 5.83333...</td>
    </tr>
    <tr>
      <td>76</td>
      <td>Instagram &gt; Youtube</td>
      <td>2</td>
      <td>4</td>
      <td>4</td>
      <td>0.500000</td>
      <td>[2.0, 0.0]</td>
    </tr>
    <tr>
      <td>77</td>
      <td>Organic</td>
      <td>64</td>
      <td>92</td>
      <td>92</td>
      <td>0.695652</td>
      <td>[64.0]</td>
    </tr>
    <tr>
      <td>78</td>
      <td>Organic &gt; Youtube</td>
      <td>8</td>
      <td>11</td>
      <td>11</td>
      <td>0.727273</td>
      <td>[30.5, -22.5]</td>
    </tr>
    <tr>
      <td>79</td>
      <td>Youtube</td>
      <td>11</td>
      <td>15</td>
      <td>15</td>
      <td>0.733333</td>
      <td>[11.0]</td>
    </tr>
  </tbody>
</table>


### Visualization
After obtaining every attribution from different models stored in our ***.group_by_channels_models*** object it is possible to plot and compare results for insights

```python
attributions.plot()
```
![png](readme-images/output_45_1.png)

In case you're only interested in the algorithmic models, this can me specified in the *model_type* parameter.

```python
attributions.plot(model_type='algorithmic')
```

![png](readme-images/output_47_1.png)
