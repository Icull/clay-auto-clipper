import os
import io
import json
import sys
import re
import subprocess
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

DRIVE_FOLDER_ID_HARDCODED = "11UbjlQiPdQ3nkLrelQL57R234r37mfuX"

def extract_drive_id(url):
    match = re.search(r'[-\w]{25,}', url)
    return match.group(0) if match else None

def main():
    print("🤖 Memulai Clay Auto Clipper 24/7 (AUTHENTICATED DRIVE RENDER ENGINE)...")
    
    sa_key_str = os.environ.get('GCP_SA_KEY')
    sheet_url = os.environ.get('SPREADSHEET_URL')
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID') or DRIVE_FOLDER_ID_HARDCODED

    if not sa_key_str or not sheet_url:
        print("❌ ERROR: Secret GCP_SA_KEY atau SPREADSHEET_URL belum terisi!")
        sys.exit(1)

    # 1. Koneksi Service Account
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
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Terhubung ke Google Sheet & Drive API!")
    except Exception as e:
        print(f"❌ GAGAL KONEKSI API: {e}")
        sys.exit(1)

    # 2. Baca Data Spreadsheet
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

            # 3. Unduh Mentahan dari Drive (Bypass Izin via supportsAllDrives)
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

            # 4. Potong Format 9:16 (detik 10 s/d 40)
            print("✂️ Mulai memotong video ke format 9:16...")
            ffmpeg_cmd = f"""
            ffmpeg -y -i "{input_raw}" -ss 00:00:10 -t 00:00:30 \
            -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
            [0:v]scale=1080:-1[fg]; [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
            -c:v libx264 -c:a aac "{output_clip}"
            """
            subprocess.run(ffmpeg_cmd, shell=True, capture_output=True)

            # 5. Upload Hasil Potong ke Drive Target (KUNCI FIX: supportsAllDrives=True)
            if os.path.exists(output_clip) and os.path.getsize(output_clip) > 0:
                try:
                    file_metadata = {
                        'name': f"{judul[:15].replace(' ', '_')}_clip.mp4",
                        'parents': [drive_folder_id]
                    }
                    media = MediaFileUpload(output_clip, mimetype='video/mp4')
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id',
                        supportsAllDrives=True,
                        supportsTeamDrives=True
                    ).execute()

                    print(f"🎉 BERHASIL! Video hasil potong ID Drive: {uploaded_file.get('id')}")
                    sheet.update_cell(row_index, 6, 'SELESAI')
                except Exception as upload_err:
                    print(f"❌ Gagal Upload Hasil ke Drive: {upload_err}")
                    sheet.update_cell(row_index, 6, 'GAGAL')
                    has_error = True
            else:
                print(f"❌ Gagal Render FFmpeg!")
                sheet.update_cell(row_index, 6, 'GAGAL')
                has_error = True

            # Bersihkan file lokal
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
