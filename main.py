import os
import json
import subprocess
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    print("🤖 Memulai Bot Clay Auto Clipper 24/7...")
    
    sa_key_str = os.environ.get('GCP_SA_KEY')
    sheet_url = os.environ.get('SPREADSHEET_URL')
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')

    if not sa_key_str or not sheet_url or not drive_folder_id:
        print("❌ Error: Secrets environment belum lengkap.")
        return

    try:
        sa_info = json.loads(sa_key_str)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_url(sheet_url).sheet1
        print("✅ Berhasil konek ke Google Sheet!")
    except Exception as e:
        print(f"❌ Gagal koneksi Google Sheet: {e}")
        return

    try:
        data = sheet.get_all_records()
    except Exception as e:
        print(f"❌ Gagal membaca data sheet: {e}")
        return

    row_index = 2
    found_any = False

    for row in data:
        # Fleksibel membaca header 'Approve?' maupun 'Approve? (Centang)'
        approve_val = row.get('Approve?', row.get('Approve? (Centang)', ''))
        is_approved = str(approve_val).strip().upper() == 'TRUE'
        status = str(row.get('Status Proses', '')).strip().upper()

        if is_approved and status not in ['SELESAI', 'GAGAL', 'PROSES...']:
            found_any = True
            link_video = row.get('Link Video', '')
            judul = row.get('Judul', f'Video_{row_index}')

            print(f"\n🎬 Memproses Video: {judul}")
            sheet.update_cell(row_index, 6, 'PROSES...')

            temp_output = f"clip_{row_index}.mp4"

            ffmpeg_cmd = f"""
            ffmpeg -y -i $(yt-dlp -g -f bestvideo "{link_video}") -i $(yt-dlp -g -f bestaudio "{link_video}") -ss 00:00:10 -t 00:00:30 \
            -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
            [0:v]scale=1080:-1[fg]; [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
            -c:v libx264 -c:a aac "{temp_output}"
            """

            res = subprocess.run(ffmpeg_cmd, shell=True, capture_output=True, text=True)

            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    file_metadata = {
                        'name': f"{judul[:15].replace(' ', '_')}_clip.mp4",
                        'parents': [drive_folder_id]
                    }
                    media = MediaFileUpload(temp_output, mimetype='video/mp4')
                    uploaded_file = drive_service.files().create(
                        body=file_metadata, media_body=media, fields='id'
                    ).execute()

                    print(f"✅ Sukses! Video berhasil masuk Drive (ID: {uploaded_file.get('id')})")
                    sheet.update_cell(row_index, 6, 'SELESAI')
                except Exception as upload_err:
                    print(f"❌ Upload Error: {upload_err}")
                    sheet.update_cell(row_index, 6, 'GAGAL')

                if os.path.exists(temp_output):
                    os.remove(temp_output)
            else:
                print(f"❌ Render Error:\n{res.stderr[-300:]}")
                sheet.update_cell(row_index, 6, 'GAGAL')

        row_index += 1

    if not found_any:
        print("ℹ️ Tidak ada antrean video ter-approve.")

if __name__ == '__main__':
    main()
