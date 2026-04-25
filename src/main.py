import os
import sys

from gmail_client import fetch_unread_coop_emails, get_service as gmail_service, mark_as_processed
from claude_client import extract_application_data
from sheets_client import append_row, get_service as sheets_service

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")


def main():
    if not SPREADSHEET_ID:
        print("ERROR: SPREADSHEET_ID environment variable is not set.")
        sys.exit(1)

    gmail = gmail_service()
    sheets = sheets_service()

    emails = fetch_unread_coop_emails(gmail)
    print(f"Found {len(emails)} new email(s) to process.")

    processed = 0
    skipped = 0

    for email in emails:
        try:
            data = extract_application_data(email["subject"], email["body"])

            row = [
                email["date"],        # Date Received
                data["company"],      # Company
                data["role"],         # Role
                data["status"],       # Status
                data["deadline"],     # Deadline
                email["subject"],     # Email Subject
                email["body"][:200],  # just a snippet so you can sanity check the row
            ]

            append_row(sheets, SPREADSHEET_ID, row)
            mark_as_processed(gmail, email["id"])

            print(f"  ✓ {data['company']} | {data['role']} | {data['status']}")
            processed += 1

        except Exception as e:
            # don't let one bad email crash the whole run, just skip it
            print(f"  ✗ Skipped email '{email['subject']}': {e}")
            skipped += 1

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
