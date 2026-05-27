# Infrastructure as Code Strategy

## Repository structure

```
infra/
  modules/
    pubsub/       Topic, subscription, DLQ, IAM
    bigquery/     Datasets, tables, partitioning, clustering
    cloudrun/     Ingestion API service
  environments/
    dev/          Development environment
    staging/      Staging (future)
    prod/         Production (future)
```

## State management

- **Backend:** GCS bucket `{project_id}-tf-state` with versioning enabled
- **Prefix:** `ota-search/{env}` per environment
- **Locking:** GCS native state locking
- **Drift detection:** Weekly scheduled `terraform plan` in GitLab CI

## Module design

- Each module owns its resources and IAM bindings
- Typed variables and outputs for composability
- Env-specific sizing via `terraform.tfvars` (e.g. Cloud Run max instances)
- Principle of least privilege: ingestion SA can publish to Pub/Sub only; Dataflow SA can write BQ + GCS

## Applying changes

| Environment | Trigger | Approval |
|---|---|---|
| dev | Merge to `main` | Auto-apply |
| staging | Merge to `main` | Manual |
| prod | Tagged release | Manual + second reviewer |

## CI/CD pipeline (GitLab CI)

1. **validate** — `terraform fmt -check`, `terraform validate`
2. **test** — `pytest validation/`, `dbt parse`
3. **plan** — `terraform plan -out=plan.tfplan` (on every PR)
4. **deploy** — `terraform apply plan.tfplan` (dev auto, prod manual)

See [`.gitlab-ci.yml`](../.gitlab-ci.yml) for the full pipeline definition.

## Deployment order

1. Terraform: Pub/Sub, BigQuery datasets, GCS buckets, service accounts
2. Docker build + push: ingestion API image
3. Terraform: Cloud Run service (references image)
4. Dataflow Flex Template deploy (via Airflow or manual)
5. Airflow DAG deploy to Composer
6. dbt models run (Cosmos-triggered)
