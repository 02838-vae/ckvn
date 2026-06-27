"""
components.py — viết lại hoàn toàn, không dùng pandas Styler
"""
import streamlit as st
import pandas as pd
import numpy as np
from data_loader import get_summary_stats


# ── Metrics bar ────────────────────────────────────────────────────────────────
def render_metrics_bar(df: pd.DataFrame):
    stats = get_summary_stats(df)
    cols = st.columns(6)
    metrics = [
        ("📋 Tổng mã",       str(stats["total"]),            "#58a6ff"),
        ("📈 Tăng (1T)",      str(stats["tang"]),             "#3fb950"),
        ("📉 Giảm (1T)",      str(stats["giam"]),             "#f85149"),
        ("🔴 RSI Quá mua",    str(stats["rsi_ob"]),           "#e3b341"),
        ("🟢 RSI Quá bán",    str(stats["rsi_os"]),           "#58a6ff"),
        ("💰 GD TB (Median)", f'{stats["avg_val"]:.1f} tỷ',  "#a5d6ff"),
    ]
    for col, (label, value, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{label}</div>
              <div class="value" style="color:{color}">{value}</div>
            </div>""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _fmt_pct(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '<span style="color:#8b949e">—</span>'
    color = "#3fb950" if val > 0 else ("#f85149" if val < 0 else "#e6edf3")
    sign  = "+" if val > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{val:.2f}%</span>'


def _fmt_rsi(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '<span style="color:#8b949e">—</span>'
    if val > 70:
        return f'<span style="color:#f85149;font-weight:600">🔴 {val:.1f}</span>'
    if val < 30:
        return f'<span style="color:#3fb950;font-weight:600">🟢 {val:.1f}</span>'
    return f'<span style="color:#e3b341">{val:.1f}</span>'


def _fmt_val(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '<span style="color:#8b949e">—</span>'
    txt = f"{val/1000:.1f}k" if val >= 1000 else f"{val:.1f}"
    return f'<span style="color:#e6edf3">{txt}</span>'


def _fmt_price(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '<span style="color:#8b949e">—</span>'
    return f'<span style="color:#e6edf3">{val:,.1f}</span>'


def _fmt_san(val):
    if not val:
        return ""
    colors = {"HOSE": "#58a6ff", "HNX": "#3fb950", "UPCOM": "#e3b341"}
    c = colors.get(str(val).upper(), "#8b949e")
    return f'<span style="color:{c};font-weight:600;font-size:11px">{val}</span>'


def _fmt_ticker(val):
    return f'<span style="color:#58a6ff;font-weight:700;font-size:13px">{val}</span>'


# ── HTML table ─────────────────────────────────────────────────────────────────
def render_results_table(df: pd.DataFrame):
    display_df = df.copy()
    if len(display_df) > 500:
        st.warning(f"⚠️ Hiển thị 500/{len(display_df)} mã đầu tiên.")
        display_df = display_df.head(500)

    # Xác định cột nào có trong df
    has = lambda c: c in display_df.columns

    # Build header
    headers = ["#", "Mã"]
    if has("Sàn"):            headers.append("Sàn")
    if has("Giá"):             headers.append("Giá")
    if has("Giá trị GD TB (tỷ)"): headers.append("GT GD TB (tỷ)")
    if has("% 1 tháng"):      headers.append("% 1 tháng")
    if has("% 3 tháng"):      headers.append("% 3 tháng")
    if has("% 6 tháng"):      headers.append("% 6 tháng")
    if has("RSI"):             headers.append("RSI")

    th_style = (
        "background:#21262d;color:#58a6ff;font-size:11px;font-weight:600;"
        "padding:10px 12px;text-align:right;border-bottom:2px solid #30363d;"
        "white-space:nowrap"
    )
    th_left = th_style.replace("text-align:right", "text-align:left")

    header_html = "".join(
        f'<th style="{th_left if h in ["#","Mã","Sàn"] else th_style}">{h}</th>'
        for h in headers
    )

    # Build rows
    rows_html = ""
    for i, row in enumerate(display_df.itertuples(index=False)):
        bg = "#0d1117" if i % 2 == 0 else "#161b22"
        td = f'style="padding:8px 12px;border-bottom:1px solid #21262d;background:{bg};'

        def cell(content, align="right"):
            return f'<td {td}text-align:{align}">{content}</td>'

        r = f'<tr>'
        r += cell(f'<span style="color:#8b949e;font-size:11px">{i+1}</span>', "left")
        r += cell(_fmt_ticker(getattr(row, "Mã", "—")), "left")
        if has("Sàn"):
            r += cell(_fmt_san(getattr(row, "Sàn", "")), "left")
        if has("Giá"):
            r += cell(_fmt_price(getattr(row, "Giá", None)))
        if has("Giá trị GD TB (tỷ)"):
            r += cell(_fmt_val(getattr(row, "_4" if not has("Sàn") else "Giá trị GD TB (tỷ)", None)))
        if has("% 1 tháng"):
            v = getattr(row, "% 1 tháng".replace(" ","_").replace("%",""), None)
            # fallback dùng index
            try:
                v = display_df.iloc[i]["% 1 tháng"]
            except Exception:
                pass
            r += cell(_fmt_pct(v))
        if has("% 3 tháng"):
            try: v = display_df.iloc[i]["% 3 tháng"]
            except: v = None
            r += cell(_fmt_pct(v))
        if has("% 6 tháng"):
            try: v = display_df.iloc[i]["% 6 tháng"]
            except: v = None
            r += cell(_fmt_pct(v))
        if has("RSI"):
            try: v = display_df.iloc[i]["RSI"]
            except: v = None
            r += cell(_fmt_rsi(v))
        r += "</tr>"
        rows_html += r

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #30363d;border-radius:8px;margin-top:8px">
      <table style="width:100%;border-collapse:collapse;font-size:13px;font-family:monospace">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div style="display:flex;gap:16px;margin-top:8px;font-size:11px;color:#8b949e">
      <span><span style="color:#3fb950">■</span> Tăng / RSI quá bán</span>
      <span><span style="color:#f85149">■</span> Giảm / RSI quá mua</span>
      <span><span style="color:#e3b341">■</span> RSI trung tính</span>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
