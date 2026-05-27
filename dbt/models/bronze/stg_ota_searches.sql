-- Bronze staging: parse raw JSON from BigQuery landing table

with source as (
    select *
    from {{ source('ota_bronze', 'raw_ota_searches') }}
    {% if is_incremental() %}
    where ingestion_time > (select coalesce(max(ingestion_time), timestamp('1970-01-01')) from {{ this }})
    {% endif %}
),

parsed as (
    select
        event_id,
        dedup_key,
        ingestion_time,
        json_value(payload, '$.arrival_date') as arrival_date,
        json_value(payload, '$.departure_date') as departure_date,
        cast(json_value(payload, '$.length_of_stay') as int64) as length_of_stay,
        json_value(payload, '$.user_country') as user_country,
        cast(json_value(payload, '$.hotel_id') as int64) as hotel_id,
        json_value(payload, '$.hotel_name') as hotel_name,
        cast(json_value(payload, '$.hotel_latitude') as float64) as hotel_latitude,
        cast(json_value(payload, '$.hotel_longitude') as float64) as hotel_longitude,
        timestamp(json_value(payload, '$.timestamp')) as search_timestamp,
        payload as raw_payload
    from source
)

select * from parsed
