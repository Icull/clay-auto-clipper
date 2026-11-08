import os
import json
import sys
import subprocess
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    print("🤖 Memulai Clay Auto Clipper 24/7 (Authenticated Mode)...")
    
    sa_key_str = os.environ.get('GCP_SA_KEY')
    sheet_url = os.environ.get('SPREADSHEET_URL')
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')
    youtube_cookies = os.environ.get('YOUTUBE_COOKIES')

    if not sa_key_str or not sheet_url or not drive_folder_id:
        print("❌ ERROR: Secret GCP_SA_KEY, SPREADSHEET_URL, atau DRIVE_FOLDER_ID belum terisi!")
        sys.exit(1)

    # Menyiapkan file cookies sementara jika ada
    cookie_file = "youtube_cookies.txt"
    use_cookies = False
    if youtube_cookies and len(youtube_cookies.strip()) > 0:
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(youtube_cookies)
        use_cookies = True
        print("🔑 Cookies YouTube resmi terdeteksi dan dimuat!")

    # 1. Autentikasi Google Sheet & Drive
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

    # 2. Baca Data Sheet
    try:
        data = sheet.get_all_records()
        print(f"📊 Berhasil membaca {len(data)} baris data dari Google Sheet.")
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
            print(f"🔗 Link: {link_video}")
            sheet.update_cell(row_index, 6, 'PROSES...')

            input_raw = f"raw_{row_index}.mp4"
            output_clip = f"clip_{row_index}.mp4"

            # Command Unduh dengan Cookies Resmi
            cookie_arg = f'--cookies "{cookie_file}"' if use_cookies else ''
            dl_cmd = f'yt-dlp {cookie_arg} -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --no-playlist -o "{input_raw}" "{link_video}"'
            
            print("⏳ Downloading video dari YouTube...")
            dl_res = subprocess.run(dl_cmd, shell=True, capture_output=True, text=True)

            if not os.path.exists(input_raw) or os.path.getsize(input_raw) == 0:
                print(f"❌ Gagal Download Video! Detail:\n{dl_res.stderr[-400:]}")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True
                row_index += 1
                continue

            # Step B: Potong 9:16 (Detik 10 s/d 40) via FFmpeg
            print("✂️ Motong video ke format 9:16...")
            ffmpeg_cmd = f"""
            ffmpeg -y -i "{input_raw}" -ss 00:00:10 -t 00:00:30 \
            -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
            [0:v]scale=1080:-1[fg]; [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
            -c:v libx264 -c:a aac "{output_clip}"
            """
            ff_res = subprocess.run(ffmpeg_cmd, shell=True, capture_output=True, text=True)

            # Step C: Upload ke Google Drive
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
                print(f"❌ Gagal Render Video! Detail:\n{ff_res.stderr[-400:]}")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True

            # Clean temporary files
            for temp_f in [input_raw, output_clip, cookie_file]:
                if os.path.exists(temp_f):
                    os.remove(temp_f)

        row_index += 1

    if not found:
        print("ℹ️ Tidak ada antrean video ter-centang/approve di Sheet.")

    if has_error:
        sys.exit(1)

if __name__ == '__main__':
    main()
