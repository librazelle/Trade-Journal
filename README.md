# trade-lens

Jurnal trading yang digabung dengan berita ekonomi AS secara realtime. Versi awal (first try).

## Yang sudah ada

- Form catat entry: instrumen, arah, harga, waktu, lot, SL, TP, catatan.
- Konteks otomatis: berita N jam sebelum entry (default 5 jam), dibekukan saat trade dicatat.
- Berita live lewat Server-Sent Events, dengan label delay di tiap item.
- Worker yang polling connector. Saat ini baru Federal Reserve press release (RSS resmi).
- Label status berita: resmi, dilaporkan, rumor.
- Database SQLite satu file, tanpa setup tambahan.

## Belum ada (roadmap)

- Connector BLS (CPI, PPI, NFP), FRED, EIA, GDELT, dan kalender ekonomi.
- Harga live XAUUSD dan perhitungan PnL.
- Login dan multi-user.
- Mode review: replay berita dan harga.

## Menjalankan

Butuh Python 3.11 atau lebih baru.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Buka http://localhost:8000. Di GitHub Codespaces, buka tab Ports lalu klik port 8000.

`--workers 1` wajib. Broadcast live hanya berjalan dalam satu proses.

## Tes

```bash
python -m pytest
```

## Konfigurasi (environment variable)

| Variabel | Default | Fungsi |
|---|---|---|
| `TL_DB_PATH` | `trade_lens.db` | Lokasi file SQLite |
| `TL_DISPLAY_TZ` | `Asia/Jakarta` | Zona waktu tampilan |
| `TL_LOOKBACK_HOURS` | `5` | Berapa jam berita sebelum entry yang diambil |
| `TL_ENABLE_WORKER` | `1` | Set `0` untuk mematikan polling connector |
| `TL_USER_AGENT` | `trade-lens/0.1 ...` | User-Agent saat mengambil data. Isi dengan kontak kamu. |

## Menambah connector baru

1. Buat file di `app/connectors/`, misalnya `bls_calendar.py`.
2. Implementasikan class yang mewarisi `Connector` dan mengembalikan list `NewsItem` dari `fetch()`.
3. Daftarkan instance-nya di `app/connectors/__init__.py`.
4. Tambahkan test kecil di `tests/`.

Aturan status: `official` hanya untuk sumber resmi pemerintah atau bank sentral. Laporan media memakai `reported`. Rumor atau berita yang belum terkonfirmasi memakai `rumor`.

## Catatan jujur

- URL feed Fed (`federalreserve.gov/feeds/press_all.xml`) perlu diverifikasi saat pertama dijalankan. Kalau 403 atau 404, cek User-Agent atau URL-nya.
- Konteks dihitung dari berita yang sudah masuk sistem saat trade dicatat. Karena itu, catat trade sesegera mungkin setelah entry supaya konteksnya akurat.
- GDELT hanya update sekitar 15 menit, jadi tidak memenuhi target delay 1-5 menit.

## Lisensi dan etika data

- Kode: MIT (ganti sesuai keputusan kamu).
- Simpan judul, link, dan ringkasan pendek saja. Jangan menyimpan isi artikel penuh.
- Setiap connector wajib mendokumentasikan ToS sumbernya.
- Ini alat jurnal dan informasi, bukan saran investasi.
