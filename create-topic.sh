#!/bin/bash

# This script creates the Pub/Sub topic required for the transcript retriever application.
source .env
# --- Configuration ---
TOPIC_ID="transcript-notifications"
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "Google Cloud project not set. Please run 'gcloud config set project YOUR_PROJECT_ID'"
    exit 1
fi

echo "Creating Pub/Sub topic '$TOPIC_ID' in project '$PROJECT_ID'..."

gcloud pubsub topics create $TOPIC_ID --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "Pub/Sub topic '$TOPIC_ID' created successfully."
else
    echo "Failed to create Pub/Sub topic '$TOPIC_ID'."
fi
