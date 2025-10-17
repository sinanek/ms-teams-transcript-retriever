import functions_framework
from flask import jsonify
import os
import asyncio
import re
from azure.identity.aio import ClientSecretCredential
from msgraph_beta import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection
from dotenv import load_dotenv

load_dotenv()
# --- Configuration ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID = os.environ.get("TENANT_ID")

async def fetch_transcript(resource_url):
    """Fetches the transcript content from the given resource URL."""

    user_id_match = re.search(r"users\('([^']*)'\)", resource_url)
    meeting_id_match = re.search(r"onlineMeetings\('([^']*)'\)", resource_url)
    transcript_id_match = re.search(r"transcripts\('([^']*)'\)", resource_url)

    if user_id_match and meeting_id_match and transcript_id_match:
        user_id = user_id_match.group(1)
        meeting_id = meeting_id_match.group(1)
        transcript_id = transcript_id_match.group(1)

        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        graph_client = GraphServiceClient(credentials=credential, scopes=["https://graph.microsoft.com/.default"])

        try:
            # Fetch transcript content
            headers = HeadersCollection()
            headers.add("Accept", "text/vtt")
            request_configuration = RequestConfiguration(headers=headers)
            transcript_content = await graph_client.users.by_user_id(user_id).online_meetings.by_online_meeting_id(meeting_id).transcripts.by_call_transcript_id(transcript_id).content.get(request_configuration=request_configuration)
            #print("Transcript content:")
            #print(transcript_content)

            # Fetch meeting participants and their recordings folder
            meeting_info = await graph_client.users.by_user_id(user_id).online_meetings.by_online_meeting_id(meeting_id).get()
            if meeting_info and meeting_info.participants:
                display_name = meeting_info.participants.organizer.identity.user.display_name
                filename = f"{meeting_info.subject}_{meeting_info.start_date_time.strftime('%Y%m%d_%H%M%S')}_transcript.txt"
                
                print("Meeting Organizer:")
                if meeting_info.participants.organizer and meeting_info.participants.organizer.identity and meeting_info.participants.organizer.identity.user:
                    organizer_id = meeting_info.participants.organizer.identity.user.id
                    
                    print(f"  - {display_name if display_name else organizer_id}")
                    org_drive = await graph_client.users.by_user_id(organizer_id).drive.get()
                    print(f"    Drive ID: {org_drive.id}")
                    recordings_folder = await graph_client.drives.by_drive_id(org_drive.id).special.by_drive_item_id('recordings').get()
                    if recordings_folder and recordings_folder.id:
                        drive_id = recordings_folder.parent_reference.drive_id
                        recordings_folder_id = recordings_folder.id
                        # Upload the file to the recordings folder
                        uploaded_item = await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(filename).content.put(transcript_content)
                        
                        print(f"Transcript uploaded successfully: {filename}")
                        print(f"Item ID: {uploaded_item.id if uploaded_item else 'Unknown'}")
                    
                print("Meeting Attendees:")
                if meeting_info.participants.attendees:
                    for attendee in meeting_info.participants.attendees:
                        if attendee.identity and attendee.identity.user:
                            attendee_id = attendee.identity.user.id
                            display_name = attendee.identity.user.display_name
                            print(f"  - {display_name if display_name else attendee_id}")
                            att_drive = await graph_client.users.by_user_id(attendee_id).drive.get()
                            print(f"    Drive ID: {att_drive.id}")
                            recordings_folder = await graph_client.drives.by_drive_id(att_drive.id).special.by_drive_item_id('recordings').get()
                            if recordings_folder and recordings_folder.id:
                                drive_id = recordings_folder.parent_reference.drive_id
                                recordings_folder_id = recordings_folder.id
                                # Upload the file to the recordings folder
                                uploaded_item = await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(filename).content.put(transcript_content)
                                
                                print(f"Transcript uploaded successfully: {filename} for attendee: {display_name if display_name else attendee_id}")
                        

        except Exception as e:
            print(f"Error fetching transcript or participants: {e}")

@functions_framework.http
def main(request):
    """HTTP Cloud Function to handle Microsoft Graph notifications."""

    # Handle subscription validation
    validation_token = request.args.get('validationToken')
    if validation_token:
        print("Validation token received:", validation_token)
        return validation_token, 200, {'Content-Type': 'text/plain'}

    # Handle notification
    request_json = request.get_json(silent=True)
    if request_json:
        print("Received Microsoft Graph notification:")
        resource_url = request_json['value'][0]['resource']
        print(f"  Resource URL: {resource_url}")
        asyncio.run(fetch_transcript(resource_url))
        return jsonify({"status": "received"}), 200
    else:
        print("No JSON payload received.")
        return jsonify({"error": "Invalid request"}), 400
