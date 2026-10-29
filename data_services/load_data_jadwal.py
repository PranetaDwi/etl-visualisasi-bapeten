import sys
from pathlib import Path
import pandas as pd

import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from services.google_services_own_account import (
    connect_google,
    read_excel,
)

FILE_ID_EXCEL = "1w5oauNrRO1WA9-t7nUWs6lHNLmbaaTUc"


def load_data_jadwal_function():
    drive, _ = connect_google()

    excel_data = read_excel(FILE_ID_EXCEL, drive)

    df = pd.read_excel(
        excel_data,
        sheet_name="Sheet1",
        engine="openpyxl",
    )

    df["Tahun"] = df["Tanggal Pelaksanaan"].astype(str).str[:4]

    return df


def load_data_jadwal_with_filter(filter_provinsi, filter_tahun):
    df = load_data_jadwal_function()

    mask = pd.Series(True, index=df.index)

    if filter_provinsi != "Semua":
        mask &= df["Propinsi"].eq(filter_provinsi)

    if filter_tahun != "Semua":
        mask &= df["Tahun"].astype(str).eq(str(filter_tahun))

    return int(mask.sum())

