# Transcript Retriever

This project subscribes to Microsoft Graph notifications for meeting transcripts and provides a Cloud Function to receive the notifications and fetch the transcript content.

## Deployment

To deploy the Cloud Function, you will need to have the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured.

Run the following command to deploy the function:

```bash
gcloud functions deploy transcript-retriever \
  --gen2 \
  --runtime python311 \
  --trigger-http \
  --entry-point main \
  --source function/ \
  --region europe-west1 \
  --allow-unauthenticated
```

**Note:**
- Replace `<YOUR_REGION>` with the Google Cloud region where you want to deploy the function (e.g., `us-central1`).
- The runtime is set to `python311`, as Python 3.13 is not yet available as a Cloud Functions runtime. Please ensure that your code is compatible with Python 3.12.

## Local Testing

You can test your function locally without deploying it to the cloud. The `functions-framework` provides a local development server.

1.  **Start the local server:**

    ```bash
    functions-framework --target main --source function/main.py --port 8080
    ```

2.  **Send a request to the local function:**

    In a separate terminal, you can use `curl` to send a POST request to your local function with a sample payload. Make sure you have a `payload.json` file with the sample notification payload.

    ```bash
    curl -X POST -H "Content-Type: application/json" -d @payload.json http://localhost:8080
    ```

This will allow you to test your function's logic without having to deploy it every time you make a change.