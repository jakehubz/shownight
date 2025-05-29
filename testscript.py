import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define scope for Sheets + Drive access
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials and authorize client
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open your sheet by its name
spreadsheet = client.open("Chicago Shows by Text")
sheet = spreadsheet.sheet1  # or .worksheet("Sheet1")

# Fetch all records as a list of dicts
data = sheet.get_all_records()

# Print the data to test it worked
print("Successfully fetched data:")
for row in data:
    print(row)
