"""Market Insight API — expose per-city search trend metrics."""

from __future__ import annotations

from datetime import date
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from pipeline.config import ensure_data_dirs, settings

app = FastAPI(
    title="Market Insight API",
    description="City-level OTA search trends for Lighthouse Market Insight product",
    version="1.0.0",
)


class ArrivalDateTrend(BaseModel):
    arrival_date: date
    search_date: date
    search_count: int


class CountryTrend(BaseModel):
    user_country: str
    user_country_iso: str
    search_count: int
    pct_of_total: float
    avg_los: float


class LosDistribution(BaseModel):
    los_bucket: str
    search_count: int
    pct_of_total: float


class CityTrendsResponse(BaseModel):
    city: str
    from_date: date | None
    to_date: date | None
    arrival_date_popularity: list[ArrivalDateTrend]
    country_trends: list[CountryTrend]
    los_distribution: list[LosDistribution]


def _get_conn() -> duckdb.DuckDBPyConnection:
    ensure_data_dirs()
    if not settings.duckdb_path.exists():
        raise HTTPException(status_code=503, detail="Warehouse not initialized; ingest data first")
    return duckdb.connect(str(settings.duckdb_path), read_only=True)


def _table_exists(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [table]
    ).fetchone()
    return row[0] > 0


@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "market-insight-api"}


@app.get("/cities")
def list_cities() -> dict[str, list[str]]:
    conn = _get_conn()
    try:
        if not _table_exists(conn, "gold_country_trends"):
            return {"cities": []}
        rows = conn.execute(
            "SELECT DISTINCT city FROM gold_country_trends ORDER BY city"
        ).fetchall()
        return {"cities": [r[0] for r in rows]}
    finally:
        conn.close()


@app.get("/cities/{city}/trends", response_model=CityTrendsResponse)
def get_city_trends(
    city: str,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
) -> CityTrendsResponse:
    conn = _get_conn()
    try:
        for table in (
            "gold_arrival_date_popularity",
            "gold_country_trends",
            "gold_los_distribution",
        ):
            if not _table_exists(conn, table):
                raise HTTPException(
                    status_code=503,
                    detail=f"Gold table '{table}' not ready; run pipeline after ingesting data",
                )

        date_filter = ""
        params: list[Any] = [city]
        if from_date:
            date_filter += " AND search_date >= ?"
            params.append(from_date)
        if to_date:
            date_filter += " AND search_date <= ?"
            params.append(to_date)

        arrival_rows = conn.execute(
            f"""
            SELECT arrival_date, search_date, search_count
            FROM gold_arrival_date_popularity
            WHERE city = ?{date_filter}
            ORDER BY search_date, arrival_date
            """,
            params,
        ).fetchall()

        country_rows = conn.execute(
            f"""
            SELECT user_country, user_country_iso, search_count, pct_of_total, avg_los
            FROM gold_country_trends
            WHERE city = ?{date_filter}
            ORDER BY search_count DESC
            """,
            params,
        ).fetchall()

        los_rows = conn.execute(
            f"""
            SELECT los_bucket, search_count, pct_of_total
            FROM gold_los_distribution
            WHERE city = ?{date_filter}
            ORDER BY los_bucket
            """,
            params,
        ).fetchall()

        if not arrival_rows and not country_rows and not los_rows:
            raise HTTPException(status_code=404, detail=f"No trends found for city '{city}'")

        return CityTrendsResponse(
            city=city,
            from_date=from_date,
            to_date=to_date,
            arrival_date_popularity=[
                ArrivalDateTrend(arrival_date=r[0], search_date=r[1], search_count=r[2])
                for r in arrival_rows
            ],
            country_trends=[
                CountryTrend(
                    user_country=r[0],
                    user_country_iso=r[1],
                    search_count=r[2],
                    pct_of_total=float(r[3]),
                    avg_los=float(r[4]),
                )
                for r in country_rows
            ],
            los_distribution=[
                LosDistribution(los_bucket=r[0], search_count=r[1], pct_of_total=float(r[2]))
                for r in los_rows
            ],
        )
    finally:
        conn.close()


@app.get("/cities/{city}/trends/arrival-dates")
def get_arrival_trends(city: str) -> dict[str, list[dict[str, Any]]]:
    trends = get_city_trends(city)
    return {
        "city": city,
        "data": [t.model_dump() for t in trends.arrival_date_popularity],
    }


@app.get("/cities/{city}/trends/countries")
def get_country_trends(city: str) -> dict[str, list[dict[str, Any]]]:
    trends = get_city_trends(city)
    return {
        "city": city,
        "data": [t.model_dump() for t in trends.country_trends],
    }


@app.get("/cities/{city}/trends/los-distribution")
def get_los_trends(city: str) -> dict[str, list[dict[str, Any]]]:
    trends = get_city_trends(city)
    return {
        "city": city,
        "data": [t.model_dump() for t in trends.los_distribution],
    }
