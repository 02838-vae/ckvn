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

# ─── AUTH ─────────────────────────────────────────────────
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

# ─── CSS ──────────────────────────────────────────────────
COMMON_CSS = """
<style>
header[data-testid="stHeader"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="InputInstructions"] { display: none !important; }
</style>
"""

# ─── LOGIN ────────────────────────────────────────────────
def show_login(timed_out=False):
    st.markdown(COMMON_CSS + """
    <style>
    .block-container { padding-top:0!important; display:flex; align-items:center; justify-content:center; min-height:100vh; }
    input[type="text"], input[type="password"] {
        border:2px solid #1a73e8!important; border-radius:6px!important;
        padding:10px 12px!important; font-size:15px!important;
        outline:none!important; box-shadow:none!important;
    }
    input[type="text"]:focus, input[type="password"]:focus {
        border:2px solid #1a73e8!important;
        box-shadow:0 0 0 2px rgba(26,115,232,0.2)!important;
    }
    div[data-baseweb="input"] { border:none!important; box-shadow:none!important; }
    div[data-testid="stFormSubmitButton"] button {
        background-color:#1a73e8!important; color:white!important;
        border:none!important; border-radius:6px!important;
        font-size:15px!important; padding:10px!important;
    }
    div[data-testid="stFormSubmitButton"] button:hover { background-color:#1558b0!important; }
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

# ─── DATA: lấy danh sách mã + sàn ────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_all_symbols():
    """Trả về DataFrame với cột: symbol, organ_name, exchange"""
    try:
        from vnstock import Listing
        df = Listing().all_symbols(show_log=False)
        # Chuẩn hóa tên cột
        df.columns = [c.lower() for c in df.columns]
        sym_col   = next((c for c in df.columns if "symbol" in c or "ticker" in c), None)
        name_col  = next((c for c in df.columns if "organ" in c or "company" in c or "name" in c), None)
        exch_col  = next((c for c in df.columns if "exchange" in c or "type" in c), None)
        rename = {}
        if sym_col:  rename[sym_col]  = "symbol"
        if name_col: rename[name_col] = "organ_name"
        if exch_col: rename[exch_col] = "exchange"
        df = df.rename(columns=rename)
        keep = [c for c in ["symbol", "organ_name", "exchange"] if c in df.columns]
        return df[keep].dropna(subset=["symbol"]).reset_index(drop=True)
    except Exception as e:
        return None

# ─── DATA: price_board batch (nhanh, 1-2 lần gọi) ────────
@st.cache_data(ttl=900, show_spinner=False)
def get_price_board_batch(symbols_tuple):
    """
    Gọi price_board theo batch 200 mã/lần → nhanh hơn rất nhiều.
    Trả về DataFrame với cột: symbol, match_val (giá trị khớp lệnh hôm nay, VND)
    """
    from vnstock import Trading
    symbols = list(symbols_tuple)
    BATCH = 200
    frames = []
    for i in range(0, len(symbols), BATCH):
        chunk = symbols[i:i+BATCH]
        try:
            t = Trading(source="TCBS", symbol=chunk[0], show_log=False)
            df = t.price_board(symbols=chunk)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception:
            # thử VCI nếu TCBS lỗi
            try:
                t2 = Trading(source="VCI", symbol=chunk[0], show_log=False)
                df2 = t2.price_board(symbols=chunk)
                if df2 is not None and not df2.empty:
                    frames.append(df2)
            except Exception:
                pass
    if not frames:
        return None
    result = pd.concat(frames, ignore_index=True)
    result.columns = [c.lower() for c in result.columns]
    return result

# ─── DATA: lịch sử 1 tháng theo batch (fallback) ─────────
@st.cache_data(ttl=1800, show_spinner=False)
def get_avg_value_history(symbols_tuple, months):
    """
    Fallback: lấy lịch sử giá theo batch nhỏ → tính GD TB/ngày.
    Chỉ dùng khi price_board không có cột giá trị.
    """
    from vnstock import Quote
    end   = datetime.today()
    start = end - timedelta(days=30 * months)
    ss, es = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    rows = []
    for sym in symbols_tuple:
        try:
            q = Quote(symbol=sym, source="KBS")
            h = q.history(start=ss, end=es, interval="1D", show_log=False)
            if h is not None and not h.empty:
                cols = [c.lower() for c in h.columns]
                h.columns = cols
                # tìm cột close/price và volume
                price_c = next((c for c in cols if c in ("close","price","ref")), None)
                vol_c   = next((c for c in cols if "vol" in c), None)
                if price_c and vol_c:
                    avg = (h[price_c] * h[vol_c]).mean()
                    rows.append({"symbol": sym, "match_val": avg})
        except Exception:
            pass
    return pd.DataFrame(rows) if rows else None

# ─── MAIN APP ─────────────────────────────────────────────
def show_app():
    update_activity()
    st.markdown(COMMON_CSS + """
    <style>
    .block-container { padding-top:1rem!important; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    c1, c2 = st.columns([8, 1])
    with c1:
        st.markdown("## 📈 Lọc Cổ Phiếu theo Thanh Khoản")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Đăng xuất"):
            logout()

    st.markdown("---")

    # ── Tùy chọn ──
    col_a, col_b = st.columns([2, 3])
    with col_a:
        st.markdown("#### 📅 Kỳ tính GD TB/ngày")
        months = st.selectbox(
            "Lấy dữ liệu bao nhiêu tháng?",
            [1, 2, 3],
            format_func=lambda x: f"{x} tháng gần nhất"
        )
        st.caption("GD TB/ngày = Tổng giá trị khớp lệnh ÷ số ngày giao dịch")

    with col_b:
        st.markdown("#### 🔍 Ngưỡng thanh khoản tối thiểu")
        threshold_label = st.radio(
            "Chọn mức GD TB/ngày:",
            ["Trên 200 triệu", "Trên 500 triệu", "Trên 1 tỷ", "Trên 10 tỷ"],
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

    if st.button("🚀 Tải & Lọc dữ liệu", type="primary"):
        # Bước 1: danh sách mã
        with st.spinner("Đang lấy danh sách mã niêm yết..."):
            symbols_df = get_all_symbols()

        if symbols_df is None or symbols_df.empty:
            st.error("❌ Không lấy được danh sách mã. Kiểm tra kết nối mạng.")
            return

        all_syms = symbols_df["symbol"].tolist()
        st.info(f"📋 Tổng số mã: **{len(all_syms)}** (HOSE + HNX + UPCOM)")

        # Bước 2: price_board batch — nhanh ~5-15 giây
        with st.spinner("Đang tải bảng giá (batch)... thường xong trong 10–20 giây"):
            pb = get_price_board_batch(tuple(all_syms))

        val_df = None

        if pb is not None and not pb.empty:
            # Tìm cột symbol và cột giá trị
            sym_c = next((c for c in pb.columns if "symbol" in c or "ticker" in c or c == "sym"), None)
            # các tên cột giá trị thường gặp trong TCBS/VCI price board
            val_c = next((c for c in pb.columns if c in (
                "nm_deal_val","deal_val","total_val","match_val",
                "nmtotalval","totalvalue","tradingvalue","value",
                "t_value","trading_value","vol_val"
            )), None)

            if sym_c and val_c:
                val_df = pb[[sym_c, val_c]].copy()
                val_df.columns = ["symbol", "match_val"]
                val_df["match_val"] = pd.to_numeric(val_df["match_val"], errors="coerce").fillna(0)
                # Nếu giá trị là của 1 ngày → dùng thẳng
                # Nếu muốn TB nhiều tháng thì cần fallback history
                st.success(f"✅ Lấy bảng giá thành công: {len(val_df)} mã")
            else:
                st.warning(f"⚠️ Bảng giá không có cột giá trị rõ ràng. Các cột hiện có: {list(pb.columns)}")
                st.info("Đang chuyển sang lấy lịch sử giá (chậm hơn ~2-3 phút)...")

        if val_df is None:
            # Fallback: lịch sử giá
            with st.spinner(f"Đang tính GD TB/ngày từ lịch sử {months} tháng... (~2-3 phút)"):
                hist_df = get_avg_value_history(tuple(all_syms[:600]), months)
            if hist_df is None or hist_df.empty:
                st.error("❌ Không lấy được dữ liệu. Vui lòng thử lại sau.")
                return
            val_df = hist_df
            st.success(f"✅ Tính xong: {len(val_df)} mã")

        # Merge với tên công ty + sàn
        merged = val_df.merge(symbols_df, on="symbol", how="left")
        merged["organ_name"] = merged.get("organ_name", merged["symbol"])
        merged["exchange"]   = merged.get("exchange",   "")

        # Lọc theo ngưỡng
        filtered = merged[merged["match_val"] >= threshold].copy()
        filtered["GD TB/ngày (tỷ)"] = (filtered["match_val"] / 1e9).round(2)
        filtered = filtered.rename(columns={
            "symbol":     "Mã",
            "organ_name": "Tên công ty",
            "exchange":   "Sàn",
        })
        filtered = filtered.sort_values("GD TB/ngày (tỷ)", ascending=False).reset_index(drop=True)
        filtered.index += 1

        # Hiển thị
        st.markdown(f"### ✅ {len(filtered)} mã có GD TB/ngày **{threshold_label}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Số mã tìm thấy", len(filtered))
        c2.metric("Ngưỡng lọc", threshold_label)
        c3.metric("Tổng mã đã quét", len(merged))

        show_cols = [c for c in ["Mã", "Tên công ty", "Sàn", "GD TB/ngày (tỷ)"] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True, height=500)

        csv = filtered[show_cols].to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Tải xuống CSV",
            data=csv,
            file_name=f"loc_cp_{threshold_label.replace(' ','_')}_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    st.markdown("""<script>setTimeout(function(){window.location.reload();},60000);</script>""",
                unsafe_allow_html=True)

# ─── ROUTER ───────────────────────────────────────────────
timed_out = check_timeout()
if timed_out:
    show_login(timed_out=True)
elif not st.session_state.logged_in:
    show_login()
else:
    show_app()
