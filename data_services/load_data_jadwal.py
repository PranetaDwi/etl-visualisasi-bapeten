
import pandas as pd
import streamlit as st

from services.google_services_own_account import (
    connect_google,
    read_excel,
)

FILE_ID_EXCEL = "1w5oauNrRO1WA9-t7nUWs6lHNLmbaaTUc"


@st.cache_data(ttl=3600, show_spinner="Memuat data jadwal...")
def load_data_jadwal_function():
    drive, _ = connect_google()

    excel_data = read_excel(FILE_ID_EXCEL, drive)

    df = pd.read_excel(
        excel_data,
        sheet_name="Sheet1",
        engine="openpyxl",
    )

    df = df.loc[
        df["Sifat"].ne("Verifikasi Perizinan")
    ].copy()

    df["Tahun"] = (
        df["Tanggal Pelaksanaan"]
        .astype(str)
        .str[:4]
    )

    return df


def load_data_jadwal_with_filter(filter_provinsi, filter_tahun):
    df = load_data_jadwal_function()

    mask = pd.Series(True, index=df.index)

    if filter_provinsi != "Semua":
        mask &= df["Propinsi"].eq(filter_provinsi)

    if filter_tahun != "Semua":
        mask &= df["Tahun"].eq(str(filter_tahun))

    return int(mask.sum())
