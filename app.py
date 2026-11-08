import streamlit as st
import google.generativeai as genai
import os
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Clay AI Clipper | CEO Dashboard", page_icon="✂️", layout="wide")

# --- SISTEM LOGIN PRIVATE ---
def check_password():
    """Mengembalikan True jika password benar."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari session
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 Masukkan Password CEO", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 Masukkan Password CEO", type="password", on_change=password_entered, key="password")
        st.error("❌ Password salah.")
        return False
    return True

if not check_password():
    st.stop()

# --- INISIALISASI GEMINI AI ---
# Mengambil API Key dari rahasia Streamlit
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# --- HEADER DASHBOARD ---
st.title("✂️ Clay Auto Clipper - Executive Dashboard")
st.markdown("Selamat datang, CEO. Pantau radar viral dan setujui klip untuk diproduksi.")

# --- NAVIGASI TAB ---
tab1, tab2, tab3 = st.tabs(["📡 Radar & Scanner", "✂️ Studio Analisis", "📂 Content Vault"])

with tab1:
    st.header("🔍 Manual Link Scanner")
    st.write("Masukkan link podcast (YouTube) untuk dianalisis AI sebelum dipotong.")
    
    video_url = st.text_input("🔗 Link Video YouTube:")
    
    if st.button("🧠 Analisis Potensi Viral"):
        if video_url:
            with st.spinner("AI sedang membedah transkrip dan mencari Hook..."):
                time.sleep(2) # Simulasi proses ekstraksi
                
                # Simulasi prompt ke Gemini (Nantinya akan disambungkan dengan transkrip asli)
                prompt = f"Berikan analisis simulasi untuk video podcast ini terkait potensi viralnya di TikTok, berikan skor 0-100, alasan, timestamp imajiner, dan ide caption: {video_url}"
                response = ai_model.generate_content(prompt)
                
                st.session_state['last_analysis'] = response.text
                st.session_state['ready_to_approve'] = True
                st.success("✅ Analisis Selesai! Buka tab 'Studio Analisis' untuk melihat hasil.")
        else:
            st.warning("⚠️ Masukkan link terlebih dahulu.")

    st.divider()
    st.header("📈 Auto-Radar Feed (Coming Soon)")
    st.info("Sistem scraper otomatis sedang memantau channel Timothy Ronald & Leo Clippo. Belum ada lonjakan trafik signifikan dalam 24 jam terakhir.")

with tab2:
    st.header("📊 AI Virality Analysis")
    
    if 'last_analysis' in st.session_state:
        st.markdown("### 📋 Hasil Bedah AI:")
        st.write(st.session_state['last_analysis'])
        
        st.divider()
        st.markdown("### ⚙️ Executive Action")
        
        col1, col2 = st.columns(2)
        with col1:
            revisi = st.text_area("✏️ Instruksi Revisi (Opsional):", placeholder="Contoh: Majukan potongan ke detik 04:10...")
        
        with col2:
            st.write(" ")
            st.write(" ")
            if st.button("🚀 APPROVE & RENDER KLIP", type="primary", use_container_width=True):
                st.info("⏳ Memulai proses rendering 9:16 dan pemasangan subtitle di server... (Proses ini memakan waktu beberapa menit).")
                # Logika pemicu FFmpeg/GitHub Actions akan diletakkan di sini
                time.sleep(3)
                st.success("🎉 Berhasil! Video masuk ke Content Vault.")
    else:
        st.write("Belum ada video yang dianalisis. Silakan gunakan fitur Scanner di tab pertama.")

with tab3:
    st.header("📦 Content Vault (Stok Cuan)")
    st.write("Semua video yang sudah selesai di-render dan siap di-upload ke TikTok/Instagram.")
    st.info("Belum ada klip yang dirender hari ini.")
    # Nantinya video .mp4 akan muncul di sini dengan tombol st.download_button()
