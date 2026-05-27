-- Gold: length-of-stay distribution by city (Market Insight LOS chart)

select
    city,
    search_date,
    los_bucket,
    count(*) as search_count,
    round(100.0 * count(*) / sum(count(*)) over (
        partition by city, search_date
    ), 1) as pct_of_total
from {{ ref('searches_enriched') }}
where city is not null
group by city, search_date, los_bucket
