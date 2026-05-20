"""
MCAQMD Hourly PM2.5 Spike Advisory Poster (via Buffer)
Checks AirNow hourly for PM2.5 levels across all Mendocino County
zip codes. If AQI >= 101 is detected and was also >= 101 in the
previous hour (sustained 2 hours), posts an air quality advisory
to the MCAQMD Facebook Page via Buffer.

Runs via GitHub Actions every hour.
Uses GitHub Actions cache to store previous hour's readings.
"""

import os
import json
import time
import requests
from datetime import datetime
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
AIRNOW_API_KEY    = os.environ["AIRNOW_API_KEY"]
BUFFER_API_KEY    = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.environ["BUFFER_CHANNEL_ID"]

TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# State file to track previous hour's readings and posted advisories
STATE_FILE = "spike_state.json"

# ── All Mendocino County zip codes ────────────────────────────────────────────
MENDOCINO_ZIPS = {
    "95410": "Albion",
    "95415": "Boonville",
    "95420": "Caspar",
    "95427": "Comptche",
    "95428": "Covelo",
    "95429": "Dos Rios",
    "95432": "Elk",
    "95437": "Fort Bragg",
    "95445": "Gualala",
    "95449": "Hopland",
    "95454": "Laytonville",
    "95456": "Little River",
    "95459": "Manchester",
    "95460": "Mendocino",
    "95463": "Navarro",
    "95466": "Philo",
    "95468": "Point Arena",
    "95469": "Potter Valley",
    "95470": "Redwood Valley",
    "95482": "Ukiah",
    "95485": "Willits",
    "95488": "Westport",
    "95490": "Willits",
    "95494": "Yorkville",
}

# AQI threshold to trigger advisory
SPIKE_THRESHOLD = 101

# ── AQI category ──────────────────────────────────────────────────────────────
def aqi_category(aqi):
    # Note: this function is only ever called when AQI >= 101
    # so the "Moderate" category (0-100) will never appear in a post
    if aqi <= 150:  return "Unhealthy for Sensitive Groups 🟠"
    if aqi <= 200:  return "Unhealthy 🔴"
    if aqi <= 300:  return "Very Unhealthy 🟣"
    return "Hazardous ⚫"

def aqi_health_message(aqi):
    if aqi <= 150:
        return (
            "People with heart or lung disease, older adults, children, "
            "and people who are active outdoors should reduce prolonged or heavy exertion."
        )
    if aqi <= 200:
        return (
            "Everyone should reduce prolonged or heavy exertion. "
            "People with heart or lung disease, older adults, and children "
            "should avoid all outdoor physical activity."
        )
    if aqi <= 300:
        return (
            "Everyone should avoid prolonged or heavy exertion outdoors. "
            "People with heart or lung disease, older adults, and children "
            "should remain indoors and keep activity levels low."
        )
    return (
        "HEALTH ALERT: Everyone should avoid all outdoor exertion. "
        "Remain indoors with windows closed. Run air conditioning or an air purifier if available. "
        "If you must go outside, wear an N95 or KN95 respirator."
    )

