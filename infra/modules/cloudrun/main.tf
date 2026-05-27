variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "service_name" {
  type = string
}

variable "image" {
  type        = string
  description = "Container image URL"
}

variable "service_account_email" {
  type = string
}

variable "pubsub_topic_id" {
  type = string
}

variable "max_instances" {
  type    = number
  default = 10
}

resource "google_cloud_run_v2_service" "ingestion" {
  name     = var.service_name
  project  = var.project_id
  location = var.region

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 1
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      env {
        name  = "PUBSUB_TOPIC"
        value = var.pubsub_topic_id
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion.name
  role     = "roles/run.invoker"
  member   = "allUsers" # Restrict to LB SA in production
}

output "service_url" {
  value = google_cloud_run_v2_service.ingestion.uri
}

output "service_name" {
  value = google_cloud_run_v2_service.ingestion.name
}
