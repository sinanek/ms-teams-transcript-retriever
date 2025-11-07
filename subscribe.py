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

class SubscriptionManager:
    """Manages Microsoft Graph subscriptions."""

    def __init__(self):
        """Initializes the SubscriptionManager."""
        self.client_id = os.environ.get("CLIENT_ID")
        self.client_secret = os.environ.get("CLIENT_SECRET")
        self.tenant_id = os.environ.get("TENANT_ID")
        self.notification_url = os.environ.get("NOTIFICATION_URL")

        if not all([self.client_id, self.client_secret, self.tenant_id, self.notification_url]):
            raise ValueError("Missing required environment variables.")

        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        self.graph_client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])

    async def get_existing_subscription(self, resource_url: str):
        """Gets an existing subscription for a given resource."""
        try:
            subscriptions = await self.graph_client.subscriptions.get()
            for subscription in subscriptions.value:
                if subscription.resource == resource_url:
                    return subscription
        except Exception as e:
            print(f"Error getting subscriptions: {e}")
        return None

    async def create_or_update_subscription(self, resource_url: str):
        """Creates a new subscription or updates an existing one."""
        existing_subscription = await self.get_existing_subscription(resource_url)
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=70)

        if existing_subscription:
            print(f"Subscription for {resource_url} already exists. Updating...")
            subscription = Subscription(
                expiration_date_time=expiration_time,
            )
            try:
                result = await self.graph_client.subscriptions.by_subscription_id(existing_subscription.id).patch(body=subscription)
                if result:
                    print(f"Subscription updated successfully!")
                    print(f"  ID: {result.id}")
                    print(f"  Resource: {result.resource}")
                    print(f"  Expiration: {result.expiration_date_time}")
            except Exception as e:
                print(f"Error updating subscription: {e}")
        else:
            print(f"Creating new subscription for {resource_url}...")
            subscription = Subscription(
                change_type="created",
                notification_url=self.notification_url,
                lifecycle_notification_url=self.notification_url,
                resource=resource_url,
                expiration_date_time=expiration_time,
                client_state="secretClientValue",
            )
            try:
                result = await self.graph_client.subscriptions.post(body=subscription)
                if result:
                    print(f"Subscription created successfully!")
                    print(f"  ID: {result.id}")
                    print(f"  Resource: {result.resource}")
                    print(f"  Expiration: {result.expiration_date_time}")
                    print(f"  Notification URL: {result.notification_url}")
            except Exception as e:
                print(f"Error creating subscription: {e}")

async def main():
    """Main function to create or update subscriptions."""
    try:
        manager = SubscriptionManager()
        await manager.create_or_update_subscription("communications/onlineMeetings/getAllTranscripts")
        await manager.create_or_update_subscription("communications/adhocCalls/getAllTranscripts")
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
