# Cost Estimate — OTA Search Pipeline (Production, EU)

**Assumptions:** ~260 GB/month ingested, 100 req/s sustained, moderate dashboard query load, single OTA partner, `europe-west1` region.

## Monthly cost breakdown

| Component | Estimate (USD/mo) | Calculation basis |
|---|---|---|
| Cloud Run (ingestion API) | $30–80 | 1 min instance, ~8.6M requests/mo, 512 Mi RAM |
| Cloud Load Balancer | $20–40 | 1 forwarding rule + ingress traffic |
| Pub/Sub | $5–15 | ~260 GB/month message volume |
| Dataflow streaming | $150–400 | 2–4 n1-standard-2 workers, 24/7 |
| BigQuery storage | $5–20 | ~260 GB bronze + ~5 GB gold; active storage $0.02/GB |
| BigQuery queries | $50–200 | dbt runs + dashboard queries on gold only |
| GCS bronze archive | $5–10 | Standard → Nearline after 30 days |
| Cloud Composer 2 (small) | $300–500 | Largest fixed cost; Airflow + Cosmos |
| GKE (Market Insight, existing) | $0 incremental | Shared cluster; marginal query cost only |
| Cloud Monitoring / Logging | $20–50 | Log volume controls important |
| Secret Manager | $1–5 | API keys, partner credentials |
| **Total** | **~$650–1,500/mo** | |

## Cost drivers

1. **Cloud Composer** (~30–40% of total) — fixed cost regardless of data volume
2. **Dataflow streaming** (~20–30%) — always-on workers for real-time bronze landing
3. **BigQuery queries** (~10–15%) — scales with dashboard usage and dbt frequency

## Cost reduction strategies

| Strategy | Savings | Trade-off |
|---|---|---|
| **Batch-only MVP** (skip Dataflow, micro-batch load every 5 min) | ~$150–400/mo | 5 min freshness instead of seconds |
| **Drop Composer in dev/staging** (Cloud Scheduler + Cloud Run for dbt) | ~$300/mo per env | No Airflow UI in non-prod |
| **BigQuery partition TTL** (expire bronze after 90 days) | Storage grows linearly without this | Cannot reprocess old data |
| **Pre-aggregate in gold** (avoid scanning bronze for dashboards) | Query costs stay flat as volume grows | More dbt maintenance |
| **Right-size Dataflow workers** (start with 2, autoscale to 4) | ~$75–150/mo | May lag during spikes |
| **Committed use discounts** (1-yr Dataflow/Compute CUD) | ~20–30% on compute | Upfront commitment |
| **Cloud Workflows instead of Composer** (simpler orchestration) | ~$300/mo | Less mature dbt integration |

## MVP vs production cost

| Phase | Estimated monthly cost | Notes |
|---|---|---|
| **Phase 1 (MVP)** | ~$200–400 | No Dataflow, no Composer; Cloud Scheduler + dbt on Cloud Run |
| **Phase 2 (streaming)** | ~$500–900 | Add Dataflow + Composer |
| **Phase 3 (production)** | ~$650–1,500 | Full stack, monitoring, multi-env |

## Scaling projection

At **10× volume** (1,000 req/s, 2.6 TB/month):

| Component | Impact |
|---|---|
| Cloud Run | Linear (~$300/mo with autoscaling) |
| Pub/Sub | Linear (~$50/mo) |
| Dataflow | Linear (~$1,500/mo, 8–16 workers) |
| BigQuery storage | Linear (~$50/mo) |
| BigQuery queries | Sub-linear if gold pre-aggregation holds |
| Composer | Fixed (~$500/mo) |
| **Total** | **~$2,500–4,000/mo** |

Pre-aggregated gold tables and partition pruning are critical to keep query costs sub-linear.
