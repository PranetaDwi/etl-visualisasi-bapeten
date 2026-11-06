import pandas as pd
import streamlit as st
import re

from services.google_services_own_account import (
    connect_google,
    read_excel,
)

ID_FILE_TEMUAN = "1vqxcE_9L_T4VZ3z7g-BC8fp7StIMVSX_"


provinsi_indonesia = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau",
    "Kepulauan Riau", "Jambi", "Sumatera Selatan", "Kepulauan Bangka Belitung",
    "Bengkulu", "Lampung", "DKI Jakarta", "Banten", "Jawa Barat",
    "Jawa Tengah", "DI Yogyakarta", "Jawa Timur", "Bali",
    "Nusa Tenggara Barat", "Nusa Tenggara Timur", "Kalimantan Barat",
    "Kalimantan Tengah", "Kalimantan Selatan", "Kalimantan Timur",
    "Kalimantan Utara", "Sulawesi Utara", "Gorontalo",
    "Sulawesi Tengah", "Sulawesi Barat", "Sulawesi Selatan",
    "Sulawesi Tenggara", "Maluku", "Maluku Utara", "Papua",
    "Papua Barat", "Papua Selatan", "Papua Tengah",
    "Papua Pegunungan", "Papua Barat Daya"
]

# Alias untuk variasi penulisan alamat
alias_provinsi = {
    "D.I. Yogyakarta": "DI Yogyakarta",
    "Daerah Istimewa Yogyakarta": "DI Yogyakarta",
    "D.I. Yogyakarta": "DI Yogyakarta",
    "DKI Jakarta": "DKI Jakarta",
    "Daerah Khusus Jakarta": "DKI Jakarta",
}

# Cocokkan nama terpanjang terlebih dahulu
pola = re.compile(
    r"(?<!\w)(" +
    "|".join(
        re.escape(p)
        for p in sorted(
            provinsi_indonesia + list(alias_provinsi.keys()),
            key=len,
            reverse=True
        )
    ) +
    r")(?!\w)",
    flags=re.IGNORECASE
)

def cari_provinsi(alamat):
    if not isinstance(alamat, str):
        return None

    hasil = pola.search(alamat)
    if hasil is None:
        return None

    nama = hasil.group(0)

    for alias, nama_resmi in alias_provinsi.items():
        if nama.lower() == alias.lower():
            return nama_resmi

    # Samakan dengan ejaan pada daftar
    return next(
        (p for p in provinsi_indonesia if p.lower() == nama.lower()),
        None
    )


@st.cache_data(ttl=3600, show_spinner="Memuat data temuan...")
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

    # Siapkan kode IKK sekali saja
    df["kode"] = (
        df["Kode Temuan"].astype("string").str[2:4]
    )

    mapping_ikk = {
        "01": "01 - Kode Perizinan",
        "02": "02 - Ketersediaan SDM",
        "03": "03 - Pemantauan Dosis Radiasi",
        "04": "04 - Pemantauan Kesehatan Pekerja Radiasi",
        "05": "05 - Ketersediaan Peralatan Keselamatan dan Keamanan SRP",
        "06": "06 - Pemantauan Paparan Radiasi Daerah Kerja",
        "07": "07 - Ketersediaan dan Kesesuaian Dokumen dan Rekaman Keselamatan dan Keamanan SRP",
    }

    df["Kode IKK"] = df["kode"].map(mapping_ikk).fillna(df["kode"])

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
    return load_data_temuan_function()


def load_data_temuan_filter(filter_provinsi, nama_kategori):
    df = load_data_temuan_function()

    mask = df["Kategori Temuan"].astype(str).eq(str(nama_kategori))

    if filter_provinsi != "Semua":
        mask &= df["Provinsi"].eq(filter_provinsi)

    return int(mask.sum())
