terraform {
  backend "gcs" {
    bucket = "lighthouse-dev-tf-state"
    prefix = "ota-search/dev"
  }
}
