import functions_framework
from flask import jsonify
import os
import asyncio
import re
import markdown
from azure.identity.aio import ClientSecretCredential
from msgraph_beta import GraphServiceClient
from msgraph_beta.generated.models.chat_message import ChatMessage
from msgraph_beta.generated.models.event import Event
from msgraph_beta.generated.models.item_body import ItemBody
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection
from msgraph_beta.generated.users.item.events.events_request_builder import EventsRequestBuilder
import base64
from msgraph_beta.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph_beta.generated.models.message import Message
from msgraph_beta.generated.models.body_type import BodyType
from msgraph_beta.generated.models.recipient import Recipient
from msgraph_beta.generated.models.email_address import EmailAddress
from msgraph_beta.generated.models.file_attachment import FileAttachment
from dotenv import load_dotenv
from google import genai
from google.genai import types
from . import prompt

load_dotenv()
# --- Configuration ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID = os.environ.get("TENANT_ID")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")

async def summarize_with_gemini(transcript_content):
    """Summarizes the transcript using Gemini."""
    try:
        client = genai.Client(
            vertexai=True,project=GOOGLE_CLOUD_PROJECT,location=GOOGLE_CLOUD_LOCATION
        )
        model = "gemini-2.5-flash-preview-09-2025"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt.PROMPT.format(transcript_content=transcript_content))
                ]
            )
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            seed=0,
            max_output_tokens=65535,
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
            ),
        )

        response = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response += chunk.text
        print(response)
        return response

    except Exception as e:
        print(f"Error summarizing with Gemini: {e}")
        return None

async def update_meeting_notes(graph_client, user_id, meeting_info, summary):
    """
    Finds the calendar event for the meeting and updates its body with the summary.

    Args:
        graph_client: An authenticated GraphServiceClient.
        user_id: The ID of the user (meeting organizer).
        meeting_info: The onlineMeeting object from Graph.
        summary: The summary text to append to the meeting notes.
    """
    try:
        join_url = meeting_info.join_web_url
        if not join_url:
            print("No join URL found for the meeting.")
            return

        # Find the calendar event associated with the meeting by subject and start time
        subject = meeting_info.subject.replace("'", "''")
        start_time_str = meeting_info.start_date_time.isoformat()
        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            filter=f"subject eq '{subject}' and start/dateTime eq '{start_time_str}'"
        )
        request_configuration = RequestConfiguration(
            query_parameters=query_params
        )
        
        events = await graph_client.users.by_user_id(user_id).events.get(request_configuration=request_configuration)

        if events and events.value:
            meeting_event = events.value[0]
            event_id = meeting_event.id
            
            # Prepare the updated body, preserving original content
            original_body = meeting_event.body.content if meeting_event.body and meeting_event.body.content else ""
            content_type = meeting_event.body.content_type if meeting_event.body and meeting_event.body.content_type else "html"
            
            # Format summary as HTML and append it
            summary_html = f"<br><hr><h2>Meeting Summary</h2><p>{markdown.markdown(summary,extensions=['tables'])}</p>"
            new_body_content = original_body + summary_html
            
            new_body = ItemBody(
                content=new_body_content,
                content_type=content_type
            )
            
            update_payload = Event(
                body=new_body
            )
            
            # Patch the event with the new body
            await graph_client.users.by_user_id(user_id).events.by_event_id(event_id).patch(update_payload)
            print(f"Successfully updated meeting notes for event: {event_id}")
        else:
            print("Could not find a matching calendar event for the meeting.")

    except Exception as e:
        print(f"Error updating meeting notes: {e}")

