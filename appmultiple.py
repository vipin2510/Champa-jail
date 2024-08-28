from flask import Flask, render_template, request, jsonify, redirect, send_file
from datetime import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Check if we're running on Vercel
ON_VERCEL = os.environ.get('VERCEL')

# Load .env file if not on Vercel
if not ON_VERCEL:
    from dotenv import load_dotenv
    load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

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
SPREADSHEET_ID = '19SKGC7kUFi3ZVZEHxSavCrGOMuHVQASs-3jTIddFedg'
drive_service = build('drive', 'v3', credentials=creds)

# Fetch settings from the 'Setting' sheet
def get_settings():
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet('Setting')
        settings = sheet.get_all_values()[1:]  # Exclude header row

        valid_settings = []
        for row in settings:
            # Check if the row has at least 7 columns (index 6)
            if len(row) < 7:
                app.logger.warning(f"Row has fewer columns than expected: {row}")
                continue

            # Ensure all necessary columns are non-empty
            try:
                time_of_display = int(row[1]) if row[1] else 0
                columns_to_display = row[3].split(',') if row[3] else []
                photo_column = row[6] if row[6] else None
                display = row[4]
                title = row[5]

                if time_of_display > 0:
                    valid_settings.append({
                        'sheet_name': row[0],
                        'time_of_display': time_of_display,
                        'columns_to_display': columns_to_display,
                        'photo_column': photo_column,
                        'display': display,
                        'title': title
                    })
            except ValueError as e:
                app.logger.error(f"Error processing row: {row}. Error: {str(e)}")

        return valid_settings
    except Exception as e:
        app.logger.error(f"Error fetching settings: {str(e)}")
        return []


# Extract file ID from Google Drive link
def get_file_id_from_url(url):
    file_id = None
    if 'drive.google.com' in url:
        if '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in url:
            file_id = url.split('id=')[1].split('&')[0]
    return file_id

# Fetch data from specified sheet
def get_sheet_data(sheet_name, columns_to_display, photo_column, display_type):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    all_values = sheet.get_all_values()
    headers = [all_values[0][ord(col) - ord('A')] for col in columns_to_display]
    
    data = []
    for row in all_values[1:]:
        row_data = []
        for col in columns_to_display:
            cell_value = row[ord(col) - ord('A')]
            # Check if the column is the photo column
            if col == photo_column:
                file_id = get_file_id_from_url(cell_value)
                if file_id:
                    # Link to download the image via Flask route
                    cell_value = f'/get_image/{file_id}'
            row_data.append(cell_value)
        data.append(row_data)

    if display_type == 'last 5 row':
        data = data[-5:]
    
    return headers, data

# Route to download and serve the image from Google Drive
@app.route('/get_image/<file_id>')
def get_image(file_id):
    try:
        # Use the Google Drive API to download the image
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        return send_file(fh, mimetype='image/jpeg', as_attachment=False)
    except Exception as e:
        app.logger.error(f"Error fetching image: {str(e)}")
        return redirect('/static/placeholder.png')

@app.route('/')
def display_sheets():
    try:
        settings = get_settings()
        sheets_data = []
        
        for setting in settings:
            headers, data = get_sheet_data(
                setting['sheet_name'],
                setting['columns_to_display'],
                setting['photo_column'],  # Pass photo column
                setting['display']
            )
            sheets_data.append({
                'title': setting['title'],
                'headers': headers,
                'data': data,
                'time_of_display': setting['time_of_display']
            })
        
        return render_template('sheet.html', sheets_data=sheets_data)
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"

@app.route('/update_data')
def update_data():
    try:
        settings = get_settings()
        sheets_data = []
        
        for setting in settings:
            headers, data = get_sheet_data(
                setting['sheet_name'],
                setting['columns_to_display'],
                setting['photo_column'],  # Pass photo column
                setting['display']
            )
            sheets_data.append({
                'title': setting['title'],
                'headers': headers,
                'data': data,
                'time_of_display': setting['time_of_display']
            })
        
        return jsonify(sheets_data)
    except Exception as e:
        app.logger.error(f"An error occurred in update_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)