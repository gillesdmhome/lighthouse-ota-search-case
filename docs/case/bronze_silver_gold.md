# Bronze → Silver → Gold Transforms

How OTA search events move through the medallion layers before reaching Market Insight.

**Orchestration:** Airflow runs dbt every 15 minutes (silver first, then gold).

---

## End-to-end flow

```
OTA JSON event
  → Dataflow lands in bronze (raw_ota_searches)
  → dbt bronze staging (stg_ota_searches)
  → dbt silver (searches_enriched)
  → dbt gold (3 trend tables)
  → Market Insight API
```

| Layer | Table / model | Grain | Purpose |
|---|---|---|---|
| Bronze | `raw_ota_searches` | One row per ingested event | Immutable audit trail; full JSON preserved |
| Bronze staging | `stg_ota_searches` | One row per event | Parse JSON into typed columns |
| Silver | `searches_enriched` | One row per unique search | Clean, deduped, analysis-ready events |
| Gold | 3 aggregate tables | One row per city + day + metric | Pre-computed dashboard metrics |

---

## What lands in bronze

Before dbt runs, Dataflow writes each validated Pub/Sub message to `ota_bronze.raw_ota_searches`:

| Column | Description |
|---|---|
| `event_id` | UUID assigned at landing |
| `dedup_key` | `SHA256(hotel_id \| timestamp \| user_country \| arrival_date)` |
| `ingestion_time` | When the event entered the warehouse |
| `payload` | Full partner JSON as a string |

Bronze is **append-only**, partitioned by ingestion date, with a **90-day TTL**.

**Model:** [`dbt/models/bronze/stg_ota_searches.sql`](../../dbt/models/bronze/stg_ota_searches.sql)

---

## Bronze → Silver

Silver is built in two dbt steps: parse bronze, then enrich and filter.

### Step 1 — Parse bronze (`stg_ota_searches`)

Extract typed fields from the JSON `payload`:

- Dates: `arrival_date`, `departure_date`
- Metrics: `length_of_stay`, `hotel_id`, coordinates
- Dimensions: `user_country`, `hotel_name`
- Timestamps: `search_timestamp` (from payload `timestamp`)

Runs **incrementally** — only rows with `ingestion_time` newer than the last run are processed.

### Step 2 — Enrich and dedupe (`searches_enriched`)

**Model:** [`dbt/models/silver/searches_enriched.sql`](../../dbt/models/silver/searches_enriched.sql)

| Transform | What happens |
|---|---|
| **Resolve city** | `LEFT JOIN dim_hotels` on `hotel_id` → `city` (city is not in the inbound JSON) |
| **Normalize country** | Map country name → ISO code (e.g. `Belgium` → `BE`); fallback: first two letters uppercased |
| **Derive `search_date`** | `DATE(search_timestamp)` — when the user performed the search |
| **Derive `los_bucket`** | Bucket length of stay for the dashboard: `1`, `2`, `3`, `4-7`, `8-14` |
| **Validate LOS** | Recompute nights as `departure_date − arrival_date` (checkout day exclusive; e.g. Mar 1 → Mar 5 = 4 nights) and drop rows where it ≠ `length_of_stay` |
| **Filter invalid rows** | Drop null dates/LOS; drop stays outside dashboard buckets (`los_bucket = 'other'`) |
| **Deduplicate** | Keep one row per `dedup_key` (latest `ingestion_time` wins — handles partner retries) |

**Materialization:** incremental merge on `dedup_key`.

### Rows excluded from silver

| Reason | Example |
|---|---|
| Missing required fields | Null `arrival_date` or `length_of_stay` |
| LOS mismatch | `length_of_stay = 4` but dates span 3 days |
| Out-of-range stay | 15-night stay (no matching LOS bucket) |
| Duplicate retry | Same `dedup_key` already ingested |

Rows with an unknown `hotel_id` are **kept** but `city` is null — they are excluded from gold via `WHERE city IS NOT NULL`.

---

## Silver → Gold

Gold reads only from `searches_enriched` where `city IS NOT NULL`. Each gold table maps to one Market Insight chart.

### Facts and dimensions in gold

**Short answer:** Gold does **not** use a Kimball-style star schema with separate `fact_*` and `dim_*` tables. It uses **three wide, pre-aggregated mart tables** — one per dashboard chart. Dimensional thinking still applies, but dimensions are **denormalized into each mart** rather than stored as joinable lookup tables.

| Layer | Modeling style | What lives here |
|---|---|---|
| **Silver** | Event-level fact table + dimension join | `searches_enriched` is one row per search (the “fact” at event grain). `dim_hotels` is the only explicit dimension table — joined in silver to resolve `city`. |
| **Gold** | Chart-specific aggregate marts | Each gold table is a **pre-computed GROUP BY** over silver. Dimension attributes (`city`, `user_country`, `los_bucket`, dates) and measures (`search_count`, `pct_of_total`, `avg_los`) sit in the **same table**. |

