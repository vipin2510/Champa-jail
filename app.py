import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set up credentials using environment variables
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = {
    "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("GOOGLE_PRIVATE_KEY") else None,
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL")
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
client = gspread.authorize(creds)

@app.route('/')
def display_sheet():
    try:
        # Open the spreadsheet
        sheet = client.open_by_key('1u0wz3jnjb50T_6D8YCqHnpaT7Cejyg5Rafu7FBA1vZk').worksheet('DB-Naxal')

        # Get all values
        rows = sheet.get_all_values()

        # Separate headers and data
        headers = rows[0]
        data = rows[1:]

        # Get current time
        current_time = datetime.now().strftime("%H:%M")

        return render_template('sheet.html', headers=headers, data=data, current_time=current_time)
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Remove the if __name__ == '__main__': block