import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from cryptography.fernet import Fernet
from streamlit_autorefresh import st_autorefresh
import uuid

# 🌐 Supabase 연결
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ENCRYPTION_KEY = st.secrets["ENCRYPTION_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
cipher = Fernet(ENCRYPTION_KEY)

# 🔁 2초마다 자동 새로고침
st_autorefresh(interval=2000, key="refresh")

# 📄 기본 설정
st.set_page_config(page_title="🔐 암호화 채팅", layout="centered")
st.title("🔐 암호화 채팅 앱")

# 👤 닉네임 입력
if "username" not in st.session_state:
    username = st.text_input("닉네임을 입력하세요")
    if st.button("입장") and username.strip():
        st.session_state.username = username
        st.rerun()
    st.stop()

# 💬 메시지 입력
message = st.text_input("메시지를 입력하세요", key="msg_input")
if st.button("전송") and message.strip():
    try:
        encrypted_message = cipher.encrypt(message.encode()).decode()
        supabase.table("messages").insert({
            "id": str(uuid.uuid4()),
            "username": st.session_state.username,
            "message": encrypted_message,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        st.rerun()
    except Exception as e:
        st.error("❌ 메시지 전송 중 오류 발생")
        st.exception(e)
        st.stop()

# 📜 메시지 출력
st.subheader("💬 채팅 내역")
try:
    response = supabase.table("messages").select("*").order("timestamp").execute()
    for msg in response.data:
        try:
            decrypted_message = cipher.decrypt(msg["message"].encode()).decode()
        except Exception:
            decrypted_message = "⚠️ 복호화 실패"
        st.markdown(f"**[{msg['username']}]**: {decrypted_message}")
except Exception as e:
    st.error("❌ 메시지 불러오기 실패")
    st.exception(e)
