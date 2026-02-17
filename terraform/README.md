# Deployment Guide (Terraform)

This guide explains how to deploy the Transcript Retriever using Terraform.

## Prerequisites

1.  **Terraform**: Install Terraform.
2.  **Google Cloud SDK**: Ensure `gcloud` is installed and authenticated.
3.  **Project**: A Google Cloud Project.

## Steps

1.  **Navigate to Terraform directory**:
    ```bash
    cd terraform
    ```

2.  **Initialize Terraform**:
    ```bash
    terraform init
    ```

3.  **Create `terraform.tfvars`**:
    Create a file named `terraform.tfvars` with your secrets (DO NOT COMMIT THIS FILE):
    ```hcl
    project_id    = "your-project-id"
    region        = "europe-west1"
    client_id     = "your-client-id"
    client_secret = "your-client-secret"
    tenant_id     = "your-tenant-id"
    ```

4.  **Review Plan**:
    ```bash
    terraform plan
    ```

5.  **Deploy**:
    ```bash
    terraform apply
    ```

## Outputs
After deployment, Terraform will output the URIs for the deployed services:
- `receiver_uri`
- `processor_uri`
- `subscriber_uri`

## Verification
- **Receiver**: Send a validation request to `receiver_uri` or wait for MS Graph notifications.
- **Subscriber**: The Cloud Scheduler job `daily-subscription-renewal` will automatically trigger the `subscriber` function. you can manually force run it via Cloud Console or:
    ```bash
    gcloud scheduler jobs run daily-subscription-renewal --location=europe-west1
    ```
