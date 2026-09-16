from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class YouTubeClient:
    def __init__(self, creds):
        self.service = build("youtube", "v3", credentials=creds)

    def upload_short(self, file_path, title, description, tags, category_id, privacy_status):
        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = self.service.videos().insert(
            part="snippet,status", body=body, media_body=media
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response["id"]
