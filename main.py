import os
import json
import sys
import subprocess
import requests
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pytubefix import YouTube

def download_video_robust(link_video, output_path):
    print("⏳ [Engine 1] PyTubeFix (Bypass PO Token)...")
    try:
        # use_po_token=True adalah kunci menembus blokir YouTube di GitHub Actions
        yt = YouTube(link_video, use_po_token=True)
        ys = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not ys:
            ys = yt.streams.get_highest_resolution()
        
        ys.download(filename=output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("✅ Engine 1 (PyTubeFix) Sukses!")
            return True
    except Exception as e:
        print(f"⚠️ Engine 1 Error: {e}")

    print("⏳ [Engine 2] Cobalt API v7 (Serverless)...")
    try:
        # Endpoint API Cobalt yang benar (bukan /api/json lagi)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        res = requests.post("https://api.cobalt.tools/", json={"url": link_video}, headers=headers, timeout=30)
        
        if res.status_code == 200 and "url" in res.json():
            with requests.get(res.json()["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("✅ Engine 2 (Cobalt) Sukses!")
                return True
        else:
            print(f"⚠️ Penolakan Engine 2: {res.text}")
    except Exception as e:
        print(f"⚠️ Engine 2 Error: {e}")

    return False

def main():
    print("🤖 Memulai Clay Auto Clipper 24/7 (PO Token Mode)...")
    
    sa_key_str = os.environ.get('GCP_SA_KEY')
    sheet_url = os.environ.get('SPREADSHEET_URL')
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')

    if not sa_key_str or not sheet_url or not drive_folder_id:
        print("❌ ERROR: Secret GCP_SA_KEY, SPREADSHEET_URL, atau DRIVE_FOLDER_ID belum terisi!")
        sys.exit(1)

    try:
        sa_info = json.loads(sa_key_str)
        if 'private_key' in sa_info:
            sa_info['private_key'] = sa_info['private_key'].replace('\\n', '\n')

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_url(sheet_url).sheet1
        print("✅ Terhubung ke Google Sheet!")
    except Exception as e:
        print(f"❌ GAGAL KONEKSI SPREADSHEET: {e}")
        sys.exit(1)

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

            input_raw = f"raw_{row_index}.mp4"
            output_clip = f"clip_{row_index}.mp4"

            # Proses Download Anti-Bot
            if not download_video_robust(link_video, input_raw):
                print("❌ Gagal Download Video dari seluruh Engine!")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True
                row_index += 1
                continue

            # Proses Potong 9:16
            print("✂️ Motong video ke format 9:16...")
            ffmpeg_cmd = f"""
            ffmpeg -y -i "{input_raw}" -ss 00:00:10 -t 00:00:30 \
            -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
            [0:v]scale=1080:-1[fg]; [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
            -c:v libx264 -c:a aac "{output_clip}"
            """
            subprocess.run(ffmpeg_cmd, shell=True, capture_output=True)

            # Upload ke Drive
            if os.path.exists(output_clip) and os.path.getsize(output_clip) > 0:
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    file_metadata = {
                        'name': f"{judul[:15].replace(' ', '_')}_clip.mp4",
                        'parents': [drive_folder_id]
                    }
                    media = MediaFileUpload(output_clip, mimetype='video/mp4')
                    uploaded_file = drive_service.files().create(
                        body=file_metadata, media_body=media, fields='id'
                    ).execute()

                    print(f"🎉 BERHASIL! Video ID Drive: {uploaded_file.get('id')}")
                    sheet.update_cell(row_index, 6, 'SELESAI')
                except Exception as upload_err:
                    print(f"❌ Gagal Upload Drive: {upload_err}")
                    sheet.update_cell(row_index, 6, 'GAGAL')
                    has_error = True
            else:
                print(f"❌ Gagal Render Video!")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True

            # Bersihkan file
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
