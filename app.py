import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta

# ─── CONFIG ───────────────────────────────────────────────
USERNAME = "vae02838"
PASSWORD = "victory"
TIMEOUT_SECONDS = 3600

st.set_page_config(page_title="Lọc Cổ Phiếu VN", page_icon="📈", layout="wide")

# ─── SESSION STATE ────────────────────────────────────────
for k, v in {"logged_in": False, "last_activity": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── AUTH FUNCTIONS ───────────────────────────────────────
def login(u, p):
    if u == USERNAME and p == PASSWORD:
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
        if time.time() - st.session_state.last_activity > TIMEOUT_SECONDS:
            st.session_state.logged_in = False
            st.session_state.last_activity = None
            return True
    return False

# ─── CSS CHUNG ────────────────────────────────────────────
COMMON_CSS = """
<style>
header[data-testid="stHeader"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="InputInstructions"] { display: none !important; }
</style>
"""

# ─── LOGIN PAGE ───────────────────────────────────────────
def show_login(timed_out=False):
    st.markdown(COMMON_CSS + """
    <style>
    .block-container {
        padding-top: 0 !important;
        display: flex; align-items: center;
        justify-content: center; min-height: 100vh;
    }
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
    div[data-baseweb="input"] { border: none !important; box-shadow: none !important; }
    div[data-testid="stFormSubmitButton"] button {
        background-color: #1a73e8 !important; color: white !important;
        border: none !important; border-radius: 6px !important;
        font-size: 15px !important; padding: 10px !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover { background-color: #1558b0 !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if timed_out:
            st.warning("⏰ Phiên đã hết hạn. Vui lòng đăng nhập lại.")
        with st.form("login_form"):
            username = st.text_input("username")
            password = st.text_input("password", type="password")
            if st.form_submit_button("Đăng nhập", use_container_width=True):
                login(username, password)

# ─── DATA FUNCTIONS ───────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def load_all_symbols():
    """Lấy danh sách tất cả mã niêm yết kèm sàn và tên công ty."""
    try:
        from vnstock import Listing
        listing = Listing()
        df = listing.all_symbols(show_log=False)
        return df
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_trading_value(symbols_df, months=1):
    """
    Với mỗi mã, lấy lịch sử giá `months` tháng gần nhất,
    tính GD TB/ngày = mean(close × volume).
    Trả về DataFrame: symbol, organ_name, exchange, avg_value_per_day
    """
    from vnstock import Quote
    end = datetime.today()
    start = end - timedelta(days=30 * months)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")

    results = []
    # Lấy tối đa 700 mã để tránh timeout trên Streamlit Cloud
    sample = symbols_df.head(700)

    for _, row in sample.iterrows():
        sym = row.get("symbol") or row.get("ticker", "")
        name = row.get("organ_name", row.get("company_name", ""))
        exchange = row.get("exchange", row.get("type", ""))
        try:
            q = Quote(symbol=sym, source="KBS")
            hist = q.history(start=start_str, end=end_str, interval="1D", show_log=False)
            if hist is not None and not hist.empty and "close" in hist.columns and "volume" in hist.columns:
                hist["value"] = hist["close"] * hist["volume"]
                trading_days = len(hist)
                total_value = hist["value"].sum()
                avg = total_value / trading_days if trading_days > 0 else 0
                results.append({
                    "Mã": sym,
                    "Tên công ty": name,
                    "Sàn": exchange,
                    "GD TB/ngày (tỷ)": round(avg / 1e9, 2),
                    "Số ngày GD": trading_days,
                    "_avg_raw": avg,
                })
        except Exception:
            continue

    return pd.DataFrame(results)

# ─── MAIN APP ─────────────────────────────────────────────
def show_app():
    update_activity()
    st.markdown(COMMON_CSS + """
    <style>
    .block-container { padding-top: 1.2rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──
    col_title, col_logout = st.columns([8, 1])
    with col_title:
        st.markdown("## 📈 Lọc Cổ Phiếu theo Thanh Khoản")
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Đăng xuất"):
            logout()

    st.markdown("---")

    # ── Bước 1: Số tháng lấy dữ liệu ──
    col1, col2 = st.columns([3, 4])
    with col1:
        st.markdown("#### 📅 Kỳ tính toán")
        months = st.selectbox(
            "Lấy dữ liệu bao nhiêu tháng gần nhất?",
            options=[1, 2, 3],
            index=0,
            format_func=lambda x: f"{x} tháng gần nhất",
        )
        st.caption("GD TB/ngày = Tổng giá trị GD ÷ Số ngày có giao dịch trong kỳ")

    with col2:
        st.markdown("#### 🔍 Ngưỡng thanh khoản tối thiểu")
        threshold_label = st.radio(
            "Chọn mức giá trị giao dịch trung bình mỗi ngày:",
            options=["Trên 200 triệu", "Trên 500 triệu", "Trên 1 tỷ", "Trên 10 tỷ"],
            horizontal=True,
        )

    threshold_map = {
        "Trên 200 triệu": 200_000_000,
        "Trên 500 triệu": 500_000_000,
        "Trên 1 tỷ":      1_000_000_000,
        "Trên 10 tỷ":     10_000_000_000,
    }
    threshold = threshold_map[threshold_label]

    st.markdown("---")

    # ── Nút tải dữ liệu ──
    if st.button("🚀 Tải & Lọc dữ liệu", type="primary"):
        with st.spinner("Đang lấy danh sách mã niêm yết..."):
            symbols_df = load_all_symbols()

        if symbols_df is None or (isinstance(symbols_df, tuple)):
            st.error("❌ Không lấy được danh sách mã. Vui lòng thử lại.")
            return

        st.info(f"📋 Tổng số mã đang xử lý: **{min(len(symbols_df), 700)}** mã (HOSE + HNX + UPCOM)")

        progress = st.progress(0, text="Đang tải dữ liệu giá...")
        with st.spinner(f"Đang tính GD TB/ngày ({months} tháng)... có thể mất 2–4 phút"):
            df_result = fetch_trading_value(symbols_df, months=months)
        progress.progress(100, text="Hoàn tất!")

        if df_result.empty:
            st.warning("⚠️ Không lấy được dữ liệu. Kiểm tra kết nối internet.")
            return

        # Lọc theo ngưỡng
        df_filtered = df_result[df_result["_avg_raw"] >= threshold].drop(columns=["_avg_raw"])
        df_filtered = df_filtered.sort_values("GD TB/ngày (tỷ)", ascending=False).reset_index(drop=True)
        df_filtered.index += 1  # bắt đầu từ 1

        # ── Kết quả ──
        st.markdown(f"### ✅ Kết quả: {len(df_filtered)} mã có GD TB/ngày **{threshold_label}**")

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Tổng mã tìm thấy", len(df_filtered))
        col_m2.metric("Kỳ tính toán", f"{months} tháng")
        col_m3.metric("Ngưỡng lọc", threshold_label)

        st.dataframe(
            df_filtered[["Mã", "Tên công ty", "Sàn", "GD TB/ngày (tỷ)", "Số ngày GD"]],
            use_container_width=True,
            height=500,
        )

        # Nút tải xuống
        csv = df_filtered.to_csv(index=True).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Tải xuống CSV",
            data=csv,
            file_name=f"loc_co_phieu_{threshold_label.replace(' ', '_')}_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    # Auto-refresh check timeout
    st.markdown("""
        <script>setTimeout(function(){window.location.reload();}, 60000);</script>
    """, unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────
timed_out = check_timeout()
if timed_out:
    show_login(timed_out=True)
elif not st.session_state.logged_in:
    show_login()
else:
    show_app()
