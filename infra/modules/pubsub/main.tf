variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "topic_name" {
  type        = string
  description = "Primary Pub/Sub topic name"
}

variable "dlq_topic_name" {
  type        = string
  description = "Dead-letter topic name"
}

variable "publisher_members" {
  type        = list(string)
  description = "IAM members allowed to publish to the topic"
  default     = []
}

variable "subscriber_members" {
  type        = list(string)
  description = "IAM members allowed to subscribe"
  default     = []
}

resource "google_pubsub_topic" "main" {
  name    = var.topic_name
  project = var.project_id

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "dlq" {
  name    = var.dlq_topic_name
  project = var.project_id
}

resource "google_pubsub_subscription" "main" {
  name    = "${var.topic_name}-sub"
  topic   = google_pubsub_topic.main.name
  project = var.project_id

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_topic_iam_member" "publishers" {
  for_each = toset(var.publisher_members)

  project = var.project_id
  topic   = google_pubsub_topic.main.name
  role    = "roles/pubsub.publisher"
  member  = each.value
}

resource "google_pubsub_subscription_iam_member" "subscribers" {
  for_each = toset(var.subscriber_members)

  project      = var.project_id
  subscription = google_pubsub_subscription.main.name
  role         = "roles/pubsub.subscriber"
  member       = each.value
}

output "topic_id" {
  value = google_pubsub_topic.main.id
}

output "subscription_id" {
  value = google_pubsub_subscription.main.id
}

output "dlq_topic_id" {
  value = google_pubsub_topic.dlq.id
}
