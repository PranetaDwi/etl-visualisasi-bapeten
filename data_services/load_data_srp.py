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
    read_parquet_drive,
)

FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"

def load_data_srp_function():
    drive, _ = connect_google()
    return read_parquet_drive(FILE_PARQUET_ID, drive)

def load_with_filter(filter_provinsi, filter_status_sumber):

    df = load_data_srp_function()

    mask = pd.Series(True, index=df.index)

    if filter_status_sumber:
        mask &= df["status_sumber"].isin(filter_status_sumber)

    if filter_provinsi != "Semua":
        mask &= df["propinsi"].eq(filter_provinsi)

    return df.loc[mask]


def load_kpi(file_olah, tipe):
    return file_olah["jenis_sumber"].eq(tipe).sum()
