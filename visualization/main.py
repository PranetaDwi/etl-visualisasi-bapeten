
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import json
import re
import unicodedata
from urllib.request import urlopen
from branca.colormap import linear
from streamlit_folium import st_folium
import sys
from pathlib import Path

ROOT_DIR = Path(r"D:\BAPETEN\BAPETEN PROJEK\neta-eksplorasi")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from etl.update_data_srp import refresh_data_srp

from services.google_services_own_account import (
    connect_google,
    read_parquet_drive,
    read_sheet
)

FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"
ID_FILE_EXCEL = "1jZt22z352D151rMTqZITiPbenX45VIC7iTWe79VyjsA"

st.set_page_config(
    page_title="Data SRP",
    layout="wide"
)

def load_data_srp():
    drive, sheets = connect_google()
    return read_parquet_drive(FILE_PARQUET_ID, drive)

def load_data_rekapitulasi():
    drive, sheets = connect_google()
    return read_sheet(ID_FILE_EXCEL, drive, sheet_name="Sheet1")


st.subheader("Data SRP")

if st.button("🔄 Refresh Data", type="primary"):
    try:
        with st.spinner(
            "Mengambil, membersihkan, dan memperbarui data SRP..."
        ):
            refresh_data_srp()

            # Baca ulang Parquet setelah ETL selesai
            file_df = load_data_srp()

            df_baru = load_data_rekapitulasi()

            st.session_state["df_srp"] = df_baru
            st.session_state["file_df"] = file_df

        st.toast("Data SRP berhasil diperbarui!", icon="✅")

    except Exception as e:
        st.error(f"Gagal memperbarui data SRP: {e}")


# Baca Parquet saat halaman pertama kali dibuka
if "file_df" not in st.session_state:
    try:
        with st.spinner("Memuat data SRP..."):
            st.session_state["file_df"] = load_data_srp()

    except Exception as e:
        st.error(f"Gagal membaca data Parquet: {e}")


if "file_df" in st.session_state:
    file_df = st.session_state["file_df"]
    st.dataframe(file_df, use_container_width=True)

st.title("Persebaran Jumlah SRP per Provinsi di Indonesia")

# URL GeoJSON dari repository GitHub
URL_PROVINSI = (
    "https://raw.githubusercontent.com/"
    "Firdatulayuni/maps/main/provinsi.geojson"
)

URL_KAB_KOTA = (
    "https://raw.githubusercontent.com/"
    "Firdatulayuni/maps/main/kab_kota.geojson"
)


# Memuat GeoJSON menggunakan GeoPandas
@st.cache_data
def load_geojson(url):
    with urlopen(url, timeout=30) as response:
        data = json.load(response)

    return gpd.GeoDataFrame.from_features(
        data["features"],
        crs="EPSG:4326"
    )


# Menyamakan format nama provinsi
def normalisasi_nama(nama):
    nama = str(nama).strip().lower()

    nama = unicodedata.normalize("NFKD", nama)
    nama = "".join(
        karakter for karakter in nama
        if not unicodedata.combining(karakter)
    )

    nama = re.sub(r"[^a-z0-9]", "", nama)

    alias = {
        "daerahkhususibukotajakarta": "dkijakarta",
        "daerahkhususjakarta": "dkijakarta",
        "jakarta": "dkijakarta",
        "daerahistimewayogyakarta": "diyogyakarta",
        "diy": "diyogyakarta",
        "yogyakarta": "diyogyakarta",
    }

    return alias.get(nama, nama)


# Menyamakan format kode wilayah
def normalisasi_kode(kode):
    if pd.isna(kode):
        return ""

    return re.sub(r"\D", "", str(kode))

# Memuat data SRP
if "df_srp" not in st.session_state:
    try:
        with st.spinner("Memuat data dari Google Drive..."):
            st.session_state["df_srp"] = load_data_rekapitulasi()

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Drive: {e}")
        st.stop()

df = st.session_state["df_srp"].copy()

