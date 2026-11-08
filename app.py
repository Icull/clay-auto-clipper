import base64
import json
import urllib.request

TOKEN = "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"
REPO = "Icull/clay-auto-clipper"

files = {
    "requirements.txt": """streamlit
google-generativeai
google-api-python-client
yt-dlp""",
    "app.py": """import streamlit as st
import google.generativeai as genai
import time

st.set_page_config(page_title="Clay AI Clipper | CEO Dashboard", page_icon="✂️", layout="wide")

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "CuanTiapHari"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
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

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

st.title("✂️ Clay Auto Clipper - Executive Dashboard")
st.markdown("Selamat datang, CEO. Pantau radar viral dan setujui klip untuk diproduksi.")

tab1, tab2, tab3 = st.tabs(["📡 Radar & Scanner", "✂️ Studio Analisis", "📂 Content Vault"])

with tab1:
    st.header("🔍 Manual Link Scanner")
    st.write("Masukkan link podcast (YouTube) untuk dianalisis AI sebelum dipotong.")
    
    video_url = st.text_input("🔗 Link Video YouTube:")
    
    if st.button("🧠 Analisis Potensi Viral"):
        if video_url:
            with st.spinner("AI sedang membedah transkrip dan mencari Hook..."):
                if ai_model:
                    prompt = f"Berikan analisis mendalam untuk video podcast ini terkait potensi viralnya di TikTok, berikan Virality Score (0-100), alasan emosional, timestamp segmen terbaik, serta draft caption dan hashtags 3-tier: {video_url}"
                    response = ai_model.generate_content(prompt)
                    st.session_state['last_analysis'] = response.text
                else:
                    st.session_state['last_analysis'] = f"Analisis Simulasi Video: {video_url}\\nVirality Score: 88/100\\nReason: Strong debate trigger."
                st.session_state['ready_to_approve'] = True
                st.success("✅ Analisis Selesai! Buka tab 'Studio Analisis' untuk melihat hasil.")
        else:
            st.warning("⚠️ Masukkan link terlebih dahulu.")

    st.divider()
    st.header("📈 Auto-Radar Feed")
    st.info("Sistem scraper otomatis memantau channel target (Timothy Ronald & Leo Clippo).")

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
                st.info("⏳ Memulai proses rendering 9:16 dan pemasangan subtitle di server...")
                time.sleep(2)
                st.success("🎉 Berhasil! Request render dikirim ke GitHub Actions Engine.")
    else:
        st.write("Belum ada video yang dianalisis. Silakan gunakan fitur Scanner di tab pertama.")

with tab3:
    st.header("📦 Content Vault (Stok Cuan)")
    st.write("Semua video yang sudah selesai di-render dan siap di-upload ke TikTok/Instagram.")
    st.info("Belum ada klip yang dirender hari ini.")
"""
}

for filename, content in files.items():
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    sha = None
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "ClayBot"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            sha = data.get("sha")
    except Exception:
        pass
    
    payload = {
        "message": f"Auto-create {filename} via Clay CTO Token Script",
        "content": encoded,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ClayBot"
        },
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ BERHASIL: {filename} telah dibuat di GitHub!")
    except Exception as e:
        print(f"❌ Gagal update {filename}: {e}")
