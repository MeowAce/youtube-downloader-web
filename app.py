from flask import Flask, render_template, request, send_file, flash, jsonify
import yt_dlp
import os
import time
import threading
import uuid
import shutil
import re # Digunakan untuk membersihkan teks persentase dari karakter aneh

app = Flask(__name__)
app.secret_key = "super_secret_key" 
DOWNLOAD_FOLDER = 'downloads'

tasks = {}

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def hapus_file_lama():
    waktu_sekarang = time.time()
    for nama_item in os.listdir(DOWNLOAD_FOLDER):
        path_item = os.path.join(DOWNLOAD_FOLDER, nama_item)
        waktu_modifikasi = os.path.getmtime(path_item)
        
        if waktu_sekarang - waktu_modifikasi > 1800:
            try:
                if os.path.isfile(path_item):
                    os.remove(path_item)
                elif os.path.isdir(path_item):
                    shutil.rmtree(path_item)
            except:
                pass

@app.route('/preview', methods=['POST'])
def preview():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL kosong'})

    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'extract_flat': 'in_playlist'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                title = info.get('title', 'Playlist YouTube')
                uploader = info.get('uploader', 'Berbagai Channel')
                duration = "Playlist"
                thumbnail = info['entries'][0].get('thumbnails', [{}])[-1].get('url') if info.get('entries') else ''
            else:
                title = info.get('title', 'Video Tidak Diketahui')
                uploader = info.get('uploader', 'Channel Tidak Diketahui')
                thumbnail = info.get('thumbnail', '')
                duration_sec = info.get('duration')
                
                if duration_sec:
                    mins, secs = divmod(duration_sec, 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0:
                        duration = f"{int(hours):02d}:{int(mins):02d}:{int(secs):02d}"
                    else:
                        duration = f"{int(mins):02d}:{int(secs):02d}"
                else:
                    duration = "Live / Tidak diketahui"

        return jsonify({
            'success': True,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# --- FUNGSI BACKGROUND DENGAN PROGRESS HOOK ---
def proses_download_background(task_id, url, format_choice, resolution_choice, audio_quality, is_playlist):
    try:
        task_folder = os.path.join(DOWNLOAD_FOLDER, task_id)
        os.makedirs(task_folder, exist_ok=True)

        # Fungsi khusus untuk menangkap progres persentase dari yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Coba ambil persen dari hitungan byte (paling akurat)
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = (downloaded / total) * 100
                    tasks[task_id]['progress'] = f"{percent:.1f}"
                else:
                    # Alternatif: ambil dari string bawaan yt-dlp dan bersihkan kode warna ANSI
                    percent_str = d.get('_percent_str', '0.0%')
                    clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '').strip()
                    tasks[task_id]['progress'] = clean_percent
            elif d['status'] == 'finished':
                # Saat selesai download tapi sedang proses gabung audio+video (FFmpeg)
                tasks[task_id]['progress'] = "100" 
                tasks[task_id]['processing_msg'] = "Menggabungkan File (Harap Tunggu)..."

        ydl_opts = {
            'outtmpl': os.path.join(task_folder, '%(title)s.%(ext)s'),
            'noplaylist': not is_playlist,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook], # <-- Memasukkan hook ke sini
        }

        if format_choice == 'audio':
            codec = 'mp3'
            quality = '192'

            if audio_quality == 'mp3_320': quality = '320'
            elif audio_quality == 'flac': codec = 'flac'
            elif audio_quality == 'wav': codec = 'wav'

            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                }],
            })
            if codec in ['mp3', 'm4a']:
                ydl_opts['postprocessors'][0]['preferredquality'] = quality

        else: 
            format_string = f'bestvideo[height<={resolution_choice}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_choice}]+bestaudio/best'
            ydl_opts.update({
                'format': format_string,
                'merge_output_format': 'mp4'
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_files = os.listdir(task_folder)

        if len(downloaded_files) == 0:
            raise Exception("Tidak ada file yang berhasil didownload.")
        elif len(downloaded_files) == 1:
            final_file = os.path.join(task_folder, downloaded_files[0])
            tasks[task_id]['filename'] = final_file
        else:
            tasks[task_id]['processing_msg'] = "Membuat file ZIP Playlist..."
            zip_filename_base = os.path.join(DOWNLOAD_FOLDER, f"Playlist_{task_id}")
            shutil.make_archive(zip_filename_base, 'zip', task_folder)
            tasks[task_id]['filename'] = f"{zip_filename_base}.zip"

        tasks[task_id]['status'] = 'completed'

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)


@app.route('/', methods=['GET', 'POST'])
def index():
    hapus_file_lama()

    if request.method == 'POST':
        url = request.form.get('url')
        format_choice = request.form.get('format')
        resolution_choice = request.form.get('resolution')
        audio_quality = request.form.get('audio_quality')
        is_playlist = 'is_playlist' in request.form 
        
        if not url:
            flash('Harap masukkan URL YouTube!')
            return render_template('index.html')

        task_id = str(uuid.uuid4())
        # Menambahkan variabel progress ke dalam dictionary
        tasks[task_id] = {'status': 'processing', 'filename': '', 'error': '', 'progress': '0', 'processing_msg': 'Memulai Download...'}

        thread = threading.Thread(target=proses_download_background, 
                                  args=(task_id, url, format_choice, resolution_choice, audio_quality, is_playlist))
        thread.start()

        return render_template('index.html', task_id=task_id)

    return render_template('index.html')

@app.route('/status/<task_id>')
def cek_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'error': 'Task tidak ditemukan'})
    return jsonify(task)

@app.route('/ambil_file/<task_id>')
def ambil_file(task_id):
    task = tasks.get(task_id)
    if task and task['status'] == 'completed':
        return send_file(task['filename'], as_attachment=True)
    return "File tidak siap atau tidak ditemukan.", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)