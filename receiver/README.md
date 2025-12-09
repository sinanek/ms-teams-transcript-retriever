# Subscriber Cloud Function

This Cloud Function acts as a webhook for Microsoft Graph notifications. It receives notifications, publishes them to a Pub/Sub topic for asynchronous processing, and immediately returns a `202 Accepted` response to avoid timeouts from the source service.

## Deployment

1.  Make sure you have a Pub/Sub topic created. You can use the `create-topic.sh` script in the root directory.
2.  Deploy the function using `gcloud`:

    ```sh
gcloud run deploy transcription-receiver \
  --function main \
  --source receiver/ \
  --base-image python313 \
  --region europe-west1 \
  --env-vars-file=.env \
  --set-secrets="TENANT_ID=TENANT_ID:latest" \
  --max-instances 10 \
  --allow-unauthenticated
    ```

