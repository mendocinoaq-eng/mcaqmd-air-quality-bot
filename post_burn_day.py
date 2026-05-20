"""
MCAQMD Burn Day Email → Facebook Poster (via Buffer)
Reads the daily burn day determination email forwarded to Gmail,
parses the burn status, and posts to the MCAQMD Facebook Page via Buffer.
Runs via GitHub Actions once daily after 5:30 PM PT.

Email format expected:
    Subject: Fw: Burn Call for Mendocino County: Wednesday, May 20, 2026 is a Permissive Burn Day
    Body contains:
        Burn Call Date: Wednesday, May 20, 2026
        Burn Status: Permissive Burn Day
"""

import os
import re
import base64
import requests
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
GMAIL_CLIENT_ID     = os.environ["GMAIL_CLIENT_ID"]
GMAIL_CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
GMAIL_REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]
BUFFER_API_KEY      = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID   = os.environ["BUFFER_CHANNEL_ID"]

SENDER_EMAIL   = "mcaqmd@mendocinocounty.org"
TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── Step 1: Get Gmail access token using refresh token ────────────────────────
def get_gmail_token():
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "refresh_token": GMAIL_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

# ── Step 2: Search Gmail for the burn day email ───────────────────────────────
def get_burn_email(token):
    headers = {"Authorization": f"Bearer {token}"}

    # Search for forwarded burn call emails from the known sender
    query = 'from:mcaqmd@mendocinocounty.org subject:"Burn Call for Mendocino County"'

    search_resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers,
        params={"q": query, "maxResults": 5},
        timeout=15,
    )
    search_resp.raise_for_status()
    messages = search_resp.json().get("messages", [])

    if not messages:
        raise RuntimeError(
            f"No burn day email found from {SENDER_EMAIL} with subject "
            "'Burn Call for Mendocino County'. "
            "Make sure auto-forwarding is set up correctly."
        )

    # Get the full content of the most recent matching email
    msg_id = messages[0]["id"]
    msg_resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
        headers=headers,
        params={"format": "full"},
        timeout=15,
    )
    msg_resp.raise_for_status()
    return msg_resp.json()

# ── Step 3: Extract subject and body text from Gmail message ──────────────────
def extract_email_text(message):
    subject = ""
    body    = ""

    # Get subject from headers
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "subject":
            subject = h["value"]
            break

    # Decode body
    payload = message.get("payload", {})

    def decode_part(part):
        data = part.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        return ""

    # Handle simple single-part messages
    if payload.get("body", {}).get("data"):
        body = decode_part(payload)
    else:
        # Handle multipart messages — prefer plain text
        for part in payload.get("parts", []):
            mime = part.get("mimeType", "")
            if mime == "text/plain":
                body = decode_part(part)
                break
            elif mime == "text/html" and not body:
                body = decode_part(part)

    # Strip any HTML tags
    body = re.sub(r"<[^>]+>", " ", body)
    # Collapse extra whitespace
    body = re.sub(r"\s+", " ", body).strip()

    return subject, body

# ── Step 4: Parse burn date and status ────────────────────────────────────────
def parse_burn_status(subject, body):
    full_text = subject + " " + body

    # Try to extract burn date from "Burn Call Date: Wednesday, May 20, 2026"
    date_match = re.search(
        r"Burn Call Date:\s*([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})",
        full_text
    )

    # Fallback: extract date from subject line
    # "Burn Call for Mendocino County: Wednesday, May 20, 2026 is a Permissive Burn Day"
    if not date_match:
        date_match = re.search(
            r"Mendocino County:\s*([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})",
            full_text
        )

    burn_date = date_match.group(1).strip() if date_match else "tomorrow"

    # Try to extract status from "Burn Status: Permissive Burn Day"
    status_match = re.search(r"Burn Status:\s*([^\n\r]+)", full_text)
    raw_status   = status_match.group(1).strip() if status_match else None

    # Fallback: extract status from subject line
    # "...is a Permissive Burn Day" or "...is a No Burn Day"
    if not raw_status:
        subject_status = re.search(
            r"is an? (Permissive Burn Day|No Burn Day|Spare the Air[^,\n]*)",
            full_text,
            re.IGNORECASE
        )
        if subject_status:
            raw_status = subject_status.group(1).strip()

    if not raw_status:
        raw_status = "Status Unavailable"

    # Clean up any trailing whitespace or extra characters
    raw_status = raw_status.strip()

    return burn_date, raw_status

