# auth.py
import streamlit as st
import bcrypt
import time
from config import USERS, SESSION_TIMEOUT_SECONDS

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def check_session_timeout():
    """Kiểm tra nếu quá 1h không thao tác → tự động logout"""
    if "last_activity" in st.session_state:
        elapsed = time.time() - st.session_state["last_activity"]
        if elapsed > SESSION_TIMEOUT_SECONDS:
            logout()
            st.warning("⏰ Phiên làm việc đã hết hạn sau 1 giờ không hoạt động.")
            st.stop()
    # Cập nhật thời gian thao tác mới nhất
    st.session_state["last_activity"] = time.time()

def login_form():
    """Hiển thị form đăng nhập"""
    st.markdown("## 🔐 Đăng nhập")
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập")
        if submitted:
            if username in USERS and verify_password(password, USERS[username]):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["last_activity"] = time.time()
                st.rerun()
            else:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")

def logout():
    """Xóa session"""
    for key in ["authenticated", "username", "last_activity"]:
        st.session_state.pop(key, None)

def require_auth():
    """Gọi ở đầu mỗi page để bắt buộc đăng nhập"""
    if not st.session_state.get("authenticated"):
        login_form()
        st.stop()
    check_session_timeout()
