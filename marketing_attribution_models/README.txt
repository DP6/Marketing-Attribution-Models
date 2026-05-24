Descrição das CTE’s

events_base: query que puxa diversas colunas da tabela bruta do GA4 e realiza alguns tratamentos para desaninhar campos em formato RECORD e também para deduplicar e ordenar eventos que são disparados por cada usuário.

leads: CTE que filtra somente os eventos de conversão “generate_lead” de cada usuário (utilizando como base o user_pseudo_id, por enquanto). Isso é feito através da regra “is_conversion”, que retorna um valor booleano que identifica se o evento em cada linha da CTE “events_base” é uma conversão ou não.

touchpoints: une os dados de eventos de cada usuário e os relaciona com os dados de geração de lead através do user_pseudo_id.


Colunas Essenciais

lead_timestamp - define o momento exato em que o evento generate_lead foi coletado. esta coluna é utilizada para calcular os valores na coluna days_to_lead.

lead_sequence - Ajuda a distinguir leads em sequência do mesmo usuário e definir o fim de cada jornada. Um mesmo usuário pode ter gerar vários leads, então esta coluna permite identificar e individualizar cada jornada, assumindo que após a geração do lead sempre consideramos que todos os eventos subsequentes daquele usuário fazem parte de uma nova jornada.

days_to_lead - Calcula a diferença em dias entre o timestamp do evento em cada linha da tabela e o timestamp da geração do lead.