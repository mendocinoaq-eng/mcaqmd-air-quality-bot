"""
MCAQMD Burn Day Email → Facebook Poster (via Buffer)
Reads the daily burn day determination email from the MCAQMD
Outlook inbox using Microsoft Graph API, parses the burn status,
and posts to the MCAQMD Facebook Page via Buffer.
Runs via GitHub Actions once daily at 6:30 PM PT.

Email format expected:
    Subject: Burn Call for Mendocino County: Wednesday, May 20, 2026 is a Permissive Burn Day
    Body contains:
        Burn Call Date: Wednesday, May 20, 2026
        Burn Status: Permissive Burn Day
"""

import os
import re
import requests
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
AZURE_CLIENT_ID     = os.environ["AZURE_CLIENT_ID"]
AZURE_CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
AZURE_TENANT_ID     = os.environ["AZURE_TENANT_ID"]
BUFFER_API_KEY      = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID   = os.environ["BUFFER_CHANNEL_ID"]

INBOX_EMAIL    = "mcaqmd@mendocinocounty.gov"
TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── Step 1: Get Microsoft access token ────────────────────────────────────────
def get_ms_token():
    url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type":    "client_credentials",
        "client_id":     AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope":         "https://graph.microsoft.com/.default",
    }
    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]

# ── Step 2: Search Outlook inbox for burn day email ───────────────────────────
def get_burn_email(token):
    url = (
        f"https://graph.microsoft.com/v1.0/users/{INBOX_EMAIL}/messages"
        f"?$filter=contains(subject,'Burn Call for Mendocino County')"
        f"&$orderby=receivedDateTime desc"
        f"&$top=5"
        f"&$select=subject,body,receivedDateTime"
    )
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    messages = resp.json().get("value", [])

    if not messages:
        raise RuntimeError(
            f"No burn day email found in {INBOX_EMAIL} with subject "
            "'Burn Call for Mendocino County'."
        )
    return messages[0]

# ── Step 3: Parse burn status from email ──────────────────────────────────────
def parse_burn_status(message):
    subject    = message.get("subject", "")
    body       = message.get("body", {}).get("content", "")
    clean_body = re.sub(r"<[^>]+>", " ", body)
    clean_body = re.sub(r"\s+", " ", clean_body).strip()
    full_text  = subject + " " + clean_body

    # Extract burn date from "Burn Call Date: Wednesday, May 20, 2026"
    date_match = re.search(
        r"Burn Call Date:\s*([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})",
        full_text
    )
    # Fallback: extract from subject line
    if not date_match:
        date_match = re.search(
            r"Mendocino County:\s*([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})",
            full_text
        )
    burn_date = date_match.group(1).strip() if date_match else "tomorrow"

    # Extract status from "Burn Status: Permissive Burn Day"
    status_match = re.search(r"Burn Status:\s*([^\n\r<]+)", full_text)
    raw_status   = status_match.group(1).strip() if status_match else None

    # Fallback: extract from subject line
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

    return burn_date, raw_status.strip()

# ── Step 4: Build the Facebook post ───────────────────────────────────────────
def build_burn_day_message(burn_date, raw_status):
    status_lower = raw_status.lower()

    if "permissive" in status_lower:
        emoji       = "✅"
        status_line = "PERMISSIVE BURN DAY"
        detail      = (
            "Open Outdoor Burning is permitted. Always follow all applicable regulations.\n"
            "• Burn only clean, dry wood\n"
            "• Do not burn any material imported from outside the bounds of the property\n"
            "• Never burn garbage, treated wood, or plastics\n"
            "• Burn hours are 9 AM to 3 PM\n"
	    "• Burn piles are limited to 4 x 4 feet, unless otherwise stated by a fire agency\n
            "• Stop burning if smoke impacts neighbors\n"
            "• ALL Open Outdoor Burning requires an MCAQMD Burn Permit and a Fire Permit from Cal Fire or your local Fire Agency."
        )
    elif "no burn" in status_lower or "prohibited" in status_lower:
        emoji       = "🚫"
        status_line = "NO BURN DAY"
        detail      = (
            "All open outdoor burning IS NOT permitted.\n"
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
        f"🌐 More info: co.mendocino.ca.us/aqmd\n\n"
        f"#MendocinoCounty #BurnDay #MCAQMD #AirQuality #Ukiah"
    )

# ── Step 5: Post to Buffer ─────────────────────────────────────────────────────
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
    print("Getting Microsoft access token...")
    token = get_ms_token()

    print(f"Searching {INBOX_EMAIL} for burn day email...")
    message = get_burn_email(token)
    print(f"Found email: {message['subject']}")

    burn_date, raw_status = parse_burn_status(message)
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
