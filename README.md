# Transcript Retriever

This project subscribes to Microsoft Graph notifications for meeting transcripts and provides a Cloud Function to receive the notifications and fetch the transcript content.

The transcripts are stored in the local recordings folder for each user that was invited to the meeting.


## Deployment

### Step 1
Create an app registration on portal.azure.com

### Step 2
Give the app the following permissions
![alt text](images/image.png)

### Step 3
Create a client secret and copy the key
![alt text](images/image-1.png)

### Step 4
Update access policies for the app. We ran these powershell command:

```
New-CsApplicationAccessPolicy -Identity transcript-policy -AppIds "8d26bdaf-6c6d-44a0-b9b8-3698e0812cab" -Description "This allows the agent to retrieve transcripts on behalf of users" 

Grant-CsApplicationAccessPolicy -PolicyName transcript-policy -Global
```

More on access policies here: https://learn.microsoft.com/en-us/graph/cloud-communication-online-meeting-application-access-policy#supported-permissions-and-additional-resources

### Step 5
Take the application id + tenant id for the app registration and the key you just created and configure the variables in a .env file (example provided in .env.example)
![alt text](images/image-2.png)
### Step 6

Deploy main.py as a function

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
- Replace the region with the Google Cloud region where you want to deploy the function (e.g., `us-central1`).

### Step 7

Replace the notificationUrl with the URL of the function that is created in .env file

### Step 8
Run subscribe.py to create a subscription to call and meeting transcripts.


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

## Things to improve
- domain level filtering 
- scheduled task for subscribing to notifications as they expire
- only store transcripts in the organizers folder when meeting participants over a certain size
- small optimizations in the code e.g. adding concurrency
- error handling