import asyncio
from datetime import datetime, timedelta, timezone
import os

from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider,
)
from msgraph_beta import GraphServiceClient
from msgraph_beta.generated.models.subscription import Subscription
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
CLIENT_ID = "8d26bdaf-6c6d-44a0-b9b8-3698e0812cab"
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID = "caa38daf-99d2-4f73-8492-0fc366809dec"
NOTIFICATION_URL = "https://transcript-retriever-633265597134.europe-west1.run.app"

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
        print("Creating subscription...")
        result = await graph_client.subscriptions.post(body=subscription)

        if result:
            print(f"Subscription created successfully!")
            print(f"  ID: {result.id}")
            print(f"  Resource: {result.resource}")
            print(f"  Expiration: {result.expiration_date_time}")
            print(f"  Notification URL: {result.notification_url}")

    except Exception as e:
        print(f"Error creating subscription: {e}")

if __name__ == "__main__":
    if CLIENT_ID == "YOUR_CLIENT_ID" or CLIENT_SECRET == "YOUR_CLIENT_SECRET" or TENANT_ID == "YOUR_TENANT_ID":
        print("Please configure CLIENT_ID, CLIENT_SECRET, and TENANT_ID before running the script.")
    else:
        asyncio.run(create_subscription("communications/onlineMeetings/getAllTranscripts"))
        asyncio.run(create_subscription("communications/adhocCalls/getAllTranscripts"))