import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The tab name inside the Google Sheet — change if yours is named differently.
SHEET_TAB = "Sheet1"


def get_service():
    """Authenticate and return a Google Sheets API service object.

    Reuses the same token.json as the Gmail client — both APIs were enabled
    on the same Google Cloud project, so one OAuth flow covers both.
    """
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("sheets", "v4", credentials=creds)


def append_row(service, spreadsheet_id: str, row: list):
    """Append a single row to the bottom of the tracker sheet.

    row should be a list in this column order:
        [Date Received, Company, Role, Status, Deadline, Email Subject, Email Snippet]
    """
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="USER_ENTERED",  # lets Sheets parse dates automatically
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
