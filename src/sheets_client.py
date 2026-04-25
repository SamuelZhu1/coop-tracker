import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# change this if your sheet tab has a different name
SHEET_TAB = "Sheet1"


def get_service():
    # same token.json as gmail_client - one oauth flow covers both since they're
    # on the same google cloud project
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
    # row order: [Date Received, Company, Role, Status, Deadline, Email Subject, Email Snippet]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="USER_ENTERED",  # USER_ENTERED lets sheets parse dates properly
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
