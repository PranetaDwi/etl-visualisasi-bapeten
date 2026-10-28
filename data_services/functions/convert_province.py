import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

