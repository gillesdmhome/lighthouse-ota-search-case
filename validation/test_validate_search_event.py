"""Tests for OTA search event validation."""

import copy

import pytest

from validation.validate_search_event import is_valid, validate_event

VALID_PAYLOAD = {
    "arrival_date": "2022-03-01",
    "departure_date": "2022-03-05",
    "length_of_stay": 4,
    "user_country": "Belgium",
    "hotel_id": 1235,
    "hotel_name": "Holiday Inn Manhattan",
    "hotel_latitude": 40.70825421355257,
    "hotel_longitude": -74.0142071188057,
    "timestamp": "2022-01-24T11:01:12",
    "search_results": [
        {"room_name": "Deluxe Suite", "price": 124, "currency": "USD"}
    ],
}


class TestValidPayload:
    def test_valid_payload_passes(self):
        assert validate_event(VALID_PAYLOAD) == []
        assert is_valid(VALID_PAYLOAD) is True


class TestSchemaValidation:
    def test_missing_required_field(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        del payload["hotel_id"]
        errors = validate_event(payload)
        assert any("hotel_id" in e for e in errors)

    def test_empty_search_results(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["search_results"] = []
        errors = validate_event(payload)
        assert any("search_results" in e for e in errors)

    def test_invalid_latitude(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["hotel_latitude"] = 95.0
        errors = validate_event(payload)
        assert any("hotel_latitude" in e for e in errors)

    def test_invalid_longitude(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["hotel_longitude"] = 200.0
        errors = validate_event(payload)
        assert any("hotel_longitude" in e for e in errors)

    def test_invalid_date_format(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["arrival_date"] = "01-03-2022"
        errors = validate_event(payload)
        assert any("arrival_date" in e for e in errors)


class TestBusinessRules:
    def test_los_mismatch(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["length_of_stay"] = 3
        errors = validate_event(payload)
        assert any("length_of_stay" in e for e in errors)

    def test_departure_before_arrival(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["departure_date"] = "2022-02-28"
        errors = validate_event(payload)
        assert any("departure_date" in e for e in errors)

    def test_unknown_country(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["user_country"] = "Narnia"
        errors = validate_event(payload)
        assert any("user_country" in e for e in errors)

    def test_invalid_currency(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["search_results"][0]["currency"] = "XYZ"
        errors = validate_event(payload)
        assert any("currency" in e for e in errors)

    def test_zero_price(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["search_results"][0]["price"] = 0
        errors = validate_event(payload)
        assert any("price" in e for e in errors)

    def test_negative_price(self):
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["search_results"][0]["price"] = -10
        errors = validate_event(payload)
        assert len(errors) > 0
