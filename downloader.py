import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
import cv2
import pickle
import numpy as np
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def download_file(real_file_id, creds, file_name):

    file_name = "rgbs/" + file_name.split()[2]

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        file_id = real_file_id

        # pylint: disable=maybe-no-member
        request = service.files().get_media(fileId=file_id)

        if (os.path.isfile(file_name)):
            print("already downloaded")
            return file_name

        print(file_name)
        file = open(file_name, 'wb')

        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}.")
        return file_name

    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None


def _compute_frame_average(frame: np.ndarray) -> float:
    num_pixel_values = float(frame.shape[0] * frame.shape[1] * frame.shape[2])
    avg_pixel_value = np.sum(frame[:, :, :]) / num_pixel_values
    return avg_pixel_value


def process_file(file_name):

    width = 352
    height = 288
    fps = 30

    frame_size = width * height * 3
    total_frames = int(np.fromfile(
        file_name, dtype=np.uint8).shape[0] / frame_size)

    averages = []
    with open(file_name, 'rb') as file:
        for _ in range(total_frames):
            frame_data = np.fromfile(file, dtype=np.uint8, count=frame_size)

            frame = frame_data.reshape((height, width, 3))

            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            avg = _compute_frame_average(frame)
            averages.append(avg)

    pickle_name = file_name.replace(".rgb", ".pkl")
    with open(pickle_name, 'wb') as handle:
        pickle.dump(averages, handle, protocol=pickle.HIGHEST_PROTOCOL)


def search_file():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)
        files = []
        page_token = None
        while True:
            # pylint: disable=maybe-no-member
            response = (
                service.files()
                .list(
                    q="name='576_dataset_rgb'",
                    corpora="allDrives",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                    includeItemsFromAllDrives="true",
                    supportsAllDrives="true"
                )
                .execute()
            )
            for file in response.get("files", []):
                # Process change
                print("Listing files in: ", file.get("name"))
                file_id = file.get("id")
                new_response = (
                    service.files().list(
                        q="'" + file_id + "' in parents",
                        corpora="allDrives",
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token,
                        includeItemsFromAllDrives="true",
                        supportsAllDrives="true"
                    ).execute()
                )
                for f in new_response.get("files", []):
                    print(f'Found file: {f.get("name")}, {f.get("id")}')
                    file_name = download_file(
                        f.get("id"), creds, f.get("name"))
                    process_file(file_name)

                    # deleting the file
                    os.remove(file_name)

                # only process dataset video
                break

            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break

    except HttpError as error:
        print(f"An error occurred: {error}")
        files = None

    return files


if __name__ == "__main__":
    search_file()
