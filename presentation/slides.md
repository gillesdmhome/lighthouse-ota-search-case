# Lighthouse Data Engineer Case — Presentation

**Duration:** 30 minutes | **Format:** Import into Google Slides or PowerPoint

Visual assets: [`presentation/assets/`](assets/) — 13 PNG charts and diagrams (regenerate with `python scripts/generate_presentation_assets.py`)

Each section below maps to a **case requirement** from the assignment slide. Assumptions are called out on the slides where they drive design decisions.

---

## Slide 1: Title

**OTA Search Ingestion Pipeline**

Design for Market Insight — Lighthouse Data Engineer Case

Gilles | [Date]

![Architecture overview](assets/01_architecture_overview.png)

---

## Slide 2: Case Requirements — What We Must Answer

The assignment asks for seven deliverables. This deck addresses each explicitly:

| # | Case requirement | Covered on |
|---|---|---|
| 1 | Design a system to **receive, store, and expose** data | Slides 6–11 |
| 2 | Expose **per-city trends** (arrival date, country, LOS) | Slide 11 |
| 3 | **Architecture diagram** and technology choices | Slides 5–7, 13 |
| 4 | **Validate incoming data** (with code) | Slide 12 |
| 5 | **Infrastructure provisioning**, Terraform, CI/CD | Slide 14 |
| 6 | **Monthly cost estimate** and reduction strategies | Slide 15 |
| 7 | Data quality, governance, privacy, performance, error handling | Slide 16 |

Supporting docs: `docs/case/01`–`07` · Full assumption list: `docs/assumptions.md`

---

## Slide 3: Problem Statement

**Partnership with an OTA** (booking.com, trivago, …)

- Partner sends hotel search events via HTTP POST
- We visualize trends **per city** in Market Insight:
  - Popularity of arrival dates
  - Top searcher countries (% share, avg length of stay)
  - Length-of-stay distribution

**Goal:** Receive → Store → Expose trend data to the product

![Market Insight dashboard mockup](assets/02_market_insight_dashboard.png)

---

## Slide 4: Requirements, Constraints & Assumptions Overview

![Throughput and volume](assets/11_throughput_volume.png)

| Constraint | Value |
|---|---|
| Throughput | 100 req/s sustained (~8.6M events/day) |
| Payload | ~1 KB JSON per request; one event per POST (max 2 KB) |
| Raw volume | ~260 GB/month bronze |
| Freshness | Trends refreshed every **15 minutes** |
| Privacy | No PII; city-level aggregates only |
| Residency | All GCP resources in **EU (`europe-west1`)** |

**Assumptions that shape the whole design** (details on later slides):

| Category | Key assumptions |
|---|---|
| **Data & schema** | `city` not in JSON → join `dim_hotels`; `user_country` is a name → ISO in silver; LOS = **nights** (checkout day exclusive); `search_results` ≥ 1 room; schema stamped `v1`; `timestamp` in UTC |
| **Delivery** | At-least-once partner retries → dedup key; 100 req/s average, burst ≤ 200 req/s |
| **Security & privacy** | No user ID / email / IP in payload; API key + IP allowlist for MVP; bronze TTL **90 days** |
| **Product** | Market Insight already on GKE; gold consumed by existing backend; `dim_hotels` owned by Integrations |
| **Operations** | Single partner for MVP; Terraform + GitLab CI; Composer in prod, Scheduler in dev; Atlan already deployed |

Full list: `docs/assumptions.md`

---

## Slide 5: Architecture Overview

**Case req 3:** Architecture diagram and technology choices

![Pipeline schematic](assets/14_pipeline_schematic.png)

![Architecture overview](assets/01_architecture_overview.png)

**Each step (left → right):**

| Step | Component | One-line role |
|---|---|---|
| 1 | OTA Partner | Sends search JSON via HTTPS POST (~100 req/s) |
| 2 | Cloud Load Balancer | Stable public URL, TLS, IP allowlist, traffic to Cloud Run |
| 3 | FastAPI · Cloud Run | Validate + auth → publish to Pub/Sub → `202 Accepted` |
| 4 | Pub/Sub | Durable buffer; decouples API from warehouse writes |
| ↳ | DLQ | Failed messages quarantined for audit/replay |
| 5 | Dataflow · Beam | Stream to bronze within seconds |
| 6 | BigQuery Bronze + GCS | Raw landing + immutable archive |
| 7 | Airflow + dbt | Batch transforms every 15 min |
| 8 | BigQuery Silver / Gold | Clean events → pre-aggregated dashboard metrics |
| 9 | Market Insight · GKE | Existing product reads gold tables |

