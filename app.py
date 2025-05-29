from flask import Flask, request, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

user_sessions = {}

# Google Sheets setup
import os
import json

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load Google credentials from an environment variable
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Chicago Shows by Text").sheet1

def get_tonight_shows():
    data = sheet.get_all_records()
    today = datetime.now().date()
    weekday = datetime.now().strftime('%A')
    tonight = []
    for show in data:
        try:
            start_date = datetime.strptime(show.get("Start Date", ""), "%m/%d/%Y").date()
            end_date = datetime.strptime(show.get("End Date", ""), "%m/%d/%Y").date()
        except:
            continue
        if start_date <= today <= end_date:
            showtime = show.get(weekday, "").strip()
            if showtime:
                tonight.append({
                    "title": show.get("Show Title", "Untitled").upper(),
                    "type": show.get("Show Type", ""),
                    "adjective": show.get("Adjective", ""),
                    "about": show.get("About", ""),
                    "venue": show.get("Venue", ""),
                    "neighborhood": show.get("Neighborhood", ""),
                    "cost": show.get("Cost", ""),
                    "time": showtime,
                    "website": show.get("Website", "").strip(),
                    "tickets": show.get("Ticket Link", "").strip()
                })
    return tonight

@app.route("/", methods=["GET", "POST"])
def index():
    response = ""
    user_id = "demo-user"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"start": 0, "current": [], "filter_options": [], "filtered_type": None}

    session_data = user_sessions[user_id]

    if request.method == "POST":
        user_input = request.form["message"].strip().lower()
        tonight = get_tonight_shows()

        # First message: show type selection
        if "show" in user_input or "tonight" in user_input:
            types = sorted(set(show["type"] for show in tonight if show["type"]))
            options = ["All shows"] + types
            session_data["filter_options"] = options
            session_data["filtered_type"] = None
            session_data["start"] = 0

            response = f"There are {len(tonight)} shows happening in and around Chicago tonight.<br>"
            response += "What kind of show are you interested in?<br>"
            for i, opt in enumerate(options, start=1):
                response += f"{i}. {opt}<br>"

        # Numeric response: show filtered results
        elif user_input.isdigit():
            idx = int(user_input) - 1
            options = session_data.get("filter_options", [])
            if 0 <= idx < len(options):
                selected_type = options[idx]
                filtered = tonight if selected_type == "All shows" else [s for s in tonight if s["type"].lower() == selected_type.lower()]

                session_data["filtered_type"] = selected_type
                session_data["start"] = 5 if len(filtered) > 5 else len(filtered)
                session_data["current"] = filtered[0:5]

                response = ""
                for i, show in enumerate(filtered[0:5], start=1):
                    adj = show["adjective"]
                    article = "an" if adj and adj[0].lower() in "aeiou" else "a"
                    response += f"{i}. {show['title']} – {article} {adj} {show['type']} about {show['about']} at {show['venue']} in {show['neighborhood']}. {show['time']} – {show['cost']}<br><br>"
                if session_data["start"] < len(filtered):
                    response += f"Reply with MORE to see additional {selected_type.lower()} shows."
                else:
                    response += f"🎉 That’s all the {selected_type.lower()} shows tonight.<br>"

            else:
                response = "Invalid selection. Please enter a valid number from the list."

        elif "more" in user_input:
            filtered_type = session_data.get("filtered_type")
            options = session_data.get("filter_options", [])
            tonight = get_tonight_shows()
            filtered = tonight if filtered_type == "All shows" else [s for s in tonight if s["type"].lower() == filtered_type.lower()]
            start = session_data["start"]
            end = min(start + 5, len(filtered))

            if start >= len(filtered):
                response = f"🎉 That’s all the {filtered_type.lower()} shows tonight.<br><br>Type SHOWS TONIGHT to start over."
            else:
                session_data["current"] = filtered[start:end]
                session_data["start"] = end

                response = ""
                for i, show in enumerate(filtered[start:end], start=1):
                    adj = show["adjective"]
                    article = "an" if adj and adj[0].lower() in "aeiou" else "a"
                    response += f"{i}. {show['title']} – {article} {adj} {show['type']} about {show['about']} at {show['venue']} in {show['neighborhood']}. {show['time']} – {show['cost']}<br><br>"
                if end >= len(filtered):
                    response += f"🎉 That’s all the {filtered_type.lower()} shows tonight.<br><br>Type SHOWS TONIGHT to start over."
                else:
                    response += f"Reply with MORE to see additional {filtered_type.lower()} shows."

        else:
            response = "Type 'SHOWS TONIGHT' to see what's playing in Chicago."

    return render_template("index.html", response=response)

if __name__ == "__main__":
    app.run(debug=True)
