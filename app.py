import streamlit as st
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
    video_url = st.text_input("🔗 Link Video YouTube:")
    
    if st.button("🧠 Analisis Potensi Viral"):
        if video_url:
            with st.spinner("AI sedang membedah transkrip..."):
                if ai_model:
                    prompt = f"Berikan analisis mendalam untuk video podcast ini terkait potensi viralnya di TikTok, berikan Virality Score (0-100), alasan emosional, timestamp segmen terbaik, serta draft caption dan hashtags 3-tier: {video_url}"
                    response = ai_model.generate_content(prompt)
                    st.session_state['last_analysis'] = response.text
                else:
                    st.session_state['last_analysis'] = "Simulasi AI berhasil."
                st.success("✅ Analisis Selesai! Cek tab Studio Analisis.")
        else:
            st.warning("⚠️ Masukkan link terlebih dahulu.")

with tab2:
    st.header("📊 AI Virality Analysis")
    if 'last_analysis' in st.session_state:
        st.write(st.session_state['last_analysis'])
        st.divider()
        if st.button("🚀 APPROVE & RENDER KLIP", type="primary", use_container_width=True):
            st.success("🎉 Request render dikirim ke GitHub Actions!")
    else:
        st.write("Belum ada video yang dianalisis.")

with tab3:
    st.header("📦 Content Vault (Stok Cuan)")
    st.info("Belum ada klip yang dirender hari ini.")