# ── Load and save state ────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "previous_readings": {},   # zip: aqi from last hour
        "active_advisories": {},   # zip: timestamp of last advisory posted
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── Fetch AirNow data for a single zip code ────────────────────────────────────
def get_aqi_for_zip(zip_code, retries=2, delay=5):
    url = "https://www.airnowapi.org/aq/observation/zipCode/current/"
    params = {
        "format":   "application/json",
        "zipCode":  zip_code,
        "distance": 25,
        "API_KEY":  AIRNOW_API_KEY,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            pm25 = next((d for d in data if d.get("ParameterName") == "PM2.5"), None)
            if pm25:
                return pm25["AQI"], pm25.get("ReportingArea", MENDOCINO_ZIPS.get(zip_code, zip_code))
            return None, None
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(delay)
        except Exception as e:
            print(f"  Error fetching {zip_code}: {e}")
            return None, None
    return None, None

# ── Build advisory post text ───────────────────────────────────────────────────
def build_advisory_message(spikes):
    now      = datetime.now(TIMEZONE)
    date_str = now.strftime("%A, %B %d, %Y at %-I:%M %p")

    # Sort by AQI descending so highest is listed first
    spikes_sorted = sorted(spikes, key=lambda x: x["aqi"], reverse=True)
    highest_aqi   = spikes_sorted[0]["aqi"]
    category      = aqi_category(highest_aqi)
    health_msg    = aqi_health_message(highest_aqi)

    # Build location list
    location_lines = ""
    for s in spikes_sorted:
        location_lines += f"• {s['area']} — AQI {s['aqi']} ({aqi_category(s['aqi'])})\n"

    # Pick appropriate urgency level
    if highest_aqi >= 201:
        opener = "🚨 AIR QUALITY ADVISORY"
    else:
        opener = "⚠️ AIR QUALITY ADVISORY"

    message = (
        f"{opener} — {date_str}\n\n"
        f"AirNow monitoring data has detected elevated PM2.5 (fine particle) levels "
        f"sustained for 2 or more hours in the following areas of Mendocino County:\n\n"
        f"{location_lines}\n"
        f"📌 What may be causing this?\n"
        f"Elevated PM2.5 readings can have many causes — not all of them emergencies. "
        f"Possible sources include permitted prescribed burns, agricultural burning, "
        f"residential wood stove and fireplace smoke, or unpermitted events such as "
        f"illegal burning, wildfire activity, dust, or heavy vehicle traffic. "
        f"MCAQMD is monitoring the situation. If you see or smell smoke and believe "
        f"an unpermitted burn is occurring, please call us at (707) 463-4354 or "
        f"email mcaqmd@mendocinocounty.gov.\n\n"
        f"🫁 Health guidance for AQI {highest_aqi} — {category}:\n"
        f"{health_msg}\n\n"
        f"💡 Tips to protect yourself:\n"
        f"• Stay indoors with windows and doors closed\n"
        f"• Use an air purifier with a HEPA filter if available\n"
        f"• Avoid burning wood, candles, or anything that adds smoke indoors\n"
        f"• If you must go outside, wear a properly fitted N95 or KN95 respirator\n\n"
        f"Monitor current conditions at airnow.gov.\n\n"
        f"#MendocinoCounty #AirQuality #AirQualityAdvisory #MCAQMD #Smoke #PM25"
    )
    return message

# ── Post to Buffer ─────────────────────────────────────────────────────────────
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
    now_pt  = datetime.now(TIMEZONE)
    now_str = now_pt.strftime("%Y-%m-%d %H:%M %Z")
    print(f"\n── MCAQMD Spike Check — {now_str} ──────────────────")

    state             = load_state()
    previous_readings = state.get("previous_readings", {})
    active_advisories = state.get("active_advisories", {})
    current_readings  = {}
    spikes_to_alert   = []

    print(f"Checking {len(MENDOCINO_ZIPS)} Mendocino County zip codes...\n")

    for zip_code, city in MENDOCINO_ZIPS.items():
        aqi, area = get_aqi_for_zip(zip_code)

        if aqi is None:
            print(f"  {zip_code} ({city}): No data")
            continue

        current_readings[zip_code] = aqi
        prev_aqi = previous_readings.get(zip_code)

        print(f"  {zip_code} ({city}): AQI {aqi} (prev: {prev_aqi})")

        # Check for sustained spike — current AND previous hour both >= threshold
        if aqi >= SPIKE_THRESHOLD and prev_aqi is not None and prev_aqi >= SPIKE_THRESHOLD:
            # Don't re-alert for the same area within 4 hours
            last_alert = active_advisories.get(zip_code)
            if last_alert:
                last_alert_time = datetime.fromisoformat(last_alert)
                hours_since = (now_pt.replace(tzinfo=None) - last_alert_time.replace(tzinfo=None)).total_seconds() / 3600
                if hours_since < 4:
                    print(f"    → Spike detected but advisory already posted {hours_since:.1f}hrs ago, skipping.")
                    continue

            print(f"    → ⚠️ SUSTAINED SPIKE DETECTED! AQI {aqi} for 2+ hours.")
            spikes_to_alert.append({
                "zip":  zip_code,
                "city": city,
                "area": area or city,
                "aqi":  aqi,
            })

        # Small delay between API calls to be polite to AirNow
        time.sleep(1)

    # Post advisory if any sustained spikes found
    if spikes_to_alert:
        print(f"\n⚠️ Posting advisory for {len(spikes_to_alert)} area(s)...")
        message = build_advisory_message(spikes_to_alert)
        print("\n── Post preview ──────────────────────────────")
        print(message)
        print("──────────────────────────────────────────────\n")

        post = post_to_buffer(message)
        print(f"✅ Advisory posted! Post ID: {post['id']}")

        # Record advisory times
        for s in spikes_to_alert:
            active_advisories[s["zip"]] = now_pt.isoformat()
    else:
        print("\n✅ No sustained spikes detected. No advisory needed.")

    # Save updated state
    state["previous_readings"] = current_readings
    state["active_advisories"] = active_advisories
    save_state(state)
    print(f"\nState saved. Next check in 1 hour.")

if __name__ == "__main__":
    main()