# Memastikan kolom yang dibutuhkan tersedia
kolom_wajib = ["Provinsi", "Total SRP"]
kolom_hilang = [
    kolom for kolom in kolom_wajib
    if kolom not in df.columns
]

if kolom_hilang:
    st.error(f"Kolom berikut tidak ditemukan: {kolom_hilang}")
    st.stop()

df["Total SRP"] = pd.to_numeric(
    df["Total SRP"], errors="coerce"
).fillna(0)

df["key_provinsi"] = df["Provinsi"].apply(normalisasi_nama)

# Memuat batas wilayah dari GitHub
try:
    with st.spinner("Memuat peta wilayah Indonesia..."):
        gdf_provinsi = load_geojson(URL_PROVINSI)
        gdf_kab_kota = load_geojson(URL_KAB_KOTA)
        gdf_kab_kota["kode_normal"] = (
            gdf_kab_kota["code"].apply(normalisasi_kode)
        )

except Exception as e:
    st.error(f"Gagal memuat GeoJSON dari GitHub: {e}")
    st.stop()

# Memeriksa kolom GeoJSON
if "name" not in gdf_provinsi.columns:
    st.error("Kolom 'name' tidak ditemukan pada GeoJSON provinsi.")
    st.stop()

if "code" not in gdf_provinsi.columns:
    st.error("Kolom 'code' tidak ditemukan pada GeoJSON provinsi.")
    st.stop()

if "code" not in gdf_kab_kota.columns:
    st.error("Kolom 'code' tidak ditemukan pada GeoJSON kabupaten/kota.")
    st.stop()

# Menggabungkan data SRP dengan geometri provinsi
gdf_provinsi["key_provinsi"] = (
    gdf_provinsi["name"].apply(normalisasi_nama)
)

df_ringkas = (
    df.groupby("key_provinsi", as_index=False)
    .agg({"Total SRP": "sum"})
)

gdf_provinsi = gdf_provinsi.merge(
    df_ringkas,
    on="key_provinsi",
    how="left"
)

gdf_provinsi["Total SRP"] = (
    gdf_provinsi["Total SRP"].fillna(0)
)

# Informasi provinsi yang belum cocok dengan data
provinsi_data = set(df["key_provinsi"].dropna())
provinsi_peta = set(gdf_provinsi["key_provinsi"].dropna())

provinsi_tidak_cocok = provinsi_data - provinsi_peta

if provinsi_tidak_cocok:
    st.warning(
        "Sebagian nama provinsi pada data belum cocok dengan peta. "
        "Periksa penamaan provinsi pada sumber data."
    )



# Menyiapkan tampilan peta
if "map_view" not in st.session_state:
    st.session_state["map_view"] = "provinsi"

if "selected_province" not in st.session_state:
    st.session_state["selected_province"] = None


