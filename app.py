from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Check if we're running on Vercel
ON_VERCEL = os.environ.get('VERCEL')

# Load .env file if not on Vercel
if not ON_VERCEL:
    from dotenv import load_dotenv
    load_dotenv()


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

app = Flask(__name__)

last_modified_time = None

@app.route('/', methods=['GET', 'POST'])
def display_sheet():
    global last_modified_time
    try:
        # Open the spreadsheet
        sheet = client.open_by_key('1EWc4ZEPuE3oLvHmuQ5_4Bb7uR3Gy8bwYlRxdbuUf_4s').worksheet('Sheet1')
        
        # Update the last modified time
        last_modified_time = datetime.now()
        
        # Get all values
        rows = sheet.get_all_values()
        headers = rows[0][1:5]  # Get headers excluding the first column (क्रमांक) and last column (दिनांक)
        
        # Get the selected date or use today's date
        selected_date = request.form.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
        
        # Filter data for the selected date
        filtered_data = []
        for idx, row in enumerate(rows[1:], start=1):
            try:
                row_date = datetime.strptime(row[-1], "%m/%d/%Y")
                if row_date.date() == selected_date_obj.date():
                    filtered_data.append([idx] + row[1:5])  # Add serial number and exclude first and last columns
            except ValueError:
                continue  # Skip rows with invalid date format
        
        # Get current date and time
        current_date = datetime.now().strftime("%d/%m/%Y")
        current_time = last_modified_time.strftime("%H:%M")
        
        # Check if data exists for the selected date
        if not filtered_data:
            error_message = f"Data not found for {selected_date_obj.strftime('%d/%m/%Y')}"
            return render_template('sheet.html', headers=headers, data=[], current_time=current_time, 
                                   release_date=current_date, error_message=error_message, selected_date=selected_date)
        
        return render_template('sheet.html', headers=['क्रमांक'] + headers, data=filtered_data, 
                               current_time=current_time, release_date=selected_date_obj.strftime("%d/%m/%Y"),
                               selected_date=selected_date)
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/check_changes')
def check_changes():
    global last_modified_time
    sheet = client.open_by_key('1EWc4ZEPuE3oLvHmuQ5_4Bb7uR3Gy8bwYlRxdbuUf_4s').worksheet('Sheet1')
    current_modified_time = sheet.updated
    
    if current_modified_time != last_modified_time:
        last_modified_time = current_modified_time
        return jsonify({"hasChanges": True})
    return jsonify({"hasChanges": False})

if __name__ == '__main__':
    app.run(debug=True)