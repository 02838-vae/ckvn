import streamlit as st
import time

# ─── CONFIG ───────────────────────────────────────────────
USERNAME = "vae02838"
PASSWORD = "victory"
TIMEOUT_SECONDS = 3600  # 1 giờ = 3600 giây

# ─── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(page_title="My App", page_icon="🔒", layout="centered")

# ─── SESSION STATE INIT ───────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "last_activity" not in st.session_state:
    st.session_state.last_activity = None

# ─── HELPER FUNCTIONS ─────────────────────────────────────
def login(username, password):
    if username == USERNAME and password == PASSWORD:
        st.session_state.logged_in = True
        st.session_state.last_activity = time.time()
        st.rerun()
    else:
        st.error("❌ Sai username hoặc password!")

def logout():
    st.session_state.logged_in = False
    st.session_state.last_activity = None
    st.rerun()

def update_activity():
    st.session_state.last_activity = time.time()

def check_timeout():
    if st.session_state.logged_in and st.session_state.last_activity:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > TIMEOUT_SECONDS:
            st.session_state.logged_in = False
            st.session_state.last_activity = None
            return True  # đã timeout
    return False

# ─── LOGIN PAGE ───────────────────────────────────────────
def show_login():
    st.markdown("""
        <style>
        .login-box {
            max-width: 400px;
            margin: 80px auto 0 auto;
            padding: 2rem;
            border-radius: 12px;
            background: #f8f9fa;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔒 Đăng nhập")
        st.markdown("---")

        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Nhập username...")
            password = st.text_input("🔑 Password", type="password", placeholder="Nhập password...")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submitted:
                login(username, password)

# ─── MAIN APP (sau khi đăng nhập) ────────────────────────
def show_app():
    # Cập nhật activity mỗi khi user tương tác
    update_activity()

    # Tính thời gian còn lại
    elapsed = time.time() - st.session_state.last_activity
    remaining = TIMEOUT_SECONDS - elapsed
    mins = int(remaining // 60)
    secs = int(remaining % 60)

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏠 Trang chính")
    with col2:
        st.markdown(f"<small>⏱ Còn lại: {mins:02d}:{secs:02d}</small>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"):
            logout()

    st.markdown("---")

    # ── NỘI DUNG APP CỦA BẠN Ở ĐÂY ──
    st.success(f"✅ Xin chào, **{USERNAME}**! Bạn đã đăng nhập thành công.")
    st.info("💡 Thêm nội dung app của bạn vào đây.")

    # Auto-refresh mỗi 60 giây để check timeout
    st.markdown("""
        <script>
            setTimeout(function() { window.location.reload(); }, 60000);
        </script>
    """, unsafe_allow_html=True)

# ─── MAIN LOGIC ───────────────────────────────────────────
timed_out = check_timeout()

if timed_out:
    st.warning("⏰ Phiên làm việc đã hết hạn (1 giờ không hoạt động). Vui lòng đăng nhập lại.")
    show_login()
elif not st.session_state.logged_in:
    show_login()
else:
    show_app()
