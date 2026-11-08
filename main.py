import os
import io
import json
import sys
import re
import subprocess
import requests
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def extract_drive_id(url):
    match = re.search(r'[-\w]{25,}', url)
    return match.group(0) if match else None

def send_telegram_video(bot_token, chat_id, video_path, caption):
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    print("📤 Mengirim video hasil klip ke Telegram...")
    try:
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {'chat_id': chat_id, 'caption': caption}
            response = requests.post(url, data=data, files=files, timeout=180)
            
        if response.status_code == 200:
            print("✅ BERHASIL! Video dikirim ke Telegram!")
            return True
        else:
            print(f"❌ Gagal kirim ke Telegram (Status {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error kirim Telegram: {e}")
        return False

def main():
    print("🤖 Memulai Clay Auto Clipper 24/7 (TELEGRAM ENGINE)...")
    
    sa_key_str = os.environ.get('GCP_SA_KEY')
    sheet_url = os.environ.get('SPREADSHEET_URL')
    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not sa_key_str or not sheet_url or not telegram_token or not telegram_chat_id:
        print("❌ ERROR: Secret GCP_SA_KEY, SPREADSHEET_URL, TELEGRAM_BOT_TOKEN, atau TELEGRAM_CHAT_ID belum terisi!")
        sys.exit(1)

    # 1. Autentikasi Google Sheet & Drive API
    try:
        sa_info = json.loads(sa_key_str)
        if 'private_key' in sa_info:
            sa_info['private_key'] = sa_info['private_key'].replace('\\n', '\n')

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_url(sheet_url).sheet1
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Terhubung ke Google Sheet & Drive API!")
    except Exception as e:
        print(f"❌ GAGAL KONEKSI API: {e}")
        sys.exit(1)

    # 2. Baca Data Sheet
    try:
        data = sheet.get_all_records()
    except Exception as e:
        print(f"❌ GAGAL MEMBACA DATA SHEET: {e}")
        sys.exit(1)

    row_index = 2
    found = False
    has_error = False

    for row in data:
        approve_val = None
        for key in row.keys():
            if 'approve' in str(key).lower():
                approve_val = row[key]
                break
        
        is_approved = str(approve_val).strip().upper() in ['TRUE', '1', 'YES'] if approve_val is not None else False
        status = str(row.get('Status Proses', '')).strip().upper()

        if is_approved and status not in ['SELESAI', 'GAGAL', 'PROSES...']:
            found = True
            link_video = str(row.get('Link Video', '')).strip()
            judul = str(row.get('Judul', f'Video_{row_index}')).strip()

            print(f"\n🎬 Memproses Baris {row_index}: {judul}")
            sheet.update_cell(row_index, 6, 'PROSES...')

            file_id = extract_drive_id(link_video)
            if not file_id:
                print("❌ Kolom Link Video BUKAN Link Google Drive!")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True
                row_index += 1
                continue

            input_raw = f"raw_{row_index}.mp4"
            output_clip = f"clip_{row_index}.mp4"

            # 3. Unduh File Mentahan dari Drive
            print(f"⏳ Mengunduh mentahan dari Drive (ID: {file_id})...")
            try:
                request = drive_service.files().get_media(fileId=file_id)
                fh = io.FileIO(input_raw, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status_dl, done = downloader.next_chunk()
                    print(f"   Download progress: {int(status_dl.progress() * 100)}%.")
            except Exception as e:
                print(f"❌ Gagal unduh mentahan: {e}")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True
                row_index += 1
                continue

            # 4. Potong Format 9:16 (Detik 10 s/d 40)
            print("✂️ Mulai memotong video ke format 9:16...")
            ffmpeg_cmd = f"""
            ffmpeg -y -i "{input_raw}" -ss 00:00:10 -t 00:00:30 \
            -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
            [0:v]scale=1080:-1[fg]; [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
            -c:v libx264 -c:a aac "{output_clip}"
            """
            subprocess.run(ffmpeg_cmd, shell=True, capture_output=True)

            # 5. Kirim Hasil Potongan ke Telegram Chat
            if os.path.exists(output_clip) and os.path.getsize(output_clip) > 0:
                caption_text = f"🎬 *{judul}*\n✅ Klip 9:16 berhasil dipotong!"
                success = send_telegram_video(telegram_token, telegram_chat_id, output_clip, caption_text)
                
                if success:
                    sheet.update_cell(row_index, 6, 'SELESAI')
                else:
                    sheet.update_cell(row_index, 6, 'GAGAL')
                    has_error = True
            else:
                print(f"❌ Gagal Render FFmpeg!")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True

            # Bersihkan file sampah
            for temp_f in [input_raw, output_clip]:
                if os.path.exists(temp_f):
                    os.remove(temp_f)

        row_index += 1

    if not found:
        print("ℹ️ Tidak ada antrean video ter-centang/approve di Sheet.")

    if has_error:
        sys.exit(1)

if __name__ == '__main__':
    main()
