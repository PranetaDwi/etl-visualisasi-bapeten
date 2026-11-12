import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def load_data_rekapitulasi_kategori(provinsi, data_olah, nama_column, parameter):
    if provinsi=="Semua":
        return sum(data_olah[parameter])

    else:
        jumlah = data_olah.loc[
            data_olah[nama_column] == provinsi,
            parameter
        ].iloc[0].item()

    return jumlah


