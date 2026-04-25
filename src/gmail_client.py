import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# We need these two Gmail scopes:
#   - gmail.readonly: read email contents
#   - gmail.modify:   add/remove labels (to mark emails as processed)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]

PROCESSED_LABEL = "coop-tracker-processed"

# Gmail search query: match co-op related emails that haven't been processed yet.
# The -label: part prevents double-processing on every run.
SEARCH_QUERY = (
    '(subject:"co-op" OR subject:"coop" OR subject:"internship" OR '
    'subject:"application" OR subject:"thank you for applying" OR '
    'subject:"interview") -label:coop-tracker-processed'
)


def get_service():
    """Authenticate and return a Gmail API service object.

    On first run this opens a browser for OAuth consent.
    After that it uses the saved token.json so no browser needed.
    """
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If credentials are missing or expired, refresh or re-authorize.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the token so the next run doesn't need a browser.
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _get_or_create_label(service, label_name):
    """Return the label ID for label_name, creating it in Gmail if it doesn't exist."""
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in existing:
        if label["name"] == label_name:
            return label["id"]

    # Label doesn't exist yet — create it.
    created = (
        service.users()
        .labels()
        .create(userId="me", body={"name": label_name})
        .execute()
    )
    return created["id"]


def _decode_body(payload):
    """Recursively extract plain-text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Multi-part message — recurse into each part.
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result

    return ""


def fetch_unread_coop_emails(service):
    """Return a list of unprocessed co-op emails.

    Each item is a dict:
        id       — Gmail message ID (used to mark processed later)
        subject  — email subject line
        body     — plain-text body (may be empty if HTML-only email)
        date     — RFC 2822 date string from the email headers
    """
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
    """Add the coop-tracker-processed label to an email so it won't be fetched again."""
    label_id = _get_or_create_label(service, PROCESSED_LABEL)
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"addLabelIds": [label_id]},
    ).execute()
