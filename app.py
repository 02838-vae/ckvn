import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os, warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Stock Screener VN",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  /* ── Reset Streamlit chrome ── */
  .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important;
                     max-width: 1100px !important; margin: 0 auto !important; }
  #MainMenu, header, footer { visibility: hidden; }
  div[data-testid="stDecoration"] { display: none; }

  /* ── Base ── */
  .stApp { background: #0d1117; color: #e6edf3; font-size: 15px; }
  * { box-sizing: border-box; }

  /* ── Typography ── */
  .app-title {
    font-size: 32px; font-weight: 800; color: #58a6ff;
    text-align: center; letter-spacing: -0.5px; margin: 0 0 6px;
  }
  .app-sub {
    font-size: 15px; color: #8b949e; text-align: center; margin: 0 0 28px;
  }

  /* ── Big load button ── */
  .center-wrap { display: flex; flex-direction: column; align-items: center; padding: 48px 0 16px; }
  div.big-btn > div.stButton > button {
    background: #238636 !important; color: #fff !important;
    border: 1px solid #2ea043 !important; border-radius: 10px !important;
    font-size: 17px !important; font-weight: 700 !important;
    padding: 16px 40px !important; letter-spacing: 0.2px;
  }
  div.big-btn > div.stButton > button:hover { background: #2ea043 !important; }

  /* ── Info tag ── */
  .info-tag {
    display: inline-block; font-size: 13px; color: #8b949e;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 5px; padding: 3px 10px; margin-bottom: 12px;
  }

  /* ── Filter row ── */
  .filter-row {
    display: flex; gap: 12px; align-items: stretch;
    margin: 20px 0 12px;
  }

  /* ── Filter pill button ── */
  div.fpill > div.stButton > button {
    background: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; border-radius: 8px !important;
    font-size: 14px !important; font-weight: 600 !important;
    padding: 10px 20px !important; white-space: nowrap;
    transition: all .15s;
  }
  div.fpill > div.stButton > button:hover,
  div.fpill-active > div.stButton > button {
    background: #1f3a5f !important; color: #58a6ff !important;
    border-color: #58a6ff !important;
  }

  /* ── Show result button ── */
  div.show-btn > div.stButton > button {
    background: #1f6feb !important; color: #fff !important;
    border: 1px solid #388bfd !important; border-radius: 8px !important;
    font-size: 15px !important; font-weight: 700 !important;
    padding: 10px 28px !important;
  }
  div.show-btn > div.stButton > button:hover { background: #388bfd !important; }

  /* ── Dropdown panel ── */
  .drop-panel {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 20px 22px; margin-bottom: 16px;
  }
  .drop-title { font-size: 13px; font-weight: 700; color: #58a6ff;
                text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 14px; }

  /* ── Option chips ── */
  div.opt-chip > div.stButton > button {
    background: #21262d !important; color: #c9d1d9 !important;
    border: 1px solid #30363d !important; border-radius: 20px !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 6px 16px !important;
  }
  div.opt-chip-sel > div.stButton > button {
    background: #1f3a5f !important; color: #58a6ff !important;
    border: 1px solid #58a6ff !important; border-radius: 20px !important;
    font-size: 13px !important; font-weight: 700 !important;
    padding: 6px 16px !important;
  }

  /* ── Divider ── */
  hr { border-color: #30363d !important; margin: 6px 0 !important; }

  /* ── Metrics ── */
  .metric-row { display: flex; gap: 10px; margin: 18px 0; flex-wrap: wrap; }
  .metric-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 18px; flex: 1; min-width: 120px; text-align: center;
  }
  .metric-card .mlabel { font-size: 11px; color: #8b949e; text-transform:uppercase; letter-spacing:.6px; }
  .metric-card .mval   { font-size: 22px; font-weight: 700; color: #58a6ff; margin-top: 4px; }

  /* ── Selected filter summary ── */
  .sel-summary {
    font-size: 13px; color: #8b949e; background: #161b22;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 8px 14px; margin-bottom: 12px;
  }
  .sel-summary b { color: #e6edf3; }

  /* ── Streamlit radio/select overrides ── */
  .stRadio label, .stSelectbox label { font-size: 14px !important; color: #c9d1d9 !important; }
  div[data-testid="stMarkdownContainer"] p { font-size: 15px; }
</style>
""", unsafe_allow_html=True)

from data_loader import fetch_and_save_all, load_saved_data, get_summary_stats, CACHE_FILE
from filters import apply_filters
from components import render_results_table

# ── Title ───────────────────────────────────────────────────────────────────────
st.markdown('<p class="app-title">📈 Stock Screener — Việt Nam</p>', unsafe_allow_html=True)
st.markdown('<p class="app-sub">Lọc cổ phiếu HOSE · HNX · UPCOM theo giá trị GD · % tăng/giảm · RSI</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 1 — TẢI DỮ LIỆU
# ══════════════════════════════════════════════════════════════════════════════
cache_exists = os.path.exists(CACHE_FILE)
cache_time   = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).strftime("%H:%M %d/%m/%Y") if cache_exists else None

if cache_exists:
    st.markdown(f'<span class="info-tag">💾 Dữ liệu đã lưu: {cache_time}</span>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([2, 2, 6])
    with c1:
        btn_use = st.button("📂 Dùng dữ liệu đã lưu", use_container_width=True)
    with c2:
        btn_reload = st.button("🔄 Tải lại từ đầu", use_container_width=True)
    triggered   = btn_use or btn_reload
    force_fetch = btn_reload
else:
    st.markdown('<div class="center-wrap">', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;font-size:14px;margin-bottom:16px">Chưa có dữ liệu. Nhấn nút bên dưới để bắt đầu.</p>', unsafe_allow_html=True)
    _, cc, _ = st.columns([3, 2, 3])
    with cc:
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        btn_load = st.button("⬇️  Tải dữ liệu tất cả cổ phiếu", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    triggered   = btn_load
    force_fetch = True

if triggered:
    if force_fetch:
        with st.spinner("⏳ Đang tải dữ liệu toàn thị trường..."):
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

if not st.session_state.get("data_loaded", False):
    st.stop()

# ── Load file ───────────────────────────────────────────────────────────────────
df_all = load_saved_data()
if df_all is None or df_all.empty:
    st.error("❌ Không đọc được file. Thử tải lại.")
    if st.button("🔄 Tải lại"):
        st.session_state.pop("data_loaded", None)
        st.rerun()
    st.stop()

# ── Metrics ─────────────────────────────────────────────────────────────────────
stats = get_summary_stats(df_all)
st.markdown(f"""
<div class="metric-row">
  <div class="metric-card"><div class="mlabel">📋 Tổng mã</div><div class="mval">{stats['total']}</div></div>
  <div class="metric-card"><div class="mlabel">📈 Tăng (1T)</div><div class="mval" style="color:#3fb950">{stats['tang']}</div></div>
  <div class="metric-card"><div class="mlabel">📉 Giảm (1T)</div><div class="mval" style="color:#f85149">{stats['giam']}</div></div>
  <div class="metric-card"><div class="mlabel">🔴 RSI Quá mua</div><div class="mval" style="color:#e3b341">{stats['rsi_ob']}</div></div>
  <div class="metric-card"><div class="mlabel">🟢 RSI Quá bán</div><div class="mval" style="color:#3fb950">{stats['rsi_os']}</div></div>
  <div class="metric-card"><div class="mlabel">💰 GD TB Median</div><div class="mval">{stats['avg_val']:.1f}tỷ</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🔧 Bộ lọc", unsafe_allow_html=False)

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 2 — 3 NÚT BỘ LỌC
# ══════════════════════════════════════════════════════════════════════════════
# Session state cho trạng thái mở/đóng panel
for k, d in [("panel", None), ("gtgd_val", None), ("pct_period", None),
             ("pct_dir", None), ("rsi_period", None), ("rsi_zone", None)]:
    if k not in st.session_state:
        st.session_state[k] = d

# ── Hàng 3 nút ──────────────────────────────────────────────────────────────────
c_gtgd, c_pct, c_rsi, c_spacer = st.columns([1.6, 1.6, 1.6, 3.2])

with c_gtgd:
    lbl_gtgd = "💰 Giá trị GD/ngày" + (
        f" ≥ {st.session_state['gtgd_val']}" if st.session_state['gtgd_val'] else ""
    )
    cls_gtgd = "fpill-active" if st.session_state["panel"] == "gtgd" else "fpill"
    st.markdown(f'<div class="{cls_gtgd}">', unsafe_allow_html=True)
    if st.button(lbl_gtgd, key="btn_gtgd", use_container_width=True):
        st.session_state["panel"] = None if st.session_state["panel"] == "gtgd" else "gtgd"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c_pct:
    pct_lbl = "📊 % Tăng/giảm"
    if st.session_state["pct_period"]:
        pct_lbl += f" ({st.session_state['pct_period']})"
    cls_pct = "fpill-active" if st.session_state["panel"] == "pct" else "fpill"
    st.markdown(f'<div class="{cls_pct}">', unsafe_allow_html=True)
    if st.button(pct_lbl, key="btn_pct", use_container_width=True):
        st.session_state["panel"] = None if st.session_state["panel"] == "pct" else "pct"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c_rsi:
    rsi_lbl = "📉 RSI"
    if st.session_state["rsi_period"]:
        rsi_lbl += f" ({st.session_state['rsi_period']})"
    cls_rsi = "fpill-active" if st.session_state["panel"] == "rsi" else "fpill"
    st.markdown(f'<div class="{cls_rsi}">', unsafe_allow_html=True)
    if st.button(rsi_lbl, key="btn_rsi", use_container_width=True):
        st.session_state["panel"] = None if st.session_state["panel"] == "rsi" else "rsi"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL: GTGD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["panel"] == "gtgd":
    st.markdown('<div class="drop-panel">', unsafe_allow_html=True)
    st.markdown('<div class="drop-title">💰 Giá trị giao dịch bình quân / ngày</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;font-size:13px;margin-bottom:14px">= Tổng giá trị GD trong tháng ÷ số phiên GD</p>', unsafe_allow_html=True)

    gtgd_opts = ["Tất cả", "≥ 200 triệu", "≥ 500 triệu", "≥ 1 tỷ", "≥ 10 tỷ"]
    cur = st.session_state["gtgd_val"] or "Tất cả"
    cols_g = st.columns(len(gtgd_opts))
    for i, opt in enumerate(gtgd_opts):
        with cols_g[i]:
            cls = "opt-chip-sel" if cur == opt else "opt-chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(opt, key=f"g_{i}", use_container_width=True):
                st.session_state["gtgd_val"] = opt
                st.session_state["panel"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL: % TĂNG/GIẢM
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["panel"] == "pct":
    st.markdown('<div class="drop-panel">', unsafe_allow_html=True)
    st.markdown('<div class="drop-title">📊 % Thay đổi giá</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;font-size:13px;margin-bottom:14px">= (Giá đóng cửa cuối kỳ − Giá mở cửa đầu kỳ) ÷ Giá mở cửa đầu kỳ × 100</p>', unsafe_allow_html=True)

    # Kỳ
    st.markdown('<div style="font-size:13px;color:#8b949e;margin-bottom:8px">Chọn kỳ:</div>', unsafe_allow_html=True)
    periods = ["1 tuần", "1 tháng", "3 tháng", "6 tháng", "1 năm"]
    cur_p   = st.session_state["pct_period"] or "1 tháng"
    cols_p  = st.columns(len(periods))
    for i, p in enumerate(periods):
        with cols_p[i]:
            cls = "opt-chip-sel" if cur_p == p else "opt-chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(p, key=f"pp_{i}", use_container_width=True):
                st.session_state["pct_period"] = p
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # Hướng tăng/giảm + ngưỡng %
    st.markdown('<div style="font-size:13px;color:#8b949e;margin-bottom:8px">Lọc theo hướng:</div>', unsafe_allow_html=True)
    dir_opts = ["Tất cả", "Tăng > 0%", "Tăng > 5%", "Tăng > 10%", "Tăng > 20%",
                "Giảm < 0%", "Giảm < -5%", "Giảm < -10%"]
    cur_d = st.session_state["pct_dir"] or "Tất cả"
    cols_d = st.columns(4)
    for i, d in enumerate(dir_opts):
        with cols_d[i % 4]:
            cls = "opt-chip-sel" if cur_d == d else "opt-chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(d, key=f"pd_{i}", use_container_width=True):
                st.session_state["pct_dir"] = d
                st.session_state["panel"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL: RSI
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["panel"] == "rsi":
    st.markdown('<div class="drop-panel">', unsafe_allow_html=True)
    st.markdown('<div class="drop-title">📉 RSI (Relative Strength Index)</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;font-size:13px;margin-bottom:14px">Tính 14 phiên theo khung thời gian đã chọn (ngày/tuần/tháng/...)</p>', unsafe_allow_html=True)

    # Khung thời gian
    st.markdown('<div style="font-size:13px;color:#8b949e;margin-bottom:8px">Khung thời gian:</div>', unsafe_allow_html=True)
    rsi_tf_opts = ["1 ngày", "1 tuần", "1 tháng", "3 tháng", "6 tháng"]
    cur_rt = st.session_state["rsi_period"] or "1 ngày"
    cols_rt = st.columns(len(rsi_tf_opts))
    for i, r in enumerate(rsi_tf_opts):
        with cols_rt[i]:
            cls = "opt-chip-sel" if cur_rt == r else "opt-chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(r, key=f"rt_{i}", use_container_width=True):
                st.session_state["rsi_period"] = r
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # Vùng RSI
    st.markdown('<div style="font-size:13px;color:#8b949e;margin-bottom:8px">Vùng RSI:</div>', unsafe_allow_html=True)
    rsi_zone_opts = [
        ("Tất cả", "0–100"),
        ("Quá bán ≤ 30", "🟢 Cơ hội mua"),
        ("Trung tính 30–70", "🟡 Bình thường"),
        ("Quá mua ≥ 70", "🔴 Cân nhắc bán"),
    ]
    cur_rz = st.session_state["rsi_zone"] or "Tất cả"
    cols_rz = st.columns(len(rsi_zone_opts))
    for i, (label, hint) in enumerate(rsi_zone_opts):
        with cols_rz[i]:
            cls = "opt-chip-sel" if cur_rz == label else "opt-chip"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(f"{label}", key=f"rz_{i}", use_container_width=True):
                st.session_state["rsi_zone"] = label
                st.session_state["panel"] = None
                st.rerun()
            st.markdown(f'<div style="font-size:11px;color:#8b949e;text-align:center;margin-top:2px">{hint}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tóm tắt bộ lọc đang chọn ──────────────────────────────────────────────────
parts = []
if st.session_state["gtgd_val"] and st.session_state["gtgd_val"] != "Tất cả":
    parts.append(f"GT GD: <b>{st.session_state['gtgd_val']}</b>")
if st.session_state["pct_period"]:
    d = st.session_state["pct_dir"] or "Tất cả"
    parts.append(f"% giá ({st.session_state['pct_period']}): <b>{d}</b>")
if st.session_state["rsi_period"] or st.session_state["rsi_zone"]:
    z = st.session_state["rsi_zone"] or "Tất cả"
    t = st.session_state["rsi_period"] or "1 ngày"
    parts.append(f"RSI ({t}): <b>{z}</b>")

if parts:
    st.markdown(f'<div class="sel-summary">🔍 Đang lọc: {" &nbsp;·&nbsp; ".join(parts)}</div>', unsafe_allow_html=True)

# ── Nút Hiện kết quả ───────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
_, cb, _ = st.columns([3, 2, 3])
with cb:
    st.markdown('<div class="show-btn">', unsafe_allow_html=True)
    show = st.button("🔍  Hiện kết quả", key="show_btn", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BƯỚC 3 — KẾT QUẢ
# ══════════════════════════════════════════════════════════════════════════════
if show:
    st.session_state["show_result"] = True
    st.session_state["filter_snapshot"] = {
        "gtgd_val":   st.session_state["gtgd_val"],
        "pct_period": st.session_state["pct_period"],
        "pct_dir":    st.session_state["pct_dir"],
        "rsi_period": st.session_state["rsi_period"],
        "rsi_zone":   st.session_state["rsi_zone"],
    }

if st.session_state.get("show_result"):
    snap = st.session_state.get("filter_snapshot", {})

    with st.spinner("⏳ Đang lọc..."):
        df_result = apply_filters(df_all, snap)

    st.markdown("---")
    r1, r2 = st.columns([4, 1])
    with r1:
        st.markdown(
            f"### Kết quả: <b style='color:#58a6ff'>{len(df_result)}</b> mã / {len(df_all)} mã",
            unsafe_allow_html=True,
        )
    with r2:
        csv = df_result.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ Tải CSV", data=csv,
                           file_name=f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                           mime="text/csv", use_container_width=True)

    if df_result.empty:
        st.info("ℹ️ Không có mã nào phù hợp. Thử nới rộng điều kiện lọc.")
    else:
        render_results_table(df_result)

st.markdown(
    '<p style="color:#8b949e;font-size:12px;text-align:center;margin-top:36px">'
    '📊 Dữ liệu từ TCBS · Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư</p>',
    unsafe_allow_html=True,
)
