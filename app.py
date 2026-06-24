# app.py
import streamlit as st
import pandas as pd
from auth import require_auth, logout

# ============================================================
# CẤU HÌNH TRANG — phải đặt TRƯỚC mọi lệnh st khác
# ============================================================
st.set_page_config(
    page_title="Stock Screener VN",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# XÁC THỰC — chặn ngay nếu chưa đăng nhập
# ============================================================
require_auth()

# ============================================================
# HEADER
# ============================================================
col_title, col_logout = st.columns([9, 1])
with col_title:
    st.title("📈 Stock Screener — Chứng khoán Việt Nam")
    st.caption(f"👤 {st.session_state['username']}  |  Dữ liệu tự động làm mới mỗi 5 phút")
with col_logout:
    st.write("")  # Đẩy nút xuống cho cân
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()

st.divider()

# ============================================================
# TẢI DỮ LIỆU
# ============================================================
@st.cache_data(ttl=300)  # Cache 5 phút
def load_data():
    """Lấy dữ liệu bảng giá toàn thị trường từ vnstock3"""
    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol='ACB', source='VCI')
        df = stock.trading.price_board(['ACB', 'VCB', 'HPG', 'VIC', 'MSN',
                                         'FPT', 'MWG', 'TCB', 'VHM', 'BID',
                                         'CTG', 'GAS', 'PLX', 'SAB', 'VNM',
                                         'POW', 'HDB', 'SSI', 'VPB', 'MBB'])
        return df, None
    except Exception as e:
        return None, str(e)


# ============================================================
# SIDEBAR — BỘ LỌC
# ============================================================
with st.sidebar:
    st.header("🎯 Bộ lọc")

    st.subheader("📊 Khối lượng giao dịch")
    min_vol = st.number_input("Tối thiểu (nghìn CP)", min_value=0, value=0, step=100)

    st.subheader("📉 Biến động giá (%)")
    price_change_range = st.slider(
        "% thay đổi so với hôm qua",
        min_value=-15.0, max_value=15.0,
        value=(-15.0, 15.0), step=0.5
    )

    st.subheader("💰 Giá (nghìn VNĐ)")
    price_range = st.slider(
        "Khoảng giá",
        min_value=0, max_value=200,
        value=(0, 200)
    )

    st.divider()
    btn_refresh = st.button("🔄 Làm mới dữ liệu", use_container_width=True)
    if btn_refresh:
        st.cache_data.clear()
        st.rerun()

# ============================================================
# LOAD & HIỂN THỊ DỮ LIỆU
# ============================================================
with st.spinner("⏳ Đang tải dữ liệu thị trường..."):
    df, error = load_data()

if error:
    st.warning(f"⚠️ Không lấy được dữ liệu thực: `{error}`")
    st.info("👇 Đang hiển thị dữ liệu mẫu để kiểm tra giao diện")

    # Dữ liệu mẫu khi vnstock3 lỗi hoặc ngoài giờ giao dịch
    df = pd.DataFrame({
        "Mã CP":           ["VCB",   "HPG",   "VIC",   "MSN",   "FPT",   "MWG",   "TCB",   "BID",   "VHM",   "SSI"],
        "Giá":             [85.5,    28.3,    42.1,    71.0,    95.2,    45.6,    22.8,    44.1,    38.7,    28.5],
        "% Thay đổi":      [1.2,    -0.8,     2.5,    -1.1,     3.0,     0.5,    -2.1,     1.8,    -0.3,     4.2],
        "KL Khớp (nghìn)": [1200,    5400,    800,     950,    2100,    3200,    4100,    1800,     650,    5800],
        "Ngành":           ["Ngân hàng","Thép","BĐS","Thực phẩm","Công nghệ","Bán lẻ","Ngân hàng","Ngân hàng","BĐS","Chứng khoán"],
        "Sàn":             ["HOSE"] * 10,
    })

# ---- Áp dụng bộ lọc ----
if df is not None and not df.empty:
    try:
        # Lọc % thay đổi
        if "% Thay đổi" in df.columns:
            df = df[df["% Thay đổi"].between(price_change_range[0], price_change_range[1])]

        # Lọc giá
        if "Giá" in df.columns:
            df = df[df["Giá"].between(price_range[0], price_range[1])]

        # Lọc khối lượng
        kl_col = [c for c in df.columns if "KL" in c or "kltt" in c.lower() or "vol" in c.lower()]
        if kl_col:
            df = df[df[kl_col[0]] >= min_vol]

    except Exception:
        pass  # Nếu tên cột từ vnstock3 khác → bỏ qua filter, vẫn hiện bảng

    # ---- Metrics tổng quan ----
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng số mã", len(df))

    try:
        tang = len(df[df["% Thay đổi"] > 0])
        giam = len(df[df["% Thay đổi"] < 0])
        m2.metric("🟢 Tăng", tang)
        m3.metric("🔴 Giảm", giam)
        m4.metric("⬜ Đứng", len(df) - tang - giam)
    except Exception:
        pass

    st.divider()

    # ---- Bảng dữ liệu ----
    st.subheader("📋 Danh sách cổ phiếu")
    st.dataframe(
        df,
        use_container_width=True,
        height=500,
        hide_index=True
    )

    # ---- Nút xuất CSV ----
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Tải xuống CSV",
        data=csv,
        file_name="stock_screener.csv",
        mime="text/csv"
    )

else:
    st.error("Không có dữ liệu để hiển thị.")
