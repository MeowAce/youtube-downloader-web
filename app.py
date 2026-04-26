from flask import Flask, render_template, request, send_file, flash, jsonify, session, Response
from flask_socketio import SocketIO
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import yt_dlp
import os
import time
import traceback
import uuid
import shutil
import re 
import urllib.request
from dotenv import load_dotenv

# Muat token dari file .env 
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") 
socketio = SocketIO(app, cors_allowed_origins="*") 
DOWNLOAD_FOLDER = 'downloads'

tasks = {}

preview_cache = {}

# Fungsi pembersih cache (opsional, untuk mencegah RAM penuh)
def bersihkan_cache_tua():
    sekarang = time.time()
    expired_keys = [k for k, v in preview_cache.items() if sekarang > v['expires']]
    for k in expired_keys:
        del preview_cache[k]

executor = ThreadPoolExecutor(max_workers=3) 

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# [PENINGKATAN PERFORMA]: Membersihkan memori RAM dari task yang sudah usang
def hapus_file_lama():
    waktu_sekarang = time.time()
    task_keys_to_delete = []
    for nama_item in os.listdir(DOWNLOAD_FOLDER):
        path_item = os.path.join(DOWNLOAD_FOLDER, nama_item)
        waktu_modifikasi = os.path.getmtime(path_item)
        if waktu_sekarang - waktu_modifikasi > 300: 
            try:
                if os.path.isfile(path_item): os.remove(path_item)
                elif os.path.isdir(path_item): shutil.rmtree(path_item)
                
                # Ekstrak task_id dari nama file/folder jika memungkinkan
                if nama_item.startswith("Media_Batch_"):
                    t_id = nama_item.replace("Media_Batch_", "").replace(".zip", "")
                    task_keys_to_delete.append(t_id)
                else:
                    task_keys_to_delete.append(nama_item)
            except: pass
            
    for t_id in task_keys_to_delete:
        if t_id in tasks:
            del tasks[t_id]

scheduler = BackgroundScheduler()
scheduler.add_job(func=hapus_file_lama, trigger="interval", minutes=5)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

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
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    return send_file('static/manifest.json', mimetype='application/manifest+json')

@app.route('/preview', methods=['POST'])
def preview():
    data = request.get_json()
    url = data.get('url')
    if not url: return jsonify({'success': False, 'error': 'URL kosong'})

    # 1. Cek apakah sudah ada di Cache (berlaku 10 menit)
    if url in preview_cache and time.time() < preview_cache[url]['expires']:
        cached_data = preview_cache[url]['response']
        return jsonify(cached_data)

    try:
        ydl_opts = {
            'skip_download': True, 
            'quiet': True,
            'no_warnings': True,
            'source_address': '0.0.0.0',
            'remote_components': ['ejs:github'],
            'extract_flat': 'in_playlist', # Mempercepat loading playlist
        }
        
        if os.path.exists('cookies.txt'):
            perbaiki_cookies('cookies.txt')
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extract_info adalah bagian yang paling lama
            info = ydl.extract_info(url, download=False)
            
            # Logika ekstraksi format (seperti yang sudah kamu buat sebelumnya)
            res_set = set()
            ext_set = set()
            audio_ext_set = set()
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec') != 'none':
                        h = f.get('height')
                        if h: res_set.add(h)
                        e = f.get('ext')
                        if e: ext_set.add(e)
                    elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        ae = f.get('ext')
                        if ae: audio_ext_set.add(ae)

            available_formats = {
                'resolutions': sorted(list(res_set), reverse=True),
                'video_ext': sorted(list(ext_set)),
                'audio_ext': sorted(list(audio_ext_set))
            }

            # Ambil metadata dasar
            title = info.get('title') or 'Video Tidak Diketahui'
            uploader = info.get('uploader') or info.get('channel') or 'Akun Tidak Diketahui'
            thumbnail = info.get('thumbnail') or (info['thumbnails'][-1].get('url') if info.get('thumbnails') else '')
            
            duration_sec = info.get('duration')
            
            # --- MULAI PROTEKSI DURASI ---
            # Batasi maksimal 2 jam (7200 detik). Kamu bisa mengubah angka ini.
            if duration_sec and duration_sec > 7200:
                return jsonify({'success': False, 'error': 'Video terlalu panjang! Batas maksimal server adalah 2 Jam.'})
            # --- AKHIR PROTEKSI DURASI ---
            
            duration = "Live / Tidak diketahui"
            if duration_sec:
                mins, secs = divmod(duration_sec, 60)

            response_data = {
                'success': True, 
                'title': title, 
                'thumbnail': thumbnail, 
                'uploader': uploader, 
                'duration': duration,
                'formats': available_formats
            }

            # 2. Simpan ke Cache selama 10 menit (600 detik)
            preview_cache[url] = {
                'info': info, # Simpan objek info asli untuk dipakai saat download
                'response': response_data,
                'expires': time.time() + 600
            }

            return jsonify(response_data)

    except Exception as e: 
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    if task_id not in tasks:
        tasks[task_id] = {}
    tasks[task_id]['cancelled'] = True
    return jsonify({"success": True})

