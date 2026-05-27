variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "job_name" {
  type = string
}

variable "template_gcs_path" {
  type        = string
  description = "GCS path to Dataflow flex template"
}

variable "input_subscription" {
  type = string
}

variable "output_table" {
  type = string
}

variable "output_path" {
  type = string
}

variable "dataflow_sa_email" {
  type = string
}

variable "max_workers" {
  type    = number
  default = 4
}

variable "machine_type" {
  type    = string
  default = "n1-standard-2"
}

resource "google_dataflow_flex_template_job" "bronze_landing" {
  provider                = google-beta
  project                 = var.project_id
  region                  = var.region
  name                    = var.job_name
  container_spec_gcs_path = var.template_gcs_path

  parameters = {
    input_subscription = var.input_subscription
    output_table       = var.output_table
    output_path        = var.output_path
  }

  service_account_email = var.dataflow_sa_email
  max_workers           = var.max_workers
  machine_type          = var.machine_type
}

output "job_id" {
  value = google_dataflow_flex_template_job.bronze_landing.job_id
}
