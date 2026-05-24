--CTE para tratamento, desaninhamento e deduplicação dos eventos da base bruta do GA4
WITH events_base AS (
  SELECT
    CAST(event_date AS DATE FORMAT 'YYYYMMDD') AS date,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id,
    CONCAT(user_pseudo_id, (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')) AS session_id,
    user_pseudo_id,
    timestamp_micros(event_timestamp) AS event_timestamp,
    event_bundle_sequence_id,
    event_name,
    collected_traffic_source.manual_source,
    collected_traffic_source.manual_medium,
    collected_traffic_source.manual_campaign_name,
    collected_traffic_source.gclid,
    session_traffic_source_last_click.google_ads_campaign.campaign_name as gads_campaign_name,
    session_traffic_source_last_click.dv360_campaign.campaign_name as dv360_campaign_name,
    session_traffic_source_last_click.sa360_campaign.campaign_name as sa360_campaign_name,
    session_traffic_source_last_click.cm360_campaign.campaign_name as cm360_campaign_name,
    'zapimoveis' AS brand,
    geo.country AS country, 
    geo.region AS state,
    geo.city AS city,
    platform,
    device.category AS device,
    COALESCE((SELECT IFNULL(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'main_category'),'(not set)') AS main_category,
    COALESCE((SELECT IFNULL(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = "main_category_id" ),'(not set)') AS main_category_id,
    COALESCE((SELECT IFNULL(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'sub_category' ),'(not set)') AS sub_category,
    COALESCE((SELECT IFNULL(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = "sub_category_id" ),'(not set)') AS sub_category_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'content_group') AS content_group,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'reply_type') AS reply_type,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lead_category') AS lead_category,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'lead_type') AS lead_type,
    --Mecanismo de deduplicação
    ROW_NUMBER() OVER (PARTITION BY event_timestamp, event_name, user_pseudo_id) AS row_num,
    --Identificação do evento de conversão
    CASE WHEN event_name = 'generate_lead' THEN 1 ELSE 0 END AS is_conversion
  FROM
    `mkt-data-analytics.analytics_407374944.events_*`
  WHERE
    _TABLE_SUFFIX BETWEEN '20251101' AND '20251107'

),

-- CTE que identifica todos os eventos de conversão e o momento em que ocorreram.
leads AS (
  SELECT
    user_pseudo_id,
    event_timestamp AS lead_timestamp,
    --Identificação da ordem de cada lead gerado pelo usuário, assumindo que um usuário pode gerar mais de um lead.
    ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY event_timestamp) AS lead_sequence
  FROM
    events_base
  WHERE
    is_conversion = 1
    AND row_num = 1
),

-- Junta os eventos (touchpoints) com o lead subsequente mais próximo
touchpoints AS (
  SELECT
    t1.* EXCEPT(row_num),
    t2.lead_timestamp,
    t2.lead_sequence,
    -- Calcula a diferença de tempo (em dias) entre o touchpoint e o lead
    TIMESTAMP_DIFF(t2.lead_timestamp, t1.event_timestamp, DAY) AS days_to_lead
  FROM
    events_base AS t1
  INNER JOIN
    leads AS t2
    USING(user_pseudo_id)
  WHERE
    t1.row_num = 1
    -- Garante que o touchpoint ocorreu antes ou no momento da geração do lead
    AND t1.event_timestamp <= t2.lead_timestamp
    -- Seleciona o lead subsequente mais próximo para cada evento
    AND t2.lead_sequence = (
      SELECT MIN(lead_sequence) 
        FROM leads 
      WHERE user_pseudo_id = t1.user_pseudo_id 
      AND lead_timestamp >= t1.event_timestamp
    )
)
-- Consulta final aplicando a janela de lookback de 7 dias e a criação da coluna de canal
SELECT
  *,
  -- Placeholder para agrupamento de canais que será definido posteriormente
  'placeholder' AS channel_grouping
FROM
  touchpoints
WHERE
  -- Filtra para incluir apenas touchpoints dentro da janela de 7 dias (incluindo o próprio lead, onde days_to_lead = 0)
  days_to_lead <= 7
ORDER BY
  user_pseudo_id, lead_sequence, event_timestamp