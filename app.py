from flask import Flask, render_template
from datetime import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Check if we're running on Vercel
ON_VERCEL = os.environ.get('VERCEL')

# Load .env file if not on Vercel
if not ON_VERCEL:
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)

# Set up credentials using environment variables
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = {
    "type": os.environ.get("GOOGLE_SERVICE_ACCOUNT_TYPE"),
    "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
    "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if os.environ.get("GOOGLE_PRIVATE_KEY") else None,
    "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
    "auth_uri": os.environ.get("GOOGLE_AUTH_URI"),
    "token_uri": os.environ.get("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.environ.get("GOOGLE_CLIENT_X509_CERT_URL")
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
client = gspread.authorize(creds)

@app.route('/')
def display_sheet():
    try:
        # Open the spreadsheet
        sheet = client.open_by_key('1EWc4ZEPuE3oLvHmuQ5_4Bb7uR3Gy8bwYlRxdbuUf_4s').worksheet('Sheet1')
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

if __name__ == '__main__':
    app.run(debug=True)