-- Gold: arrival date popularity by city (Market Insight search level chart)

select
    city,
    parse_date('%Y-%m-%d', arrival_date) as arrival_date,
    search_date,
    count(*) as search_count
from {{ ref('searches_enriched') }}
where city is not null
group by city, arrival_date, search_date
