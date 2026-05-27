"""Bronze layer storage: local file queue + DuckDB."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from pipeline.common import build_bronze_record
from pipeline.config import ensure_data_dirs, settings

BRONZE_DDL = """
CREATE TABLE IF NOT EXISTS bronze_raw_ota_searches (
    event_id VARCHAR PRIMARY KEY,
    dedup_key VARCHAR NOT NULL,
    ingestion_time TIMESTAMP NOT NULL,
    partner_id VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    payload VARCHAR NOT NULL,
    hotel_id INTEGER,
    search_timestamp TIMESTAMP
)
"""


def get_connection() -> duckdb.DuckDBPyConnection:
    ensure_data_dirs()
    conn = duckdb.connect(str(settings.duckdb_path))
    conn.execute(BRONZE_DDL)
    return conn


def enqueue_payload(payload: dict) -> dict:
    """Validate path: write to file queue and bronze table."""
    ensure_data_dirs()
    record = build_bronze_record(payload, settings.partner_id, settings.schema_version)

    queue_file = settings.bronze_queue_dir / f"{record['event_id']}.json"
    queue_file.write_text(json.dumps({"payload": payload, "record": record}), encoding="utf-8")

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO bronze_raw_ota_searches
            (event_id, dedup_key, ingestion_time, partner_id, schema_version, payload, hotel_id, search_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO NOTHING
            """,
            [
                record["event_id"],
                record["dedup_key"],
                record["ingestion_time"],
                record["partner_id"],
                record["schema_version"],
                record["payload"],
                record["hotel_id"],
                record["search_timestamp"],
            ],
        )
    finally:
        conn.close()

    return record


def write_to_dlq(reason: str, payload: dict | None = None) -> None:
    ensure_data_dirs()
    dlq_dir = settings.data_dir / "dlq"
    dlq_dir.mkdir(parents=True, exist_ok=True)
    entry = {"reason": reason, "payload": payload}
    path = dlq_dir / f"dlq_{hash(json.dumps(entry, sort_keys=True)) & 0xFFFFFFFF:08x}.json"
    path.write_text(json.dumps(entry), encoding="utf-8")


def count_bronze_rows() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM bronze_raw_ota_searches").fetchone()[0]
    finally:
        conn.close()
