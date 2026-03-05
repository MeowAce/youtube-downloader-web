# Gunakan OS Linux dengan Python 3.10
FROM python:3.10-slim

# Instal FFmpeg (Sangat wajib agar yt-dlp tidak error)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Pindah ke dalam folder aplikasi di server
WORKDIR /app

# Salin requirements.txt dan instal
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa file kita (app.py, folder templates, dll)
COPY . .

# Buka akses jaringan
EXPOSE 5000

# Jalankan aplikasi
CMD ["python", "app.py"]