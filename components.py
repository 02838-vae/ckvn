"""
components.py
─────────────
Các component UI tái sử dụng cho Stock Screener.
"""

import streamlit as st
import pandas as pd
import numpy as np
from data_loader import get_summary_stats


# ══════════════════════════════════════════════════════════════════════════════
#  METRICS BAR
# ══════════════════════════════════════════════════════════════════════════════
def render_metrics_bar(df: pd.DataFrame):
    stats = get_summary_stats(df)
    cols = st.columns(6)

    metrics = [
        ("📋 Tổng mã",      str(stats["total"]),           "#58a6ff"),
        ("📈 Tăng (1T)",     str(stats["tang"]),            "#3fb950"),
        ("📉 Giảm (1T)",     str(stats["giam"]),            "#f85149"),
        ("🔴 RSI Quá mua",   str(stats["rsi_ob"]),          "#e3b341"),
        ("🟢 RSI Quá bán",   str(stats["rsi_os"]),          "#58a6ff"),
        ("💰 GD TB (Median)", f'{stats["avg_val"]:.1f} tỷ', "#a5d6ff"),
    ]

    for col, (label, value, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{label}</div>
              <div class="value" style="color:{color}">{value}</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COLOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _color_pct(val):
    if pd.isna(val):
        return "color: #8b949e"
    if val > 0:
        return "color: #3fb950; font-weight: 600"
    if val < 0:
        return "color: #f85149; font-weight: 600"
    return "color: #e6edf3"


def _color_rsi(val):
    if pd.isna(val):
        return "color: #8b949e"
    if val > 70:
        return "color: #f85149; font-weight: 600"
    if val < 30:
        return "color: #3fb950; font-weight: 600"
    return "color: #e3b341"


def _fmt_pct(val):
    if pd.isna(val):
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def _fmt_val(val):
    if pd.isna(val):
        return "—"
    if val >= 1000:
        return f"{val/1000:.1f}k"
    return f"{val:.1f}"


def _rsi_badge(val):
    if pd.isna(val):
        return "—"
    if val >= 70:
        label = f"🔴 {val:.1f}"
        cls = "badge-red"
    elif val <= 30:
        label = f"🟢 {val:.1f}"
        cls = "badge-green"
    else:
        label = f"🟡 {val:.1f}"
        cls = "badge-yellow"
    return f'<span class="badge {cls}">{label}</span>'


def _san_badge(val):
    if pd.isna(val):
        return val
    cls_map = {"HOSE": "badge-blue", "HNX": "badge-green", "UPCOM": "badge-yellow"}
    cls = cls_map.get(str(val).upper(), "badge-blue")
    return f'<span class="badge {cls}">{val}</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTS TABLE
# ══════════════════════════════════════════════════════════════════════════════
def render_results_table(df: pd.DataFrame):
    """Hiển thị bảng kết quả với màu sắc và định dạng đẹp."""

    # Chuẩn bị bản sao để format
    display_df = df.copy()

    # Giới hạn 500 hàng để tránh lag
    if len(display_df) > 500:
        st.warning(f"⚠️ Hiển thị 500/{len(display_df)} mã đầu tiên.")
        display_df = display_df.head(500)

    # ── Dùng st.dataframe với Styler ─────────────────────────────────────
    style_cols = ["% 1 tháng", "% 3 tháng", "% 6 tháng"]
    available_style = [c for c in style_cols if c in display_df.columns]

    def style_df(df):
        styler = df.style

        # Format số
        fmt = {}
        for c in available_style:
            fmt[c] = lambda x: _fmt_pct(x)
        if "Giá trị GD TB (tỷ)" in df.columns:
            fmt["Giá trị GD TB (tỷ)"] = lambda x: _fmt_val(x)
        if "Giá" in df.columns:
            fmt["Giá"] = lambda x: f"{x:,.1f}" if not pd.isna(x) else "—"
        if "RSI" in df.columns:
            fmt["RSI"] = lambda x: f"{x:.1f}" if not pd.isna(x) else "—"

        styler = styler.format(fmt, na_rep="—")

        # Màu % thay đổi
        for col in available_style:
            if col in df.columns:
                _cell_map = getattr(styler, "map", None) or styler.applymap
                styler = _cell_map(_color_pct, subset=[col])

        # Màu RSI
        if "RSI" in df.columns:
            styler = styler.applymap(_color_rsi, subset=["RSI"])

        # Background xen kẽ nhẹ
        styler = styler.set_table_styles([{
            "selector": "tr:nth-child(even)",
            "props": [("background-color", "#161b22")]
        }, {
            "selector": "th",
            "props": [
                ("background-color", "#21262d"),
                ("color", "#58a6ff"),
                ("font-weight", "600"),
                ("font-size", "12px"),
            ]
        }, {
            "selector": "td",
            "props": [
                ("font-size", "13px"),
                ("padding", "8px 12px"),
            ]
        }])

        return styler

    st.dataframe(
        style_df(display_df),
        use_container_width=True,
        height=min(600, 40 + len(display_df) * 36),
        hide_index=True,
    )

    # ── Chú thích màu ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;gap:16px;margin-top:8px;font-size:11px;">
      <span><span style="color:#3fb950">■</span> Tăng / RSI quá bán</span>
      <span><span style="color:#f85149">■</span> Giảm / RSI quá mua</span>
      <span><span style="color:#e3b341">■</span> RSI trung tính</span>
      <span><span style="color:#8b949e">■</span> Không có dữ liệu</span>
    </div>
    """, unsafe_allow_html=True)
