
from io import BytesIO
from pathlib import Path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = BASE_DIR / "client-secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]



def connect_google():
    credentials = None

    # Gunakan token login yang sudah tersimpan
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # Login ulang atau perbarui token jika diperlukan
    if not credentials or not credentials.valid:
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )

            credentials = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    drive = build("drive", "v3", credentials=credentials)
    sheets = build("sheets", "v4", credentials=credentials)

    return drive, sheets



def read_excel(file_id, drive):
    request = drive.files().get_media(fileId=file_id)

    buffer = BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    print("Berhasil")

    return buffer


def read_sheet(spreadsheet_id, drive, sheet_name=0):
    request = drive.files().export_media(
        fileId=spreadsheet_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    file_buffer = BytesIO()

    downloader = MediaIoBaseDownload(
        file_buffer,
        request
    )

    done = False

    while not done:
        status, done = downloader.next_chunk()

    file_buffer.seek(0)

    df = pd.read_excel(
        file_buffer,
        sheet_name=sheet_name
    )

    return df


def write_sheet(df, spreadsheet_id, range_name, sheets):
    values = [
        df.columns.tolist()
    ] + df.fillna("").astype(str).values.tolist()

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def upload_parquet(
    df,
    drive,
    filename="data_srp_clean.parquet",
    folder_id=None,
):
    buffer = BytesIO()

    df.to_parquet(
        buffer,
        index=False,
        engine="pyarrow",
    )

    buffer.seek(0)

    media = MediaIoBaseUpload(
        buffer,
        mimetype="application/octet-stream",
        resumable=True,
    )

    # Cari file dengan nama yang sama dalam folder tujuan
    escaped_name = filename.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"name = '{escaped_name}' "
        "and mimeType = 'application/octet-stream' "
        "and trashed = false"
    )

    if folder_id:
        query += f" and '{folder_id}' in parents"

    result = drive.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    existing_files = result.get("files", [])

    if existing_files:
        file_id = existing_files[0]["id"]

        drive.files().update(
            fileId=file_id,
            media_body=media,
            supportsAllDrives=True,
        ).execute()

        print(f"Parquet berhasil diperbarui: {filename}")
        return file_id

    metadata = {
        "name": filename,
        "mimeType": "application/octet-stream",
    }

    if folder_id:
        metadata["parents"] = [folder_id]

    uploaded = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()

    print(f"Parquet berhasil diunggah: {filename}")
    return uploaded["id"]


# DOWNLOAD PARQUET FROM GOOGLE DRIVE
def read_parquet_drive(file_id, drive):
    request = drive.files().get_media(fileId=file_id)

    buffer = BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)

    return pd.read_parquet(
        buffer,
        engine="pyarrow",
    )