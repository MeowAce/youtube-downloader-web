from flask import Flask, render_template, request, send_file, flash, jsonify, Response
from flask_socketio import SocketIO
import yt_dlp
import os
import time
import threading
import uuid
import shutil
import re 
import urllib.request

app = Flask(__name__)
app.secret_key = "super_secret_key" 
socketio = SocketIO(app, cors_allowed_origins="*") 
DOWNLOAD_FOLDER = 'downloads'

tasks = {}

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def hapus_file_lama():
    waktu_sekarang = time.time()
    for nama_item in os.listdir(DOWNLOAD_FOLDER):
        path_item = os.path.join(DOWNLOAD_FOLDER, nama_item)
        waktu_modifikasi = os.path.getmtime(path_item)
        if waktu_sekarang - waktu_modifikasi > 300: 
            try:
                if os.path.isfile(path_item): os.remove(path_item)
                elif os.path.isdir(path_item): shutil.rmtree(path_item)
            except: pass

def perbaiki_cookies(filepath='cookies.txt'):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    butuh_perbaikan = False
    if not lines or not lines[0].startswith('# Netscape HTTP Cookie File'):
        lines.insert(0, '# Netscape HTTP Cookie File\n\n')
        butuh_perbaikan = True
    for i in range(len(lines)):
        line = lines[i]
        if not line.startswith('#') and '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0].startswith('.') and parts[1].upper() == 'FALSE':
                parts[1] = 'TRUE'
                lines[i] = '\t'.join(parts)
                butuh_perbaikan = True
    if butuh_perbaikan:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

def parse_waktu(waktu_str):
    if not waktu_str: return None
    try:
        parts = waktu_str.strip().split(':')
        if len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1: return float(parts[0])
    except: return None
    return None

@app.route('/favicon.ico')
def favicon():
    return send_file('static/icon-192.png', mimetype='image/png')

@app.route('/proxy_gambar')
def proxy_gambar():
    url_gambar = request.args.get('url')
    if not url_gambar: return "URL kosong", 400
    try:
        req = urllib.request.Request(url_gambar, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return Response(response.read(), mimetype=response.info().get_content_type())
    except Exception as e: return str(e), 404


@app.route('/sw.js')
def serve_sw():
    # Menyajikan Service Worker dari folder static
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    # Menyajikan Manifest dari folder static
    return send_file('static/manifest.json', mimetype='application/manifest+json')

@app.route('/preview', methods=['POST'])
def preview():
    data = request.get_json()
    url = data.get('url')
    if not url: return jsonify({'success': False, 'error': 'URL kosong'})

    try:
        ydl_opts = {
            'skip_download': True, 'quiet': True, 'extract_flat': 'in_playlist',
            'source_address': '0.0.0.0', 'remote_components': ['ejs:github']
        }
        if os.path.exists('cookies.txt'):
            perbaiki_cookies('cookies.txt')
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                title = info.get('title', 'Playlist / Multi-Media')
                uploader = info.get('uploader', 'Berbagai Sumber')
                duration = "Playlist / Carousel"
                thumbnail = info['entries'][0].get('thumbnails', [{}])[-1].get('url') if info.get('entries') else ''
            else:
                title = info.get('title', 'Video Tidak Diketahui')
                uploader = info.get('uploader', 'Akun Tidak Diketahui')
                thumbnail = info.get('thumbnail')
                if not thumbnail and info.get('thumbnails'):
                    thumbnail = info['thumbnails'][-1].get('url', '')
                elif not thumbnail: thumbnail = ''
                
                duration_sec = info.get('duration')
                if duration_sec:
                    mins, secs = divmod(duration_sec, 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0: duration = f"{int(hours):02d}:{int(mins):02d}:{int(secs):02d}"
                    else: duration = f"{int(mins):02d}:{int(secs):02d}"
                else: duration = "Live / Tidak diketahui"

        return jsonify({'success': True, 'title': title, 'thumbnail': thumbnail, 'uploader': uploader, 'duration': duration})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})

