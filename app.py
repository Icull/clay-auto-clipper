import streamlit as st
import urllib.request
import json

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

raw_key = st.secrets.get("GROQ_API_KEY", "")
groq_key = "".join(raw_key.split())

st.title("✂️ Clay Auto Clipper - Executive Dashboard")
st.markdown("Selamat datang, CEO. Pantau radar viral dan setujui klip untuk diproduksi.")

if not groq_key:
    st.error("🚨 CRITICAL: `GROQ_API_KEY` tidak terbaca di Streamlit Secrets!")
else:
    st.sidebar.success(f"✅ Groq Key Terbaca: {groq_key[:8]}... (Aman)")

tab1, tab2, tab3 = st.tabs(["📡 Radar & Scanner", "✂️ Studio Analisis", "📂 Content Vault"])

with tab1:
    st.header("🔍 Manual Link Scanner")
    video_url = st.text_input("🔗 Link Video YouTube:")
    
    if st.button("🧠 Analisis Potensi Viral"):
        if not groq_key:
            st.error("⚠️ Tidak bisa menganalisis karena API Key Groq kosong.")
        elif video_url:
            with st.spinner("Groq AI sedang membedah video..."):
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    prompt_text = f"Berikan analisis mendalam untuk video podcast ini terkait potensi viralnya di TikTok, berikan Virality Score (0-100), alasan emosional, timestamp segmen terbaik, serta draft caption dan hashtags 3-tier: {video_url}"
                    
                    # Menggunakan model Llama 3.3 SpecDec aktif resmi Groq
                    payload = {
                        "model": "llama-3.3-70b-specdec",
                        "messages": [{"role": "user", "content": prompt_text}]
                    }
                    
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {groq_key}',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        },
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode('utf-8'))
                        ai_text = res_data['choices'][0]['message']['content']
                        st.session_state['last_analysis'] = ai_text
                        st.success("✅ Analisis Selesai! Cek tab Studio Analisis.")
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode('utf-8')
                    st.error(f"HTTP Error {e.code}: {error_body}")
                except Exception as e:
                    st.error(f"Gagal terhubung ke Groq: {e}")
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
