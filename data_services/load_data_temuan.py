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

    df["Tgl Batas Tindak Lanjut"] = pd.to_datetime(
        df["Tgl Batas Tindak Lanjut"],
        errors="coerce"
    ).dt.date

    df["Provinsi"] = df["Lokasi Pemanfaatan"].apply(cari_provinsi)

    df = df.dropna(subset=["Provinsi"]).reset_index(drop=True)

    return df

def load_data_temuan_terbuka_tertutup_function():
    df = load_data_temuan_function()

    df_status = (
        df.groupby(
            [
                "Kelompok Kegiatan",
                "Kode Temuan",
                "Status Bundling/ Temuan",
            ],
            sort=False,
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .rename(
            columns={
                "Kelompok Kegiatan": "Jenis Kegiatan",
                "Kode Temuan": "Kode",
                "Terbuka": "terbuka",
                "Tertutup": "tertutup",
            }
        )
    )

    for col in ["terbuka", "tertutup"]:
        if col not in df_status.columns:
            df_status[col] = 0

    df_status["Total Temuan"] = (
        df_status["terbuka"] + df_status["tertutup"]
    )

    return df_status


def load_data_temuan_per_ikk_function():
    df = load_data_temuan_function()

    mapping_ikk = {
        "01": "01 - Kode Perizinan",
        "02": "02 - Ketersediaan SDM",
        "03": "03 - Pemantauan Dosis Radiasi",
        "04": "04 - Pemantauan Kesehatan Pekerja Radiasi",
        "05": "05 - Ketersediaan Peralatan Keselamatan dan Keamanan SRP",
        "06": "06 - Pemantauan Paparan Radiasi Daerah Kerja",
        "07": "07 - Ketersediaan dan Kesesuaian Dokumen dan Rekaman Keselamatan dan Keamanan SRP",
    }

    df["kode"] = df["Kode Temuan"].astype("string").str[2:4]
    df["Kode IKK"] = df["kode"].map(mapping_ikk).fillna(df["kode"])

    return df
