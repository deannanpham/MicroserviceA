import os
import io
import tempfile
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import speech_recognition as sr
from pydub.utils import which
from pydub import AudioSegment

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")

scope = ['https://www.googleapis.com/auth/drive']
input_id = '1A1FBA_2GNzbRKX0mkGPHmyDGiKsXrBqh'
output_id = '1EZtGucwrRtTEnUt9tMByD7nAQ7wTSYfq'

#get credentials from OAuth drive credentials
def drive_authenticate():
    o_auth_flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scope)
    creds = o_auth_flow.run_local_server(port=0)
    return build('drive', 'v3', credentials=creds)

#get audio files by querying drive folder to search for audio type files
def get_audio(auth, folder):
    query = f"'{folder}' in parents and (mimeType contains 'audio/' or mimeType='video/mp4')"
    list_files = auth.files().list(q=query, fields="files(id, name)").execute()
    return list_files.get('files', [])

#download audio files from passed in folder and filename
def download_audio_file(auth, folder, filename):
    request = auth.files().get_media(fileId=folder)

    #open file with IO
    f = io.BytesIO()
    downloader = MediaIoBaseDownload(f, request)
    done = False

    #iterate through every audio file
    while not done:
        done = downloader.next_chunk()
    with open(filename, 'wb') as file:
        file.write(f.getvalue())

#transcribe audio using python libraries
def transcribe_audio(filename):

    #speech recognition python library
    recognizer = sr.Recognizer()

    #audio segment from pydub to get audio
    audio = AudioSegment.from_file(filename)

    #use pydub to convert to wav file to work with AudioFile  
    wav = os.path.splitext(filename)[0] + '.wav'  #
    audio.export(wav, format='wav')

    #Use AudioFile from speech recognition library to convert to text
    with sr.AudioFile(wav) as source:
        audio_sound = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_sound)
            return text
        except sr.UnknownValueError:
            return "Audio didn't work."
        except sr.RequestError as e:
            return f"[API Error: {e}]"

#upload text file back to google drive
def upload_text(auth, text, filename, folder):

    #open file to write text
    with open(filename, 'w') as f:
        f.write(text)
    file_metadata = {
        'name': os.path.basename(filename),
        'parents': [folder],
        'mimeType': 'text/plain'
    }

    #create file and upload to drive
    media = MediaFileUpload(filename, mimetype='text/plain')
    auth.files().create(body=file_metadata, media_body=media).execute()

#workflow for downloading audio, transcribing, and then re-uploading
def main():
    #get drive authentification to access drive
    auth = drive_authenticate()

    #get audio files
    audio_files = get_audio(auth, input_id)

    #iterate through all found audio files
    for file in audio_files:
        #locate directory to pass as parameter
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, file['name'])

            #download audio file to transcribe
            download_audio_file(auth, file['id'], audio_path)

            #transcribe audio file
            transcript = transcribe_audio(audio_path)
            text_filename = os.path.join(tmpdir, file['name'].rsplit('.', 1)[0] + '.txt')

            #upload transcribed text to drive
            upload_text(auth, transcript, text_filename, output_id)

if __name__ == '__main__':
    main()