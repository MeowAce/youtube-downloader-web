# 1. Gunakan OS Linux ringan yang sudah terinstal Python 3.10
FROM python:3.10-slim

# 2. Atur folder kerja di dalam Docker
WORKDIR /app

# 3. Instal FFmpeg (Wajib untuk yt-dlp menggabungkan video & audio)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. Salin file requirements dan instal library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Salin semua file kodemu (app.py, folder templates, dll) ke dalam Docker
COPY . .

# 6. Buat folder downloads jika belum ada
RUN mkdir -p downloads

# 7. Buka port 5000 agar bisa diakses dari luar
EXPOSE 5000

# 8. Perintah untuk menjalankan aplikasi saat container menyala
CMD ["python", "app.py"]