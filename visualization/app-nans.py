import base64
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import sys

# 1. konfigurasi
# 1. Konfigurasi Path & Service
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent  # root repo, tempat folder services berada

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.google_services_own_account import (
    connect_google,
    read_parquet_drive,
    read_sheet
)

FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"

st.set_page_config(
    page_title="Data SRP",
    layout="wide"
)

def load_data_srp():
    drive, sheets = connect_google()
    return read_parquet_drive(FILE_PARQUET_ID, drive)

ID_FILE_EXCEL = "1jZt22z352D151rMTqZITiPbenX45VIC7iTWe79VyjsA"

def load_data_rekapitulasi():
    drive, sheets = connect_google()
    return read_sheet(ID_FILE_EXCEL, drive, sheet_name="Sheet1")

#NYAMBUNG DATA ------------------------------
df = load_data_srp()
df_sheet = load_data_rekapitulasi()
# -------------------------------------------


LOGO = APP_DIR / "assets" / "logo_bapeten.png"
CSS_FILE = APP_DIR / "assets" / "style.css"

UNKNOWN = "Tidak diketahui"  # pengganti nilai kosong

# Kolom teks yang wajib ada di data
TEXT_COLUMNS = [
    "propinsi", "kab_kota", "instansi", "Kegiatan", "SubLingkup",
    "jenis_sumber", "status_sumber", "status_ktun", "sumber_radiasi_pengion",
]

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


# 2. data
# Baca file Excel (hasilnya di-cache supaya tidak dibaca ulang tiap interaksi)
@st.cache_data(show_spinner=False)
def read_excel(source) -> pd.DataFrame:
    return pd.read_excel(source)


# Cari file Excel bawaan. Utamakan PREFERRED_FILE, kalau tidak ada pakai .xlsx pertama
# def find_default_file():
#     folders = [folder for folder in DATA_DIRS if folder.exists()]
#     preferred = [folder / PREFERRED_FILE for folder in folders if (folder / PREFERRED_FILE).exists()]
#     others = [f for folder in folders for f in sorted(folder.glob("*.xlsx")) if not f.name.startswith("~$")]
#     return next(iter(preferred + others), None)


# Rapikan nama kolom dan isi data supaya konsisten
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Samakan huruf besar/kecil nama kolom dengan TEXT_COLUMNS
    lower_names = {c.lower(): c for c in df.columns}
    df = df.rename(columns={lower_names[c.lower()]: c for c in TEXT_COLUMNS if c.lower() in lower_names})

    # Pastikan semua kolom ada, hapus spasi, dan isi nilai kosong dengan UNKNOWN
    for column in TEXT_COLUMNS:
        if column not in df.columns:
            df[column] = UNKNOWN
        text = df[column].astype("string").str.strip().fillna(UNKNOWN)
        df[column] = text.replace({"": UNKNOWN, "nan": UNKNOWN, "NaN": UNKNOWN}).astype(str)

    df["jenis_sumber"] = df["jenis_sumber"].str.upper()
    df["status_sumber"] = df["status_sumber"].str.title()
    df["propinsi"] = df["propinsi"].str.title().replace(
        {"Dki Jakarta": "DKI Jakarta", "Di Yogyakarta": "DI Yogyakarta"}
    )
    return df


# 3. fungsi bantu tampilan
# Tampilkan HTML. Indentasi dihapus agar markdown tidak menganggapnya code block
def html(text: str):
    st.markdown("".join(line.strip() for line in text.splitlines()), unsafe_allow_html=True)


# Bentuk ikon (isi SVG) yang dipakai di halaman
ICONS = {
    "pin": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}


# Bangun tag <svg> untuk ikon `name`
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