async def send_summary_email(graph_client, organizer_id, organizer_email, meeting_subject, summary, transcript_content, transcript_filename):
    """
    Sends an email to the organizer with the summary and transcript.

    Note: This function requires the 'Mail.Send' application permission in Azure AD.
    """
    try:
        summary_html = markdown.markdown(summary, extensions=['tables'])
        email_body = ItemBody(
            content_type=BodyType.Html,
            content=f"<h2>Summary for your meeting: {meeting_subject}</h2>{summary_html}"
        )

        #Prepare the recipient (the meeting organizer)
        to_recipient = Recipient(
            email_address=EmailAddress(
                address=organizer_email
            )
        )

        #Prepare the transcript as a file attachment
        transcript_bytes = transcript_content.encode('utf-8')
        
        attachment = FileAttachment(
            odata_type="#microsoft.graph.fileAttachment",
            name=transcript_filename,
            content_type="text/plain",
            content_bytes=transcript_bytes
        )

        #Construct the final message
        message = Message(
            subject=f"Summary for: {meeting_subject}",
            body=email_body,
            to_recipients=[to_recipient],
            attachments=[attachment]
        )

        #Construct the request body and send the email
        request_body = SendMailPostRequestBody(
            message=message,
            save_to_sent_items=True
        )

        await graph_client.users.by_user_id(organizer_id).send_mail.post(request_body)
        print(f"Summary email sent successfully to {organizer_email}")

    except Exception as e:
        print(f"Error sending summary email: {e}")

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
            transcript_content_bytes = await graph_client.users.by_user_id(user_id).online_meetings.by_online_meeting_id(meeting_id).transcripts.by_call_transcript_id(transcript_id).content.get(request_configuration=request_configuration)
            
            transcript_content = ""
            if transcript_content_bytes:
                transcript_content = transcript_content_bytes.decode('utf-8')

            # Summarize the transcript
            summary = await summarize_with_gemini(transcript_content)
            
            # Fetch meeting participants and their recordings folder
            meeting_info = await graph_client.users.by_user_id(user_id).online_meetings.by_online_meeting_id(meeting_id).get()
            
            # Send summary to Teams channel
            # if summary and meeting_info and meeting_info.chat_info:
            #     chat_id = meeting_info.chat_info.thread_id
            #     chat_message = ChatMessage(
            #         body=ItemBody(
            #             content_type="html",
            #             content=summary
            #         )
            #     )
            #     try:
            #         await graph_client.chats.by_chat_id(chat_id).messages.post(chat_message)
            #         print(f"Summary sent to Teams channel: {chat_id}")
            #     except Exception as e:
            #         print(f"Error sending summary to Teams channel: {e}")

            # Update meeting notes with summary
            if summary and meeting_info:
                await update_meeting_notes(graph_client, user_id, meeting_info, summary)

            # Send summary email to organizer
            if summary and meeting_info and meeting_info.participants and meeting_info.participants.organizer:
                organizer_identity = meeting_info.participants.organizer.identity
                if organizer_identity and organizer_identity.user and organizer_identity.user.id:
                    organizer_id = organizer_identity.user.id
                    try:
                        # Fetch organizer's user object to get their email
                        organizer_user = await graph_client.users.by_user_id(organizer_id).get()
                        organizer_email = organizer_user.mail
                        if organizer_email:
                            base_filename = f"{meeting_info.subject}_{meeting_info.start_date_time.strftime('%Y%m%d_%H%M%S')}"
                            transcript_filename = f"{base_filename}_transcript.txt"
                            await send_summary_email(
                                graph_client=graph_client,
                                organizer_id=organizer_id,
                                organizer_email=organizer_email,
                                meeting_subject=meeting_info.subject,
                                summary=summary,
                                transcript_content=transcript_content,
                                transcript_filename=transcript_filename
                            )
                    except Exception as e:
                        print(f"Error preparing or sending summary email: {e}")
                        

            if meeting_info and meeting_info.participants:
                display_name = meeting_info.participants.organizer.identity.user.display_name
                base_filename = f"{meeting_info.subject}_{meeting_info.start_date_time.strftime('%Y%m%d_%H%M%S')}"
                transcript_filename = f"{base_filename}_transcript.txt"
                summary_filename = f"{base_filename}_summary.txt"
                
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
                        # Upload the transcript
                        await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(transcript_filename).content.put(transcript_content_bytes)
                        print(f"Transcript uploaded successfully: {transcript_filename}")
                        
                        # Upload the summary
                        if summary:
                            summary_bytes = summary.encode('utf-8')
                            await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(summary_filename).content.put(summary_bytes)
                            print(f"Summary uploaded successfully: {summary_filename}")

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
                                # Upload the transcript
                                await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(transcript_filename).content.put(transcript_content_bytes)
                                print(f"Transcript uploaded successfully: {transcript_filename} for attendee: {display_name if display_name else attendee_id}")

                                # Upload the summary
                                if summary:
                                    summary_bytes = summary.encode('utf-8')
                                    await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(recordings_folder_id).children.by_drive_item_id1(summary_filename).content.put(summary_bytes)
                                    print(f"Summary uploaded successfully: {summary_filename} for attendee: {display_name if display_name else attendee_id}")

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