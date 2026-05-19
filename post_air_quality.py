"""
MCAQMD Air Quality Facebook Poster (via Buffer)
Pulls PM2.5 data from AirNow API and posts to the MCAQMD
Facebook Page through Buffer's GraphQL API.
Runs via GitHub Actions twice daily.
"""

import os
import requests
from datetime import datetime
import pytz

# ── Config (set these as GitHub Secrets) ──────────────────────────────────────
AIRNOW_API_KEY    = os.environ["AIRNOW_API_KEY"]
BUFFER_API_KEY    = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.environ["BUFFER_CHANNEL_ID"]

UKIAH_ZIP      = "95482"
TIMEZONE       = pytz.timezone("America/Los_Angeles")
BUFFER_API_URL = "https://api.buffer.com"

# ── AQI helpers ────────────────────────────────────────────────────────────────
def aqi_category(aqi):
    if aqi <= 50:   return "Good 🟢"
    if aqi <= 100:  return "Moderate 🟡"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups 🟠"
    if aqi <= 200:  return "Unhealthy 🔴"
    if aqi <= 300:  return "Very Unhealthy 🟣"
    return "Hazardous ⚫"

def aqi_health_tip(aqi):
    if aqi <= 50:
        return "Air quality is great — a perfect day to enjoy the outdoors!"
    if aqi <= 100:
        return "Air quality is acceptable. Unusually sensitive people should consider limiting prolonged outdoor exertion."
    if aqi <= 150:
        return "Members of sensitive groups (children, elderly, those with heart or lung conditions) should reduce prolonged outdoor exertion."
    if aqi <= 200:
        return "Everyone should reduce prolonged outdoor exertion. Sensitive groups should avoid outdoor activity."
    if aqi <= 300:
        return "Everyone should avoid prolonged outdoor exertion. Sensitive groups should remain indoors."
    return "Health alert: Everyone should avoid all outdoor exertion and remain indoors."

# ── Fetch AirNow data ──────────────────────────────────────────────────────────
def get_air_quality():
    url = "https://www.airnowapi.org/aq/observation/zipCode/current/"
    params = {
        "format":   "application/json",
        "zipCode":  UKIAH_ZIP,
        "distance": 25,
        "API_KEY":  AIRNOW_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# ── Build post text ────────────────────────────────────────────────────────────
def build_message(data):
    now = datetime.now(TIMEZONE)
    time_of_day = "Morning" if now.hour < 12 else "Afternoon"
    date_str = now.strftime("%A, %B %d, %Y")

    pm25    = next((d for d in data if d.get("ParameterName") == "PM2.5"), None)
    reading = pm25 or (data[0] if data else None)

    if not reading:
        return (
            f"🌿 {time_of_day} Air Quality Update — {date_str}\n\n"
            f"No air quality data is currently available for Mendocino County.\n\n"
            f"For real-time updates visit airnow.gov\n"
            f"📞 Burn Day Status: (707) 463-4391\n\n"
            f"#MendocinoCounty #AirQuality #MCAQMD"
        )

    aqi       = reading["AQI"]
    category  = aqi_category(aqi)
    tip       = aqi_health_tip(aqi)
    area      = reading.get("ReportingArea", "Mendocino County")
    pollutant = reading["ParameterName"]

    return (
        f"🌿 {time_of_day} Air Quality Update — {date_str}\n\n"
        f"📍 {area}\n"
        f"💨 {pollutant} AQI: {aqi} — {category}\n\n"
        f"ℹ️ {tip}\n\n"
        f"For real-time conditions visit airnow.gov or call (707) 463-4354.\n"
        f"🔥 Burn Day Status Line: (707) 463-4391\n\n"
        f"#MendocinoCounty #AirQuality #MCAQMD #CleanAir #Ukiah"
    )

# ── Post to Buffer via GraphQL API ─────────────────────────────────────────────
def post_to_buffer(message):
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            status
          }
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
            "schedulingType": "automatic",  # automatic = Buffer publishes it directly
            "mode":           "shareNow",   # shareNow = post immediately, no queue
            "assets":         [],           # required field, empty for text-only post
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
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()

    if "errors" in result:
        raise RuntimeError(f"Buffer GraphQL error: {result['errors']}")

    post_result = result["data"]["createPost"]

    # If it's not a success it will have a "message" field with the error
    if "message" in post_result:
        raise RuntimeError(f"Buffer rejected post: {post_result['message']}")

    return post_result["post"]

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Fetching AirNow data for Ukiah (95482)...")
    data = get_air_quality()
    print(f"Got {len(data)} reading(s) from AirNow.")

    message = build_message(data)
    print("\n── Post preview ──────────────────────────────")
    print(message)
    print("──────────────────────────────────────────────\n")

    post = post_to_buffer(message)
    print(f"✅ Posted to Buffer! Post ID: {post['id']} | Status: {post['status']}")

if __name__ == "__main__":
    main()