# Bangun HTML satu kartu KPI. value=None berarti datanya belum tersedia (tampil '–')
def kpi_card(index, label, value) -> str:
    if value is None:
        text, value_class = "–", "na"
    elif isinstance(value, str):
        text, value_class = value, "txt"
    else:
        text, value_class = f"{int(value):,}", ""

    is_first = index == 0  # kartu pertama (Provinsi) tampil sebagai blok coral
    pin = f'<span class="kic">{icon("pin")}</span>' if is_first else ""
    return (
        f'<div class="kpi{" first" if is_first else ""}">'
        f'<div class="kh"><span class="kl">{escape(label)}</span>{pin}</div>'
        f'<div class="kmid"><div class="kv {value_class}" title="{escape(text)}">{escape(text)}</div></div>'
        f'</div>'
    )


# 4. sidebar (logo, filter, upload data)
with st.sidebar:
    if LOGO.exists():
        logo_base64 = base64.b64encode(LOGO.read_bytes()).decode()
        logo_html = f'<img class="brand-logo" src="data:image/png;base64,{logo_base64}" alt="BAPETEN">'
    else:
        logo_html = '<div class="logo-fb">B</div>'  # cadangan kalau file logo tidak ada

    html(f'<div class="brandbox">{logo_html}<div class="brand">BAPETEN</div></div>')
    sidebar_label("sliders", "Filter")
    filter_box = st.container(border=True, key="card_filter")
    sidebar_label("file", "Data")
    uploaded_file = st.file_uploader("Upload file Excel (opsional)", type=["xlsx"])

# Pilih sumber data: file upload dulu, kalau tidak ada pakai file bawaan
# default_file = find_default_file()
# source = uploaded_file or default_file
# if source is None:
#     st.warning("Belum ada data. Taruh file .xlsx di `eksplorasi/hasil_olah/` atau upload lewat sidebar.")
#     st.stop()

# source_name = source.name

with st.sidebar:
    html(
        f'<div class="srccard"><div class="av">XLS</div><div class="si">'
        f'<div class="sn" </div>'
        f'<div class="sm">{len(df):,} baris data</div></div></div>'
    )

# Isi kotak filter (dibuat setelah data dibaca karena pilihannya diambil dari data)
with filter_box:
    selected_province = st.selectbox("Provinsi", ["Semua"] + sorted(df["propinsi"].unique()))
    selected_types = st.multiselect("Jenis sumber", sorted(df["jenis_sumber"].unique()))
    selected_status = st.multiselect("Status sumber", sorted(df["status_sumber"].unique()))

# Terapkan filter; filter yang tidak dipilih dilewati
filtered = df
for column, picked in {"jenis_sumber": selected_types, "status_sumber": selected_status}.items():
    if picked:
        filtered = filtered[filtered[column].isin(picked)]
if selected_province != "Semua":
    filtered = filtered[filtered["propinsi"] == selected_province]


# 5. header (judul, tombol perbarui, jam)
# Jam WIB yang berdetak tiap 1 detik (hanya bagian ini yang dimuat ulang)
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
    if st.button("Perbarui data", icon=":material/refresh:", key="btn_refresh",
                 help=f"Muat ulang data dari"):
        st.cache_data.clear()
        st.rerun()
    with st.container(key="clock"):
        clock()

if filtered.empty:
    st.info("Tidak ada data yang cocok dengan filter.")
    st.stop()


def load_data_rekapitulasi_kategori(provinsi, data_olah, nama_column, parameter):
    if provinsi=="Semua":
        return sum(data_olah[parameter])

    else:
        jumlah = data_olah.loc[
            data_olah[nama_column] == provinsi,
            parameter
        ].iloc[0].item()

    return jumlah

# 6. kartu KPI (value=None -> kolom sumber datanya belum ada di Excel, jadi tampil "–")
counts = filtered["jenis_sumber"].value_counts()
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


# 7. kartu grafik (isi menyusul) oke ya
CARD_HEIGHT = 520
map_column, ikk_column = st.columns(2)

with map_column:
    with st.container(border=True, height=CARD_HEIGHT, key="card_map"):
        card_title("Persebaran Provinsi berdasarkan Total SRP")

with ikk_column:
    with st.container(border=True, height=CARD_HEIGHT, key="card_kab"):
        card_title("Persentase per IKK")

with st.container(border=True, height=320, key="card_tbl"):
    card_title("Kegiatan dan Jumlah Temuan")