import json
import os
import anthropic

# Haiku is 20x cheaper than Sonnet/Opus and handles structured extraction perfectly.
# There's no reason to use a more expensive model for a task this simple.
MODEL = "claude-haiku-4-5-20251001"

PROMPT_TEMPLATE = """Extract the following from this co-op application email.
Respond ONLY with valid JSON. No markdown fences, no explanation, no other text.

Fields:
- company (string): the company that sent this email
- role (string): the specific job title or role mentioned
- status (string): one of exactly: "rejection", "interview_invite", "received", "other"
  - "rejection": they declined your application
  - "interview_invite": they want to interview you
  - "received": they confirmed receiving your application
  - "other": anything else (offer, follow-up, etc.)
- deadline (string or null): any deadline mentioned, in YYYY-MM-DD format, or null if none

Email subject: {subject}

Email body:
{body}"""


def extract_application_data(subject: str, body: str) -> dict:
    """Call Claude Haiku to extract structured data from one email.

    Returns a dict with keys: company, role, status, deadline.
    Raises ValueError if Claude returns malformed JSON (caller should catch and skip).
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Truncate body to 2000 chars — Claude doesn't need the full email for extraction,
    # and this keeps token costs low on long HTML-heavy emails.
    truncated_body = body[:2000] if body else "(no body)"

    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    subject=subject, body=truncated_body
                ),
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown fences if Claude wrapped the JSON anyway (it sometimes does).
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned non-JSON: {raw_text!r}") from e

    # Normalise to expected keys with safe defaults.
    return {
        "company": data.get("company", "Unknown"),
        "role": data.get("role", "Unknown"),
        "status": data.get("status", "other"),
        "deadline": data.get("deadline") or "",
    }
