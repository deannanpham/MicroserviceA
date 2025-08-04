from flask import Flask, request, redirect, session, jsonify, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io, os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change_me')

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CLIENT_SECRETS_FILE = 'client_secret_web.json'

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    return jsonify({"message": "Login successful!"})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    creds = Credentials(**session['credentials'])
    file_id = request.json.get('fileId')
    if not file_id:
        return jsonify({'error': 'fileId is required'}), 400

    try:
        drive = build('drive', 'v3', credentials=creds)
        meta = drive.files().get(fileId=file_id, fields='name').execute()
        name = meta['name']
        req = drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        transcript = f"Dummy transcript for {name}"
        return jsonify({
            'transcriptFileName': name.rsplit('.', 1)[0] + '.txt',
            'transcriptText': transcript
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)