**Why not a star schema in gold?**

1. **Product fit** — Market Insight needs three fixed charts, not ad-hoc slicing. One table per chart keeps the GKE backend simple: filter by `city` + date range, read rows — no multi-table joins at query time.
2. **Performance** — Pre-aggregation means dashboard queries scan ~5 GB of gold, not hundreds of GB of silver events. A normalized star would still require joins and re-aggregation on every read.
3. **Scope** — The case has a small, stable set of dimensions (city, country, LOS bucket, dates). There is no need for shared conformed dimensions like `dim_date` or `dim_country` when each mart already carries the columns its chart needs.

**How star-schema concepts still map:**

```
Silver (event grain)                    Gold (aggregate marts)
─────────────────────                   ────────────────────────
searches_enriched                       gold_arrival_date_popularity
  ├─ measures: length_of_stay, …    →     city, arrival_date, search_date, search_count
  ├─ dims: city, user_country, …        gold_country_trends
  └─ joined from dim_hotels         →     city, search_date, user_country, search_count, pct_of_total, avg_los
                                          gold_los_distribution
                                    →     city, search_date, los_bucket, search_count, pct_of_total
```

- **Facts (measures):** `search_count`, `pct_of_total`, and `avg_los` — additive or semi-additive metrics derived from counting silver rows.
- **Dimensions (attributes):** `city`, `search_date`, `arrival_date`, `user_country`, `user_country_iso`, `los_bucket` — baked into each mart’s grain. They are not separate `dim_*` tables because gold never needs to join them; they were already resolved in silver.
- **`dim_hotels`:** Used only in silver. Gold never joins it — unknown hotels are filtered out upstream (`city IS NOT NULL`).

If the product later needed flexible drill-down (e.g. hotel-level trends or cross-chart filters on a shared date spine), we would introduce conformed dimensions (`dim_date`, `dim_city`, `dim_country`) and a single `fact_searches_daily` at a coarser grain. For the current Market Insight scope, **wide marts are the simpler and faster choice**.

### 1. Arrival date popularity

**Model:** [`dbt/models/gold/gold_arrival_date_popularity.sql`](../../dbt/models/gold/gold_arrival_date_popularity.sql)

**Powers:** Search level time-series chart.

```
GROUP BY city, arrival_date, search_date
→ search_count
```

Answers: *For a given city, how many searches targeted each check-in date, by search day?*

### 2. Country trends

**Model:** [`dbt/models/gold/gold_country_trends.sql`](../../dbt/models/gold/gold_country_trends.sql)

**Powers:** Top countries panel (% share + average LOS).

```
GROUP BY city, search_date, user_country
→ search_count, pct_of_total, avg_los
```

`pct_of_total` = that country's share of all searches for the city on that day.

### 3. LOS distribution

**Model:** [`dbt/models/gold/gold_los_distribution.sql`](../../dbt/models/gold/gold_los_distribution.sql)

**Powers:** Length-of-stay distribution chart.

```
GROUP BY city, search_date, los_bucket
→ search_count, pct_of_total
```

`pct_of_total` = share of searches in each LOS bucket for the city on that day.

---

## Layer comparison

| Concern | Bronze | Silver | Gold |
|---|---|---|---|
| **Data shape** | Raw JSON + metadata | Flat, typed event | Aggregated metrics |
| **Facts / dimensions** | N/A | Event fact + `dim_hotels` join | Wide marts (dims + measures in one table) |
| **City** | Not present | Joined from `dim_hotels` | Grouped by city |
| **Duplicates** | Allowed (at-least-once ingest) | Removed (`dedup_key`) | N/A (counts) |
| **Invalid events** | Stored as-is | Filtered out | Never seen |
| **Refresh** | Streaming (seconds) | Batch incremental (15 min) | Full rebuild from silver (15 min) |
| **Consumer** | Replay, audit, dbt | dbt gold models, Soda checks | Market Insight API |

---

## Related artifacts

| Artifact | Path |
|---|---|
| Hotel → city dimension | [`dbt/seeds/dim_hotels.csv`](../../dbt/seeds/dim_hotels.csv) |
| dbt tests (silver + gold) | [`dbt/models/schema.yml`](../../dbt/models/schema.yml) |
| LOS consistency test | [`dbt/tests/assert_los_consistency.sql`](../../dbt/tests/assert_los_consistency.sql) |
| Local DuckDB equivalent | [`pipeline/transforms.py`](../../pipeline/transforms.py) |
| Trend API mapping | [02_city_trends_exposure.md](02_city_trends_exposure.md) |
