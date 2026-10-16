"""Plain Indonesian explainers for community readers.

These are rule-based summaries, not translations of every detail or financial advice.
Unknown stories get a cautious generic explanation rather than an invented claim.
"""


def explain_news(title: str = "", summary: str = "", tags: str = "") -> dict:
    text = f"{title or ''} {summary or ''} {tags or ''}".lower()
    if any(k in text for k in ("fomc", "federal reserve", "fed funds rate", "interest rate decision", "powell")):
        normal = "Berita ini berkaitan dengan kebijakan bank sentral AS (The Fed), terutama suku bunga atau arah kebijakan moneter. Pasar menilai dampaknya terhadap dolar, imbal hasil obligasi, emas, dan saham."
        simple = "Intinya: ini kabar soal keputusan bank sentral Amerika. Kalau bunga atau rencana The Fed berubah dari perkiraan, harga emas dan saham bisa bergerak cepat. Arah geraknya tidak selalu sama."
    elif any(k in text for k in ("consumer price index", "cpi", "inflation", "price index", "ppi", "pce")):
        normal = "Berita ini terkait inflasi, yaitu perubahan harga barang dan jasa. Data yang lebih tinggi atau lebih rendah dari perkiraan bisa mengubah ekspektasi suku bunga dan menggerakkan dolar, emas, serta indeks saham."
        simple = "Intinya: ini berita tentang harga barang makin mahal atau tidak. Kalau angka inflasi beda dari perkiraan, pasar bisa menebak The Fed bakal mengubah bunga. Tebakan itu bisa bikin emas dan saham naik-turun."
    elif any(k in text for k in ("nonfarm payroll", "employment situation", "unemployment", "payroll employment", "jobs report", "job openings", "labor market", "labour market")):
        normal = "Berita ini membahas kondisi pasar kerja AS, seperti jumlah pekerjaan atau pengangguran. Data tenaga kerja dapat memengaruhi perkiraan kebijakan suku bunga dan pergerakan dolar, emas, serta indeks saham."
        simple = "Intinya: ini kabar soal pekerjaan di Amerika, misalnya orang yang dapat kerja atau yang masih menganggur. Kalau hasilnya mengejutkan, pasar bisa mengubah perkiraan soal bunga. Akibatnya harga emas dan saham bisa ikut bergerak."
    elif any(k in text for k in ("gross domestic product", "gdp", "economic growth", "productivity", "business activity")):
        normal = "Berita ini memberi petunjuk tentang pertumbuhan atau produktivitas ekonomi AS. Hasilnya dapat memengaruhi penilaian investor terhadap kekuatan ekonomi dan kebijakan suku bunga."
        simple = "Intinya: berita ini mencoba menjawab ekonomi Amerika lagi kuat atau melemah. Kalau hasilnya beda dari dugaan, investor bisa mengubah keputusan beli atau jual aset."
    elif any(k in text for k in ("treasury", "bond yield", "yield", "auction", "debt")):
        normal = "Berita ini berkaitan dengan obligasi pemerintah AS atau imbal hasilnya. Perubahan yield dapat memengaruhi biaya pinjaman dan daya tarik relatif dolar, emas, serta saham."
        simple = "Intinya: ini kabar soal surat utang pemerintah Amerika dan imbal hasilnya. Perubahannya bisa membuat investor memindahkan uang antara obligasi, dolar, emas, dan saham."
    elif any(k in text for k in ("tariff", "trade war", "sanction", "geopolitical", "war", "missile")):
        normal = "Berita ini berkaitan dengan risiko geopolitik atau perdagangan. Dampak pasarnya bergantung pada skala kejadian, respons pemerintah, dan seberapa besar hal itu sudah diperkirakan."
        simple = "Intinya: ada kabar soal konflik atau aturan dagang yang bisa bikin pasar khawatir. Saat orang takut risiko makin besar, sebagian bisa mencari aset yang dianggap lebih aman, tapi reaksi harga tetap bisa berbeda-beda."
    elif any(k in text for k in ("enforcement action", "enforcement actions", "bank", "financial institution")):
        normal = "Berita ini berkaitan dengan tindakan pengawasan atau lembaga keuangan. Dampak ke pasar luas belum tentu besar; konteks dan isi pengumuman lengkap perlu diperiksa."
        simple = "Intinya: ini kabar tentang bank atau tindakan dari pengawas keuangan. Belum tentu bikin emas atau saham bergerak besar. Buka berita aslinya dulu untuk tahu masalah dan dampaknya."
    else:
        normal = "Berita ini belum bisa diringkas secara spesifik hanya dari judul dan ringkasan yang tersedia. Baca sumber asli sebelum menganggapnya sebagai pemicu pergerakan pasar."
        simple = "Intinya: sistem belum cukup yakin berita ini membahas apa. Jangan langsung dipakai buat keputusan trading. Buka berita aslinya dulu."
    return {"summary_id": normal, "summary_simple": simple}
