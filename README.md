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
- `GET /status/<task_id>`: Cek status download
- `GET /ambil_file/<task_id>`: Download file hasil

## Struktur Proyek

```
Yt-downloader/
├── app.py                 # Aplikasi Flask utama
├── requirements.txt       # Dependencies Python
├── Dockerfile            # Konfigurasi Docker
├── LICENSE               # Lisensi MIT
├── templates/
│   └── index.html        # Template web interface
└── downloads/            # Folder untuk file unduhan (dibuat otomatis)
```

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