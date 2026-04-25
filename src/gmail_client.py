import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# gmail.modify covers both reading emails and adding labels
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]

PROCESSED_LABEL = "coop-tracker-processed"

# -label:coop-tracker-processed makes sure we don't reprocess emails on the next run
SEARCH_QUERY = (
    '(subject:"co-op" OR subject:"coop" OR subject:"internship" OR '
    'subject:"application" OR subject:"thank you for applying" OR '
    'subject:"interview") -label:coop-tracker-processed'
)


def get_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # first run opens a browser to authorize, after that token.json handles it
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _get_or_create_label(service, label_name):
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in existing:
        if label["name"] == label_name:
            return label["id"]

    # label doesn't exist yet, make it
    created = (
        service.users()
        .labels()
        .create(userId="me", body={"name": label_name})
        .execute()
    )
    return created["id"]


def _decode_body(payload):
    # emails can be plain text, html, or multipart - we only want plain text
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result

    return ""


def fetch_unread_coop_emails(service):
    result = (
        service.users()
        .messages()
        .list(userId="me", q=SEARCH_QUERY, maxResults=50)
        .execute()
    )
    messages = result.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_ref["id"], format="full")
            .execute()
        )

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        date = headers.get("Date", "")
        body = _decode_body(msg["payload"])

        emails.append(
            {
                "id": msg_ref["id"],
                "subject": subject,
                "body": body,
                "date": date,
            }
        )

    return emails


def mark_as_processed(service, email_id):
    label_id = _get_or_create_label(service, PROCESSED_LABEL)
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"addLabelIds": [label_id]},
    ).execute()
