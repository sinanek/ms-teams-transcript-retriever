output "receiver_uri" {
  value = google_cloudfunctions2_function.receiver.service_config[0].uri
}

output "processor_uri" {
  value = google_cloudfunctions2_function.processor.service_config[0].uri
}

output "subscriber_uri" {
  value = google_cloudfunctions2_function.subscriber.service_config[0].uri
}