def proses_download_background(task_id, urls, format_choice, resolution_choice, audio_quality, is_playlist, video_ext, start_time, end_time):
    try:
        task_folder = os.path.join(DOWNLOAD_FOLDER, task_id)
        os.makedirs(task_folder, exist_ok=True)

        def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = (downloaded / total) * 100
                    socketio.emit('progress', {'task_id': task_id, 'status': 'processing', 'progress': f"{percent:.1f}"})
                else:
                    percent_str = d.get('_percent_str', '0.0%')
                    clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '').strip()
                    socketio.emit('progress', {'task_id': task_id, 'status': 'processing', 'progress': clean_percent})
            elif d['status'] == 'finished':
                socketio.emit('progress', {'task_id': task_id, 'status': 'processing', 'progress': '100', 'processing_msg': 'Memproses/Konversi File...'})

        ydl_opts = {
            'outtmpl': os.path.join(task_folder, '%(title)s.%(ext)s'), 'noplaylist': not is_playlist,
            'ignoreerrors': True, 'progress_hooks': [progress_hook], 'source_address': '0.0.0.0',
            'remote_components': ['ejs:github']
        }
        
        if os.path.exists('cookies.txt'):
            perbaiki_cookies('cookies.txt')
            ydl_opts['cookiefile'] = 'cookies.txt'

        if start_time or end_time:
            mulai_sec = parse_waktu(start_time) or 0
            selesai_sec = parse_waktu(end_time) or 999999 
            ydl_opts['download_ranges'] = lambda info_dict, ydl: [{'start_time': mulai_sec, 'end_time': selesai_sec}]
            ydl_opts['force_keyframes_at_cuts'] = True

        if format_choice == 'audio':
            codec = 'mp3'
            quality = '192'
            if audio_quality == 'mp3_320': quality = '320'
            elif audio_quality in ['m4a', 'aac', 'flac', 'wav', 'opus']: codec = audio_quality
            
            # Jika user minta webm audio, kita ambil format aslinya tanpa konversi codec FFmpeg
            if audio_quality == 'webm':
                ydl_opts.update({'format': 'bestaudio[ext=webm]/bestaudio/best'})
            else:
                ydl_opts.update({
                    'format': 'bestaudio/best', 
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec}]
                })
                if codec in ['mp3', 'm4a', 'aac', 'opus']: 
                    ydl_opts['postprocessors'][0]['preferredquality'] = quality
        else: 
            if video_ext == 'webm': format_string = f'bestvideo[height<={resolution_choice}][ext=webm]+bestaudio[ext=webm]/bestvideo[height<={resolution_choice}]+bestaudio/best'
            elif video_ext == 'mkv': format_string = f'bestvideo[height<={resolution_choice}]+bestaudio/bestvideo[height<={resolution_choice}]+bestaudio/best'
            else: 
                format_string = f'bestvideo[height<={resolution_choice}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_choice}]+bestaudio/best'
                
            ydl_opts['format'] = format_string
            
            # Mendukung format baru: avi, mov, flv dll (Akan dikonversi oleh ffmpeg)
            if video_ext in ['avi', 'mov']:
                ydl_opts['merge_output_format'] = 'mkv' # Gabung aman dulu
                ydl_opts.setdefault('postprocessors', []).append({'key': 'FFmpegVideoConvertor', 'preferedformat': video_ext})
            elif video_ext == 'webm' and 'instagram.com' in urls[0]: 
                ydl_opts['merge_output_format'] = 'mp4'
            else: 
                ydl_opts['merge_output_format'] = video_ext

        # Eksekusi yt-dlp dengan LIST URL (Batch Mode)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)

        downloaded_files = os.listdir(task_folder)
        if len(downloaded_files) == 0: raise Exception("Tidak ada file yang berhasil diunduh.")
        elif len(downloaded_files) == 1:
            tasks[task_id] = {'filename': os.path.join(task_folder, downloaded_files[0])}
        else:
            socketio.emit('progress', {'task_id': task_id, 'status': 'processing', 'progress': '100', 'processing_msg': 'Membungkus ke dalam file ZIP...'})
            zip_filename_base = os.path.join(DOWNLOAD_FOLDER, f"Media_Batch_{task_id}")
            shutil.make_archive(zip_filename_base, 'zip', task_folder)
            tasks[task_id] = {'filename': f"{zip_filename_base}.zip"}

        socketio.emit('completed', {'task_id': task_id})

    except Exception as e:
        socketio.emit('error', {'task_id': task_id, 'error': str(e)})


@app.route('/', methods=['GET', 'POST'])
def index():
    hapus_file_lama()
    if request.method == 'POST':
        urls_raw = request.form.get('url', '')
        # Pisahkan URL berdasarkan baris baru (Enter) atau koma, bersihkan whitespace
        urls = [u.strip() for u in urls_raw.replace(',', '\n').split('\n') if u.strip()]
        
        format_choice = request.form.get('format')
        resolution_choice = request.form.get('resolution')
        audio_quality = request.form.get('audio_quality')
        video_ext = request.form.get('video_ext', 'mp4') 
        is_playlist = 'is_playlist' in request.form 
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        if not urls:
            flash('Harap masukkan URL!')
            return render_template('index.html')

        task_id = str(uuid.uuid4())
        thread = threading.Thread(target=proses_download_background, 
                                  args=(task_id, urls, format_choice, resolution_choice, audio_quality, is_playlist, video_ext, start_time, end_time))
        thread.start()
        return render_template('index.html', task_id=task_id)

    return render_template('index.html')

@app.route('/ambil_file/<task_id>')
def ambil_file(task_id):
    task = tasks.get(task_id)
    if task: return send_file(task['filename'], as_attachment=True)
    return "File tidak siap atau tidak ditemukan.", 404

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)