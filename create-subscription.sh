#!/bin/bash

# This script deploys the Cloud Function that processes transcript notifications
# and automatically creates a Pub/Sub push subscription for it.

# --- Configuration ---
FUNCTION_NAME=$(gcloud run services describe transcript-processor --platform=managed --region=europe-west1 --format='value(status.url)')
SUBSCRIPTION_NAME="process-transcripts"
TOPIC_ID="transcript-notifications"
source .env

if [ -z "$SERVICE_ACCOUNT" ]; then
    echo "SERVICE_ACCOUNT not set in .env. Please set it to your Compute Engine default service account or similar."
    exit 1
fi

gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
--topic=$TOPIC_ID \
--push-endpoint=$FUNCTION_NAME \
--ack-deadline 600 \
--min-retry-delay 10 \
--push-auth-service-account $SERVICE_ACCOUNT \
--max-retry-delay 600

if [ $? -eq 0 ]; then
    echo "Pub/Sub Subscription '$SUBSCRIPTION_NAME' created successfully."
else
    echo "Failed to create Pub/Sub Subscription '$FUNCTION_NAME'."
fi
