# Interview Q&A Preparation

Hard questions likely during the 30-minute case Q&A, with prepared answers.

---

## Architecture

### Why Pub/Sub instead of writing directly to BigQuery?

Three reasons:
1. **Decoupling** — ingestion API returns `202` immediately; storage latency doesn't affect partner SLA
2. **Replay** — if Dataflow or dbt fails, events are retained in Pub/Sub (7-day retention) and can be reprocessed
3. **Multiple consumers** — same stream can feed bronze landing, audit logging, and future real-time features

At 100 req/s this is not strictly necessary, but it matches Lighthouse's streaming patterns and scales cleanly to higher volumes.

### Why dbt for gold aggregations instead of Dataflow?

- **Separation of concerns** — Dataflow handles speed-layer landing (seconds); dbt handles batch transforms (15 min)
- **Testability** — dbt tests (`unique`, `accepted_values`, singular tests) are declarative and run in CI
- **Lineage** — Atlan auto-ingests dbt manifest; SQL models are self-documenting
- **Team skills** — Data Products team owns dbt models; Data Platform team owns Dataflow infra

Dataflow would be appropriate if we needed sub-minute gold refreshes or complex stateful windowing.

### Why Composer at this volume — would you start simpler?

Honestly, **no for MVP**. Phase 1 uses Cloud Scheduler + Cloud Run to run dbt (~$50/mo vs ~$400/mo). Composer is added in Phase 2 when:
- Multiple DAGs need coordination (Dataflow health + dbt + Soda + partition expiry)
- Cosmos integration provides proper dbt task dependencies
- Team needs Airflow UI for monitoring and backfills

This shows pragmatism — don't pay for Composer on day one.

---

## Data quality

### How do you handle schema evolution if the partner adds fields?

1. JSON Schema is versioned (`v1`, `v2`); `additionalProperties: true` allows unknown fields through
2. Bronze stores full JSON payload — new fields are preserved even if not yet modeled
3. dbt silver model uses explicit column extraction; new fields added via dbt model update
4. Dual-write period: accept both v1 and v2 payloads, tagged by `schema_version` attribute
5. Atlan documents schema changes; breaking changes require partner coordination

### How do you deduplicate retried POSTs?

- **Dedup key:** `SHA256(hotel_id | timestamp | user_country | arrival_date)`
- Applied at two layers:
  1. Dataflow bronze landing (assigns key, writes all events)
  2. dbt silver (`QUALIFY ROW_NUMBER() OVER (PARTITION BY dedup_key ORDER BY ingestion_time DESC) = 1`)
- Partner retries with identical payload → same dedup key → only latest kept in silver

### What happens if Dataflow lag exceeds 5 minutes?

1. Cloud Monitoring alert fires on `dataflow.googleapis.com/job/data_watermark_age`
2. Airflow health check task detects lag and skips dbt run (prevent partial data)
3. On recovery, Dataflow catches up from Pub/Sub backlog (7-day retention)
4. dbt incremental model processes all new bronze partitions in next run
5. If lag exceeds retention window → escalate to partner for backfill request

---

## Performance & scale

### Why pre-aggregate vs query bronze at request time?

- Market Insight dashboards query by city across date ranges — scanning 260 GB/month bronze for each request is expensive and slow
- Gold tables are ~5 GB total with pre-computed aggregations
- BigQuery query cost: bronze scan ~$1.30/TB vs gold scan ~$0.025/request
- Dashboard p95 latency: bronze scan ~5–25s vs gold lookup ~200ms

### How would you scale to 10,000 req/s?

| Component | Scaling action |
|---|---|
| Cloud Run | Auto-scales to ~100 instances; add min instances |
| Pub/Sub | Handles 10K msg/s natively; no change |
| Dataflow | Increase max workers (16–32); consider regional subscriptions |
| BigQuery | Partition pruning critical; consider streaming inserts → batch load |
| dbt | Increase frequency or switch gold to materialized views |
| Composer | May need medium environment |

Bottleneck would likely be Dataflow worker count — address with horizontal scaling and optimized ParDo functions.

---

## Privacy & governance

### Where does PII boundary sit if partner later adds user segments?

- Current payload: no PII (no user ID, email, IP)
- If partner adds `user_segment` or `device_id`:
  1. Privacy review required before acceptance
  2. Store in bronze only (not in silver/gold)
  3. Aggregate at segment level only if DPA permits
  4. Never expose user-level data in Market Insight API
  5. Update Atlan classification tags

### How does Atlan integrate with dbt for lineage?

- dbt generates `manifest.json` and `catalog.json` on each run
- Atlan ingests these artifacts automatically (native dbt integration)
- Lineage graph: `raw_ota_searches` → `searches_enriched` → `gold_*` → Market Insight API
- Column-level lineage from dbt model SQL
- Data stewards assign ownership and classification in Atlan UI

---

## Operations

### How do you handle a bad deploy?

| Layer | Rollback strategy |
|---|---|
| Cloud Run (ingestion) | Traffic split; instant rollback to previous revision |
| Dataflow | Drain old job, start new job from same Pub/Sub subscription |
| dbt | `dbt run --full-refresh` from previous git tag; gold tables versioned |
| Terraform | `terraform apply` with previous state; GCS state versioning |

### What SLIs do you monitor?

| SLI | Target | Alert threshold |
|---|---|---|
| Ingestion API p99 latency | < 200 ms | > 500 ms for 5 min |
| End-to-end freshness | < 20 min | > 30 min |
| Validation error rate | < 0.5% | > 1% for 10 min |
| dbt run success rate | > 99% | Any failure |
| DLQ message rate | < 0.1% | > 1% for 5 min |
| Dataflow watermark age | < 60 s | > 300 s |

---

## Lighthouse-specific

### How does this integrate with existing Market Insight?

- Gold tables live in `ota_gold` dataset
- Market Insight backend on GKE adds new data source config pointing to gold tables
- No new API endpoints — existing chart components query new gold tables
- Feature flag in product to enable OTA search trends per city

### What would you ask Lighthouse in the interview?

1. Is `dim_hotels` available in BigQuery with reliable `hotel_id → city` mapping?
2. What freshness SLA does Market Insight require for these trends?
3. Is there an existing partner ingestion pattern (API gateway, auth) to reuse?
4. Does the product query BigQuery directly or through a caching layer?
5. Which Atlan workflows are already in place for new dataset onboarding?
