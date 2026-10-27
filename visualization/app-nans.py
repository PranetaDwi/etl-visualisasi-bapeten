
import base64
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# 1. KONFIGURASI HALAMAN DAN PATH
# =========================================================

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOGO = APP_DIR / "assets" / "logo_bapeten.png"
CSS_FILE = APP_DIR / "assets" / "style.css"

st.set_page_config(
    page_title="Dashboard Persebaran SRP",
    page_icon=str(LOGO) if LOGO.exists() else None,
    layout="wide",
)

if CSS_FILE.exists():
    st.markdown(
        f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

from services.google_services_own_account import (
    connect_google,
    read_parquet_drive,
    read_sheet,
    read_excel,
)

from etl.update_data_srp import refresh_data_srp


# =========================================================
# 2. KONSTANTA
# =========================================================

FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"
ID_FILE_EXCEL = "1jZt22z352D151rMTqZITiPbenX45VIC7iTWe79VyjsA"
ID_FILE_TEMUAN = "1vqxcE_9L_T4VZ3z7g-BC8fp7StIMVSX_"

TAHUN_DEFAULT = 2026
TAHUN_COLUMN_NAMES = ("tahun", "year", "thn", "tahun_inspeksi")

HARI = [
    "Senin", "Selasa", "Rabu", "Kamis",
    "Jumat", "Sabtu", "Minggu",
]

BULAN = [
    "Januari", "Februari", "Maret", "April",
    "Mei", "Juni", "Juli", "Agustus",
    "September", "Oktober", "November", "Desember",
]

WIB = timezone(timedelta(hours=7))


# =========================================================
# 3. LOAD DATA DENGAN CACHE
# =========================================================

@st.cache_data(ttl=3600, show_spinner="Memuat data SRP...")
def load_data_srp():
    drive, _ = connect_google()
    return read_parquet_drive(FILE_PARQUET_ID, drive)


@st.cache_data(ttl=3600, show_spinner="Memuat rekapitulasi...")
def load_data_rekapitulasi():
    drive, _ = connect_google()
    return read_sheet(
        ID_FILE_EXCEL,
        drive,
        sheet_name="Sheet1",
    )


@st.cache_data(ttl=3600, show_spinner="Memuat data temuan...")
def load_data_temuan():
    drive, _ = connect_google()
    excel_data = read_excel(ID_FILE_TEMUAN, drive)

    return pd.read_excel(
        excel_data,
        sheet_name="clean_data",
        engine="openpyxl",
    )


# =========================================================
# 4. PENGOLAHAN DATA TEMUAN DENGAN CACHE
# =========================================================

@st.cache_data(ttl=3600)
def load_data_temuan_terbuka_tertutup():
    df = load_data_temuan()

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


@st.cache_data(ttl=3600)
def load_data_temuan_per_ikk():
    df = load_data_temuan().copy()

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


# =========================================================
# 5. FUNGSI BANTU HTMLq

def html(text: str):
    st.markdown(
        "".join(line.strip() for line in text.splitlines()),
        unsafe_allow_html=True,
    )


ICONS = {
    "pin": (
        '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/>'
    ),
    "sliders": (
        '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3'
        'M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>'
    ),
    "file": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16'
        'a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/>'
    ),
    "calendar": (
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<path d="M16 2v4M8 2v4M3 10h18"/>'
    ),
}


def icon(name, size=16, stroke=1.7):
    return (
        f'<svg class="ico" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS[name]}</svg>'
    )


def sidebar_label(icon_name, text):
    html(
        f'<div class="side-label">'
        f'{icon(icon_name, 14)}<span>{text}</span></div>'
    )


def card_title(title):
    html(
        f'<div class="ctitle"><span>{escape(title)}</span></div>'
    )


def kpi_card(index, label, value):
    if value is None:
        text_value, value_class = "–", "na"
    elif isinstance(value, str):
        text_value, value_class = value, "txt"
    else:
        text_value = f"{int(value):,}"
        value_class = ""

    pin = (
        f'<span class="kic">{icon("pin")}</span>'
        if index == 0 else ""
    )

    return (
        f'<div class="kpi{" first" if index == 0 else ""}">'
        f'<div class="kh"><span class="kl">{escape(label)}</span>'
        f'{pin}</div>'
        f'<div class="kmid"><div class="kv {value_class}" '
        f'title="{escape(text_value)}">'
        f'{escape(text_value)}</div></div></div>'
    )


# =========================================================
# 6. MUAT DATA
# =========================================================

df = load_data_srp()
df_sheet = load_data_rekapitulasi()
df_temuan = load_data_temuan_terbuka_tertutup()
df_temuan_ikk = load_data_temuan_per_ikk()


# =========================================================
# 7. PERSIAPAN KOLOM FILTER
# =========================================================

# Salinan agar perubahan kolom lokal tidak mengubah data cache.
df = df.copy()

tahun_column = next(
    (
        col for col in df.columns
        if str(col).strip().lower() in TAHUN_COLUMN_NAMES
    ),
    None,
)

if tahun_column is not None:
    df["_tahun"] = pd.to_numeric(
        df[tahun_column],
        errors="coerce",
    )

    year_options = sorted(
        df["_tahun"].dropna().astype(int).unique().tolist(),
        reverse=True,
    )

    if not year_options:
        year_options = [TAHUN_DEFAULT]
else:
    year_options = [TAHUN_DEFAULT]

year_index = (
    year_options.index(TAHUN_DEFAULT)
    if TAHUN_DEFAULT in year_options
    else 0
)

province_options = sorted(
    df["propinsi"].dropna().unique().tolist()
)

status_options = sorted(
    df["status_sumber"].dropna().unique().tolist()
)


# =========================================================
# 8. SIDEBAR DAN FILTER
# =========================================================

