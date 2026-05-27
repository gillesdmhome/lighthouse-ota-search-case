"""Pipeline configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
BRONZE_QUEUE_DIR = DATA_DIR / "bronze_queue"
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", DATA_DIR / "warehouse.duckdb"))
DIM_HOTELS_PATH = PROJECT_ROOT / "dbt" / "seeds" / "dim_hotels.csv"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = DATA_DIR
    bronze_queue_dir: Path = BRONZE_QUEUE_DIR
    duckdb_path: Path = DUCKDB_PATH
    dim_hotels_path: Path = DIM_HOTELS_PATH
    api_key: str = os.getenv("API_KEY", "dev-api-key-change-me")
    pubsub_topic: str | None = os.getenv("PUBSUB_TOPIC")
    gcp_project_id: str | None = os.getenv("GCP_PROJECT_ID")
    partner_id: str = os.getenv("PARTNER_ID", "ota-partner-1")
    schema_version: str = "v1"
    max_request_bytes: int = 2048
    rate_limit_per_second: int = int(os.getenv("RATE_LIMIT_PER_SECOND", "100"))


settings = Settings()


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.bronze_queue_dir.mkdir(parents=True, exist_ok=True)
