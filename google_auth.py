import os
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


def get_credentials(credentials_file, token_file, interactive=False):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise RuntimeError(
                "Google rejected the saved refresh token (it was revoked or expired). "
                "If the OAuth consent screen is still in 'Testing' status, tokens expire "
                "after 7 days — publish it to 'In production'. Then delete auth/token.json, "
                "re-run 'python3 setup_auth.py', and update the GOOGLE_TOKEN_JSON_B64 secret."
            ) from e
        _save_token(creds, token_file)
        return creds

    if not interactive:
        raise RuntimeError(
            f"No valid token at {token_file}. Run 'python3 setup_auth.py' once "
            "to authorize this app before scheduling it."
        )

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=8080)
    _save_token(creds, token_file)
    return creds


def _save_token(creds, token_file):
    os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
    with open(token_file, "w") as f:
        f.write(creds.to_json())
