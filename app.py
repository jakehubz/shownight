from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Set up Google Sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Chicago Shows by Text").sheet1

# Helper: Get today's shows
def get_shows_for_today():
    today = datetime.now().strftime("%A")
    today_date = datetime.now().date()

    rows = sheet.get_all_records()
    matching_shows = []

    for row in rows:
        try:
            start_date = datetime.strptime(row["Start Date"], "%m/%d/%Y").date()
            end_date = datetime.strptime(row["End Date"], "%m/%d/%Y").date()
        except ValueError:
            continue

        if start_date <= today_date <= end_date:
            show_time = row.get(today, "").strip()
            if show_time:
                title = row.get("Show Title", "").upper()
                adj = row.get("Adjective", "").lower()
                about = row.get("About", "")
                venue = row.get("Venue", "")
                neighborhood = row.get("Neighborhood", "")
                cost = row.get("Cost", "")
                time = show_time

                show_str = f"{title} - a {adj} play about {about} at {venue} in {neighborhood}. {time}. ${cost}."
                matching_shows.append(show_str)

    return matching_shows[:5] if matching_shows else ["No shows found for tonight."]

@app.route("/", methods=["GET"])
def home():
    return "🎭 ShowNight is live and ready!"

# Route for Twilio SMS
@app.route("/sms", methods=["POST"])
def sms_reply():
    incoming_msg = request.values.get("Body", "").strip().upper()
    resp = MessagingResponse()

    if incoming_msg == "SHOWS TONIGHT":
        shows = get_shows_for_today()
        reply = "Here are a few shows happening tonight:\n\n"
        for i, show in enumerate(shows, 1):
            reply += f"{i}. {show}\n\n"
    else:
        reply = "Try texting SHOWS TONIGHT to find out what's playing in Chicago."

    resp.message(reply.strip())
    return str(resp)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