Full explanations: `docs/architecture.md#architecture-overview--step-by-step`

**Lambda-inspired layering:**

| Layer | Component | Latency |
|---|---|---|
| **Speed** | Dataflow → bronze | Seconds |
| **Batch** | Airflow + dbt → silver/gold | 15 min |
| **Serving** | GKE Market Insight | Pre-aggregated reads |

See full diagram: `docs/architecture.md`

---

## Slide 6: Receive — Ingestion Layer

**Case req 1:** Receive data from the OTA partner

![Sample JSON payload](assets/12_sample_json_payload.png)

**FastAPI on Cloud Run**

- `POST /v1/searches` with API key + IP allowlist
- Sync validation: JSON Schema + Python business rules
- Response: `202 Accepted` / `400 Bad Request` / `429`
- Publish to Pub/Sub with metadata attributes

**Why Pub/Sub?** Decouples ingestion from storage; enables replay; absorbs backpressure

**Assumptions:** One search event per POST; partner may retry (at-least-once) — dedup handled downstream; API key acceptable for MVP (mTLS preferred in prod)

---

## Slide 7: Store — Streaming Layer (Bronze)

**Case req 1:** Persist raw events in the warehouse

**Dataflow — Apache Beam Python SDK**

- Read Pub/Sub → parse JSON → compute `dedup_key` + `event_id`
- Write to BigQuery `raw_ota_searches` (bronze)
- Archive raw JSON to GCS
- Invalid records → DLQ topic

Latency: events land in bronze within **seconds**

**Assumptions:** Dedup key = `SHA256(hotel_id | timestamp | user_country | arrival_date)`; bronze append-only with **90-day partition TTL**; schema version `v1` stamped at landing

---

## Slide 8: Store — Medallion Data Model

**Case req 1:** Structured storage for transforms and serving

![Medallion layers](assets/06_medallion_layers.png)

| Layer | Table | Purpose |
|---|---|---|
| **Bronze** | `raw_ota_searches` | Full JSON, append-only, partitioned by day |
| **Silver** | `searches_enriched` | Typed, city resolved, deduped, LOS bucketed |
| **Gold** | 3 trend tables | Pre-aggregated for Market Insight charts |

Partition pruning + incremental dbt models keep costs low

**Assumption:** Medallion boundaries separate audit (bronze), quality (silver), and product reads (gold)

---

## Slide 9: Transform — dbt Silver

**Case req 1:** Clean, analysis-ready events

**`searches_enriched`** (incremental, merge on `dedup_key`):

- Parse JSON from bronze
- Join `hotel_id` → city via `dim_hotels`
- Normalize country name → ISO-3166
- Validate LOS consistency (filter mismatches)
- Derive `los_bucket`: 1, 2, 3, 4-7, 8-14
- Dedupe on `dedup_key`

Tests: `unique(dedup_key)`, `not_null(city)`, `accepted_values(los_bucket)`

**Assumptions:**
- **`city` not in payload** — resolved via `dim_hotels`; unknown hotels kept with `city = NULL`, excluded from gold
- **LOS = nights, not calendar days** — e.g. Mar 1 → Mar 5 with `length_of_stay = 4` (Mar 5 is checkout); validated at edge and again in silver
- **`user_country` is a name** — normalized to ISO for consistent aggregation

Details: `docs/case/bronze_silver_gold.md`

---

## Slide 10: Transform — dbt Gold

**Case req 1 (store) + req 2 (prepare exposure):** Pre-aggregated marts for the product

Three models map 1:1 to Market Insight dashboard:

![Arrival date popularity](assets/03_arrival_date_popularity.png)

![Country trends](assets/04_country_trends.png)

![LOS distribution](assets/05_los_distribution.png)

