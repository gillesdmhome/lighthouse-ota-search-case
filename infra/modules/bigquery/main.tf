variable "project_id" {
  type = string
}

variable "location" {
  type    = string
  default = "EU"
}

variable "datasets" {
  type = map(object({
    description = string
    tables = map(object({
      description   = string
      schema        = list(object({ name = string, type = string, mode = string }))
      partitioning  = optional(object({ field = string, type = string }))
      clustering    = optional(list(string))
    }))
  }))
}

resource "google_bigquery_dataset" "datasets" {
  for_each = var.datasets

  project     = var.project_id
  dataset_id  = each.key
  location    = var.location
  description = each.value.description

  default_partition_expiration_ms = each.key == "ota_bronze" ? 7776000000 : null # 90 days
}

resource "google_bigquery_table" "tables" {
  for_each = merge([
    for ds_key, ds in var.datasets : {
      for tbl_key, tbl in ds.tables :
      "${ds_key}.${tbl_key}" => {
        dataset_id  = ds_key
        table_id    = tbl_key
        description = tbl.description
        schema      = tbl.schema
        partitioning = tbl.partitioning
        clustering  = tbl.clustering
      }
    }
  ]...)

  project    = var.project_id
  dataset_id = google_bigquery_dataset.datasets[each.value.dataset_id].dataset_id
  table_id   = each.value.table_id

  description = each.value.description

  dynamic "time_partitioning" {
    for_each = each.value.partitioning != null ? [each.value.partitioning] : []
    content {
      type  = time_partitioning.value.type
      field = time_partitioning.value.field
    }
  }

  clustering = each.value.clustering

  schema = jsonencode(each.value.schema)
}

output "dataset_ids" {
  value = { for k, v in google_bigquery_dataset.datasets : k => v.dataset_id }
}

output "table_ids" {
  value = { for k, v in google_bigquery_table.tables : k => v.table_id }
}
