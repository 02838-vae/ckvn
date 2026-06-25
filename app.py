import streamlit as st
import time

# ─── CONFIG ───────────────────────────────────────────────
USERNAME = "vae02838"
PASSWORD = "victory"
TIMEOUT_SECONDS = 3600  # 1 giờ

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
            return True
    return False

# ─── LOGIN PAGE ───────────────────────────────────────────
def show_login(timed_out=False):
    st.markdown("""
        <style>
        /* Ẩn header mặc định của Streamlit */
        header[data-testid="stHeader"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* Căn giữa toàn trang */
        .block-container {
            padding-top: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }

        /* Ẩn label của input */
        label[data-testid="stWidgetLabel"] { display: none !important; }

        /* Viền xanh cho input */
        input[type="text"], input[type="password"] {
            border: 2px solid #1a73e8 !important;
            border-radius: 6px !important;
            padding: 10px 12px !important;
            font-size: 15px !important;
            outline: none !important;
            box-shadow: none !important;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            border: 2px solid #1a73e8 !important;
            box-shadow: 0 0 0 2px rgba(26,115,232,0.2) !important;
        }

        /* Ẩn placeholder khi focus */
        input:focus::placeholder { color: transparent !important; }

        /* Nút đăng nhập */
        div[data-testid="stFormSubmitButton"] button {
            background-color: #1a73e8 !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            font-size: 15px !important;
            padding: 10px !important;
            cursor: pointer !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #1558b0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if timed_out:
            st.warning("⏰ Phiên đã hết hạn. Vui lòng đăng nhập lại.")

        with st.form("login_form"):
            username = st.text_input("username", placeholder="")
            password = st.text_input("password", type="password", placeholder="")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submitted:
                login(username, password)

# ─── MAIN APP ─────────────────────────────────────────────
def show_app():
    update_activity()

    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container { padding-top: 1rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # Nút đăng xuất góc trên phải
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("Đăng xuất"):
            logout()

    # Auto-refresh mỗi 60 giây để check timeout
    st.markdown("""
        <script>
            setTimeout(function() { window.location.reload(); }, 60000);
        </script>
    """, unsafe_allow_html=True)

    # ── NỘI DUNG APP CỦA BẠN Ở ĐÂY ──


# ─── MAIN LOGIC ───────────────────────────────────────────
timed_out = check_timeout()

if timed_out:
    show_login(timed_out=True)
elif not st.session_state.logged_in:
    show_login()
else:
    show_app()
