-- Singular test: no rows where length_of_stay != computed date difference

select
    dedup_key,
    length_of_stay,
    arrival_date,
    departure_date
from {{ ref('searches_enriched') }}
where date_diff(
    parse_date('%Y-%m-%d', departure_date),
    parse_date('%Y-%m-%d', arrival_date),
    day
) != length_of_stay
