# Lighthouse — OTA Search Ingestion Pipeline

Fully functional local implementation of the Lighthouse Data Engineer case, with production-ready GCP architecture artifacts.

## Technical case deliverables (one doc per slide bullet)

| # | Topic | Document |
|---|---|---|
| 1 | Receive, store, and expose data | [docs/case/01_receive_store_expose.md](docs/case/01_receive_store_expose.md) |
| 2 | Per-city trends (arrival date, country, LOS) | [docs/case/02_city_trends_exposure.md](docs/case/02_city_trends_exposure.md) |
| 3 | Architecture diagram and technologies | [docs/case/03_architecture_and_technologies.md](docs/case/03_architecture_and_technologies.md) |
| 4 | Data validation method (with code) | [docs/case/04_data_validation.md](docs/case/04_data_validation.md) |
| 5 | Infrastructure provisioning and CI/CD | [docs/case/05_infrastructure_provisioning.md](docs/case/05_infrastructure_provisioning.md) |
| 6 | Monthly cost estimate | [docs/case/06_monthly_cost_estimate.md](docs/case/06_monthly_cost_estimate.md) |
| 7 | Quality, governance, privacy, performance, errors | [docs/case/07_operational_considerations.md](docs/case/07_operational_considerations.md) |

Index: [docs/case/README.md](docs/case/README.md)

## Technical case requirements covered

| Requirement | Implementation |
|---|---|
| Receive data | `POST /v1/searches` — FastAPI ingestion API with auth + rate limiting |
| Store data | DuckDB bronze layer (local) / BigQuery (GCP via Dataflow + dbt) |
| Expose trends per city | `GET /cities/{city}/trends` — arrival dates, countries, LOS distribution |
| Architecture diagram | [docs/architecture.md](docs/architecture.md) |
| Data validation (code) | JSON Schema + [validation/validate_search_event.py](validation/validate_search_event.py) |
| IaC / Terraform / CI/CD | [infra/](infra/) + [.gitlab-ci.yml](.gitlab-ci.yml) + [docs/iac_strategy.md](docs/iac_strategy.md) |
| Cost estimate | [docs/cost_estimate.md](docs/cost_estimate.md) |
| Assumptions | [docs/assumptions.md](docs/assumptions.md) |
| Presentation | [presentation/slides.md](presentation/slides.md) |

## Quick start (local, fully functional)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run all tests (validation + integration)
pytest validation/ tests/ -v

# 3. Start APIs (two terminals, or use docker-compose)
uvicorn services.ingestion_api.main:app --port 8080 --reload
uvicorn services.market_insight_api.main:app --port 8081 --reload

# 4. Run end-to-end demo
python scripts/demo.py
```

### Docker

```bash
docker compose up --build
python scripts/demo.py
```

## API usage

### Ingest a search event

```bash
curl -X POST http://localhost:8080/v1/searches \
  -H "X-API-Key: dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "arrival_date": "2022-03-01",
    "departure_date": "2022-03-05",
    "length_of_stay": 4,
    "user_country": "Belgium",
    "hotel_id": 1235,
    "hotel_name": "Holiday Inn Manhattan",
    "hotel_latitude": 40.70825421355257,
    "hotel_longitude": -74.0142071188057,
    "timestamp": "2022-01-24T11:01:12",
    "search_results": [{"room_name": "Deluxe Suite", "price": 124, "currency": "USD"}]
  }'
```

### Get city trends (Market Insight)

```bash
curl http://localhost:8081/cities/New%20York/trends
```

Returns all three dashboard datasets:
- `arrival_date_popularity` — search level chart
- `country_trends` — top countries with % and avg LOS
- `los_distribution` — LOS1, LOS2, LOS3, LOS4-7, LOS8-14

## Project structure

```
services/ingestion_api/     FastAPI — receive & validate
services/market_insight_api/ FastAPI — expose trends per city
pipeline/                   Bronze storage + DuckDB transforms
validation/                 Edge validation (JSON Schema + Python)
streaming/                  Dataflow Beam pipeline (GCP)
dbt/                        BigQuery warehouse models (GCP)
soda/                       Data quality checks
airflow/                    Orchestration DAG
infra/                      Terraform modules
docs/                       Architecture, costs, Q&A
presentation/               Interview slide deck
```

## GCP production path

Local DuckDB pipeline mirrors the dbt models deployed on BigQuery:

```
OTA → Cloud Run (FastAPI) → Pub/Sub → Dataflow (Beam) → BigQuery bronze
  → Airflow + dbt → silver/gold → Market Insight (GKE)
```

See [docs/architecture.md](docs/architecture.md) for full design.

## Environment variables

Copy [.env.example](.env.example) to `.env`. Key settings:

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `dev-api-key-change-me` | Ingestion API authentication |
| `DATA_DIR` | `./data` | Local storage directory |
| `DUCKDB_PATH` | `./data/warehouse.duckdb` | Warehouse database |
| `PUBSUB_TOPIC` | (empty) | Enable GCP Pub/Sub publishing |

## Interview materials

- [presentation/slides.md](presentation/slides.md) — 20-slide deck
- [docs/interview_qa.md](docs/interview_qa.md) — Q&A preparation
- [docs/cost_estimate.md](docs/cost_estimate.md) — monthly cost breakdown
