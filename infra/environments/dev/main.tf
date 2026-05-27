terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  ingestion_sa_email = "${var.ingestion_sa_id}@${var.project_id}.iam.gserviceaccount.com"
  dataflow_sa_email  = "${var.dataflow_sa_id}@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_service_account" "ingestion" {
  account_id   = var.ingestion_sa_id
  display_name = "OTA Ingestion API service account"
  project      = var.project_id
}

resource "google_service_account" "dataflow" {
  account_id   = var.dataflow_sa_id
  display_name = "OTA Dataflow pipeline service account"
  project      = var.project_id
}

resource "google_storage_bucket" "bronze" {
  name     = "${var.project_id}-ota-bronze"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 30 }
    action { type = "SetStorageClass", storage_class = "NEARLINE" }
  }
}

resource "google_storage_bucket" "tf_state" {
  name     = "${var.project_id}-tf-state"
  location = var.region
  project  = var.project_id

  versioning { enabled = true }
  uniform_bucket_level_access = true
}

module "pubsub" {
  source = "../../modules/pubsub"

  project_id    = var.project_id
  topic_name    = "ota-searches"
  dlq_topic_name = "ota-searches-dlq"

  publisher_members  = ["serviceAccount:${google_service_account.ingestion.email}"]
  subscriber_members = ["serviceAccount:${google_service_account.dataflow.email}"]
}

module "bigquery" {
  source = "../../modules/bigquery"

  project_id = var.project_id
  location   = "EU"

  datasets = {
    ota_bronze = {
      description = "Raw OTA search events"
      tables = {
        raw_ota_searches = {
          description = "Append-only raw search events from Dataflow"
          schema = [
            { name = "event_id", type = "STRING", mode = "REQUIRED" },
            { name = "dedup_key", type = "STRING", mode = "REQUIRED" },
            { name = "ingestion_time", type = "TIMESTAMP", mode = "REQUIRED" },
            { name = "payload", type = "STRING", mode = "REQUIRED" },
            { name = "hotel_id", type = "INTEGER", mode = "NULLABLE" },
            { name = "search_timestamp", type = "TIMESTAMP", mode = "NULLABLE" },
          ]
          partitioning = { field = "ingestion_time", type = "DAY" }
          clustering   = ["hotel_id"]
        }
      }
    }
    ota_silver = {
      description = "Enriched OTA search events"
      tables = {}
    }
    ota_gold = {
      description = "Pre-aggregated trend metrics for Market Insight"
      tables = {}
    }
  }
}

module "cloudrun_ingestion" {
  source = "../../modules/cloudrun"

  project_id            = var.project_id
  region                = var.region
  service_name          = "ota-ingestion-api"
  image                 = var.ingestion_image
  service_account_email = google_service_account.ingestion.email
  pubsub_topic_id       = module.pubsub.topic_id
  max_instances         = var.cloudrun_max_instances
}

resource "google_project_iam_member" "ingestion_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "dataflow_bq" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_gcs" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}
