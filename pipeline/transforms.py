"""Silver and gold transforms (DuckDB) — mirrors dbt models for local execution."""

from __future__ import annotations

import duckdb

from pipeline.bronze_store import get_connection
from pipeline.config import settings


def _load_dim_hotels(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE TABLE dim_hotels AS
        SELECT * FROM read_csv_auto(?)
        """,
        [str(settings.dim_hotels_path)],
    )


def run_silver_transform(conn: duckdb.DuckDBPyConnection) -> int:
    _load_dim_hotels(conn)
    conn.execute("DROP TABLE IF EXISTS silver_searches_enriched")
    conn.execute(
        """
        CREATE TABLE silver_searches_enriched AS
        WITH staged AS (
            SELECT
                event_id,
                dedup_key,
                ingestion_time,
                partner_id,
                schema_version,
                payload,
                hotel_id,
                search_timestamp,
                json_extract_string(payload, '$.arrival_date') AS arrival_date,
                json_extract_string(payload, '$.departure_date') AS departure_date,
                CAST(json_extract_string(payload, '$.length_of_stay') AS INTEGER) AS length_of_stay,
                json_extract_string(payload, '$.user_country') AS user_country,
                json_extract_string(payload, '$.hotel_name') AS hotel_name,
                CAST(json_extract_string(payload, '$.hotel_latitude') AS DOUBLE) AS hotel_latitude,
                CAST(json_extract_string(payload, '$.hotel_longitude') AS DOUBLE) AS hotel_longitude
            FROM bronze_raw_ota_searches
        ),
        with_hotel AS (
            SELECT s.*, h.city, h.country_iso AS hotel_country_iso
            FROM staged s
            LEFT JOIN dim_hotels h ON s.hotel_id = h.hotel_id
        ),
        country_map(name, iso) AS (
            VALUES
                ('Belgium', 'BE'),
                ('Brazil', 'BR'),
                ('France', 'FR'),
                ('Germany', 'DE'),
                ('Netherlands', 'NL'),
                ('Spain', 'ES'),
                ('Switzerland', 'CH'),
                ('United Kingdom', 'GB'),
                ('United States', 'US'),
                ('USA', 'US')
        ),
        validated AS (
            SELECT
                wh.event_id,
                wh.dedup_key,
                wh.ingestion_time,
                wh.partner_id,
                wh.schema_version,
                wh.payload,
                wh.hotel_id,
                wh.search_timestamp,
                wh.arrival_date,
                wh.departure_date,
                wh.length_of_stay,
                wh.user_country,
                wh.hotel_name,
                wh.city,
                wh.hotel_latitude,
                wh.hotel_longitude,
                wh.hotel_country_iso,
                COALESCE(cm.iso, upper(left(wh.user_country, 2))) AS user_country_iso,
                CAST(wh.search_timestamp AS DATE) AS search_date,
                CASE
                    WHEN wh.length_of_stay = 1 THEN '1'
                    WHEN wh.length_of_stay = 2 THEN '2'
                    WHEN wh.length_of_stay = 3 THEN '3'
                    WHEN wh.length_of_stay BETWEEN 4 AND 7 THEN '4-7'
                    WHEN wh.length_of_stay BETWEEN 8 AND 14 THEN '8-14'
                    ELSE 'other'
                END AS los_bucket,
                date_diff(
                    'day',
                    CAST(wh.arrival_date AS DATE),
                    CAST(wh.departure_date AS DATE)
                ) AS computed_los
            FROM with_hotel wh
            LEFT JOIN country_map cm ON lower(trim(wh.user_country)) = lower(cm.name)
            WHERE wh.arrival_date IS NOT NULL
              AND wh.departure_date IS NOT NULL
              AND wh.length_of_stay IS NOT NULL
        ),
        ranked AS (
            SELECT
                *,
                row_number() OVER (PARTITION BY dedup_key ORDER BY ingestion_time DESC) AS rn
            FROM validated
            WHERE computed_los = length_of_stay
              AND los_bucket != 'other'
        )
        SELECT
            event_id, dedup_key, ingestion_time, partner_id, schema_version, payload,
            hotel_id, search_timestamp, arrival_date, departure_date, length_of_stay,
            user_country, hotel_name, city, hotel_latitude, hotel_longitude,
            hotel_country_iso, user_country_iso, search_date, los_bucket
        FROM ranked
        WHERE rn = 1
        """
    )
    return conn.execute("SELECT COUNT(*) FROM silver_searches_enriched").fetchone()[0]


def run_gold_transforms(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    conn.execute("DROP TABLE IF EXISTS gold_arrival_date_popularity")
    conn.execute(
        """
        CREATE TABLE gold_arrival_date_popularity AS
        SELECT
            city,
            CAST(arrival_date AS DATE) AS arrival_date,
            search_date,
            COUNT(*) AS search_count
        FROM silver_searches_enriched
        WHERE city IS NOT NULL
        GROUP BY city, arrival_date, search_date
        """
    )

    conn.execute("DROP TABLE IF EXISTS gold_country_trends")
    conn.execute(
        """
        CREATE TABLE gold_country_trends AS
        WITH city_totals AS (
            SELECT city, search_date, COUNT(*) AS total_searches
            FROM silver_searches_enriched
            WHERE city IS NOT NULL
            GROUP BY city, search_date
        ),
        country_counts AS (
            SELECT
                city,
                search_date,
                user_country,
                user_country_iso,
                COUNT(*) AS search_count,
                AVG(length_of_stay) AS avg_los
            FROM silver_searches_enriched
            WHERE city IS NOT NULL
            GROUP BY city, search_date, user_country, user_country_iso
        )
        SELECT
            cc.city,
            cc.search_date,
            cc.user_country,
            cc.user_country_iso,
            cc.search_count,
            round(100.0 * cc.search_count / ct.total_searches, 1) AS pct_of_total,
            round(cc.avg_los, 1) AS avg_los
        FROM country_counts cc
        JOIN city_totals ct ON cc.city = ct.city AND cc.search_date = ct.search_date
        """
    )

    conn.execute("DROP TABLE IF EXISTS gold_los_distribution")
    conn.execute(
        """
        CREATE TABLE gold_los_distribution AS
        SELECT
            city,
            search_date,
            los_bucket,
            COUNT(*) AS search_count,
            round(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY city, search_date), 1) AS pct_of_total
        FROM silver_searches_enriched
        WHERE city IS NOT NULL
        GROUP BY city, search_date, los_bucket
        """
    )

    return {
        "gold_arrival_date_popularity": conn.execute(
            "SELECT COUNT(*) FROM gold_arrival_date_popularity"
        ).fetchone()[0],
        "gold_country_trends": conn.execute("SELECT COUNT(*) FROM gold_country_trends").fetchone()[0],
        "gold_los_distribution": conn.execute("SELECT COUNT(*) FROM gold_los_distribution").fetchone()[0],
    }


def run_full_pipeline() -> dict:
    conn = get_connection()
    try:
        silver_rows = run_silver_transform(conn)
        gold_counts = run_gold_transforms(conn)
        return {"silver_rows": silver_rows, **gold_counts}
    finally:
        conn.close()
