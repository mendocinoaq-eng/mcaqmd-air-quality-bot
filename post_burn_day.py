"""
MCAQMD Burn Day Website Scraper → Facebook Poster (via Buffer)
Scrapes the burn day status from the MCAQMD website at
co.mendocino.ca.us/aqmd and posts to the MCAQMD Facebook
Page through Buffer's GraphQL API.
Runs via GitHub Actions once daily at 6:30 PM PT.

The website contains text like:
"Thursday, May 21, 2026 is a Permissive Burn day."
in the Burn Day Status sidebar section.
"""

import os
import re
import requests
from datetime import datetime
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
BUFFER_API_KEY    = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.environ["BUFFER_CHANNEL_ID"]

MCAQMD_URL     = "https://www.co.mendocino.ca.us/aqmd/"
TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── Step 1: Scrape the MCAQMD website ─────────────────────────────────────────
def get_burn_status_from_website():
    headers = {
        # Identify ourselves politely
        "User-Agent": "MCAQMD-BurnDay-Bot/1.0 (Mendocino County Air Quality Management District)"
    }
    resp = requests.get(MCAQMD_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # Look for the burn day status sentence pattern:
    # "[Day], [Month] [D], [YYYY] is a Permissive Burn day."
    # "[Day], [Month] [D], [YYYY] is a No Burn day."
    # "[Day], [Month] [D], [YYYY] is a Spare the Air day."
    pattern = re.search(
        r"([A-Za-z]+,\s+[A-Za-z]+ \d{1,2},\s+\d{4})\s+is\s+an?\s+([^<\.\"]+(?:Burn day|Burn Day|No Burn|Spare the Air)[^<\.\"]*)",
        html,
        re.IGNORECASE
    )

    if not pattern:
        raise RuntimeError(
            "Could not find burn day status on the MCAQMD website. "
            "The website format may have changed. Please check co.mendocino.ca.us/aqmd manually."
        )

    burn_date  = pattern.group(1).strip()
    raw_status = pattern.group(2).strip()

    return burn_date, raw_status

# ── Step 2: Build the Facebook post ───────────────────────────────────────────
def build_burn_day_message(burn_date, raw_status):
    status_lower = raw_status.lower()

    if "permissive" in status_lower:
        emoji       = "✅"
        status_line = "PERMISSIVE BURN DAY"
        detail      = (
            "Open Outdoor Burning IS permitted. Always follow all applicable regulations.\n"
            "• Burn only clean, dry wood\n"
            "• Do not burn any material imported from outside the bounds of the property\n"
            "• Never burn garbage, treated wood, or plastics\n"
            "• Extinguish completely before leaving\n"
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
    print(f"Scraping burn day status from {MCAQMD_URL}...")
    burn_date, raw_status = get_burn_status_from_website()
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

