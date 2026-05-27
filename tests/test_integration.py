"""Integration tests for the full local pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def clean_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    duckdb_path = data_dir / "warehouse.duckdb"

    import pipeline.config as cfg

    test_settings = cfg.Settings(
        data_dir=data_dir,
        bronze_queue_dir=data_dir / "bronze_queue",
        duckdb_path=duckdb_path,
        dim_hotels_path=ROOT / "dbt" / "seeds" / "dim_hotels.csv",
    )
    monkeypatch.setattr(cfg, "settings", test_settings)

    import pipeline.bronze_store as bronze_store
    import pipeline.transforms as transforms

    monkeypatch.setattr(bronze_store, "settings", test_settings)
    monkeypatch.setattr(transforms, "settings", test_settings)

    import services.market_insight_api.main as insight_api

    monkeypatch.setattr(insight_api, "settings", test_settings)

    yield data_dir
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)


VALID_EVENT = {
    "arrival_date": "2022-03-01",
    "departure_date": "2022-03-05",
    "length_of_stay": 4,
    "user_country": "Belgium",
    "hotel_id": 1235,
    "hotel_name": "Holiday Inn Manhattan",
    "hotel_latitude": 40.70825421355257,
    "hotel_longitude": -74.0142071188057,
    "timestamp": "2022-01-24T11:01:12",
    "search_results": [{"room_name": "Deluxe Suite", "price": 124, "currency": "USD"}],
}


def test_bronze_to_gold_pipeline(clean_data_dir):
    from pipeline.bronze_store import enqueue_payload
    from pipeline.transforms import run_full_pipeline
    import duckdb
    from pipeline.config import settings

    enqueue_payload(VALID_EVENT)
    enqueue_payload(
        {
            **VALID_EVENT,
            "user_country": "Germany",
            "timestamp": "2022-01-25T10:00:00",
        }
    )

    result = run_full_pipeline()
    assert result["silver_rows"] >= 2
    assert result["gold_country_trends"] >= 1

    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    cities = conn.execute("SELECT DISTINCT city FROM gold_country_trends").fetchall()
    assert ("New York",) in cities
    conn.close()


def test_dedup_same_event(clean_data_dir):
    from pipeline.bronze_store import enqueue_payload
    from pipeline.transforms import run_full_pipeline
    import duckdb
    from pipeline.config import settings

    enqueue_payload(VALID_EVENT)
    enqueue_payload(VALID_EVENT)

    result = run_full_pipeline()
    assert result["silver_rows"] == 1

    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    count = conn.execute("SELECT COUNT(*) FROM silver_searches_enriched").fetchone()[0]
    assert count == 1
    conn.close()


def test_ingestion_api_accepts_valid_event(clean_data_dir):
    from fastapi.testclient import TestClient
    from services.ingestion_api.main import app

    client = TestClient(app)
    resp = client.post(
        "/v1/searches",
        json=VALID_EVENT,
        headers={"X-API-Key": "dev-api-key-change-me"},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"


def test_ingestion_api_rejects_invalid_event(clean_data_dir):
    from fastapi.testclient import TestClient
    from services.ingestion_api.main import app

    bad = {**VALID_EVENT, "length_of_stay": 99}
    client = TestClient(app)
    resp = client.post(
        "/v1/searches",
        json=bad,
        headers={"X-API-Key": "dev-api-key-change-me"},
    )
    assert resp.status_code == 400


def test_market_insight_api_returns_trends(clean_data_dir):
    from fastapi.testclient import TestClient
    from pipeline.bronze_store import enqueue_payload
    from pipeline.transforms import run_full_pipeline
    from services.market_insight_api.main import app

    enqueue_payload(VALID_EVENT)
    run_full_pipeline()

    client = TestClient(app)
    resp = client.get("/cities/New%20York/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "New York"
    assert len(body["arrival_date_popularity"]) >= 1
    assert len(body["country_trends"]) >= 1
    assert len(body["los_distribution"]) >= 1
