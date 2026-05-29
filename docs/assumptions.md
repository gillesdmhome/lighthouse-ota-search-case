# Assumptions — OTA Search Ingestion Pipeline

This document lists explicit assumptions made while designing the pipeline for the Lighthouse Data Engineer case. State these upfront in the interview presentation.

## Data & schema

| # | Assumption | Rationale |
|---|---|---|
| 1 | **`city` is not present in the inbound JSON** | Derive city by joining `hotel_id` to Lighthouse's existing `dim_hotels` dimension table. Reverse geocoding (lat/long → city) is a fallback for unknown hotels only. |
| 2 | **`user_country` is a country name, not an ISO-3166 code** | Normalize to ISO codes in the dbt silver layer (`searches_enriched`) for consistent aggregation across partners. |
| 3 | **`length_of_stay` counts nights, not inclusive calendar days** | The case example (`arrival_date: 2022-03-01`, `departure_date: 2022-03-05`, `length_of_stay: 4`) is correct: the guest stays 4 **nights** (Mar 1–4) and checks out on Mar 5. Counting every calendar day from arrival through departure inclusive would yield 5 — that is **not** how the partner defines LOS. We treat `departure_date` as the **checkout day (exclusive end)** and validate `length_of_stay = departure_date − arrival_date` in days (same as BigQuery `DATE_DIFF`). Cross-validated at the ingestion edge (Python) and again in dbt silver; mismatches are quarantined, not silently corrected. |
| 4 | **`search_results` array contains at least one room offer** | Required by JSON Schema. Empty arrays are rejected at the edge. |
| 5 | **Schema version is `v1`** | Partner payloads include no version field; we stamp `schema_version=v1` at ingestion. Future versions use a schema registry and dual-write period. |
| 6 | **`timestamp` is the search event time in UTC** | If partner sends local time without offset, contract must be clarified. MVP assumes UTC ISO-8601. |

## Idempotency & delivery semantics

| # | Assumption | Rationale |
|---|---|---|
| 7 | **Partner may retry failed POSTs (at-least-once delivery)** | Dedup key = `SHA256(hotel_id \| timestamp \| user_country \| arrival_date)`. Applied in Dataflow bronze landing and again in dbt silver. |
| 8 | **100 req/s is sustained average, not burst peak** | Cloud Run + Pub/Sub handle this easily. Burst capacity assumed ≤ 200 req/s for 5 minutes. |
| 9 | **Partner sends one search event per POST** | No batch payloads. Request body capped at 2 KB. |

## Security & privacy

| # | Assumption | Rationale |
|---|---|---|
| 10 | **Payload contains no direct PII** (no user ID, email, IP) | GDPR scope is limited. If partner adds user segments later, a separate privacy review and aggregation-only storage applies. |
| 11 | **Partner authentication via API key + IP allowlist** | mTLS is preferred for production but API key is acceptable for MVP. Keys rotated quarterly via Secret Manager. |
| 12 | **Data residency: EU (`europe-west1`)** | All GCP resources deployed in EU region. BigQuery dataset location = EU. |
| 13 | **Raw bronze data retained 90 days** | Partition TTL on `raw_ota_searches`. Gold aggregates retained indefinitely. |

## Product integration

| # | Assumption | Rationale |
|---|---|---|
| 14 | **Market Insight product already exists on GKE** | Gold tables are consumed by the existing backend; no new read API is built in this case. |
| 15 | **Trends are refreshed every 15 minutes** | Sufficient for Market Insight dashboards. Sub-minute freshness is not required. |
| 16 | **`dim_hotels` is maintained by Lighthouse Integrations team** | Data Products team owns the join contract; unknown `hotel_id` rows get `city = NULL` and are flagged in Soda. |

## Infrastructure & operations

| # | Assumption | Rationale |
|---|---|---|
| 17 | **Single OTA partner for MVP** | Multi-partner support deferred to Phase 3 (schema registry, partner-specific validation rules). |
| 18 | **Terraform manages all GCP resources** | GitLab CI runs plan on PR, apply on merge (dev auto, prod manual). |
| 19 | **Composer 2 (small) for orchestration** | Acceptable fixed cost for production. Dev/staging use Cloud Scheduler + Cloud Run for dbt to save ~$300/mo. |
| 20 | **Atlan is already deployed** | dbt manifest auto-ingested for lineage; no greenfield governance setup needed. |

## Open questions for Lighthouse

1. Is `dim_hotels` available in BigQuery with `hotel_id → city` mapping?
2. What SLA does Market Insight require for trend freshness (15 min vs hourly)?
3. Does the existing product API query BigQuery directly or via an intermediate cache?
4. Is there an existing partner ingestion pattern (API gateway, auth) to reuse?
