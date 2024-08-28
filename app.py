from flask import Flask, render_template, request, jsonify, redirect, send_file
from datetime import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import io
import requests
from googleapiclient.http import MediaIoBaseDownload
import logging

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
drive_service = build('drive', 'v3', credentials=creds)

app = Flask(__name__)
last_fetch_time = None

def get_file_id_from_url(url):
    file_id = None
    if 'drive.google.com' in url:
        if '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in url:
            file_id = url.split('id=')[1].split('&')[0]
    return file_id

def get_sheet_data(selected_date):
    sheet = client.open_by_key('1JfJLJv56Q-XTGzONMqS7sF5hfAhK2fgZX36W3bHvz4w').worksheet('Sheet1')
    rows = sheet.get_all_values()
    headers = ['क्रमांक'] + rows[0][1:5] + ['फोटो']
    
    selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
    
    filtered_data = []
    for row in rows[1:]:
        try:
            row_date = datetime.strptime(row[-2], "%m/%d/%Y")
            if row_date.date() == selected_date_obj.date():
                photo_url = row[-1]
                file_id = get_file_id_from_url(photo_url)
                if file_id:
                    photo_url = f'/get_image/{file_id}'
                filtered_data.append(row[1:5] + [photo_url])
        except ValueError:
            app.logger.warning(f"Invalid date format in row: {row}")
            continue
    
    filtered_data = [[i+1] + row for i, row in enumerate(filtered_data)]
    
    return headers, filtered_data

@app.route('/', methods=['GET', 'POST'])
def display_sheet():
    global last_fetch_time
    try:
        last_fetch_time = datetime.now()
        selected_date = request.form.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
        headers, filtered_data = get_sheet_data(selected_date)
        fetch_time = last_fetch_time.strftime("%H:%M:%S")
        
        if not filtered_data:
            error_message = f"Data not found for {datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d/%m/%Y')}"
            return render_template('sheet.html', headers=headers, data=[], fetch_time=fetch_time,
                                   error_message=error_message, selected_date=selected_date)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template('sheet_content.html', headers=headers, data=filtered_data,
                                   fetch_time=fetch_time, selected_date=selected_date)
        
        return render_template('sheet.html', headers=headers, data=filtered_data,
                               fetch_time=fetch_time, selected_date=selected_date)
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"

# Fetch and serve the image file using the Google Drive API
@app.route('/get_image/<file_id>')
def get_image(file_id):
    try:
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

@app.route('/check_changes', methods=['POST'])
def check_changes():
    global last_fetch_time
    try:
        selected_date = request.json.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
        sheet = client.open_by_key('1PUDas9d9cbRW-rxZTaaTPj_je_A_ELo8-dqTMjz8qMY').worksheet('Sheet1')
        current_modified_time = sheet.updated
        
        if current_modified_time != last_fetch_time:
            last_fetch_time = current_modified_time
            headers, filtered_data = get_sheet_data(selected_date)
            fetch_time = datetime.now().strftime("%H:%M:%S")
            
            return jsonify({
                "hasChanges": True,
                "html": render_template('sheet_content.html', headers=headers, data=filtered_data),
                "fetch_time": fetch_time
            })
        
        return jsonify({"hasChanges": False})
    except Exception as e:
        app.logger.error(f"An error occurred in check_changes: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
