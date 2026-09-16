import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class DriveClient:
    def __init__(self, creds):
        self.service = build("drive", "v3", credentials=creds)

    def list_videos(self, folder_id, extensions):
        files = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed=false"
        while True:
            resp = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, createdTime, mimeType)",
                    pageToken=page_token,
                    pageSize=1000,
                )
                .execute()
            )
            for f in resp.get("files", []):
                name = f["name"].lower()
                if any(name.endswith(ext) for ext in extensions):
                    files.append(f)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return files

    def download(self, file_id, dest_path):
        request = self.service.files().get_media(fileId=file_id)
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return dest_path

    def delete(self, file_id):
        self.service.files().delete(fileId=file_id).execute()