| Model | Chart | Metrics |
|---|---|---|
| `gold_arrival_date_popularity` | Search level (time series) | search_count by arrival_date |
| `gold_country_trends` | Top countries | search_count, pct_of_total, avg_los |
| `gold_los_distribution` | Length of stay | search_count, pct by los_bucket |

Pre-aggregated → dashboard queries scan ~5 GB, not 260 GB

**Assumptions:** Gold uses **wide marts** (dims + measures in one table), not a Kimball star schema — one table per chart, no joins at read time; gold retained indefinitely

---

## Slide 11: Expose — Per-City Trends to Market Insight

**Case req 2:** Expose arrival date, country, and length-of-stay trends per city

Gold tables → existing **Market Insight backend on GKE** (no greenfield read API in prod)

| Endpoint | Returns |
|---|---|
| `GET /cities/{city}/trends` | All three trend datasets |
| `GET /cities/{city}/trends/arrival-dates` | Arrival date popularity |
| `GET /cities/{city}/trends/countries` | Country share + avg LOS |
| `GET /cities/{city}/trends/los-distribution` | LOS1–LOS8-14 buckets |

Local demo: `services/market_insight_api/` reads gold tables from DuckDB

**Assumptions:** Product queries pre-aggregated gold only — never scans bronze at request time; 15-minute refresh is sufficient (no sub-minute SLA required)

End-to-end latency: receive < 200 ms → bronze < 5 s → gold < 15 min → API < 500 ms p95

---

## Slide 12: Validate Incoming Data (With Code)

**Case req 4:** Devise and provide a validation method

![Validation layers](assets/07_validation_layers.png)

| Layer | Tool | When |
|---|---|---|
| **1. Edge** | JSON Schema + Python validator | Sync at ingestion (< 10 ms) |
| **2. Warehouse** | dbt tests | After each dbt run |
| **3. Monitoring** | Soda Core scans | After dbt, alert on anomalies |

**Primary code deliverable** — `validation/validate_search_event.py`:

```python
def validate_event(payload: dict) -> list[str]:
    """Returns error messages. Empty list = valid."""
    # JSON Schema → departure > arrival → LOS = date diff (nights)
    # → known country → positive price → allowed currency
```

**Assumptions:** `search_results` must contain ≥ 1 room; LOS mismatch quarantined, not silently corrected; unknown countries rejected at edge, normalized in silver

**Demo:** `pytest validation/` — all tests green · Schema: `schemas/ota_search_v1.json`

---

## Slide 13: Orchestration

![Airflow DAG](assets/13_orchestration_dag.png)

**Airflow (Composer) + Astronomer Cosmos**

DAG schedule: every 15 minutes — silver first, then gold

MVP alternative: Cloud Scheduler + Cloud Run (~$300/mo cheaper)

**Assumption:** Composer 2 (small) acceptable for production; dev/staging use Scheduler to save cost

---

## Slide 14: Infrastructure Provisioning & CI/CD

**Case req 5:** Strategy for provisioning, modules, state, and deployment

**Terraform** — modular, GCS remote state per environment

```
infra/modules/{pubsub, bigquery, cloudrun, dataflow}
infra/environments/{dev, staging, prod}  →  backend.tf (GCS state per env)
```

| Concern | Approach |
|---|---|
| **Resource definition** | Typed modules with variables + outputs |
| **Module usage** | Environment `main.tf` composes modules; no resources in env root |
| **State management** | Separate GCS bucket + prefix per environment |
| **Applying changes** | PR: `terraform plan` (read-only) · Merge to main: auto-apply dev · Prod: manual approval |

**GitLab CI:** validate → test (pytest + dbt) → plan → apply

**Assumptions:** Terraform manages all GCP resources; single OTA partner for MVP (multi-partner in Phase 3)

Details: `docs/case/05_infrastructure_provisioning.md`

---

## Slide 15: Monthly Cost Estimate & Reduction Strategies

**Case req 6:** Rough monthly cost and how to reduce it

![Cost breakdown](assets/08_cost_breakdown.png)

| Component | USD/mo |
|---|---|
| Cloud Run + LB | $50–120 |
| Pub/Sub + GCS | $10–25 |
| Dataflow | $150–400 |
| BigQuery | $55–220 |
| Composer | $300–500 |
| Monitoring | $20–50 |
| **Total** | **$650–1,500** |

