import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid
import time

# ✅ Supabase secrets는 Streamlit Cloud 웹 UI에서 설정해야 함!
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="💬 실시간 채팅", layout="centered")
st.title("💬 실시간 채팅 앱")

# 사용자 닉네임 받기
if "username" not in st.session_state:
    username = st.text_input("닉네임을 입력하세요")
    if st.button("입장") and username.strip():
        st.session_state.username = username
        st.experimental_rerun()
    st.stop()

# 메시지 입력
message = st.text_input("메시지를 입력하세요", key="msg_input")
if st.button("전송") and message.strip():
    supabase.table("messages").insert({
        "id": str(uuid.uuid4()),
        "username": st.session_state.username,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()
    st.experimental_rerun()

# 메시지 출력
st.subheader("💬 채팅 내역")
data = supabase.table("messages").select("*").order("timestamp").execute()
for msg in data.data:
    st.markdown(f"**[{msg['username']}]**: {msg['message']}")

# 1초마다 새로고침
time.sleep(1)
st.experimental_rerun()
