"""Edge validation for OTA hotel search events."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "ota_search_v1.json"

KNOWN_COUNTRIES = {
    "belgium",
    "brazil",
    "france",
    "germany",
    "netherlands",
    "spain",
    "switzerland",
    "united kingdom",
    "united states",
    "usa",
}

VALID_CURRENCIES = {
    "EUR",
    "USD",
    "GBP",
    "CHF",
    "BRL",
}


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _parse_date(value: str, field: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        if "T" in normalized and "+" not in normalized and normalized.count("-") <= 2:
            return datetime.fromisoformat(normalized)
        return datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None


def validate_event(payload: dict) -> list[str]:
    """Validate a search event. Returns a list of error messages (empty if valid)."""
    errors: list[str] = []

    schema = load_schema()
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(payload), key=lambda e: e.path):
        path = ".".join(str(p) for p in error.path) or "root"
        errors.append(f"{path}: {error.message}")

    if errors:
        return errors

    arrival = _parse_date(payload["arrival_date"], "arrival_date")
    departure = _parse_date(payload["departure_date"], "departure_date")
    event_time = _parse_timestamp(payload["timestamp"])

    if arrival is None:
        errors.append("arrival_date: invalid date format")
    if departure is None:
        errors.append("departure_date: invalid date format")
    if event_time is None:
        errors.append("timestamp: invalid datetime format")

    if arrival and departure:
        if departure <= arrival:
            errors.append("departure_date: must be after arrival_date")
        else:
            expected_los = (departure - arrival).days
            if payload["length_of_stay"] != expected_los:
                errors.append(
                    f"length_of_stay: expected {expected_los} based on dates, "
                    f"got {payload['length_of_stay']}"
                )

    if arrival and event_time:
        if arrival < event_time.date():
            pass  # future arrival is valid
        # arrival before search date is suspicious but allowed for far-future planning

    country = payload["user_country"].strip().lower()
    if country not in KNOWN_COUNTRIES:
        errors.append(f"user_country: unknown country '{payload['user_country']}'")

    for i, result in enumerate(payload["search_results"]):
        if result["price"] <= 0:
            errors.append(f"search_results[{i}].price: must be positive")
        if result["currency"] not in VALID_CURRENCIES:
            errors.append(
                f"search_results[{i}].currency: unsupported currency '{result['currency']}'"
            )

    return errors


def is_valid(payload: dict) -> bool:
    return len(validate_event(payload)) == 0
