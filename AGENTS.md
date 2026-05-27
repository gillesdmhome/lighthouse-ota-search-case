# Cursor Agent Brief — Lighthouse Data Engineer Case

This repository contains a **complete solution** for the Lighthouse (formerly OTA Insight) **Experienced Data Engineer system design case** (Belgium, 2025). Use this file as context when working in this repo with Cursor agents.

---

## Assignment goal

Design and implement a **data pipeline** that:

1. **Receives** hotel search events from an OTA partner (e.g. booking.com) via HTTP POST (~100 req/s, ~1 KB JSON/event)
2. **Stores** events in a warehouse using a medallion architecture (bronze → silver → gold)
3. **Exposes** per-city trend metrics to the **Market Insight** product:
   - Popularity of **arrival dates** (time series)
   - **Top searcher countries** (% share, average length of stay)
   - **Length-of-stay distribution** (LOS1, LOS2, LOS3, LOS4–7, LOS8–14)

This is an **interview deliverable** for a Data Engineer role at Lighthouse in Ghent. The case is explicitly designed to be solved with AI agent assistance. Deliverables include architecture docs, validation code, IaC strategy, cost estimate, and a 30-minute presentation.

---

## Business context

- **Lighthouse** is a hospitality data intelligence company (formerly OTA Insight)
- **Market Insight** is their product for forward-looking market demand monitoring
- The partner sends one JSON payload per hotel search; `city` is **not** in the payload — derive via `hotel_id` → `dim_hotels` join
- No PII in the payload; product shows **city-level aggregates** only
- Lighthouse stack: **GCP, Pub/Sub, BigQuery, Dataflow (Python Beam), Airflow, dbt, Terraform, Soda, Atlan, GitLab CI, GKE**

---

## What this repo contains

| Area | Path | Purpose |
|---|---|---|
| Case docs (1 per slide bullet) | `docs/case/` | Detailed breakdown of each technical case requirement |
| Architecture | `docs/architecture.md` | Full system design with mermaid diagrams |
| Assumptions | `docs/assumptions.md` | Explicit design assumptions for the interview |
| Ingestion API | `services/ingestion_api/` | FastAPI — receive & validate POST events |
| Market Insight API | `services/market_insight_api/` | FastAPI — expose per-city trends |
| Local pipeline | `pipeline/` | DuckDB bronze → silver → gold (runnable without GCP) |
| Validation | `validation/`, `schemas/` | JSON Schema + Python validator + pytest |
| dbt models | `dbt/` | BigQuery silver/gold SQL (production path) |
| Dataflow | `streaming/bronze_landing.py` | Apache Beam streaming job (GCP) |
| Terraform | `infra/` | Pub/Sub, BigQuery, Cloud Run modules |
| Airflow DAG | `airflow/dags/` | Orchestration (Cosmos pattern) |
| Soda checks | `soda/` | Warehouse data quality |
| Presentation | `presentation/slides.md` | 20-slide interview deck |
| Interview Q&A | `docs/interview_qa.md` | Prepared answers |

---

## Runnable locally (no GCP required)

```bash
pip install -r requirements.txt
pytest validation/ tests/ -v

# Terminal 1 & 2
uvicorn services.ingestion_api.main:app --port 8080
uvicorn services.market_insight_api.main:app --port 8081

python scripts/demo.py
```

Data lands in `data/warehouse.duckdb` (gitignored).

---

## Agent guidelines

When modifying this repo:

1. **Align with Lighthouse stack** — prefer GCP + dbt + Python Beam over generic alternatives unless asked otherwise
2. **Keep local path working** — changes to dbt models should be mirrored in `pipeline/transforms.py` for local DuckDB execution
3. **Don't edit** `EXTERNAL_2025_case_*.pdf` — it's the original assignment brief
4. **Validation is a key deliverable** — edge validation lives in `validation/validate_search_event.py`; keep tests green
5. **One doc per case bullet** — detailed write-ups live in `docs/case/01_*.md` through `07_*.md`
6. **Do not commit secrets** — `.env`, `data/`, credentials; see `.gitignore`
7. **Minimal scope** — this is an interview case study, not a production deployment; avoid over-engineering

---

## Sample inbound JSON (from case PDF)

```json
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
  "search_results": [
    {"room_name": "Deluxe Suite", "price": 124, "currency": "USD"}
  ]
}
```

---

## Key design decisions (do not contradict without reason)

- **Pub/Sub** between ingestion and storage (decoupling, replay, backpressure)
- **Medallion** bronze/silver/gold in BigQuery; gold pre-aggregated for dashboard reads
- **dbt** for warehouse transforms; **Python** for ingestion, Beam, Airflow DAGs, edge validation
- **Dedup key:** `SHA256(hotel_id | timestamp | user_country | arrival_date)`
- **EU data residency** (`europe-west1`, BigQuery EU)
- **Bronze TTL:** 90 days; gold retained indefinitely

---

## Where to start reading

1. `docs/case/README.md` — index of all case deliverables
2. `docs/case/01_receive_store_expose.md` — end-to-end flow
3. `README.md` — quick start and project structure
4. `presentation/slides.md` — interview presentation outline