def proses_download_background(task_id, urls, format_choice, resolution_choice, audio_quality, is_playlist, video_ext, start_time, end_time, custom_filename, download_subtitles):
    if task_id not in tasks:
        tasks[task_id] = {}
    tasks[task_id]['cancelled'] = False

    try:
        task_folder = os.path.join(DOWNLOAD_FOLDER, task_id)
        os.makedirs(task_folder, exist_ok=True)

        if urls:
            def cek_batal(info_dict, *args, **kwargs):
                if tasks.get(task_id, {}).get('cancelled'):
                    return "Dihentikan: Pengguna membatalkan unduhan"
                return None

            state = {'last_time': 0}
            
            # [PENINGKATAN UI]: Menghapus kode warna ANSI yang mengotori string dari yt-dlp
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

            def progress_hook(d):
                if tasks.get(task_id, {}).get('cancelled'):
                    raise ValueError("Unduhan dihentikan paksa oleh pengguna.")

                info = d.get('info_dict', {})
                file_title = info.get('title', 'Media Tanpa Judul')
                file_id = info.get('id', str(abs(hash(d.get('filename', file_title)))))
                
                if d['status'] == 'downloading':
                    sekarang = time.time()
                    if sekarang - state['last_time'] < 0.5:
                        return
                    state['last_time'] = sekarang

                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        percent_str = f"{percent:.1f}"
                    else:
                        percent_str = ansi_escape.sub('', d.get('_percent_str', '0.0%')).replace('%', '').strip()
                        
                    # Ekstrak data ETA, Speed, dan Size untuk UI baru
                    speed_str = ansi_escape.sub('', d.get('_speed_str', 'N/A')).strip()
                    eta_str = ansi_escape.sub('', d.get('_eta_str', 'N/A')).strip()
                    size_str = ansi_escape.sub('', d.get('_total_bytes_str', 'N/A')).strip()
                        
                    socketio.emit('progress', {
                        'task_id': task_id, 
                        'file_id': file_id, 
                        'file_title': file_title, 
                        'progress': percent_str, 
                        'processing_msg': 'Mengunduh data...',
                        'speed': speed_str,
                        'eta': eta_str,
                        'size': size_str
                    })
                elif d['status'] == 'finished':
                    socketio.emit('progress', {'task_id': task_id, 'file_id': file_id, 'file_title': file_title, 'progress': '100', 'processing_msg': 'Menyatukan Audio & Video...'})

            ydl_opts = {
                'outtmpl': os.path.join(task_folder, '%(title)s.%(ext)s'), 
                'noplaylist': not is_playlist,
                'ignoreerrors': True, 
                'progress_hooks': [progress_hook], 
                'match_filter': cek_batal,
                'source_address': '0.0.0.0',
                'remote_components': ['ejs:github'],
                'concurrent_fragment_downloads': 4,
                'sleep_requests': 2,  # Beri jeda 2 detik agar tidak dianggap spam
                'extractor_args': {
                    'youtube': {
                    'client': ['android', 'web']
                    }
                },
                'ignoreerrors': True,
                'no_warnings': True
            }
            
        if download_subtitles:
            ydl_opts['writesubtitles'] = True        # Mengunduh subtitle manual dari uploader
            ydl_opts['writeautomaticsub'] = True     # Mengunduh auto-generated subtitle dari YouTube jika manual tidak ada
            ydl_opts['subtitleslangs'] = ['id', 'en'] # Prioritaskan Bahasa Indonesia dan Inggris
            ydl_opts['subtitlesformat'] = 'best'     # Pilih format terbaik (biasanya vtt atau srt)

        if custom_filename:
            # Bersihkan nama dari karakter yang dilarang oleh Windows/Linux
            safe_name = re.sub(r'[\\/*?:"<>|]', "", custom_filename)
            
            if is_playlist:
                # Jika playlist, tambahkan playlist_index agar file tidak tertimpa
                ydl_opts['outtmpl'] = f'{DOWNLOAD_FOLDER}/{safe_name}_%(playlist_index)s.%(ext)s'
            else:
                ydl_opts['outtmpl'] = f'{DOWNLOAD_FOLDER}/{safe_name}.%(ext)s'
        else:
            # Default jika input dikosongkan (Gunakan judul asli)
            ydl_opts['outtmpl'] = f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s'
            
            if os.path.exists('cookies.txt'):
                perbaiki_cookies('cookies.txt')
                ydl_opts['cookiefile'] = 'cookies.txt'

            if format_choice == 'metadata':
                ydl_opts.update({'skip_download': True, 'writeinfojson': True, 'clean_infojson': False})
            else:
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
                    
                    if audio_quality == 'webm':
                        ydl_opts.update({'format': 'bestaudio[ext=webm]/bestaudio/best'})
                    else:
                        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec}]})
                        if codec in ['mp3', 'm4a', 'aac', 'opus']: 
                            ydl_opts['postprocessors'][0]['preferredquality'] = quality
                else: 
                    if video_ext == 'webm': format_string = f'bestvideo[height<={resolution_choice}][ext=webm]+bestaudio[ext=webm]/bestvideo[height<={resolution_choice}]+bestaudio/best'
                    elif video_ext == 'mkv': format_string = f'bestvideo[height<={resolution_choice}]+bestaudio/bestvideo[height<={resolution_choice}]+bestaudio/best'
                    else: format_string = f'bestvideo[height<={resolution_choice}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_choice}]+bestaudio/best'
                        
                    ydl_opts['format'] = format_string
                    
                    if video_ext in ['avi', 'mov']:
                        ydl_opts['merge_output_format'] = 'mkv' 
                        ydl_opts.setdefault('postprocessors', []).append({'key': 'FFmpegVideoConvertor', 'preferedformat': video_ext})
                    elif video_ext == 'webm' and 'instagram.com' in urls[0]: 
                        ydl_opts['merge_output_format'] = 'mp4'
                    else: 
                        ydl_opts['merge_output_format'] = video_ext

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Memaksa yt-dlp untuk mengambil link baru yang segar agar tidak kena 403
                ydl.download(urls)

        if tasks.get(task_id, {}).get('cancelled'):
            raise Exception("Proses dibatalkan oleh pengguna.")

        downloaded_files = os.listdir(task_folder)
        if len(downloaded_files) == 0: 
            raise Exception("Tidak ada file yang berhasil diproses.")
        elif len(downloaded_files) == 1:
            tasks[task_id] = {'filename': os.path.join(task_folder, downloaded_files[0])}
        else:
            socketio.emit('progress', {'task_id': task_id, 'processing_msg': 'Membungkus semua file ke dalam ZIP...'})
            zip_filename_base = os.path.join(DOWNLOAD_FOLDER, f"Media_Batch_{task_id}")
            shutil.make_archive(zip_filename_base, 'zip', task_folder)
            tasks[task_id] = {'filename': f"{zip_filename_base}.zip"}

        socketio.emit('completed', {'task_id': task_id})

    except Exception as e:
        socketio.emit('error', {'task_id': task_id, 'error': str(e)})

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        
        # --- LOGIKA SESSION PIN BARU ---
        # Cek apakah user BELUM terautentikasi di session ini
        if not session.get('is_authenticated'):
            pin_input = request.form.get('pin', '')
            pin_server = os.getenv("APP_PIN", "1234")
            
            if pin_input != pin_server:
                # Jika salah, kembalikan ke halaman awal dengan status need_pin=True
                return render_template('index.html', error_msg="Akses Ditolak: PIN Server Salah!", need_pin=True)
            else:
                # Jika PIN benar, catat di memori browser (session)
                session['is_authenticated'] = True
        # -------------------------------
    
        urls_raw = request.form.get('url', '')
        urls = [u.strip() for u in urls_raw.replace(',', '\n').split('\n') if u.strip()]
        
        format_choice = request.form.get('format')
        custom_filename = request.form.get('custom_filename', '').strip()
        resolution_choice = request.form.get('resolution')
        audio_quality = request.form.get('audio_quality')
        video_ext = request.form.get('video_ext', 'mp4')
        is_playlist = 'is_playlist' in request.form

        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        download_subtitles = request.form.get('download_subtitles') == '1'
        
        if not urls:
            return render_template('index.html', need_pin=False)

        task_id = str(uuid.uuid4())
        executor.submit(proses_download_background, task_id, urls, format_choice, resolution_choice, audio_quality, is_playlist, video_ext, start_time, end_time, custom_filename, download_subtitles)
        return render_template('index.html', task_id=task_id, need_pin=False)

    tampilkan_pin = not session.get('is_authenticated')
    return render_template('index.html', need_pin=tampilkan_pin)

@app.route('/ambil_file/<task_id>')
def ambil_file(task_id):
    task = tasks.get(task_id)
    if task: return send_file(task['filename'], as_attachment=True)
    return "File tidak siap atau tidak ditemukan.", 404

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)