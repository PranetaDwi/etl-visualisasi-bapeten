from google_services_own_account import connect_google
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

drive, sheets = connect_google()

user = drive.about().get(
    fields="user(displayName,emailAddress)"
).execute()

print("Akun Google aktif:")
print(user["user"]["emailAddress"])