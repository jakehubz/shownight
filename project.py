import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set up Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open your sheet by name
sheet = client.open("Chicago Shows by Text").sheet1
data = sheet.get_all_records()

# Get today's date and weekday
today = datetime.now().date()
weekday = datetime.now().strftime('%A')  # e.g., "Friday"

print(f"Looking for shows on {weekday}, {today.strftime('%B %d, %Y')}...\n")

tonight_shows = []

for show in data:
    try:
        start_date = datetime.strptime(show.get("Start Date", ""), "%m/%d/%Y").date()
        end_date = datetime.strptime(show.get("End Date", ""), "%m/%d/%Y").date()
    except (ValueError, TypeError):
        continue  # skip rows with invalid date formats

    # Check if today's date is in the range
    if start_date <= today <= end_date:
        showtime = show.get(weekday, "").strip()
        if showtime:
            tonight_shows.append({
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

# Display results
if tonight_shows:
    for idx, show in enumerate(tonight_shows, start=1):
        print(f"{idx}. {show['title']} – {show['adjective']} {show['type']} about {show['about']} "
              f"at {show['venue']} in {show['neighborhood']}. {show['time']} – {show['cost']}")
        if show['website']:
            print(f"    Website: {show['website']}")
        if show['tickets']:
            print(f"    Tickets: {show['tickets']}")
else:
    print("No shows scheduled for tonight.")
