#!/usr/bin/env python3
"""End-to-end demo: ingest sample events and print Market Insight trends."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE_EVENTS = [
    {
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
    },
    {
        "arrival_date": "2022-03-10",
        "departure_date": "2022-03-12",
        "length_of_stay": 2,
        "user_country": "Germany",
        "hotel_id": 1235,
        "hotel_name": "Holiday Inn Manhattan",
        "hotel_latitude": 40.70825421355257,
        "hotel_longitude": -74.0142071188057,
        "timestamp": "2022-01-25T09:30:00",
        "search_results": [{"room_name": "Standard Room", "price": 89, "currency": "USD"}],
    },
    {
        "arrival_date": "2022-02-14",
        "departure_date": "2022-02-15",
        "length_of_stay": 1,
        "user_country": "Switzerland",
        "hotel_id": 1236,
        "hotel_name": "Brussels Central Hotel",
        "hotel_latitude": 50.8503,
        "hotel_longitude": 4.3517,
        "timestamp": "2022-01-24T14:00:00",
        "search_results": [{"room_name": "Double Room", "price": 95, "currency": "EUR"}],
    },
    {
        "arrival_date": "2022-03-01",
        "departure_date": "2022-03-03",
        "length_of_stay": 2,
        "user_country": "United States",
        "hotel_id": 1235,
        "hotel_name": "Holiday Inn Manhattan",
        "hotel_latitude": 40.70825421355257,
        "hotel_longitude": -74.0142071188057,
        "timestamp": "2022-01-26T08:00:00",
        "search_results": [{"room_name": "King Room", "price": 150, "currency": "USD"}],
    },
]

INGESTION_URL = "http://localhost:8080"
INSIGHT_URL = "http://localhost:8081"
API_KEY = "dev-api-key-change-me"


def main() -> None:
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    print("=== Ingesting sample OTA search events ===")
    with httpx.Client(timeout=30.0) as client:
        for i, event in enumerate(SAMPLE_EVENTS, 1):
            resp = client.post(f"{INGESTION_URL}/v1/searches", headers=headers, json=event)
            print(f"  Event {i}: {resp.status_code} — {resp.json()}")

        print("\n=== Available cities ===")
        cities_resp = client.get(f"{INSIGHT_URL}/cities")
        print(json.dumps(cities_resp.json(), indent=2))

        for city in cities_resp.json().get("cities", ["New York"]):
            print(f"\n=== Market Insight trends: {city} ===")
            trends = client.get(f"{INSIGHT_URL}/cities/{city}/trends")
            print(json.dumps(trends.json(), indent=2, default=str))


if __name__ == "__main__":
    main()
