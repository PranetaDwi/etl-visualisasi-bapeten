
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent

CLIENT_SECRET_FILE = BASE_DIR / "client-secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

flow = InstalledAppFlow.from_client_secrets_file(
    str(CLIENT_SECRET_FILE),
    SCOPES,
)

credentials = flow.run_local_server(port=0)

TOKEN_FILE.write_text(
    credentials.to_json(),
    encoding="utf-8",
)

print("Token berhasil dibuat:", TOKEN_FILE)