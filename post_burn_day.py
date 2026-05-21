"""
MCAQMD Burn Day Facebook Poster (via Buffer)
Reads the burn day status passed from Power Automate via a
GitHub repository dispatch event, parses it, and posts to the
MCAQMD Facebook Page through Buffer's GraphQL API.

The burn status is passed in the GitHub Actions environment as:
    BURN_STATUS = email subject line from Power Automate
    e.g. "Burn Call for Mendocino County: Wednesday, May 20, 2026 is a Permissive Burn Day"
"""

import os
import re
import requests
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
BUFFER_API_KEY    = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.environ["BUFFER_CHANNEL_ID"]

# Passed in from the dispatch event payload via the workflow
BURN_STATUS_RAW = os.environ.get("BURN_STATUS", "")

TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── Step 1: Parse burn date and status from subject line ──────────────────────
def parse_burn_status(subject):
    if not subject:
        raise RuntimeError("No burn status received from Power Automate.")

    print(f"Parsing subject: {subject}")

    # Extract burn date from subject:
    # "Burn Call for Mendocino County: Wednesday, May 20, 2026 is a Permissive Burn Day"
    date_match = re.search(
        r"([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})",
        subject
    )
    burn_date = date_match.group(1).strip() if date_match else "tomorrow"

    # Extract status — look for known keywords
    subject_lower = subject.lower()
    if "permissive burn day" in subject_lower:
        raw_status = "Permissive Burn Day"
    elif "no burn day" in subject_lower or "no burn" in subject_lower:
        raw_status = "No Burn Day"
    elif "spare the air" in subject_lower:
        raw_status = "Spare the Air"
    else:
        # Try to extract anything after "is a" or "is an"
        status_match = re.search(r"is an?\s+([^\"]+)$", subject, re.IGNORECASE)
        raw_status = status_match.group(1).strip() if status_match else "Status Unavailable"

    return burn_date, raw_status

# ── Step 2: Build the Facebook post ───────────────────────────────────────────
def build_burn_day_message(burn_date, raw_status):
    status_lower = raw_status.lower()

    if "permissive" in status_lower:
        emoji       = "✅"
        status_line = "PERMISSIVE BURN DAY"
        detail      = (
            "Open Outdoor Burning IS permitted. Always follow all applicable regulations.\n"
            "• Burn only clean, dry vegetative material\n"
            "• Do not burn any material imported from outside the bounds of the property\n"
            "• Never burn garbage, lumber, treated wood, or plastics\n"
            "• Burn hours are 9 AM to 3 PM\n"
            "• Pile size restricted to 4 x 4 feet unless otherwise stated by a Fire Agency\n"
            "• A responsible adult must be present for the entirety of the burn\n"
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

# ── Step 3: Post to Buffer ─────────────────────────────────────────────────────
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
    print(f"Burn status received from Power Automate: {BURN_STATUS_RAW}")

    burn_date, raw_status = parse_burn_status(BURN_STATUS_RAW)
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
