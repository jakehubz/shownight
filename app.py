from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json

@app.route("/test", methods=["GET", "POST"])
def test_sms():
    if request.method == "POST":
        body = request.form.get("Body", "").strip()
        from_number = request.form.get("From", "+19999999999")  # Fake test number
        responses = handle_incoming_sms(body, from_number)
        return "<br><br>".join(responses)
    
    return '''
        <form method="post">
            <label>Body: <input name="Body"></label><br>
            <label>From: <input name="From" value="+19999999999"></label><br>
            <button type="submit">Send</button>
        </form>
    '''

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------- Google‑Sheets setup ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Chicago Shows by Text").sheet1  # adjust if sheet name differs

# ---------- Globals ----------
user_last_shows: dict[str, list[dict]] = {}  # phone → list of show dicts
CHI_TZ = ZoneInfo("America/Chicago")
DAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

# ---------- Helpers ----------
def get_shows_for_today(limit: int = 5) -> list[dict]:
    """Return up to `limit` shows running today with full details."""
    now_chi = datetime.now(CHI_TZ)
    today_date = now_chi.date()
    weekday_name = now_chi.strftime("%A")  # e.g. "Monday"

    rows = sheet.get_all_records(default_blank="")
    shows = []

    for row in rows:
        try:
            start = datetime.strptime(row["StartDate"], "%m/%d/%Y").date()
            end   = datetime.strptime(row["EndDate"], "%m/%d/%Y").date()
        except (KeyError, ValueError):
            continue  # skip rows with bad dates

        if not (start <= today_date <= end):
            continue  # not running today

        # Pick today’s time or fall back to OtherTimes column
        time_today = row.get(weekday_name, "").strip() or row.get("OtherTimes", "").strip()
        if not time_today:
            continue  # no performance today

        show = {
            "title":        row.get("Title", "").upper(),
            "type":         row.get("Type", ""),
            "adjective":    row.get("Adjective", "").lower(),
            "about":        row.get("About", ""),
            "venue":        row.get("Venue", ""),
            "neighborhood": row.get("Neighborhood", ""),
            "address":      row.get("Address", ""),
            "time":         time_today,
            "price":        row.get("Price", ""),
            "website":      row.get("Website", ""),
            "ticket_site":  row.get("TicketSite", ""),
        }
        shows.append(show)

    return shows[:limit]

def build_brief(show: dict) -> str:
    """One‑line summary used in the list reply."""
    return (
        f"{show['title']} – a {show['adjective']} {show['type']} at "
        f"{show['venue']} in {show['neighborhood']}. "
        f"{show['time']}. ${show['price']}."
    )

def build_details(show: dict) -> str:
    """Multi‑line detailed reply when user texts a number."""
    ticket_link = show["ticket_site"] or show["website"] or "Check with venue."
    return (
        f"{show['title']}\n"
        f"A {show['adjective']} {show['type']} about {show['about']}.\n"
        f"Venue: {show['venue']}\n"
        f"Address: {show['address']}\n"
        f"Neighborhood: {show['neighborhood']}\n"
        f"Time: {show['time']}\n"
        f"Price: ${show['price']}\n"
        f"Tickets: {ticket_link}"
    )

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def home():
    return "🎭 ShowNight is live and ready!"

def handle_incoming_sms(body, from_number):
    response_messages = []
    body = body.strip()
    upper_body = body.upper()

    # ---- Command: SHOWS TONIGHT ----
    if upper_body == "SHOWS TONIGHT":
        shows = get_shows_for_today()
        if not shows:
            return ["Sorry, I couldn't find any shows for tonight."]

        # Save full list for this user
        user_last_shows[from_number] = shows

        # Build list reply
        reply_lines = ["Here are a few shows happening tonight:\n"]
        for i, show in enumerate(shows, start=1):
            reply_lines.append(f"{i}. {build_brief(show)}")
        reply_lines.append("\nReply with the number of a show for more info.")
        return ["\n\n".join(reply_lines)]

    # ---- Command: digit (show details) ----
    if body.isdigit():
        index = int(body) - 1
        shows = user_last_shows.get(from_number)
        if shows and 0 <= index < len(shows):
            return [build_details(shows[index])]
        else:
            return [
                "I don't have that show number. "
                "Text SHOWS TONIGHT to get the latest list."
            ]

    # ---- Fallback / help ----
    return [
        "Welcome to ShowNight! "
        "Text SHOWS TONIGHT to see what's playing in Chicago."
    ]
    
@app.route("/sms", methods=["POST"])
def sms_reply():
    incoming = request.values.get("Body", "").strip()
    from_number = request.values.get("From")
    resp = MessagingResponse()

    responses = handle_incoming_sms(incoming, from_number)
    for msg in responses:
        resp.message(msg)

    return str(resp)

# ---------- Main ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
