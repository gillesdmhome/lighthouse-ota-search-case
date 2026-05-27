"""FastAPI ingestion service — receive, validate, and store OTA search events."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pipeline.bronze_store import enqueue_payload, write_to_dlq
from pipeline.config import ensure_data_dirs, settings
from pipeline.pubsub_publisher import publish_event
from pipeline.transforms import run_full_pipeline
from validation.validate_search_event import validate_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OTA Search Ingestion API",
    description="Receives hotel search events from OTA partners",
    version="1.0.0",
)

_rate_buckets: dict[str, list[float]] = defaultdict(list)


class SearchResult(BaseModel):
    room_name: str
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class SearchEvent(BaseModel):
    arrival_date: str
    departure_date: str
    length_of_stay: int = Field(ge=1, le=365)
    user_country: str
    hotel_id: int = Field(ge=1)
    hotel_name: str
    hotel_latitude: float = Field(ge=-90, le=90)
    hotel_longitude: float = Field(ge=-180, le=180)
    timestamp: str
    search_results: list[SearchResult] = Field(min_length=1)


class IngestResponse(BaseModel):
    status: str
    event_id: str
    dedup_key: str
    ingestion_time: str


class ErrorResponse(BaseModel):
    status: str
    errors: list[str]


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def check_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_buckets[client]
    _rate_buckets[client] = [t for t in window if now - t < 1.0]
    if len(_rate_buckets[client]) >= settings.rate_limit_per_second:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    _rate_buckets[client].append(now)


@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "ingestion-api"}


@app.post(
    "/v1/searches",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
async def ingest_search(
    request: Request,
    _: None = Depends(verify_api_key),
    __: None = Depends(check_rate_limit),
) -> IngestResponse | JSONResponse:
    body = await request.body()
    if len(body) > settings.max_request_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")

    try:
        event = SearchEvent.model_validate_json(body)
    except Exception as exc:
        write_to_dlq("invalid_json", {"raw": body.decode("utf-8", errors="replace")[:500]})
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "rejected", "errors": [str(exc)]},
        )

    payload: dict[str, Any] = event.model_dump()
    errors = validate_event(payload)
    if errors:
        write_to_dlq("validation_failed", payload)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "rejected", "errors": errors},
        )

    record = enqueue_payload(payload)
    ingestion_time = datetime.now(timezone.utc).isoformat()

    publish_event(
        payload,
        attributes={
            "ingestion_time": ingestion_time,
            "partner_id": settings.partner_id,
            "schema_version": settings.schema_version,
        },
    )

    try:
        run_full_pipeline()
    except Exception as exc:
        logger.exception("Pipeline refresh failed after ingest: %s", exc)

    return IngestResponse(
        status="accepted",
        event_id=record["event_id"],
        dedup_key=record["dedup_key"],
        ingestion_time=record["ingestion_time"],
    )
