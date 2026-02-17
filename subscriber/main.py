import asyncio
import logging
import os
import subscribe
import functions_framework

logging.basicConfig(level=logging.INFO)

@functions_framework.http
def trigger_subscription(request):
    """
    HTTP Cloud Function to trigger the subscription process.
    """
    try:
        logging.info("Triggered subscription update via HTTP")
        # subscribe.main() is async, so we need to run it in the event loop
        asyncio.run(subscribe.main())
        return "OK", 200
    except Exception as e:
        logging.exception("Error in subscription trigger")
        return f"Error: {str(e)}", 500
