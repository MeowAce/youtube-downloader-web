# YT Downloader

Aplikasi web sederhana untuk mengunduh video dan audio dari YouTube menggunakan Flask dan yt-dlp.

## Deskripsi

YT Downloader adalah aplikasi web yang memungkinkan Anda mengunduh video YouTube dalam berbagai format dan resolusi, serta mengekstrak audio dalam format seperti MP3, M4A, AAC, FLAC, WAV, OPUS, dan VORBIS. Aplikasi ini mendukung pengunduhan playlist, pemotongan video berdasarkan waktu, dan memiliki antarmuka web yang mudah digunakan.

## Fitur

- **Preview Video/Playlist**: Lihat informasi video sebelum mengunduh
- **Download Video**: Mendukung berbagai resolusi dan format (MP4, WebM, MKV)
- **Download Audio**: Ekstrak audio dalam berbagai format dan kualitas
- **Dukungan Playlist**: Unduh seluruh playlist YouTube
- **Pemotongan Video**: Potong video berdasarkan waktu mulai dan akhir
- **Progress Tracking**: Pantau kemajuan unduhan secara real-time
- **Auto Cleanup**: File unduhan otomatis dihapus setelah 5 menit
- **Docker Support**: Mudah di-deploy menggunakan Docker

## Persyaratan

- Python 3.10+
- FFmpeg (untuk pemrosesan audio/video)
- yt-dlp (library untuk mengunduh dari YouTube)
- Flask
- flask-socketio
- python-socketio
- python-engineio

## Instalasi

### Instalasi Manual

1. **Clone repository ini:**
   ```bash
   git clone https://github.com/MeowAce/youtube-downloader-web.git
   cd Yt-downloader
   ```

2. **Buat virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Pada Windows: venv\Scripts\activate
   ```

3. **Instal dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instal FFmpeg:**
   - **Ubuntu/Debian:** `sudo apt install ffmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Windows:** Download dari [ffmpeg.org](https://ffmpeg.org/download.html)

5. **Jalankan aplikasi:**
   ```bash
   python app.py
   ```

   Aplikasi akan berjalan di `http://localhost:5000`

### Menggunakan Docker

1. **Build image:**
   ```bash
   docker build -t yt-downloader .
   ```

2. **Jalankan container:**
   ```bash
   docker run -p 5000:5000 yt-downloader
   ```

   Aplikasi akan tersedia di `http://localhost:5000`

## Penggunaan

1. Buka browser dan akses `http://localhost:5000`
2. Masukkan URL YouTube yang ingin diunduh
3. Pilih format (Video atau Audio)
4. Jika memilih Video:
   - Pilih resolusi
   - Pilih format video (MP4, WebM, MKV)
5. Jika memilih Audio:
   - Pilih kualitas audio
6. Opsional: Centang "Playlist" jika URL adalah playlist
7. Opsional: Masukkan waktu mulai dan akhir untuk memotong video
8. Klik "Download" dan tunggu proses selesai
9. Klik "Download File" untuk mengunduh file

## API Endpoints

- `GET /`: Halaman utama
- `POST /`: Memulai proses download
- `POST /preview`: Preview informasi video
- `GET /ambil_file/<task_id>`: Download file hasil
- `GET /proxy_gambar`: Proxy gambar dari URL eksternal
- WebSocket `progress`: Real-time progress tracking

## Struktur Proyek

```
Yt-downloader/
├── app.py                 # Aplikasi Flask dan socketio utama
├── requirements.txt       # Dependencies Python
├── Dockerfile            # Konfigurasi Docker
├── LICENSE               # Lisensi MIT
├── cookies.txt           # File cookies untuk autentikasi (opsional)
├── README.md             # Dokumentasi proyek
├── templates/
│   └── index.html        # Template web interface
├── static/
│   ├── manifest.json     # PWA manifest file
│   └── sw.js             # Service Worker untuk PWA
└── downloads/            # Folder untuk file unduhan (dibuat otomatis)
```

## Troubleshooting

### FFmpeg tidak terinstal
**Gejala:** Error `'ffmpeg' is not recognized` atau `ffmpeg not found`

**Solusi:**
- **Ubuntu/Debian:** `sudo apt update && sudo apt install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Windows:** Download installer dari [ffmpeg.org](https://ffmpeg.org/download.html) atau gunakan `choco install ffmpeg`

### Port 5000 sudah terpakai
**Gejala:** Error `Address already in use` atau `Port 5000 is in use`

**Solusi:**
1. Ubah port di `app.py` baris terakhir:
   ```python
   socketio.run(app, debug=True, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
   ```
2. Atau kill proses yang menggunakan port 5000:
   ```bash
   # Linux/macOS
   lsof -ti:5000 | xargs kill -9
   
   # Windows
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```

### Download gagal / Video tidak bisa diunduh
**Gejala:** Error saat download atau file kosong

**Solusi:**
- Pastikan video bukan video live atau age-restricted
- Coba gunakan cookies YouTube di `cookies.txt` (jika diperlukan untuk akun tertentu)
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Periksa apakah FFmpeg terinstal dengan benar

### Browser mengalami CORS error
**Gejala:** Error CORS saat preview atau proxy gambar

**Solusi:**
- CORS sudah diatur ke `*` di aplikasi, jika masih ada error cek browser console
- Coba di browser lain atau clear cache browser

### File unduhan tidak ditemukan
**Gejala:** Klik "Download File" tapi file tidak ada/error 404

**Solusi:**
- File dihapus otomatis setelah 5 menit jika tidak didownload
- Unduh file sebelum 5 menit berlalu
- Cek folder `downloads/` apakah file ada

## Lisensi

Proyek ini menggunakan lisensi MIT. Lihat file [LICENSE](LICENSE) untuk detail lebih lanjut.

## Kontribusi

Kontribusi sangat diterima! Silakan buat issue atau pull request untuk perbaikan dan fitur baru.

## Peringatan

- Pastikan Anda memiliki hak untuk mengunduh dan menggunakan konten YouTube
- Aplikasi ini untuk penggunaan pribadi saja
- Penggunaan untuk tujuan komersial atau distribusi massal tidak direkomendasikan

## Pengembang

Dikembangkan oleh Defha Hanief Fachry</content>