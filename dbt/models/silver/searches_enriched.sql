{{ config(
    materialized='incremental',
    unique_key='dedup_key',
    incremental_strategy='merge'
) }}

-- Silver: enriched, deduped search events with city and normalized country

with staged as (
    select * from {{ ref('stg_ota_searches') }}
    {% if is_incremental() %}
    where ingestion_time > (select coalesce(max(ingestion_time), timestamp('1970-01-01')) from {{ this }})
    {% endif %}
),

with_hotel as (
    select
        s.*,
        h.city,
        h.country_iso as hotel_country_iso
    from staged s
    left join {{ ref('dim_hotels') }} h
        on s.hotel_id = h.hotel_id
),

country_map as (
    select * from unnest([
        struct('Belgium' as name, 'BE' as iso),
        struct('Brazil', 'BR'),
        struct('France', 'FR'),
        struct('Germany', 'DE'),
        struct('Netherlands', 'NL'),
        struct('Spain', 'ES'),
        struct('Switzerland', 'CH'),
        struct('United Kingdom', 'GB'),
        struct('United States', 'US'),
        struct('USA', 'US')
    ])
),

validated as (
    select
        wh.event_id,
        wh.dedup_key,
        wh.ingestion_time,
        wh.arrival_date,
        wh.departure_date,
        wh.length_of_stay,
        wh.user_country,
        coalesce(cm.iso, upper(left(wh.user_country, 2))) as user_country_iso,
        wh.hotel_id,
        wh.hotel_name,
        wh.city,
        wh.hotel_latitude,
        wh.hotel_longitude,
        wh.search_timestamp,
        date(wh.search_timestamp) as search_date,
        case
            when wh.length_of_stay = 1 then '1'
            when wh.length_of_stay = 2 then '2'
            when wh.length_of_stay = 3 then '3'
            when wh.length_of_stay between 4 and 7 then '4-7'
            when wh.length_of_stay between 8 and 14 then '8-14'
            else 'other'
        end as los_bucket,
        date_diff(
            parse_date('%Y-%m-%d', wh.departure_date),
            parse_date('%Y-%m-%d', wh.arrival_date),
            day
        ) as computed_los
    from with_hotel wh
    left join country_map cm
        on lower(trim(wh.user_country)) = lower(cm.name)
    where wh.arrival_date is not null
      and wh.departure_date is not null
      and wh.length_of_stay is not null
),

deduped as (
    select *
    from validated
    where computed_los = length_of_stay
      and los_bucket != 'other'
    qualify row_number() over (partition by dedup_key order by ingestion_time desc) = 1
)

select * except(computed_los) from deduped
