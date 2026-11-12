import json
import re
import unicodedata
from urllib.request import urlopen

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from branca.colormap import linear
from shapely.geometry import Point
from streamlit_folium import st_folium
import sys
from pathlib import Path

URL_PROVINSI = "https://raw.githubusercontent.com/Firdatulayuni/maps/main/provinsi.geojson"
URL_KAB_KOTA = "https://raw.githubusercontent.com/Firdatulayuni/maps/main/kab_kota.geojson"

# LOAD DATA TEMUAN
FILE_PARQUET_ID = "1dqm3AKv8S85Eamp_59W7ooeGsXlPVFxU"
ID_FILE_EXCEL = "1jZt22z352D151rMTqZITiPbenX45VIC7iTWe79VyjsA"
ID_FILE_TEMUAN = "1vqxcE_9L_T4VZ3z7g-BC8fp7StIMVSX_"


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.google_services_own_account import (
    connect_google,
    read_parquet_drive,
    read_sheet,
    read_excel,
)

@st.cache_data(ttl=3600)
def load_data_temuan():
    drive, _ = connect_google()
    excel_data = read_excel(ID_FILE_TEMUAN, drive)

    return pd.read_excel(
        excel_data,
        sheet_name="clean_data",
        engine="openpyxl",
    )

df_temuan = load_data_temuan()
df_temuan_maps =df_temuan.copy()

st.write("### DEBUG DATA FASILITAS")
st.write("Jumlah baris:", len(df_temuan_maps))
st.write("Nama kolom:", df_temuan_maps.columns.tolist())

st.write(
    df_temuan_maps[
        [
            "Nama Instansi /Fasilitas",
            "Provinsi_Visualisasi",
            "Lokasi Pemanfaatan",
        ]
    ].head(10)
)

CSV_KOORDINAT = Path(__file__).resolve().parent.parent / "koordinat_fasilitas.csv"

df_koordinat = pd.read_csv(CSV_KOORDINAT)
st.write("### DEBUG DATA KOORDINAT")
st.write("Lokasi CSV:", str(CSV_KOORDINAT))
st.write("Jumlah baris:", len(df_koordinat))
st.write("Kolom:", df_koordinat.columns.tolist())
st.dataframe(df_koordinat.head(10))

@st.cache_data(show_spinner="Memuat batas wilayah...")
def load_geojson(url):
    with urlopen(url, timeout=60) as response:
        geojson = json.load(response)
    return gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")

# MAPS NI
def normalisasi_nama(nama):
    nama = str(nama).strip().lower()
    nama = unicodedata.normalize("NFKD", nama)
    nama = "".join(c for c in nama if not unicodedata.combining(c))
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


def normalisasi_kode(kode):
    if pd.isna(kode):
        return ""
    teks = str(kode).strip()
    if teks.endswith(".0"):
        teks = teks[:-2]
    return re.sub(r"\D", "", teks)


def _buat_peta_dasar(location=(-2.5, 118), zoom=4):
    return folium.Map(
        location=location,
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
    )