# Tampilan peta provinsi
if st.session_state["map_view"] == "provinsi":

    st.subheader("Persebaran SRP per Provinsi")
    st.caption("Klik wilayah provinsi pada peta untuk melihat kabupaten/kota.")

    nilai_min = float(gdf_provinsi["Total SRP"].min())
    nilai_max = float(gdf_provinsi["Total SRP"].max())

    if nilai_min == nilai_max:
        nilai_max = nilai_min + 1

    from branca.colormap import LinearColormap

    warna = LinearColormap(
        colors=["#C5E8C0", "#FFF2A6", "#F4A582", "#D73027"],
        vmin=nilai_min,
        vmax=nilai_max
    )
    warna.caption = "Jumlah SRP per Provinsi"

    # Buat peta terlebih dahulu
    peta = folium.Map(
        location=[-2.5, 118],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True
    )

    def gaya_provinsi(feature):
        nilai = feature["properties"].get("Total SRP", 0) or 0

        return {
            "fillColor": warna(nilai),
            "color": "#FFFFFF",
            "weight": 1,
            "fillOpacity": 0.8,
        }

    folium.GeoJson(
        gdf_provinsi.__geo_interface__,
        name="Jumlah SRP per Provinsi",
        style_function=gaya_provinsi,
        highlight_function=lambda feature: {
            "color": "#7F1D1D",
            "weight": 3,
            "fillOpacity": 0.95,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "Total SRP"],
            aliases=["Provinsi:", "Jumlah SRP:"],
            localize=True
        )
    ).add_to(peta)

    warna.add_to(peta)

    # Fokuskan peta ke batas seluruh Indonesia
    minx, miny, maxx, maxy = gdf_provinsi.total_bounds
    peta.fit_bounds([[miny, minx], [maxy, maxx]])

    # Menangkap koordinat yang diklik pengguna
    hasil_peta = st_folium(
        peta,
        use_container_width=True,
        height=600,
        key="peta_provinsi",
        returned_objects=["last_clicked"]
    )

    titik_klik = hasil_peta.get("last_clicked")

    if titik_klik:
        from shapely.geometry import Point

        titik = Point(
            titik_klik["lng"],
            titik_klik["lat"]
        )

        provinsi_terpilih = gdf_provinsi[
            gdf_provinsi.geometry.intersects(titik)
        ]

        if not provinsi_terpilih.empty:
            nama_provinsi = provinsi_terpilih.iloc[0]["name"]

            st.session_state["selected_province"] = nama_provinsi
            st.session_state["map_view"] = "kab_kota"
            st.rerun()


# Tampilan kabupaten/kota pada provinsi yang dipilih
else:
    provinsi_pilihan = st.session_state["selected_province"]

    data_provinsi = gdf_provinsi[
        gdf_provinsi["name"] == provinsi_pilihan
    ]

    if data_provinsi.empty:
        st.error("Provinsi tidak ditemukan pada GeoJSON.")
        st.stop()

    kode_provinsi = normalisasi_kode(
        data_provinsi.iloc[0]["code"]
    )

    gdf_pilihan = gdf_kab_kota.loc[
        gdf_kab_kota["kode_normal"].str.startswith(
            kode_provinsi
        )
    ].copy()

    st.subheader(f"Kabupaten/Kota — {provinsi_pilihan}")

    total_srp = data_provinsi.iloc[0]["Total SRP"]

    st.metric(
        label=f"Total SRP di {provinsi_pilihan}",
        value=f"{total_srp:,.0f}"
    )

    st.caption(
        "Peta menampilkan batas administratif kabupaten/kota. "
        "Jumlah SRP yang tersedia masih pada tingkat provinsi."
    )

    if gdf_pilihan.empty:
        st.warning(
            "Batas kabupaten/kota tidak ditemukan. "
            "Periksa format kode pada kedua GeoJSON."
        )
    else:
        peta = folium.Map(
            location=[-2.5, 118],
            zoom_start=6,
            tiles="OpenStreetMap",
            control_scale=True
        )

        folium.GeoJson(
            gdf_pilihan.__geo_interface__,
            name="Batas Kabupaten/Kota",
            style_function=lambda feature: {
                "color": "#991B1B",
                "weight": 1,
                "fillOpacity": 0.35,
            },
            highlight_function=lambda feature: {
                "color": "#450A0A",
                "weight": 2,
                "fillOpacity": 0.6,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["name"],
                aliases=["Kabupaten:"]
            )
        ).add_to(peta)

        minx, miny, maxx, maxy = gdf_pilihan.total_bounds

        peta.fit_bounds([[miny, minx], [maxy, maxx]])

        st_folium(
            peta,
            use_container_width=True,
            height=600,
            key=f"peta_kab_kota_{kode_provinsi}"
        )

    if st.button("← Kembali ke Peta Indonesia"):
        st.session_state["map_view"] = "provinsi"
        st.session_state["selected_province"] = None
        st.rerun()

# Menampilkan data
with st.expander("Lihat data per provinsi"):
    st.dataframe(
        df.drop(columns=["key_provinsi"], errors="ignore"),
        use_container_width=True
    )