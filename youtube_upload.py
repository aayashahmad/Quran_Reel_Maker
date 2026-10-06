import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
ROOT = Path(__file__).parent
TOKEN = ROOT / "token.json"
SECRET = ROOT / "client_secret.json"


def auth():
    """Run once on your own computer. Opens a browser to log in to your YouTube channel."""
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN.write_text(creds.to_json())
    print("Saved token.json  (keep it private!)")


def _creds():
    env = os.getenv("YT_TOKEN_JSON")
    if env:
        creds = Credentials.from_authorized_user_info(json.loads(env), SCOPES)
    elif TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    else:
        raise SystemExit("No YouTube login found. Run:  python main.py auth")
    if not creds.valid:
        creds.refresh(Request())
    return creds


def upload(path, title, description, tags, privacy="public", thumbnail=None):
    yt = build("youtube", "v3", credentials=_creds())
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(
                str(thumbnail), mimetype="image/jpeg")).execute()
        except HttpError as e:
            # Custom thumbnails need a phone-verified channel; the video is still uploaded.
            print(f"Thumbnail not set: {e}")
    return vid
