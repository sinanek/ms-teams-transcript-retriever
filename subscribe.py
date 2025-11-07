import asyncio
from datetime import datetime, timedelta, timezone
import os
import logging

from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider,
)
from msgraph_beta import GraphServiceClient
from msgraph_beta.generated.models.subscription import Subscription
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID = os.environ.get("TENANT_ID")
NOTIFICATION_URL = os.environ.get("NOTIFICATION_URL")

async def create_subscription(resource_url:str):
    """Creates a new Microsoft Graph subscription."""

    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    graph_client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])

    expiration_time = datetime.now(timezone.utc) + timedelta(hours=70)

    subscription = Subscription(
        change_type="created",
        notification_url=NOTIFICATION_URL,
        lifecycle_notification_url=NOTIFICATION_URL,
        resource=resource_url,
        expiration_date_time=expiration_time,
        client_state="secretClientValue",
    )

    try:
        logging.info("Creating subscription...")
        result = await graph_client.subscriptions.post(body=subscription)

        if result:
            logging.info("Subscription created successfully!")
            logging.info(f"  ID: {result.id}")
            logging.info(f"  Resource: {result.resource}")
            logging.info(f"  Expiration: {result.expiration_date_time}")
            logging.info(f"  Notification URL: {result.notification_url}")

    except Exception as e:
        logging.error(f"Error creating subscription: {e}")

if __name__ == "__main__":
    if CLIENT_ID == "YOUR_CLIENT_ID" or CLIENT_SECRET == "YOUR_CLIENT_SECRET" or TENANT_ID == "YOUR_TENANT_ID":
        logging.warning("Please configure CLIENT_ID, CLIENT_SECRET, and TENANT_ID before running the script.")
    else:
        asyncio.run(create_subscription("communications/onlineMeetings/getAllTranscripts"))
        asyncio.run(create_subscription("communications/adhocCalls/getAllTranscripts"))