def render_srp_map(df_map, selected_province="Semua", df_all=None, df_fasilitas=None):
    st.subheader("Persebaran SRP per Provinsi")
    st.caption(
        "Pilih provinsi dari filter dashboard atau klik provinsi pada peta. "
    )

    required = ["propinsi", "jenis_sumber"]
    missing = [col for col in required if col not in df_map.columns]
    if missing:
        st.error(f"Kolom yang dibutuhkan peta tidak ditemukan: {missing}")
        return

    data_map = df_map[["propinsi", "jenis_sumber"]].copy()
    data_map = data_map.dropna(subset=["propinsi"])
    data_map["key_provinsi"] = data_map["propinsi"].apply(normalisasi_nama)

    sumber_nama = df_all if df_all is not None else df_map
    if "propinsi" in sumber_nama.columns:
        data_nama = sumber_nama[["propinsi"]].dropna().drop_duplicates().copy()
        data_nama["key_provinsi"] = data_nama["propinsi"].apply(normalisasi_nama)
    else:
        data_nama = data_map[["propinsi", "key_provinsi"]].drop_duplicates().copy()

    ringkasan = data_map.groupby("key_provinsi").size().rename("Total SRP").reset_index()

    if "map_view" not in st.session_state:
        st.session_state["map_view"] = (
            "kab_kota"
            if selected_province and normalisasi_nama(selected_province) != normalisasi_nama("Semua")
            else "provinsi"
        )
    if "selected_province" not in st.session_state:
        st.session_state["selected_province"] = None
    if "map_last_filter" not in st.session_state:
        st.session_state["map_last_filter"] = selected_province
    if "map_last_click" not in st.session_state:
        st.session_state["map_last_click"] = None

    # Sidebar berubah: fokus ke provinsi terpilih dan tampilkan batas kab/kota.
    if selected_province != st.session_state["map_last_filter"]:
        st.session_state["map_last_filter"] = selected_province
        if selected_province and normalisasi_nama(selected_province) != normalisasi_nama("Semua"):
            st.session_state["map_view"] = "kab_kota"
        else:
            st.session_state["map_view"] = "provinsi"
        st.session_state["selected_province"] = None

    try:
        gdf_provinsi = load_geojson(URL_PROVINSI).copy()
    except Exception as exc:
        st.error(f"Gagal memuat GeoJSON provinsi: {exc}")
        return

    if not {"name", "code", "geometry"}.issubset(gdf_provinsi.columns):
        st.error("GeoJSON provinsi harus memiliki kolom name, code, dan geometry.")
        return

    gdf_provinsi["key_provinsi"] = gdf_provinsi["name"].apply(normalisasi_nama)
    gdf_provinsi = gdf_provinsi.merge(ringkasan, on="key_provinsi", how="left")
    gdf_provinsi["Total SRP"] = gdf_provinsi["Total SRP"].fillna(0)

    # Tentukan provinsi yang aktif dari klik peta atau filter sidebar.
    nama_aktif = st.session_state.get("selected_province")
    if not nama_aktif and selected_province and normalisasi_nama(selected_province) != normalisasi_nama("Semua"):
        match = gdf_provinsi[gdf_provinsi["key_provinsi"] == normalisasi_nama(selected_province)]
        if not match.empty:
            nama_aktif = match.iloc[0]["name"]
            st.session_state["selected_province"] = nama_aktif

    if st.session_state["map_view"] == "provinsi":
        peta = _buat_peta_dasar()
        min_value = float(gdf_provinsi["Total SRP"].min())
        max_value = float(gdf_provinsi["Total SRP"].max())
        if min_value == max_value:
            max_value = min_value + 1
        warna = linear.Reds_09.scale(min_value, max_value)
        warna = warna.to_step(n=7)
        warna.caption = "Jumlah SRP"

        minx, miny, maxx, maxy = gdf_provinsi.total_bounds
        peta.fit_bounds([[miny, minx], [maxy, maxx]])

        def style_province(feature):
            value = feature["properties"].get("Total SRP", 0) or 0
            return {"fillColor": warna(value), "color": "#FFFFFF", "weight": 1, "fillOpacity": 0.82}

        folium.GeoJson(
            gdf_provinsi.__geo_interface__,
            name="Jumlah SRP per Provinsi",
            style_function=style_province,
            highlight_function=lambda feature: {"color": "#7F1D1D", "weight": 2.5, "fillOpacity": 0.95},
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "Total SRP"],
                aliases=["Provinsi:", "Jumlah SRP:"],
                localize=True,
            ),
        ).add_to(peta)
        warna.add_to(peta)

        hasil = st_folium(
            peta,
            use_container_width=True,
            height=560,
            key="dashboard_peta_provinsi",
            returned_objects=["last_clicked"],
        )
        titik_klik = hasil.get("last_clicked") if isinstance(hasil, dict) else None
        if titik_klik:
            click_key = (round(titik_klik.get("lat", 0), 5), round(titik_klik.get("lng", 0), 5))
            if click_key != st.session_state.get("map_last_click"):
                st.session_state["map_last_click"] = click_key
                titik = Point(titik_klik["lng"], titik_klik["lat"])
                pilihan = gdf_provinsi[gdf_provinsi.geometry.intersects(titik)]
                if not pilihan.empty:
                    nama_geojson = pilihan.iloc[0]["name"]
                    key_geojson = normalisasi_nama(nama_geojson)
                    pilihan_data = data_nama[data_nama["key_provinsi"] == key_geojson]
                    # Nama filter diambil dari data lengkap agar tetap cocok
                    # meskipun provinsi itu tidak memiliki baris pada tahun/status terpilih.
                    st.session_state["selected_province"] = nama_geojson
                    st.session_state["map_view"] = "kab_kota"
                    if not pilihan_data.empty:
                        nama_filter = pilihan_data["propinsi"].iloc[0]
                        st.session_state["provinsi_dari_peta"] = nama_filter
                        st.session_state["map_last_filter"] = nama_filter
                    st.rerun()
        return

    # Tampilan batas kabupaten/kota untuk provinsi aktif.
    if not nama_aktif:
        st.session_state["map_view"] = "provinsi"
        st.rerun()
        return

    prov = gdf_provinsi[gdf_provinsi["name"] == nama_aktif]
    if prov.empty:
        prov = gdf_provinsi[gdf_provinsi["key_provinsi"] == normalisasi_nama(nama_aktif)]
    if prov.empty:
        st.warning(f"Provinsi '{nama_aktif}' tidak ditemukan di GeoJSON.")
        if st.button("← Kembali ke peta Indonesia", key="btn_back_missing_prov"):
            st.session_state["map_view"] = "provinsi"
            st.session_state["selected_province"] = None
            st.session_state["map_last_filter"] = "Semua"
            st.session_state["provinsi_dari_peta"] = "Semua"
            st.rerun()
        return

    nama_geojson = prov.iloc[0]["name"]
    kode_provinsi = normalisasi_kode(prov.iloc[0]["code"])

    try:
        gdf_kab = load_geojson(URL_KAB_KOTA).copy()
        if not {"name", "code", "geometry"}.issubset(gdf_kab.columns):
            st.error("GeoJSON kabupaten/kota harus memiliki kolom name, code, dan geometry.")
            return

        gdf_kab["kode_normal"] = gdf_kab["code"].apply(normalisasi_kode)
        gdf_pilihan = gdf_kab[gdf_kab["kode_normal"].str.startswith(kode_provinsi)].copy()
        if gdf_pilihan.empty:
            st.warning(
                f"Batas kabupaten/kota untuk {nama_geojson} tidak ditemukan. "
                "Periksa apakah kode pada kedua GeoJSON menggunakan format yang sama."
            )
            return

        # Sederhanakan geometri agar peta lebih ringan ditampilkan.
        gdf_pilihan["geometry"] = gdf_pilihan.geometry.simplify(0.001, preserve_topology=True)
        minx, miny, maxx, maxy = gdf_pilihan.total_bounds
        peta = _buat_peta_dasar(zoom=6)
        peta.fit_bounds([[miny, minx], [maxy, maxx]], padding=(20, 20))
        folium.GeoJson(
            gdf_pilihan.__geo_interface__,
            name="Batas Kabupaten/Kota",
            style_function=lambda feature: {
                "fillColor": "#FCA5A5",
                "color": "#991B1B",
                "weight": 1,
                "fillOpacity": 0.35,
            },
            highlight_function=lambda feature: {"color": "#450A0A", "weight": 2, "fillOpacity": 0.6},
            tooltip=folium.GeoJsonTooltip(
                fields=["name"],
                aliases=["Kabupaten/Kota:"],
                sticky=True,
            ),
        ).add_to(peta)

        # Marker fasilitas: koordinat dibaca dari file lokal agar alamat internal
        # tidak otomatis dikirim ke layanan geocoding publik.
        if df_fasilitas is not None:
            kolom_fasilitas = [
                "Nama Instansi /Fasilitas",
                "Provinsi_Visualisasi",
                "Lokasi Pemanfaatan",
            ]
            kolom_hilang = [kolom for kolom in kolom_fasilitas if kolom not in df_fasilitas.columns]
            if kolom_hilang:
                st.warning(f"Kolom data fasilitas tidak ditemukan: {kolom_hilang}")
            else:
                data_fasilitas = df_fasilitas[kolom_fasilitas].copy()
                data_fasilitas = data_fasilitas.dropna(
                    subset=["Nama Instansi /Fasilitas", "Provinsi_Visualisasi"]
                )
                data_fasilitas["key_provinsi"] = data_fasilitas["Provinsi_Visualisasi"].apply(normalisasi_nama)
                data_fasilitas = data_fasilitas[
                    data_fasilitas["key_provinsi"] == normalisasi_nama(nama_geojson)
                ].drop_duplicates(
                    subset=["Nama Instansi /Fasilitas", "Lokasi Pemanfaatan"]
                )

                try:
                    koordinat = pd.read_csv("koordinat_fasilitas.csv")
                    kolom_koordinat = [
                        "Nama Instansi /Fasilitas",
                        "Lokasi Pemanfaatan",
                        "latitude",
                        "longitude",
                    ]
                    if not set(kolom_koordinat).issubset(koordinat.columns):
                        st.warning(
                            "File koordinat_fasilitas.csv harus memiliki kolom: "
                            + ", ".join(kolom_koordinat)
                        )
                    else:
                        data_fasilitas = data_fasilitas.merge(
                            koordinat[kolom_koordinat].drop_duplicates(
                                subset=["Nama Instansi /Fasilitas", "Lokasi Pemanfaatan"]
                            ),
                            on=["Nama Instansi /Fasilitas", "Lokasi Pemanfaatan"],
                            how="left",
                        )
                        data_fasilitas["latitude"] = pd.to_numeric(
                            data_fasilitas["latitude"], errors="coerce"
                        )
                        data_fasilitas["longitude"] = pd.to_numeric(
                            data_fasilitas["longitude"], errors="coerce"
                        )
                        data_fasilitas = data_fasilitas.dropna(
                            subset=["latitude", "longitude"]
                        )
                        data_fasilitas = data_fasilitas[
                            data_fasilitas["latitude"].between(-11.5, 6.5)
                            & data_fasilitas["longitude"].between(94, 142)
                        ]

                        for _, fasilitas in data_fasilitas.iterrows():
                            nama_fasilitas = str(fasilitas["Nama Instansi /Fasilitas"])
                            alamat = str(fasilitas["Lokasi Pemanfaatan"])
                            folium.Marker(
                                location=[fasilitas["latitude"], fasilitas["longitude"]],
                                tooltip=nama_fasilitas,
                                popup=folium.Popup(
                                    f"<b>{nama_fasilitas}</b><br>{alamat}",
                                    max_width=350,
                                ),
                                icon=folium.Icon(color="blue", icon="building", prefix="fa"),
                            ).add_to(peta)

                        st.caption(
                            f"Menampilkan {len(data_fasilitas)} fasilitas dengan koordinat valid "
                            f"di {nama_geojson}."
                        )
                except FileNotFoundError:
                    st.info(
                        "Marker fasilitas belum ditampilkan. Siapkan file lokal "
                        "'koordinat_fasilitas.csv' berisi nama fasilitas, alamat, "
                        "latitude, dan longitude."
                    )

        st_folium(
            peta,
            use_container_width=True,
            height=560,
            key=f"dashboard_peta_kab_{kode_provinsi}",
        )
    except Exception as exc:
        st.error(f"Gagal memuat batas kabupaten/kota: {exc}")
        return

    st.caption("Data SRP dihitung pada tingkat provinsi. Peta ini menampilkan batas administratif kabupaten/kota.")
    if st.button("← Kembali ke Peta Indonesia", key="btn_back_indonesia"):
        st.session_state["map_view"] = "provinsi"
        st.session_state["selected_province"] = None
        st.session_state["map_last_filter"] = "Semua"
        st.session_state["provinsi_dari_peta"] = "Semua"
        st.rerun()
