import base64
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import sys

# 1. Konfigurasi Path & Service
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent  # root repo, tempat folder services berada

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.google_services_own_account import (
    connect_google,
    read_parquet_drive,
    read_sheet,
    read_excel
)

FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"

def load_data_srp():
    drive, _ = connect_google()
    return read_parquet_drive(FILE_PARQUET_ID, drive)

ID_FILE_EXCEL = "1jZt22z352D151rMTqZITiPbenX45VIC7iTWe79VyjsA"

def load_data_rekapitulasi():
    drive, _ = connect_google()
    return read_sheet(ID_FILE_EXCEL, drive, sheet_name="Sheet1")

ID_FILE_TEMUAN = "1vqxcE_9L_T4VZ3z7g-BC8fp7StIMVSX_"


def load_data_temuan():
    drive, _ = connect_google()
    df_excel = read_excel(ID_FILE_TEMUAN, drive)

    df = pd.read_excel(
        df_excel,
        sheet_name="clean_data",
        engine="openpyxl"
    )

    return df

def load_data_temuan_terbuka_tertutup():

    df = load_data_temuan()

    df_status = (
        df.groupby(["Kelompok Kegiatan", "Kode Temuan", "Status Bundling/ Temuan"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .rename(columns={
            "Kelompok Kegiatan": "Jenis Kegiatan",
            "Kode Temuan": "Kode",
            "Terbuka": "terbuka",
            "Tertutup": "tertutup"
        })
    )

    df_status["Total Temuan"] = df_status["terbuka"] + df_status["tertutup"]

    return df_status


def load_data_temuan_per_ikk():
    df = load_data_temuan()
    mapping_ikk = {
        "01": "01 - Kode Perizinan",
        "02": "02 - Ketersediaan SDM",
        "03": "03 - Pemantauan Dosis Radiasi",
        "04": "04 - Pemantauan Kesehatan Pekerja Radiasi",
        "05": "05 - Ketersediaan Peralatan Keselamatan dan Keamanan SRP",
        "06": "06 - Pemantauan Paparan Radiasi Daerah Kerja",
        "07": "07 - Ketersediaan dan Kesesuaian Dokumen dan Rekaman Keselamatan dan Keamanan SRP"
    }

    df["kode"] = df["Kode Temuan"].astype(str).str[2:4]
    df["Kode IKK"] = df["kode"].map(mapping_ikk).fillna(df["kode"])

    return df


# Muat Data
df = load_data_srp()
df_sheet = load_data_rekapitulasi()
df_temuan = load_data_temuan_terbuka_tertutup()
df_temuan_ikk = load_data_temuan_per_ikk()

LOGO = APP_DIR / "assets" / "logo_bapeten.png"
CSS_FILE = APP_DIR / "assets" / "style.css"

TAHUN_DEFAULT = 2026
TAHUN_COLUMN_NAMES = ("tahun", "year", "thn", "tahun_inspeksi")

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
WIB = timezone(timedelta(hours=7))

st.set_page_config(
    page_title="Dashboard Persebaran SRP",
    page_icon=str(LOGO) if LOGO.exists() else None,
    layout="wide",
)
st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# 2. Fungsi Bantu Tampilan
def html(text: str):
    st.markdown("".join(line.strip() for line in text.splitlines()), unsafe_allow_html=True)

ICONS = {
    "pin": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}

def icon(name, size=16, stroke=1.7) -> str:
    return (
        f'<svg class="ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS[name]}</svg>'
    )

def sidebar_label(icon_name, text):
    html(f'<div class="side-label">{icon(icon_name, 14)}<span>{text}</span></div>')

def card_title(title):
    html(f'<div class="ctitle"><span>{escape(title)}</span></div>')

def kpi_card(index, label, value) -> str:
    if value is None:
        text, value_class = "–", "na"
    elif isinstance(value, str):
        text, value_class = value, "txt"
    else:
        text, value_class = f"{int(value):,}", ""

    is_first = index == 0
    pin = f'<span class="kic">{icon("pin")}</span>' if is_first else ""
    return (
        f'<div class="kpi{" first" if is_first else ""}">'
        f'<div class="kh"><span class="kl">{escape(label)}</span>{pin}</div>'
        f'<div class="kmid"><div class="kv {value_class}" title="{escape(text)}">{escape(text)}</div></div>'
        f'</div>'
    )

# 3. Sidebar
with st.sidebar:
    if LOGO.exists():
        logo_base64 = base64.b64encode(LOGO.read_bytes()).decode()
        logo_html = f'<img class="brand-logo" src="data:image/png;base64,{logo_base64}" alt="BAPETEN">'
    else:
        logo_html = '<div class="logo-fb">B</div>'

    html(f'<div class="brandbox">{logo_html}<div class="brand">BAPETEN</div></div>')
    sidebar_label("sliders", "Filter")
    filter_box = st.container(border=True, key="card_filter")
    sidebar_label("file", "Data")

with st.sidebar:
    html(
        f'<div class="srccard"><div class="av">XLS</div><div class="si">'
        f'<div class="sn">Data SRP</div>'
        f'<div class="sm">{len(df):,} baris data</div></div></div>'
    )

tahun_column = next((c for c in df.columns if str(c).strip().lower() in TAHUN_COLUMN_NAMES), None)
if tahun_column is not None:
    df["_tahun"] = pd.to_numeric(df[tahun_column], errors="coerce")
    year_options = sorted(df["_tahun"].dropna().astype(int).unique(), reverse=True) or [TAHUN_DEFAULT]
else:
    year_options = [TAHUN_DEFAULT]
year_index = year_options.index(TAHUN_DEFAULT) if TAHUN_DEFAULT in year_options else 0

with filter_box:
    selected_province = st.selectbox("Provinsi", ["Semua"] + sorted(df["propinsi"].unique()))
    selected_year = st.selectbox("Tahun", year_options, index=year_index)
    selected_status = st.multiselect("Status sumber", sorted(df["status_sumber"].unique()))

filtered = df
if tahun_column is not None:
    filtered = filtered[filtered["_tahun"] == selected_year]
for column, picked in {"status_sumber": selected_status}.items():
    if picked:
        filtered = filtered[filtered[column].isin(picked)]
if selected_province != "Semua":
    filtered = filtered[filtered["propinsi"] == selected_province]

# 4. Header & Jam
@st.fragment(run_every="1s")
def clock():
    now = datetime.now(WIB)
    html(
        f'<div class="clock-pill">{icon("calendar", 15, 1.8)}'
        f'<span>{HARI[now.weekday()]}, {now.day} {BULAN[now.month - 1]} {now.year}</span>'
        f'<span class="sep"></span><span class="time">{now:%H:%M:%S}</span><small>WIB</small></div>'
    )

with st.container(horizontal=True, vertical_alignment="center", gap="small", key="hdr"):
    html('<div class="page-head"><div class="page-title">Persebaran Sumber Radiasi Pengion (SRP)</div></div>')
    if st.button("Perbarui data", icon=":material/refresh:", key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()
    with st.container(key="clock"):
        clock()

if filtered.empty:
    st.info("Tidak ada data yang cocok dengan filter.")
    st.stop()

def load_data_rekapitulasi_kategori(provinsi, data_olah, nama_column, parameter):
    if provinsi == "Semua":
        return sum(data_olah[parameter])
    else:
        return data_olah.loc[
            data_olah[nama_column] == provinsi,
            parameter
        ].iloc[0].item()

# 5. Kartu KPI
kpi_items = [
    ("Provinsi", selected_province),
    ("Jumlah Inspeksi per 4 Tahun", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah Inspeksi per 4 tahun")),
    ("Jumlah PRP", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah PRP")),
    ("Jumlah ZRA", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah ZRA")),
    ("Jumlah Temuan Kategori I", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah Temuan Kategori I")),
    ("Jumlah Temuan Kategori II", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah Temuan Kategori II")),
    ("Jumlah Temuan Kategori III", load_data_rekapitulasi_kategori(selected_province, df_sheet, "Provinsi", "Jumlah Temuan Kategori III")),
]
kpi_html = "".join(kpi_card(i, label, value) for i, (label, value) in enumerate(kpi_items))
html(f'<div class="kpi-row">{kpi_html}</div>')

# 6. Tata Letak Kartu Grafik & Tabel
CARD_HEIGHT = 520
map_column, ikk_column = st.columns(2)

with map_column:
    with st.container(border=True, height=CARD_HEIGHT, key="card_map"):
        card_title("Persebaran Provinsi berdasarkan Total SRP")

with ikk_column:
    with st.container(border=True, height=CARD_HEIGHT, key="card_kab"):
        card_title("Persentase per IKK")
        st.dataframe(
        df_temuan_ikk,
        hide_index=True
    )


with st.container(border=True, height=320, key="card_tbl"):
    card_title("Kegiatan dan Jumlah Temuan")
    st.dataframe(
        df_temuan,
        hide_index=True
    )