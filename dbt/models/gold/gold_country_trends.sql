-- Gold: top countries searching by city (Market Insight country panel)

with city_totals as (
    select
        city,
        search_date,
        count(*) as total_searches
    from {{ ref('searches_enriched') }}
    where city is not null
    group by city, search_date
),

country_counts as (
    select
        city,
        search_date,
        user_country,
        user_country_iso,
        count(*) as search_count,
        avg(length_of_stay) as avg_los
    from {{ ref('searches_enriched') }}
    where city is not null
    group by city, search_date, user_country, user_country_iso
)

select
    cc.city,
    cc.search_date,
    cc.user_country,
    cc.user_country_iso,
    cc.search_count,
    round(100.0 * cc.search_count / ct.total_searches, 1) as pct_of_total,
    round(cc.avg_los, 1) as avg_los
from country_counts cc
join city_totals ct
    on cc.city = ct.city
    and cc.search_date = ct.search_date