with st.sidebar:
    if LOGO.exists():
        logo_base64 = base64.b64encode(
            LOGO.read_bytes()
        ).decode()

        logo_html = (
            '<img class="brand-logo" '
            f'src="data:image/png;base64,{logo_base64}" '
            'alt="BAPETEN">'
        )
    else:
        logo_html = '<div class="logo-fb">B</div>'

    html(
        f'<div class="brandbox">{logo_html}'
        '<div class="brand">BAPETEN</div></div>'
    )

    sidebar_label("sliders", "Filter")

    with st.container(border=True, key="card_filter"):
        selected_province = st.selectbox(
            "Provinsi",
            ["Semua"] + province_options,
            key="filter_provinsi",
        )

        selected_year = st.selectbox(
            "Tahun",
            year_options,
            index=year_index,
            key="filter_tahun",
        )

        selected_status = st.multiselect(
            "Status sumber",
            status_options,
            key="filter_status",
        )

    sidebar_label("file", "Data")

    html(
        '<div class="srccard"><div class="av">XLS</div>'
        '<div class="si"><div class="sn">Data SRP</div>'
        f'<div class="sm">{len(df):,} baris data</div>'
        '</div></div>'
    )


# =========================================================
# 9. FILTER DATA
# =========================================================

# Mask tunggal menghindari rangkaian salinan DataFrame.
mask = pd.Series(True, index=df.index)

if tahun_column is not None:
    mask &= df["_tahun"].eq(selected_year)

if selected_status:
    mask &= df["status_sumber"].isin(selected_status)

if selected_province != "Semua":
    mask &= df["propinsi"].eq(selected_province)

filtered = df.loc[mask]


# =========================================================
# 10. HEADER DAN JAM
# =========================================================

@st.fragment(run_every="1s")
def clock():
    now = datetime.now(WIB)

    html(
        f'<div class="clock-pill">{icon("calendar", 15, 1.8)}'
        f'<span>{HARI[now.weekday()]}, {now.day} '
        f'{BULAN[now.month - 1]} {now.year}</span>'
        '<span class="sep"></span>'
        f'<span class="time">{now:%H:%M:%S}</span>'
        '<small>WIB</small></div>'
    )


with st.container(
    horizontal=True,
    vertical_alignment="center",
    gap="small",
    key="hdr",
):
    html(
        '<div class="page-head"><div class="page-title">'
        'Persebaran Sumber Radiasi Pengion (SRP)'
        '</div></div>'
    )

    if st.button(
        "Perbarui data",
        icon=":material/refresh:",
        key="btn_refresh",
    ):
        st.cache_data.clear()
        refresh_data_srp()
        st.rerun()

    with st.container(key="clock"):
        clock()


# =========================================================
# 11. CEK HASIL FILTER
# =========================================================

if filtered.empty:
    st.info("Tidak ada data yang cocok dengan filter.")
    st.stop()


# =========================================================
# 12. FUNGSI KPI
# =========================================================

def load_data_rekapitulasi_kategori(
    provinsi,
    data_olah,
    nama_column,
    parameter,
):
    if provinsi == "Semua":
        return data_olah[parameter].sum()

    hasil = data_olah.loc[
        data_olah[nama_column].eq(provinsi),
        parameter,
    ]

    return hasil.iloc[0] if not hasil.empty else 0


def srp_zra_prp(file_olah, tipe):
    return int(
        file_olah["jenis_sumber"].eq(tipe).sum()
    )


# =========================================================
# 13. KARTU KPI
# =========================================================

kpi_items = [
    ("Provinsi", selected_province),

    (
        "Jumlah Inspeksi per 4 Tahun",
        load_data_rekapitulasi_kategori(
            selected_province,
            df_sheet,
            "Provinsi",
            "Jumlah Inspeksi per 4 tahun",
        ),
    ),

    ("Jumlah PRP", srp_zra_prp(filtered, "PRP")),
    ("Jumlah ZRA", srp_zra_prp(filtered, "ZRA")),

    (
        "Jumlah Temuan Kategori I",
        load_data_rekapitulasi_kategori(
            selected_province,
            df_sheet,
            "Provinsi",
            "Jumlah Temuan Kategori I",
        ),
    ),

    (
        "Jumlah Temuan Kategori II",
        load_data_rekapitulasi_kategori(
            selected_province,
            df_sheet,
            "Provinsi",
            "Jumlah Temuan Kategori II",
        ),
    ),

    (
        "Jumlah Temuan Kategori III",
        load_data_rekapitulasi_kategori(
            selected_province,
            df_sheet,
            "Provinsi",
            "Jumlah Temuan Kategori III",
        ),
    ),
]

kpi_html = "".join(
    kpi_card(i, label, value)
    for i, (label, value) in enumerate(kpi_items)
)

html(f'<div class="kpi-row">{kpi_html}</div>')


# =========================================================
# 14. KARTU GRAFIK DAN TABEL
# =========================================================

CARD_HEIGHT = 520

map_column, ikk_column = st.columns(2)

with map_column:
    with st.container(
        border=True,
        height=CARD_HEIGHT,
        key="card_map",
    ):
        card_title("Persebaran Provinsi berdasarkan Total SRP")

        
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
        )


with ikk_column:
    with st.container(
        border=True,
        height=CARD_HEIGHT,
        key="card_kab",
    ):
        card_title("Persentase per IKK")

        st.dataframe(
            df_temuan_ikk,
            hide_index=True,
            use_container_width=True,
        )


with st.container(
    border=True,
    height=320,
    key="card_tbl",
):
    card_title("Kegiatan dan Jumlah Temuan")

    st.dataframe(
        df_temuan,
        hide_index=True,
        use_container_width=True,
    )
