output "ingestion_api_url" {
  value = module.cloudrun_ingestion.service_url
}

output "pubsub_topic" {
  value = module.pubsub.topic_id
}

output "pubsub_subscription" {
  value = module.pubsub.subscription_id
}

output "bronze_bucket" {
  value = google_storage_bucket.bronze.name
}

output "bigquery_datasets" {
  value = module.bigquery.dataset_ids
}