# ── Step 5: Build the Facebook post ───────────────────────────────────────────
def build_burn_day_message(burn_date, raw_status):
    status_lower = raw_status.lower()

    if "permissive" in status_lower:
        emoji       = "✅"
        status_line = "PERMISSIVE BURN DAY"
        detail      = (
            "Open Outdoor Burning IS permitted. Always follow all applicable regulations.\n"
            "• Burn only clean, dry vegetative material\n"
			"• Do not burn any material imported from outside the bounds of the property\n"
            "• Never burn garbage, treated wood, lumber, or plastics\n"
            "• Extinguish completely before leaving and only burn during allowed burn hours\n"
            "• All burn piles must be attended by an adult\n"
	        "• ALL Open Outdoor Burning requires an MCAQMD Burn Permit\n" 
            "and a Fire Permit from Cal Fire or your local Fire Agency."
        )
    elif "no burn" in status_lower or "prohibited" in status_lower:
        emoji       = "🚫"
        status_line = "NO BURN DAY"
        detail      = (
            "All open outdoor burning IS prohibited.\n"
            "Violations may result in fines."
        )
    elif "spare the air" in status_lower:
        emoji       = "⚠️"
        status_line = "SPARE THE AIR — NO BURN DAY"
        detail      = (
            "A Spare the Air Day has been declared. "
            "All open outdoor burning is prohibited to protect air quality."
        )
    else:
        emoji       = "ℹ️"
        status_line = raw_status.upper()
        detail      = "Please contact our office for details about burn restrictions."

    return (
        f"{emoji} BURN DAY STATUS — {burn_date}\n\n"
        f"Mendocino County: {status_line}\n\n"
        f"{detail}\n\n"
        f"📞 Burn Day Status Line: (707) 463-4391\n"
        f"🌐 More info: www.mendoair.org\n\n"
        f"#MendocinoCounty #BurnDay #MCAQMD #AirQuality"
    )

# ── Step 6: Post to Buffer ─────────────────────────────────────────────────────
def post_to_buffer(message):
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id text status }
        }
        ... on NotFoundError      { message }
        ... on UnauthorizedError  { message }
        ... on UnexpectedError    { message }
        ... on RestProxyError     { message }
        ... on LimitReachedError  { message }
        ... on InvalidInputError  { message }
      }
    }
    """
    variables = {
        "input": {
            "text":           message,
            "channelId":      BUFFER_CHANNEL_ID,
            "schedulingType": "automatic",
            "mode":           "shareNow",
            "assets":         [],
            "metadata": {
                "facebook": {
                    "type": "post"
                }
            }
        }
    }
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {BUFFER_API_KEY}",
    }
    resp = requests.post(
        BUFFER_API_URL,
        json={"query": mutation, "variables": variables},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if "errors" in result:
        raise RuntimeError(f"Buffer GraphQL error: {result['errors']}")
    post_result = result["data"]["createPost"]
    if "message" in post_result:
        raise RuntimeError(f"Buffer rejected post: {post_result['message']}")
    return post_result["post"]

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Getting Gmail access token...")
    token = get_gmail_token()

    print("Searching Gmail for burn day email...")
    message = get_burn_email(token)

    subject, body = extract_email_text(message)
    print(f"Found email: {subject}")
    print(f"Body preview: {body[:200]}")

    burn_date, raw_status = parse_burn_status(subject, body)
    print(f"Burn date:   {burn_date}")
    print(f"Burn status: {raw_status}")

    post_text = build_burn_day_message(burn_date, raw_status)
    print("\n── Post preview ──────────────────────────────")
    print(post_text)
    print("──────────────────────────────────────────────\n")

    post = post_to_buffer(post_text)
    print(f"✅ Posted to Buffer! Post ID: {post['id']} | Status: {post['status']}")

if __name__ == "__main__":
    main()
