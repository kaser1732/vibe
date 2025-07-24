import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from cryptography.fernet import Fernet
from streamlit_autorefresh import st_autorefresh
import uuid
import json

# 🔐 Supabase 및 암호화 키
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ENCRYPTION_KEY = st.secrets["ENCRYPTION_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
cipher = Fernet(ENCRYPTION_KEY)

# 🔁 2초마다 새로고침
st_autorefresh(interval=2000, key="autorefresh")

# 🖼 UI 기본 설정
st.set_page_config(page_title="Chatting", layout="centered")
st.title("🔐 Chatting")


# 🚪 나가기 함수 정의
def exit_user():
    username = st.session_state.get("username")
    if not username:
        return

    # 1. 현재 유저 삭제
    supabase.table("active_users").delete().eq("username", username).execute()

    # 2. 남은 유저 확인
    active = supabase.table("active_users").select("*").execute().data
    if len(active) == 0:
        # 3. 모두 나간 경우 → 메시지 저장
        messages = supabase.table("messages").select("*").execute().data
        if messages:
            supabase.table("chat_logs").insert({
                "id": str(uuid.uuid4()),
                "logs": json.dumps(messages),
                "saved_at": datetime.utcnow().isoformat()
            }).execute()

            # 4. 메시지 테이블 비우기
            supabase.table("messages").delete().neq("id", "").execute()

    # 5. 세션 초기화
    del st.session_state["username"]
    st.success("👋 채팅방을 나갔습니다.")
    st.rerun()


# 👤 입장 로직 (최대 3명 제한)
if "username" not in st.session_state:
    username = st.text_input("닉네임을 입력하세요")
    if st.button("입장") and username.strip():
        active = supabase.table("active_users").select("*").execute().data
        if len(active) >= 3:
            st.error("❌ 현재 채팅방 정원은 3명입니다.")
            st.stop()

        supabase.table("active_users").upsert({
            "username": username,
            "joined_at": datetime.utcnow().isoformat()
        }).execute()
        st.session_state["username"] = username
        st.rerun()
    st.stop()


# ✅ 현재 유저 정보
st.markdown(f"👋 안녕하세요, **{st.session_state['username']}** 님!")

# 🚪 나가기 버튼
if st.button("🚪 나가기"):
    exit_user()
    st.stop()

# 💬 메시지 입력 및 전송
message = st.text_input("메시지를 입력하세요", key="msg_input")
if st.button("전송") and message.strip():
    try:
        encrypted = cipher.encrypt(message.encode()).decode()
        supabase.table("messages").insert({
            "id": str(uuid.uuid4()),
            "username": st.session_state.username,
            "message": encrypted,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        st.experimental_set_query_params(msg_input="")  # 메시지 초기화
        st.rerun()
    except Exception as e:
        st.error("❌ 메시지 전송 중 오류")
        st.exception(e)
        st.stop()

# 📜 메시지 출력
st.subheader("💬 채팅 내역")
try:
    response = supabase.table("messages").select("*").order("timestamp").execute()
    for msg in response.data:
        try:
            decrypted = cipher.decrypt(msg["message"].encode()).decode()
        except Exception:
            decrypted = "⚠️ 복호화 실패"
        st.markdown(f"**[{msg['username']}]**: {decrypted}")
except Exception as e:
    st.error("❌ 메시지 불러오기 실패")
    st.exception(e)
