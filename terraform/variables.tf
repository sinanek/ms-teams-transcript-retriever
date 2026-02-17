variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud Region"
  type        = string
  default     = "europe-west1"
}

variable "client_id" {
  description = "Microsoft Graph Client ID"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "Microsoft Graph Client Secret"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Microsoft Graph Tenant ID"
  type        = string
  sensitive   = true
}
