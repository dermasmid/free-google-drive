import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import json
import time


data_file = "data.json"
SCOPES = ['https://www.googleapis.com/auth/drive']


creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, you have to sign in.
# to sign is download the json file from: https://developers.google.com/drive/api/v3/quickstart/python
# and select limited input device
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('drive', 'v3', credentials=creds)
service_v2 = build("drive", "v2", credentials=creds)


def upload(file_path: str):
    # Get the data from the file
    with open(file_path, "rb") as f:
        file_name = f.name
        # Get base64 bytes
        file_as_base64 = base64.b64encode(f.read())
    # Convert to a string
    file_as_string = file_as_base64.decode("ASCII")
    # Make a drive folder
    folder_id = service.files().create(body = {"name": file_name, "mimeType": "application/vnd.google-apps.folder"}).execute().get("id")

    start = 0
    end = 9980
    part_number = 0
    
    # Upload file as folder names
    print("starting upload")

    while True:
        part = file_as_string[start:end]
        if not len(part):
            # File Ended
            break
        # Add part number to name
        part = f"{part_number}|{part}"

        # Upload folder
        service.files().create(body = {"name": part, "mimeType": "application/vnd.google-apps.folder", "parents": [folder_id]}).execute()
        start = end
        end += 9980
        part_number += 1

    # Save name and folder_id for downloading
    
    data = {}
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
    data[file_name] = folder_id
    with open(data_file, "w") as f:
        json.dump(data, f)


    print("done")



def download(file_name: str):
    # Pass the file name of the file that you uploaded that you now
    # want to download

    # Get the folder id from json file
    # based on the file name passed
    with open(data_file) as f:
        data = json.load(f)
    if not file_name in data.keys():
        print("theres not data for this file name")
    folder_id = data[file_name]
    not_done = True
    next_page_token = None
    data = bytes()
    parts_done = 0
    list_of_parts = []

    # Download the file
    print("starting download")

    while not_done:
        if not next_page_token:
            files = service_v2.children().list(folderId= folder_id, maxResults= 1000).execute()
        else:
            files = service_v2.children().list(folderId= folder_id, maxResults= 1000, pageToken= next_page_token).execute()
        next_page_token = files.get("nextPageToken", None)
        parts = files["items"]
        for part in parts:
            parts_done += 1
            folder_name = service.files().get(fileId= part["id"]).execute().get("name")
            list_of_parts.append(folder_name)
            time.sleep(0.3)
        if not next_page_token:
            not_done = False


    # Sort the list and combine the file
    list_of_parts.sort(key= sort)
    for part in list_of_parts:
        bytes_without_part_number = part.split("|")[1].encode("ASCII")
        data += bytes_without_part_number
    
    # Combine all parts
    file_data = base64.b64decode(data)

    # Save to file
    with open(file_name, "wb") as f:
        f.write(file_data)

    print("done")





def sort(string):
    return int(str(string.split("|")[0]))
