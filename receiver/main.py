import os
import json
import functions_framework
from flask import jsonify
from google.cloud import pubsub_v1
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
target_tenant_id = os.environ.get("TENANT_ID")
TOPIC_ID = "transcript-notifications"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

@functions_framework.http
def main(request):
    """HTTP Cloud Function to handle Microsoft Graph notifications."""
    # Handle subscription validation
    validation_token = request.args.get('validationToken')
    if validation_token:
        logging.info(f"Validation token received: {validation_token}")
        return validation_token, 200, {'Content-Type': 'text/plain'}

    # Handle notification
    request_json = request.get_json(silent=True)
    if request_json:
        logging.info("Received Microsoft Graph notification.")

        # Validate Tenant ID
        
        if target_tenant_id:
            for notification in request_json.get('value', []):
                tenant_id = notification.get('tenantId')
                if tenant_id != target_tenant_id:
                    logging.warning(f"Unauthorized tenant: {tenant_id}")
                    return jsonify({"error": "Unauthorized"}), 401

        try:
            # Publish message to Pub/Sub
            message_data = json.dumps(request_json).encode("utf-8")
            future = publisher.publish(topic_path, message_data)
            future.result()  # Wait for publish to complete
            logging.info(f"Message published to {TOPIC_ID}")
            return jsonify({"status": "published"}), 202
        except Exception as e:
            logging.error(f"Error publishing to Pub/Sub: {e}")
            return jsonify({"error": "Failed to publish message"}), 500
    else:
        logging.warning("No JSON payload received.")
        return jsonify({"error": "Invalid request"}), 400
