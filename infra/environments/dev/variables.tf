variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "ingestion_sa_id" {
  type    = string
  default = "ota-ingestion-sa"
}

variable "dataflow_sa_id" {
  type    = string
  default = "ota-dataflow-sa"
}

variable "ingestion_image" {
  type    = string
  default = "gcr.io/lighthouse-dev/ota-ingestion-api:latest"
}

variable "cloudrun_max_instances" {
  type    = number
  default = 5
}
