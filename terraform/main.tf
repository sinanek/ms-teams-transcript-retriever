provider "google" {
  project = var.project_id
  region  = var.region
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

# --- Service Account ---
resource "google_service_account" "transcript_sa" {
  account_id   = "transcript-sa"
  display_name = "Transcript Retriever Service Account"
}

# Grant Vertex AI User to SA
resource "google_project_iam_member" "sa_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.transcript_sa.email}"
}

# --- Secrets ---
resource "google_secret_manager_secret" "client_id" {
  secret_id = "client-id"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "client_id" {
  secret      = google_secret_manager_secret.client_id.id
  secret_data = var.client_id
}

resource "google_secret_manager_secret" "client_secret" {
  secret_id = "client-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "client_secret" {
  secret      = google_secret_manager_secret.client_secret.id
  secret_data = var.client_secret
}

resource "google_secret_manager_secret" "tenant_id" {
  secret_id = "tenant-id"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "tenant_id" {
  secret      = google_secret_manager_secret.tenant_id.id
  secret_data = var.tenant_id
}

# Grant Access to Secrets
resource "google_secret_manager_secret_iam_member" "sa_client_id" {
  secret_id = google_secret_manager_secret.client_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.transcript_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "sa_client_secret" {
  secret_id = google_secret_manager_secret.client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.transcript_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "sa_tenant_id" {
  secret_id = google_secret_manager_secret.tenant_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.transcript_sa.email}"
}

# --- Pub/Sub ---
resource "google_pubsub_topic" "notifications" {
  name = "transcript-notifications"
}

# Grant Pub/Sub Publisher to SA
resource "google_pubsub_topic_iam_member" "sa_publisher" {
  topic  = google_pubsub_topic.notifications.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.transcript_sa.email}"
}

# --- Storage for Source Code ---
resource "google_storage_bucket" "source_bucket" {
  name                        = "${var.project_id}-transcript-source"
  location                    = var.region
  uniform_bucket_level_access = true
}

# --- Archives ---
data "archive_file" "receiver_zip" {
  type        = "zip"
  source_dir  = "../receiver"
  output_path = "${path.module}/receiver.zip"
}

data "archive_file" "processor_zip" {
  type        = "zip"
  source_dir  = "../processor"
  output_path = "${path.module}/processor.zip"
}

data "archive_file" "subscriber_zip" {
  type        = "zip"
  source_dir  = "../subscriber"
  output_path = "${path.module}/subscriber.zip"
}

# --- Objects ---
resource "google_storage_bucket_object" "receiver_zip" {
  name   = "receiver-${data.archive_file.receiver_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.receiver_zip.output_path
}

resource "google_storage_bucket_object" "processor_zip" {
  name   = "processor-${data.archive_file.processor_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.processor_zip.output_path
}

resource "google_storage_bucket_object" "subscriber_zip" {
  name   = "subscriber-${data.archive_file.subscriber_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.subscriber_zip.output_path
}

# --- Cloud Function: Receiver ---
resource "google_cloudfunctions2_function" "receiver" {
  name        = "transcription-receiver"
  location    = var.region
  description = "Receives MS Graph notifications"

  build_config {
    runtime     = "python311"
    entry_point = "main"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.receiver_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.transcript_sa.email
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
    }
    secret_environment_variables {
      key        = "TENANT_ID"
      project_id = var.project_id
      secret     = google_secret_manager_secret.tenant_id.secret_id
      version    = "latest"
    }
  }
}

# Allow unauthenticated invocation for Receiver (as per README 'allow-unauthenticated')
resource "google_cloud_run_service_iam_member" "receiver_invoker" {
  location = google_cloudfunctions2_function.receiver.location
  service  = google_cloudfunctions2_function.receiver.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Cloud Function: Processor ---
resource "google_cloudfunctions2_function" "processor" {
  name        = "transcript-processor"
  location    = var.region
  description = "Processes transcripts"

  build_config {
    runtime     = "python311"
    entry_point = "main"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.processor_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 20
    available_memory      = "512M"
    timeout_seconds       = 300
    service_account_email = google_service_account.transcript_sa.email
    environment_variables = {
      GOOGLE_CLOUD_PROJECT  = var.project_id
      GOOGLE_CLOUD_LOCATION = var.region
    }
    secret_environment_variables {
      key        = "CLIENT_ID"
      project_id = var.project_id
      secret     = google_secret_manager_secret.client_id.secret_id
      version    = "latest"
    }
    secret_environment_variables {
      key        = "CLIENT_SECRET"
      project_id = var.project_id
      secret     = google_secret_manager_secret.client_secret.secret_id
      version    = "latest"
    }
    secret_environment_variables {
      key        = "TENANT_ID"
      project_id = var.project_id
      secret     = google_secret_manager_secret.tenant_id.secret_id
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.notifications.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}

# --- Cloud Function: Subscriber ---
resource "google_cloudfunctions2_function" "subscriber" {
  name        = "transcript-subscriber"
  location    = var.region
  description = "Subscribes to MS Graph notifications"

  build_config {
    runtime     = "python311"
    entry_point = "trigger_subscription"
    source {
      storage_source {
        bucket = google_storage_bucket.source_bucket.name
        object = google_storage_bucket_object.subscriber_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.transcript_sa.email
    environment_variables = {
      NOTIFICATION_URL = google_cloudfunctions2_function.receiver.service_config[0].uri
    }
    secret_environment_variables {
      key        = "CLIENT_ID"
      project_id = var.project_id
      secret     = google_secret_manager_secret.client_id.secret_id
      version    = "latest"
    }
    secret_environment_variables {
      key        = "CLIENT_SECRET"
      project_id = var.project_id
      secret     = google_secret_manager_secret.client_secret.secret_id
      version    = "latest"
    }
    secret_environment_variables {
      key        = "TENANT_ID"
      project_id = var.project_id
      secret     = google_secret_manager_secret.tenant_id.secret_id
      version    = "latest"
    }
  }
}

# --- Cloud Scheduler ---
resource "google_cloud_scheduler_job" "subscriber_job" {
  name             = "daily-subscription-renewal"
  description      = "Triggers the subscriber function daily"
  schedule         = "0 0 * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.subscriber.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.transcript_sa.email
    }
  }
}

# Grant Invoke Permission to Scheduler (via SA)
resource "google_cloud_run_service_iam_member" "subscriber_invoker" {
  location = google_cloudfunctions2_function.subscriber.location
  service  = google_cloudfunctions2_function.subscriber.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.transcript_sa.email}"
}
