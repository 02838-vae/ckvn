import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Screener VN",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS: xóa vùng trắng đầu trang + style toàn bộ ─────────────────────────────
st.markdown("""
<style>
  /* Xóa padding/margin mặc định của Streamlit ở đầu trang */
  .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
  #MainMenu, header, footer { visibility: hidden; }
  div[data-testid="stDecoration"] { display: none; }

  /* Nền tối */
  .stApp { background-color: #0d1117; color: #e6edf3; }
  section[data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }

  /* Header nhỏ gọn */
  .app-title {
    font-size: 22px; font-weight: 700; color: #58a6ff;
    letter-spacing: -0.3px; margin: 0 0 2px 0;
  }
  .app-sub { font-size: 13px; color: #8b949e; margin: 0 0 20px 0; }

  /* ── Nút tải dữ liệu lớn ── */
  .load-btn-wrap { display: flex; justify-content: center; padding: 60px 0 20px; }
  .load-hint { text-align:center; color:#8b949e; font-size:13px; margin-top:12px; }

  /* ── Card bộ lọc ── */
  .filter-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 18px 20px 14px;
  }
  .filter-card-title {
    font-size: 12px; font-weight: 700; color: #58a6ff;
    text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 12px;
  }

  /* ── Buttons chung ── */
  div.stButton > button {
    background: #21262d; color: #e6edf3;
    border: 1px solid #30363d; border-radius: 6px;
    font-weight: 600; padding: 9px 16px;
    transition: all .15s;
  }
  div.stButton > button:hover { background: #30363d; border-color: #58a6ff; color: #58a6ff; }

  /* Nút chính (Tải dữ liệu) */
  .big-btn > div.stButton > button {
    background: #238636 !important; color: white !important;
    border-color: #2ea043 !important;
    font-size: 16px !important; padding: 14px 32px !important;
    border-radius: 8px !important;
  }
  .big-btn > div.stButton > button:hover { background: #2ea043 !important; }

  /* Nút Hiện kết quả */
  .show-btn > div.stButton > button {
    background: #1f6feb !important; color: white !important;
    border-color: #388bfd !important;
    font-size: 15px !important; padding: 12px 28px !important;
    border-radius: 8px !important;
  }
  .show-btn > div.stButton > button:hover { background: #388bfd !important; }

  /* Metric nhỏ */
  .stat-pill {
    display: inline-block; background: #21262d;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 6px 14px; font-size: 13px; margin: 4px 4px 4px 0;
  }
  .stat-pill b { color: #58a6ff; }

  /* Tag thông tin */
  .info-tag {
    font-size: 11px; color: #8b949e;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 4px; padding: 2px 8px; display: inline-block;
  }
</style>
""", unsafe_allow_html=True)

from data_loader import fetch_and_save_all, load_saved_data, get_summary_stats, CACHE_FILE
from filters import apply_filters
from components import render_results_table, render_metrics_bar

import os

# ── Tiêu đề ────────────────────────────────────────────────────────────────────
st.markdown('<p class="app-title">📈 Stock Screener — Việt Nam</p>', unsafe_allow_html=True)
st.markdown('<p class="app-sub">Lọc cổ phiếu HOSE · HNX · UPCOM theo giá trị GD · % tăng/giảm · RSI</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 1 — NÚT TẢI DỮ LIỆU
# ══════════════════════════════════════════════════════════════════════════════
cache_exists = os.path.exists(CACHE_FILE)
cache_time   = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).strftime("%H:%M %d/%m/%Y") if cache_exists else None

# Hiển thị trạng thái cache
if cache_exists:
    st.markdown(
        f'<span class="info-tag">💾 Dữ liệu đã lưu: {cache_time}</span>',
        unsafe_allow_html=True
    )
    col_load, col_reload, col_spacer = st.columns([2, 2, 6])
    with col_load:
        btn_use_cache = st.button("📂 Dùng dữ liệu đã lưu", use_container_width=True)
    with col_reload:
        btn_reload = st.button("🔄 Tải lại từ đầu", use_container_width=True)
    load_triggered = btn_use_cache or btn_reload
    force_reload   = btn_reload
