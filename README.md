# Transcript Retriever

This project subscribes to Microsoft Graph notifications for meeting transcripts and provides a Cloud Function to receive the notifications and fetch the transcript content.

After retrieving the transcript, the following steps are performed:
- The transcripts are stored in the local recordings folder for each user that was invited to the meeting. This can be used for developing further conversational capabilities using the OneDrive connector
- The transcripts are summarized and action items are generated using Gemini
- The summary is then:
  - Sent to the Organizer via email
  - Appended to the calendar invite for others to view

# Architecture
![alt text](images/architecture.png)

## Deployment

### Step 1
Create an app registration on portal.azure.com

### Step 2
Give the app the following permissions
| File | Operation | API Endpoint / Resource | Required Application Permission | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `processor/main.py` | Get User | `GET /users/{id}` | **User.Read.All** | |
| | List Events | `GET /users/{id}/events` | **Calendars.ReadWrite** | `ReadWrite` needed for the Update operation below. |
| | Update Event | `PATCH /users/{id}/events/{id}` | **Calendars.ReadWrite** | |
| | Send Mail | `POST /users/{id}/sendMail` | **Mail.Send** | |
| | Get Meeting | `GET /users/{id}/onlineMeetings/{id}` | **OnlineMeetings.Read.All** | |
| | Get Transcript | `GET .../transcripts/{id}/content` | **OnlineMeetingTranscript.Read.All** | Required to read the actual transcript content. |
| | Get Drive Folder | `GET /drives/{id}/special/recordings` | **Files.ReadWrite.All** | `ReadWrite` needed for the Upload operation below. |
| | Upload File | `PUT /drives/{id}/items/{id}/content` | **Files.ReadWrite.All** | |
| `subscribe.py` | Create Subscription | `POST /subscriptions`<br>Resource: `.../onlineMeetings/getAllTranscripts` | **OnlineMeetings.Read.All`<br>`OnlineMeetingTranscript.Read.All** | |

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
Take the application id + tenant id for the app registration and the key you just created. You will need these for the next steps.
![alt text](images/image-2.png)

## Deployment Options

### Option 1: Terraform (Recommended)

This project includes Terraform configurations to automate the deployment of all GCP resources, including Cloud Functions, Pub/Sub topics, Secrets, and Cloud Scheduler.

1.  **Navigate to the terraform directory**:
    ```bash
    cd terraform
    ```

2.  **Initialize Terraform**:
    ```bash
    terraform init
    ```

3.  **Create a `terraform.tfvars` file**:
    ```hcl
    project_id    = "your-project-id"
    region        = "europe-west1"
    client_id     = "your-client-id"
    client_secret = "your-client-secret"
    tenant_id     = "your-tenant-id"
    ```

4.  **Deploy**:
    You can use the provided `Makefile` to deploy easily (it loads variables from your `.env` file):
    ```bash
    make deploy
    ```
    Alternatively, using Terraform directly:
    ```bash
    cd terraform
    terraform apply
    ```

For more details, see the [Terraform Deployment Guide](terraform/README.md).

---

### Option 2: Manual Deployment

If you prefer to deploy manually using the Google Cloud SDK and provided scripts, follow these steps:

#### 1. Configure Environment
Create a `.env` file based on `.env.example` with your Azure credentials.

#### 2. Create Secrets
```bash
chmod +x create-secrets.sh
./create-secrets.sh
```

#### 3. Create Pub/Sub Topic
```bash
chmod +x create-topic.sh
./create-topic.sh
```

#### 4. Deploy Cloud Functions
```bash
# Deploy Receiver
gcloud run deploy transcription-receiver \
  --function main \
  --source receiver/ \
  --base-image python313 \
  --region europe-west1 \
  --env-vars-file=.env \
  --set-secrets="TENANT_ID=TENANT_ID:latest" \
  --max-instances 10 \
  --allow-unauthenticated

# Deploy Processor
gcloud run deploy transcript-processor \
  --function main \
  --source processor/ \
  --base-image python313 \
  --region europe-west1 \
  --env-vars-file=.env \
  --set-secrets="CLIENT_ID=CLIENT_ID:latest,CLIENT_SECRET=CLIENT_SECRET:latest,TENANT_ID=TENANT_ID:latest" \
  --max-instances 20
```

#### 5. Create Pub/Sub Subscription
```bash
chmod +x create-subscription.sh
./create-subscription.sh
```

#### 6. Initialize Subscription
Update the `NOTIFICATION_URL` in your `.env` with the URL from the `transcription-receiver` deployment, then run:
```bash
python subscribe.py
```


## Local Testing

You can test your function locally without deploying it to the cloud. The `functions-framework` provides a local development server.

1.  **Start the local server:**

    ```bash
    functions-framework --target main --source receiver/main.py --port 8080
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
- small optimizations in the code e.g. adding concurrency
- error handling