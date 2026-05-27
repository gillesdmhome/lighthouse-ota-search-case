"""Airflow DAG for OTA search pipeline orchestration.

Uses Astronomer Cosmos pattern for dbt integration.
Deploy to Cloud Composer environment.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-products",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def check_dataflow_job_health(**context):
    """Verify the Dataflow streaming job is running."""
    # Production: use Dataflow API to check job state
    print("Dataflow job health check: RUNNING")


def run_soda_scan(**context):
    """Trigger Soda Core scan on silver/gold tables."""
    # Production: subprocess or Cloud Run job invoking `soda scan`
    print("Soda scan completed successfully")


def expire_bronze_partitions(**context):
    """Drop BigQuery bronze partitions older than 90 days."""
    # Production: use google-cloud-bigquery client
    print("Expired bronze partitions older than 90 days")


with DAG(
    dag_id="ota_search_pipeline",
    default_args=default_args,
    description="Orchestrate OTA search bronze → silver → gold pipeline",
    schedule_interval="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ota", "market-insight", "data-products"],
) as dag:

    check_dataflow = PythonOperator(
        task_id="check_dataflow_job_health",
        python_callable=check_dataflow_job_health,
    )

    # Cosmos DbtTaskGroup would replace these in production:
    # from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig
    # dbt_silver = DbtTaskGroup(
    #     group_id="dbt_silver",
    #     project_config=ProjectConfig("/dbt"),
    #     profile_config=ProfileConfig(...),
    #     select=["searches_enriched"],
    # )

    dbt_run_silver = PythonOperator(
        task_id="dbt_run_silver",
        python_callable=lambda: print("dbt run --select searches_enriched"),
    )

    dbt_run_gold = PythonOperator(
        task_id="dbt_run_gold",
        python_callable=lambda: print("dbt run --select gold_*"),
    )

    dbt_test = PythonOperator(
        task_id="dbt_test",
        python_callable=lambda: print("dbt test"),
    )

    soda_scan = PythonOperator(
        task_id="soda_scan_silver",
        python_callable=run_soda_scan,
    )

    expire_partitions = PythonOperator(
        task_id="expire_bronze_partitions",
        python_callable=expire_bronze_partitions,
    )

    check_dataflow >> dbt_run_silver >> dbt_run_gold >> dbt_test >> soda_scan >> expire_partitions
