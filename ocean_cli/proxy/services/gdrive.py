from __future__ import print_function
import pickle
import os.path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import logging

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/spreadsheets']


def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow\
                .from_client_secrets_file(os.getcwd()
                                          + '/credentials.json',
                                          SCOPES)
            creds = flow.run_local_server(port=8898)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # service = build('drive', 'v3', credentials=creds)
    # service = build('sheets', 'v4', credentials=creds)
    return creds


def list_files(**kwargs):
    service = build('drive', 'v3', credentials=get_credentials())
    # Call the Drive v3 API
    results = service.files().list(
        pageSize=30, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
    return items


def upload(file, mimetype='image/jpeg', file_metadata=None):
    service = build('drive', 'v3', credentials=get_credentials())

    if not file_metadata:
        file_metadata = {
            'name': file
        }

    media = MediaFileUpload(
        file,
        mimetype=mimetype,
        resumable=True
    )

    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    return file.get('id')


def authorize(emailAddress=None, fileId=None, *args, **kwargs):
    service = build('drive', 'v3', credentials=get_credentials())
    user_permission = {
        'type': 'user',
        'role': 'reader',
        'emailAddress': emailAddress
    }
    return service.permissions().create(fileId=fileId,
                                        body=user_permission,
                                        fields='id').execute()

