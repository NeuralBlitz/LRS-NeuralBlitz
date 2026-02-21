# Terraform Configuration for NeuralBlitz Cloud Run Infrastructure

terraform {
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

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "neuralblitz-cloud-run"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "containerregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
  ])
  service = each.value
}

# Service Account
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Cloud Run Service Account"
  depends_on   = [google_project_service.apis]
}

# IAM Bindings
resource "google_project_iam_member" "datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Storage Bucket
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.project_id}-data"
  location      = var.region
  force_destroy = false
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }
  
  depends_on = [google_project_service.apis]
}

# Pub/Sub Topic
resource "google_pubsub_topic" "events" {
  name       = "neuralblitz-events"
  depends_on = [google_project_service.apis]
}

# Firestore Database
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_project_service.apis]
}

# Cloud Run Service
resource "google_cloud_run_service" "neuralblitz" {
  name     = var.service_name
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa.email
      
      containers {
        image = "gcr.io/${var.project_id}/${var.service_name}:latest"
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        env {
          name  = "STORAGE_BUCKET"
          value = google_storage_bucket.data_bucket.name
        }
        
        env {
          name  = "PUBSUB_TOPIC"
          value = google_pubsub_topic.events.name
        }
        
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
        
        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 10
          period_seconds        = 5
          failure_threshold     = 3
        }
        
        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 30
          period_seconds        = 10
          failure_threshold     = 3
        }
      }
      
      container_concurrency = 1000
      timeout_seconds       = 300
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "100"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.apis,
    google_service_account.cloud_run_sa
  ]
}

# Allow public access
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.neuralblitz.name
  location = google_cloud_run_service.neuralblitz.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Pub/Sub Push Subscription
resource "google_pubsub_subscription" "push" {
  name  = "neuralblitz-push-sub"
  topic = google_pubsub_topic.events.name
  
  push_config {
    push_endpoint = "${google_cloud_run_service.neuralblitz.status[0].url}/pubsub"
    
    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
  
  ack_deadline_seconds = 60
  
  depends_on = [google_cloud_run_service.neuralblitz]
}

# Outputs
output "service_url" {
  description = "The URL of the deployed service"
  value       = google_cloud_run_service.neuralblitz.status[0].url
}

output "bucket_name" {
  description = "Cloud Storage bucket name"
  value       = google_storage_bucket.data_bucket.name
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.cloud_run_sa.email
}
