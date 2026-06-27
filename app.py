import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Screener VN",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Nền tối chuyên nghiệp */
  .stApp { background-color: #0d1117; color: #e6edf3; }
  
  /* Sidebar */
  section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #30363d;
  }
  
  /* Header */
  .main-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .main-header h1 {
    font-size: 28px;
    font-weight: 700;
    color: #58a6ff;
    margin: 0;
    letter-spacing: -0.5px;
  }
  .main-header p {
    color: #8b949e;
    margin: 4px 0 0 0;
    font-size: 14px;
  }

  /* Metric cards */
  .metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
  }
  .metric-card .label {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
  }
  .metric-card .value {
    font-size: 26px;
    font-weight: 700;
    color: #58a6ff;
  }

  /* Table */
  .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
  
  /* Slider labels */
  .filter-section {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .filter-title {
    font-size: 12px;
    font-weight: 600;
    color: #58a6ff;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
  }

  /* Positive/Negative colors */
  .pos { color: #3fb950 !important; font-weight: 600; }
  .neg { color: #f85149 !important; font-weight: 600; }
  .neu { color: #e6edf3; }

  /* Badge */
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-green { background: #1a3a2a; color: #3fb950; border: 1px solid #3fb950; }
  .badge-red   { background: #3a1a1a; color: #f85149; border: 1px solid #f85149; }
  .badge-yellow{ background: #3a3a1a; color: #e3b341; border: 1px solid #e3b341; }
  .badge-blue  { background: #1a2a3a; color: #58a6ff; border: 1px solid #58a6ff; }

  /* Button overrides */
  div.stButton > button {
    background-color: #238636;
    color: white;
    border: 1px solid #2ea043;
    border-radius: 6px;
    font-weight: 600;
    width: 100%;
    padding: 8px;
  }
  div.stButton > button:hover {
    background-color: #2ea043;
    border-color: #3fb950;
  }
  
  /* Update time */
  .update-time {
    font-size: 11px;
    color: #8b949e;
    text-align: right;
    margin-top: -8px;
    margin-bottom: 16px;
  }
  
  /* Exchange filter */
  .stRadio > label { color: #8b949e !important; font-size: 12px; }
</style>
""", unsafe_allow_html=True)


# ── Import modules ─────────────────────────────────────────────────────────────
from data_loader import load_market_data, get_summary_stats
from filters import apply_filters
from components import render_results_table, render_metrics_bar


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
  <div>
    <h1>📈 Stock Screener — Việt Nam</h1>
    <p>Lọc cổ phiếu theo giá trị giao dịch · % tăng/giảm · RSI · Sàn · Ngành</p>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("⏳ Đang tải dữ liệu thị trường..."):
    df_all, last_updated = load_market_data()

if df_all is None or df_all.empty:
    st.error("❌ Không thể tải dữ liệu. Vui lòng kiểm tra kết nối internet và thử lại.")
    st.stop()

st.markdown(
    f'<div class="update-time">🕐 Cập nhật lần cuối: {last_updated}</div>',
    unsafe_allow_html=True
)

# ── Summary bar ────────────────────────────────────────────────────────────────
render_metrics_bar(df_all)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — BỘ LỌC
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🔍 Bộ lọc cổ phiếu")

    # ── Sàn giao dịch ──────────────────────────────────────────────────────
    st.markdown('<div class="filter-title">📌 Sàn giao dịch</div>', unsafe_allow_html=True)
    exchanges = ["Tất cả", "HOSE", "HNX", "UPCOM"]
    selected_exchange = st.radio("", exchanges, horizontal=True, label_visibility="collapsed")

    st.divider()

    # ── Giá trị GD bình quân ───────────────────────────────────────────────
    st.markdown('<div class="filter-title">💰 Giá trị GD bình quân / ngày</div>', unsafe_allow_html=True)
    min_val, max_val = st.select_slider(
        "Đơn vị: tỷ đồng",
        options=[0, 1, 5, 10, 20, 50, 100, 200, 500, 1000, 9999],
        value=(10, 9999),
        label_visibility="visible"
    )

    st.divider()

    # ── % Tăng/giảm ────────────────────────────────────────────────────────
    st.markdown('<div class="filter-title">📊 % Thay đổi giá</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("6 tháng (%)")
        ret6m_min = st.number_input("Min 6M", value=-100, step=5, label_visibility="collapsed", key="r6min")
        ret6m_max = st.number_input("Max 6M", value=500,  step=5, label_visibility="collapsed", key="r6max")
    with col2:
        st.caption("3 tháng (%)")
        ret3m_min = st.number_input("Min 3M", value=-100, step=5, label_visibility="collapsed", key="r3min")
        ret3m_max = st.number_input("Max 3M", value=500,  step=5, label_visibility="collapsed", key="r3max")

    st.caption("1 tháng (%)")
    col3, col4 = st.columns(2)
    with col3:
        ret1m_min = st.number_input("Min 1M", value=-100, step=5, label_visibility="collapsed", key="r1min")
    with col4:
        ret1m_max = st.number_input("Max 1M", value=500,  step=5, label_visibility="collapsed", key="r1max")

    st.divider()

    # ── RSI ────────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-title">📉 RSI (14 phiên)</div>', unsafe_allow_html=True)
    
    rsi_preset = st.selectbox(
        "Preset nhanh",
        ["Tùy chỉnh", "Quá bán (< 30)", "Trung tính (30–70)", "Quá mua (> 70)"]
    )
    if rsi_preset == "Quá bán (< 30)":
        rsi_range = (0, 30)
    elif rsi_preset == "Trung tính (30–70)":
        rsi_range = (30, 70)
    elif rsi_preset == "Quá mua (> 70)":
        rsi_range = (70, 100)
    else:
        rsi_range = st.slider("Khoảng RSI", 0, 100, (0, 100))

    st.divider()

    # ── Sắp xếp ────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-title">⬆️ Sắp xếp kết quả</div>', unsafe_allow_html=True)
    sort_col = st.selectbox("Theo cột", [
        "Giá trị GD TB (tỷ)", "RSI", "% 1 tháng", "% 3 tháng", "% 6 tháng"
    ])
    sort_asc = st.radio("Thứ tự", ["Giảm dần ↓", "Tăng dần ↑"], horizontal=True)

    st.divider()
    run_btn = st.button("🚀 Lọc cổ phiếu", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  RUN FILTER
# ══════════════════════════════════════════════════════════════════════════════
# Auto-run on load, re-run on button
if "df_result" not in st.session_state or run_btn:
    filter_params = {
        "exchange":  selected_exchange,
        "min_val":   min_val,
        "max_val":   max_val,
        "ret6m":     (ret6m_min, ret6m_max),
        "ret3m":     (ret3m_min, ret3m_max),
        "ret1m":     (ret1m_min, ret1m_max),
        "rsi_range": rsi_range,
        "sort_col":  sort_col,
        "sort_asc":  sort_asc == "Tăng dần ↑",
    }
    st.session_state["df_result"] = apply_filters(df_all, filter_params)

df_result = st.session_state["df_result"]

# ── Result count ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(
        f"### Kết quả: **{len(df_result)}** mã"
        f" / tổng **{len(df_all)}** mã đang lọc",
        unsafe_allow_html=True
    )
with col_b:
    # Download CSV
    csv = df_result.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Tải CSV",
        data=csv,
        file_name=f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── Table ──────────────────────────────────────────────────────────────────────
if df_result.empty:
    st.info("ℹ️ Không có mã nào thỏa điều kiện lọc. Hãy nới rộng tiêu chí.")
else:
    render_results_table(df_result)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="color:#8b949e;font-size:12px;text-align:center;">'
    '📊 Dữ liệu từ TCBS qua thư viện <b>vnstock</b> · '
    'Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư</p>',
    unsafe_allow_html=True
)