**Cost reduction strategies:**

| Strategy | Saving | Trade-off |
|---|---|---|
| Batch-only MVP (skip Dataflow initially) | ~$150–400/mo | Bronze freshness in minutes, not seconds |
| Cloud Scheduler instead of Composer in dev | ~$300/mo | Less DAG visibility |
| Bronze partition TTL (90 days) | Storage grows sub-linear | Cannot replay beyond 90 days |
| Pre-aggregate in gold | Query cost flat as volume grows | More dbt maintenance |
| Committed use discounts (BigQuery, Dataflow) | 20–40% on compute | 1-year commitment |

Details: `docs/cost_estimate.md` · `docs/case/06_monthly_cost_estimate.md`

---

## Slide 16: Operational Concerns

**Case req 7:** Data quality, governance, privacy, performance, error handling

| Topic | Approach |
|---|---|
| **Data quality** | 3-layer validation; dbt tests block gold refresh on failure; Soda anomaly scans |
| **Governance** | Atlan lineage from dbt manifest; schema registry for v2+; Data Products owns silver/gold |
| **Privacy / GDPR** | No PII in payload; EU region; bronze TTL 90 days; city-level aggregates only; DPA with partner |
| **Performance** | Partition pruning, incremental dbt, gold pre-aggregation; dashboard scans ~5 GB |
| **Error handling** | DLQ → quarantine table; alert if error rate > 1%; unknown hotels flagged in Soda |

**Observability SLIs:** ingestion latency p99, end-to-end freshness (< 20 min), dbt success rate, API p95

Details: `docs/case/07_operational_considerations.md`

---

## Slide 17: MVP Phasing

![MVP phasing](assets/09_mvp_phasing.png)

| Phase | Scope | Cost | Timeline |
|---|---|---|---|
| **1 — MVP** | FastAPI → Pub/Sub → GCS → BQ → dbt → Market Insight | ~$200–400/mo | 2–4 weeks |
| **2 — Streaming** | Add Dataflow, DLQ, Soda | ~$500–900/mo | +2 weeks |
| **3 — Production** | Atlan, multi-partner, CUD, autoscaling | ~$650–1,500/mo | Ongoing |

**Assumption:** 100 req/s does not require maximum complexity on day one

---

## Slide 18: Open Questions for Lighthouse

From `docs/assumptions.md` — validate before production:

1. Is `dim_hotels` in BigQuery with reliable `hotel_id → city`?
2. What freshness SLA does Market Insight require (15 min vs hourly)?
3. Existing partner ingestion pattern to reuse (API gateway, auth)?
4. Does the product query BigQuery directly or via an intermediate cache?
5. Atlan onboarding workflow for new datasets?

---

## Slide 19: Summary — All Seven Requirements Addressed

| # | Requirement | Solution |
|---|---|---|
| 1 | Receive, store, expose | FastAPI → Pub/Sub → Dataflow → BQ medallion → Market Insight |
| 2 | Per-city trends | 3 gold marts + read API (`arrival`, `country`, `LOS`) |
| 3 | Architecture & tech | GCP stack diagram; Lambda speed/batch/serving |
| 4 | Validation (code) | JSON Schema + `validate_search_event.py` + dbt + Soda |
| 5 | IaC & CI/CD | Terraform modules, GCS state, GitLab plan/apply |
| 6 | Cost estimate | ~$650–1,500/mo prod; MVP ~$200–400/mo with reduction levers |
| 7 | Operational concerns | DQ gates, Atlan lineage, EU/GDPR, gold pre-aggregation, DLQ |

**Total cost:** ~$650–1,500/mo production; ~$200–400/mo MVP

Repository includes runnable local demo, dbt models, Terraform, and tests.

---

## Slide 20: Thank You

**Questions?**

Repository: all code, docs, and diagrams included

- `docs/architecture.md` — full design
- `docs/assumptions.md` — complete assumption list
- `docs/case/` — one deep-dive per case requirement
- `validation/` — runnable Python validator + tests
- `dbt/` — warehouse models
- `infra/` — Terraform modules
- `presentation/assets/` — charts and diagrams
- `docs/interview_qa.md` — Q&A preparation
