"""Shared pipeline utilities."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone


def compute_dedup_key(payload: dict) -> str:
    raw = (
        f"{payload.get('hotel_id')}|{payload.get('timestamp')}|"
        f"{payload.get('user_country')}|{payload.get('arrival_date')}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def build_bronze_record(payload: dict, partner_id: str, schema_version: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "event_id": str(uuid.uuid4()),
        "dedup_key": compute_dedup_key(payload),
        "ingestion_time": now.isoformat(),
        "partner_id": partner_id,
        "schema_version": schema_version,
        "payload": json.dumps(payload),
        "hotel_id": payload.get("hotel_id"),
        "search_timestamp": payload.get("timestamp"),
    }