else:
    st.markdown('<div class="load-hint">Chưa có dữ liệu. Nhấn nút bên dưới để bắt đầu.</div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([3, 2, 3])
    with col_c:
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        btn_load = st.button("⬇️  Tải dữ liệu tất cả cổ phiếu", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    load_triggered = btn_load
    force_reload   = True

# ── Xử lý tải ──────────────────────────────────────────────────────────────────
if load_triggered:
    if force_reload:
        with st.spinner("⏳ Đang tải toàn bộ dữ liệu thị trường (HOSE + HNX + UPCOM)..."):
            ok, msg = fetch_and_save_all()
        if ok:
            st.success(f"✅ {msg}")
            st.session_state["data_loaded"] = True
            st.rerun()
        else:
            st.error(f"❌ {msg}")
            st.stop()
    else:
        st.session_state["data_loaded"] = True
        st.rerun()

# Nếu chưa load gì → dừng lại, chỉ hiện nút
if not st.session_state.get("data_loaded", False):
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA TỪ FILE
# ══════════════════════════════════════════════════════════════════════════════
df_all = load_saved_data()
if df_all is None or df_all.empty:
    st.error("❌ Không đọc được file dữ liệu. Thử tải lại.")
    if st.button("🔄 Tải lại"):
        st.session_state.pop("data_loaded", None)
        st.rerun()
    st.stop()

# Thống kê tổng quan
st.markdown("---")
render_metrics_bar(df_all)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 2 — BỘ LỌC (hiện sau khi có data)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🔧 Thiết lập bộ lọc")

# ── Hàng 1: Giá trị GD | Sắp xếp ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.markdown('<div class="filter-card"><div class="filter-card-title">💰 Giá trị GD bình quân / ngày</div>', unsafe_allow_html=True)
    val_options = [0, 1, 5, 10, 20, 50, 100, 200, 500, 1000, 9999]
    min_val, max_val = st.select_slider(
        "Đơn vị: tỷ đồng",
        options=val_options,
        value=(0, 9999),
        key="slider_val",
        label_visibility="visible",
    )
    st.markdown(
        f'Từ <b style="color:#58a6ff">{min_val}</b> → '
        f'<b style="color:#58a6ff">{"Không giới hạn" if max_val==9999 else max_val}</b> tỷ/ngày',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="filter-card"><div class="filter-card-title">📊 % Độ tăng/giảm giá</div>', unsafe_allow_html=True)
    period = st.radio("Kỳ tính", ["1 tháng", "3 tháng", "6 tháng"], horizontal=True, key="period_radio")
    c_lo, c_hi = st.columns(2)
    with c_lo:
        pct_min = st.number_input("Từ (%)", value=-100, step=5, key="pct_min")
    with c_hi:
        pct_max = st.number_input("Đến (%)", value=500, step=5, key="pct_max")
    st.markdown(
        f'<span style="color:#8b949e;font-size:12px">Lọc {period}: '
        f'<b style="color:#3fb950">+{pct_min}%</b> → '
        f'<b style="color:#3fb950">+{pct_max}%</b></span>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="filter-card"><div class="filter-card-title">📉 RSI (14 phiên)</div>', unsafe_allow_html=True)
    rsi_preset = st.radio(
        "Chọn nhanh",
        ["Tất cả", "Quá bán < 30", "Trung tính 30–70", "Quá mua > 70", "Tùy chỉnh"],
        key="rsi_preset",
    )
    if rsi_preset == "Quá bán < 30":
        rsi_lo, rsi_hi = 0, 30
        st.markdown('<span style="color:#3fb950;font-size:12px">RSI 0 → 30 (cơ hội mua)</span>', unsafe_allow_html=True)
    elif rsi_preset == "Trung tính 30–70":
        rsi_lo, rsi_hi = 30, 70
        st.markdown('<span style="color:#e3b341;font-size:12px">RSI 30 → 70</span>', unsafe_allow_html=True)
    elif rsi_preset == "Quá mua > 70":
        rsi_lo, rsi_hi = 70, 100
        st.markdown('<span style="color:#f85149;font-size:12px">RSI 70 → 100 (cân nhắc chốt lời)</span>', unsafe_allow_html=True)
    elif rsi_preset == "Tùy chỉnh":
        rsi_lo, rsi_hi = st.slider("Khoảng RSI", 0, 100, (0, 100), key="rsi_custom")
    else:
        rsi_lo, rsi_hi = 0, 100
    st.markdown('</div>', unsafe_allow_html=True)

# ── Hàng 2: Sàn + Sắp xếp ────────────────────────────────────────────────────
col4, col5, col6 = st.columns([1, 1, 1])

with col4:
    st.markdown('<div class="filter-card"><div class="filter-card-title">📌 Sàn giao dịch</div>', unsafe_allow_html=True)
    selected_exchange = st.radio("", ["Tất cả", "HOSE", "HNX", "UPCOM"],
                                 horizontal=True, key="exchange_radio",
                                 label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

with col5:
    st.markdown('<div class="filter-card"><div class="filter-card-title">⬆️ Sắp xếp kết quả</div>', unsafe_allow_html=True)
    sort_col = st.selectbox("Theo", ["Giá trị GD TB (tỷ)", "RSI", "% 1 tháng", "% 3 tháng", "% 6 tháng"], key="sort_col")
    sort_asc = st.radio("Thứ tự", ["Giảm dần ↓", "Tăng dần ↑"], horizontal=True, key="sort_asc")
    st.markdown('</div>', unsafe_allow_html=True)

with col6:
    # Nút Hiện kết quả — nằm trong col6, căn giữa dọc
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="show-btn">', unsafe_allow_html=True)
    show_result = st.button("🔍  Hiện kết quả", use_container_width=True, key="show_btn")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 3 — KẾT QUẢ
# ══════════════════════════════════════════════════════════════════════════════
# Xây dựng params từ UI
def _period_col():
    return {"1 tháng": "% 1 tháng", "3 tháng": "% 3 tháng", "6 tháng": "% 6 tháng"}[period]

filter_params = {
    "exchange":  selected_exchange,
    "min_val":   min_val,
    "max_val":   max_val,
    "ret6m":     (pct_min, pct_max) if period == "6 tháng" else (-9999, 9999),
    "ret3m":     (pct_min, pct_max) if period == "3 tháng" else (-9999, 9999),
    "ret1m":     (pct_min, pct_max) if period == "1 tháng" else (-9999, 9999),
    "rsi_range": (rsi_lo, rsi_hi),
    "sort_col":  sort_col,
    "sort_asc":  sort_asc == "Tăng dần ↑",
}

if show_result:
    st.session_state["filter_params"] = filter_params
    st.session_state["show_result"]   = True

if st.session_state.get("show_result"):
    params_to_use = st.session_state.get("filter_params", filter_params)
    df_result = apply_filters(df_all, params_to_use)

    st.markdown("---")
    rc1, rc2 = st.columns([4, 1])
    with rc1:
        st.markdown(
            f"### Kết quả: <b style='color:#58a6ff'>{len(df_result)}</b> mã"
            f" / tổng <b>{len(df_all)}</b> mã",
            unsafe_allow_html=True,
        )
    with rc2:
        csv = df_result.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Tải CSV", data=csv,
            file_name=f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True,
        )

    if df_result.empty:
        st.info("ℹ️ Không có mã nào thỏa điều kiện. Hãy nới rộng tiêu chí.")
    else:
        render_results_table(df_result)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<p style="color:#8b949e;font-size:11px;text-align:center;margin-top:32px">'
    '📊 Dữ liệu từ TCBS · Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư</p>',
    unsafe_allow_html=True,
)
