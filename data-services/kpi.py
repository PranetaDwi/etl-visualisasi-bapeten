def load_data_rekapitulasi_kategori(provinsi, data_olah, nama_column, parameter):
    if provinsi=="Semua":
        return sum(data_olah[parameter])

    else:
        jumlah = data_olah.loc[
            data_olah[nama_column] == provinsi,
            parameter
        ].iloc[0].item()

    return jumlah


