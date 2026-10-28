import sys
from pathlib import Path
import pandas as pd

import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from functions.convert_province import cari_provinsi

from services.google_services_own_account import (
    connect_google,
    read_excel,
)
ID_FILE_TEMUAN = "1vqxcE_9L_T4VZ3z7g-BC8fp7StIMVSX_"

def load_data_temuan_function():
    drive, _ = connect_google()

    excel_data = read_excel(ID_FILE_TEMUAN, drive)

    df = pd.read_excel(
        excel_data,
        sheet_name="clean_data",
        engine="openpyxl",
    )

    df["Provinsi"] = df["Lokasi Pemanfaatan"].apply(cari_provinsi)

    df = df.dropna(subset=["Provinsi"]).reset_index(drop=True)

    return df


