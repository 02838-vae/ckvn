# app.py
import streamlit as st
import pandas as pd
from auth import require_auth, logout
from vnstock3 import Vnstock

st.set_page_config(
    page_title="Stock Screener VN",
    page_icon="📈",
    layout="wide"
)

# ============ XÁC THỰC ============
require_auth()

# ============ HEADER ============
col1, col2 = st.columns([8, 1])
with col1:
    st.title("📈 Stock Screener — Chứng khoán Việt Nam")
    st.caption(f"👤 Xin chào, {st.session_state['username']}")
with col2:
    if st.button("🚪 Logout"):
        logout()
        st.rerun()

st.divider()

# ============ TẢI DỮ LIỆU ============
@st.cache_data(ttl=300)  # Cache 5 phút
def load_stock_data():
    """Lấy toàn bộ danh sách cổ phiếu và thông tin giao dịch"""
    stock = Vnstock().stock(symbol='VN30', source='VCI')
    # Lấy danh sách tất cả cổ phiếu
    listing = stock.listing.all_symbols()
    return listing

@st.cache_data(ttl=300)
def load_market_data():
    """Lấy dữ liệu giá và khối lượng toàn thị trường"""
    stock = Vnstock().stock(source='VCI')
    df = stock.trading.price_board(symbols_list=None)  # Tất cả mã
    return df

# ============ BỘ LỌC SIDEBAR ============
with st.sidebar:
    st.header("🎯 Bộ lọc cổ phiếu")

    # Lọc theo sàn
    exchange = st.multiselect(
        "Sàn giao dịch",
        ["HOSE", "HNX", "UPCOM"],
        default=["HOSE"]
    )

    # Lọc theo nhóm ngành
    industry = st.multiselect(
        "Nhóm ngành (GICS)",
        ["Ngân hàng", "Bất động sản", "Công nghệ", "Thép",
         "Dầu khí", "Bán lẻ", "Dược phẩm", "Điện", "Chứng khoán"],
        default=[]
    )

    st.subheader("📊 Khối lượng giao dịch")
    min_vol = st.number_input("Khối lượng tối thiểu (nghìn CP)", min_value=0, value=100)
    max_vol = st.number_input("Khối lượng tối đa (nghìn CP)", min_value=0, value=10000)

    st.subheader("📉 Biến động giá")
    price_change = st.slider(
        "% Thay đổi giá so với hôm qua",
        min_value=-15.0, max_value=15.0,
        value=(-15.0, 15.0), step=0.5
    )

    st.subheader("💰 Giá cổ phiếu")
    price_range = st.slider(
        "Khoảng giá (nghìn VNĐ)",
        min_value=0, max_value=200,
        value=(0, 200)
    )

    apply_filter = st.button("🔍 Lọc cổ phiếu", type="primary", use_container_width=True)

# ============ HIỂN THỊ KẾT QUẢ ============
if apply_filter or True:  # Tự động load lần đầu
    with st.spinner("Đang tải dữ liệu thị trường..."):
        try:
            df = load_market_data()
            # TODO: Apply filters dựa trên df thực tế từ vnstock3
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi tải dữ liệu: {e}")
            st.info("💡 Đang dùng dữ liệu mẫu để demo...")
            # Demo data
            demo_df = pd.DataFrame({
                "Mã CP": ["VCB", "HPG", "VIC", "MSN", "FPT"],
                "Ngành": ["Ngân hàng", "Thép", "Bất động sản", "Thực phẩm", "Công nghệ"],
                "Giá": [85.5, 28.3, 42.1, 71.0, 95.2],
                "% Thay đổi": [1.2, -0.8, 2.5, -1.1, 3.0],
                "KL Giao dịch (nghìn)": [1200, 5400, 800, 950, 2100],
                "Sàn": ["HOSE"] * 5,
            })
            st.dataframe(demo_df, use_container_width=True)
