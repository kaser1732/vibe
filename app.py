import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from cryptography.fernet import Fernet
from streamlit_autorefresh import st_autorefresh
import uuid
import json
import socket

# --------------------------
# 🔐 Supabase & 암호화 설정
# --------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ENCRYPTION_KEY = st.secrets["ENCRYPTION_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
cipher = Fernet(ENCRYPTION_KEY)

# --------------------------
# ⏱ 자동 새로고침 (2초)
# --------------------------
st_autorefresh(interval=2000, key="autorefresh")

st.set_page_config(page_title="Chatting", layout="centered")
st.title("Chatting")

# --------------------------
# 🚪 나가기 로직
# --------------------------
def exit_user():
    username = st.session_state.get("username")
    ip = st.session_state.get("ip")
    if not username or not ip:
        return

    try:
        supabase.table("active_users").delete().match({"username": username, "ip": ip}).execute()
    except Exception as e:
        st.error("❌ 나가기 처리 중 오류 발생")
        st.exception(e)
        return

    active = supabase.table("active_users").select("*").execute().data

    if len(active) == 0:
        messages = supabase.table("messages").select("*").execute().data
        if messages:
            supabase.table("chat_logs").insert({
                "id": str(uuid.uuid4()),
                "logs": json.dumps(messages),
                "saved_at": datetime.utcnow().isoformat()
            }).execute()
            supabase.table("messages").delete().neq("id", "").execute()

    del st.session_state["username"]
    del st.session_state["ip"]
    st.toast("👋 채팅방을 나갔습니다.", icon="✅")
    st.rerun()

# --------------------------
# 사용자 IP 가져오기
# --------------------------
def get_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return str(uuid.uuid4())  # fallback unique ID

# --------------------------
# 👤 닉네임 입력 (3명 + 중복 IP 제한)
# --------------------------
if "username" not in st.session_state:
    username = st.text_input("닉네임을 입력하세요")
    if st.button("입장") and username.strip():
        user_ip = get_ip()
        st.session_state["ip"] = user_ip

        try:
            active = supabase.table("active_users").select("*").execute().data
        except Exception as e:
            st.error("❌ 사용자 정보 확인 중 오류 발생")
            st.exception(e)
            st.stop()

        if any(u.get("ip") == user_ip for u in active):
            st.toast("❌ 동일한 기기(IP)에서는 중복 접속할 수 없습니다.", icon="⚠️")
            st.stop()

        if len(active) >= 3:
            st.toast("❌ 채팅방 정원은 최대 3명입니다. 잠시 후 다시 시도해주세요.", icon="⚠️")
            st.stop()

        try:
            supabase.table("active_users").upsert({
                "username": username,
                "ip": user_ip,
                "joined_at": datetime.utcnow().isoformat()
            }).execute()
            st.session_state["username"] = username
            st.rerun()
        except Exception as e:
            st.error("❌ 사용자 등록 중 오류 발생")
            st.exception(e)
            st.stop()
    st.stop()

# --------------------------
# 🚪 나가기 버튼
# --------------------------
st.markdown(f"👋 안녕하세요, **{st.session_state['username']}** 님!")
if st.button("🚪 나가기"):
    exit_user()
    st.stop()

# --------------------------
# 👥 현재 접속자 목록 표시
# --------------------------
st.subheader("👥 현재 접속자")
try:
    active_users = supabase.table("active_users").select("username, joined_at").order("joined_at").execute().data
    for user in active_users:
        st.markdown(f"• **{user['username']}** (입장: {user['joined_at'].split('T')[1][:8]})")
except Exception as e:
    st.warning("접속자 정보를 불러오지 못했습니다.")

# --------------------------
# 💬 메시지 전송
# --------------------------
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
        st.rerun()
    except Exception as e:
        st.error("❌ 메시지 전송 중 오류")
        st.exception(e)
        st.stop()

# --------------------------
# 📜 메시지 출력
# --------------------------
st.subheader("💬 채팅 내역")
try:
    response = supabase.table("messages").select("*").order("timestamp").execute()
    for msg in response.data:
        try:
            decrypted = cipher.decrypt(msg["message"].encode()).decode()
        except Exception:
            decrypted = "⚠️ 보호화 실패"
        st.markdown(f"**[{msg['username']}]**: {decrypted}")
except Exception as e:
    st.error("❌ 메시지 불러오기 실패")
    st.exception(e)

# --------------------------
# 🔍 디버그
# --------------------------
st.markdown("---")
try:
    st.write(f"**현재 접속자 수:** {len(supabase.table('active_users').select('*').execute().data)}")
    st.write(f"**현재 메시지 수:** {len(supabase.table('messages').select('*').execute().data)}")
except:
    pass
