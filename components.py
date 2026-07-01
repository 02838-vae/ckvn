"""
components.py — render bảng kết quả bằng HTML thuần, không dùng pandas Styler
"""
import streamlit as st
import pandas as pd
import numpy as np
from data_loader import get_summary_stats


# ── Metrics bar ────────────────────────────────────────────────────────────────
def render_metrics_bar(df: pd.DataFrame):
    stats = get_summary_stats(df)
    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="mlabel">📋 Tổng mã</div>
        <div class="mval">{stats['total']}</div>
      </div>
      <div class="metric-card">
        <div class="mlabel">📈 Tăng (1T)</div>
        <div class="mval" style="color:#3fb950">{stats['tang']}</div>
      </div>
      <div class="metric-card">
        <div class="mlabel">📉 Giảm (1T)</div>
        <div class="mval" style="color:#f85149">{stats['giam']}</div>
      </div>
      <div class="metric-card">
        <div class="mlabel">🔴 RSI &gt; 70</div>
        <div class="mval" style="color:#e3b341">{stats['rsi_ob']}</div>
      </div>
      <div class="metric-card">
        <div class="mlabel">🟢 RSI &lt; 30</div>
        <div class="mval" style="color:#3fb950">{stats['rsi_os']}</div>
      </div>
      <div class="metric-card">
        <div class="mlabel">💰 GD TB Median</div>
        <div class="mval">{stats['avg_val']:.2f}tỷ</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Format helpers ─────────────────────────────────────────────────────────────
def _nan(v):
    return v is None or (isinstance(v, float) and np.isnan(v))

def _fmt_pct(val):
    if _nan(val):
        return '<span style="color:#484f58">—</span>'
    color = "#3fb950" if val > 0 else ("#f85149" if val < 0 else "#8b949e")
    sign  = "+" if val > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{val:.2f}%</span>'

def _fmt_rsi(val):
    if _nan(val):
        return '<span style="color:#484f58">—</span>'
    if val >= 70:
        return f'<span style="color:#f85149;font-weight:700">🔴{val:.1f}</span>'
    if val <= 30:
        return f'<span style="color:#3fb950;font-weight:700">🟢{val:.1f}</span>'
    return f'<span style="color:#e3b341">{val:.1f}</span>'

def _fmt_gtgd(val):
    if _nan(val):
        return '<span style="color:#484f58">—</span>'
    if val >= 1:
        txt = f"{val:.2f} tỷ"
    else:
        txt = f"{val*1000:.0f} tr"
    return f'<span style="color:#c9d1d9">{txt}</span>'

def _fmt_price(val):
    if _nan(val):
        return '<span style="color:#484f58">—</span>'
    return f'<span style="color:#e6edf3;font-weight:600">{val:,.1f}</span>'

def _fmt_san(val):
    if not val:
        return ""
    colors = {"HOSE":"#58a6ff","HNX":"#3fb950","UPCOM":"#e3b341"}
    c = colors.get(str(val).upper(), "#8b949e")
    return (f'<span style="color:{c};font-size:11px;font-weight:700;'
            f'background:rgba(0,0,0,.3);padding:1px 6px;border-radius:3px">{val}</span>')

def _fmt_ticker(val):
    return f'<span style="color:#58a6ff;font-weight:800;font-size:14px">{val}</span>'

def _safe(df, i, col):
    try:
        v = df.iloc[i][col]
        return v if pd.notna(v) else np.nan
    except Exception:
        return np.nan


# ══════════════════════════════════════════════════════════════════════════════
#  RENDER TABLE
# ══════════════════════════════════════════════════════════════════════════════
def render_results_table(df: pd.DataFrame):
    if len(df) > 500:
        st.warning(f"⚠️ Hiển thị 500/{len(df)} mã đầu tiên.")
        df = df.head(500)

    has = lambda c: c in df.columns

    # ── Định nghĩa cột sẽ hiển thị ────────────────────────────────────────
    COLS = [
        ("#",                None,                   "left",  "40px"),
        ("Mã",               "Mã",                   "left",  "60px"),
        ("Sàn",              "Sàn",                  "left",  "60px"),
        ("Giá",              "Giá",                  "right", "70px"),
        ("GT GD/ngày",       "GTGD TB/ngày (tỷ)",    "right", "90px"),
        ("% 1T",             "% 1 tuần",             "right", "72px"),
        ("% 1Th",            "% 1 tháng",            "right", "72px"),
        ("% 3Th",            "% 3 tháng",            "right", "72px"),
        ("% 6Th",            "% 6 tháng",            "right", "72px"),
        ("% 1Y",             "% 1 năm",              "right", "72px"),
        ("RSI(D)",           "RSI 1D",               "right", "70px"),
        ("RSI(W)",           "RSI 1W",               "right", "70px"),
        ("RSI(M)",           "RSI 1M",               "right", "70px"),
    ]

    # Chỉ hiện cột nếu có trong df
    visible = [(h, col, align, w) for h, col, align, w in COLS
               if col is None or has(col)]

    TH = ("background:#21262d;color:#8b949e;font-size:11px;font-weight:700;"
          "padding:10px 10px;white-space:nowrap;border-bottom:2px solid #30363d;")

    headers_html = "".join(
        f'<th style="{TH}text-align:{align};width:{w}">{h}</th>'
        for h, _, align, w in visible
    )

    rows_html = ""
    for i in range(len(df)):
        bg = "#0d1117" if i % 2 == 0 else "#161b22"
        TD = f'padding:9px 10px;border-bottom:1px solid #21262d;background:{bg};font-size:13px;'

        def cell(content, align="right"):
            return f'<td style="{TD}text-align:{align}">{content}</td>'

        row = "<tr>"
        for h, col, align, _ in visible:
            if col is None:  # index
                row += cell(f'<span style="color:#484f58;font-size:11px">{i+1}</span>', "left")
            elif col == "Mã":
                row += cell(_fmt_ticker(_safe(df, i, col)), "left")
            elif col == "Sàn":
                row += cell(_fmt_san(_safe(df, i, col)), "left")
            elif col == "Giá":
                row += cell(_fmt_price(_safe(df, i, col)))
            elif col == "GTGD TB/ngày (tỷ)":
                row += cell(_fmt_gtgd(_safe(df, i, col)))
            elif col.startswith("%"):
                row += cell(_fmt_pct(_safe(df, i, col)))
            elif col.startswith("RSI"):
                row += cell(_fmt_rsi(_safe(df, i, col)))
            else:
                v = _safe(df, i, col)
                row += cell("—" if _nan(v) else str(v), align)
        row += "</tr>"
        rows_html += row

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #30363d;border-radius:10px;margin-top:8px">
      <table style="width:100%;border-collapse:collapse;font-family:'SF Mono',monospace">
        <thead><tr>{headers_html}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div style="display:flex;gap:18px;margin-top:10px;font-size:12px;color:#8b949e;flex-wrap:wrap">
      <span><span style="color:#3fb950">■</span> Tăng / RSI quá bán (&lt;30)</span>
      <span><span style="color:#f85149">■</span> Giảm / RSI quá mua (&gt;70)</span>
      <span><span style="color:#e3b341">■</span> RSI trung tính</span>
      <span><span style="color:#484f58">■</span> Không có dữ liệu</span>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
