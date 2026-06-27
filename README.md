# 📈 Stock Screener VN — Streamlit App

Ứng dụng lọc cổ phiếu Việt Nam theo:
- 💰 Giá trị giao dịch bình quân (tỷ đồng/ngày)
- 📊 % Tăng/giảm theo 1 tháng / 3 tháng / 6 tháng
- 📉 RSI 14 phiên (quá mua / quá bán / trung tính)
- 📌 Sàn: HOSE / HNX / UPCOM

---

## 🚀 Cài đặt & Chạy

### 1. Yêu cầu

- Python 3.10+
- pip

### 2. Cài thư viện

```bash
pip install -r requirements.txt
```

### 3. Chạy app

```bash
streamlit run app.py
```

Mở trình duyệt tại: http://localhost:8501

---

## 📁 Cấu trúc dự án

```
stock_screener/
├── app.py              # Giao diện chính Streamlit
├── data_loader.py      # Load + cache dữ liệu từ TCBS/vnstock
├── filters.py          # Logic lọc cổ phiếu
├── components.py       # UI components (bảng, metrics bar)
├── requirements.txt    # Thư viện cần thiết
└── README.md
```

---

## 💡 Cách hoạt động

### Nguồn dữ liệu
- **vnstock** → TCBS API (miễn phí, không cần key)
- Lấy lịch sử giá 200 ngày cho mỗi mã

### Cache thông minh
- Lần đầu: fetch từ TCBS, lưu vào `cache_market_data.parquet`
- Các lần sau (trong vòng 1 tiếng): đọc từ cache → **cực nhanh**
- `@st.cache_data(ttl=3600)` tránh re-fetch không cần thiết

### Chỉ số tính toán
| Chỉ số | Công thức |
|--------|-----------|
| % 1 tháng | (Giá hôm nay / Giá 21 phiên trước - 1) × 100 |
| % 3 tháng | (Giá hôm nay / Giá 63 phiên trước - 1) × 100 |
| % 6 tháng | (Giá hôm nay / Giá 126 phiên trước - 1) × 100 |
| RSI | EWM-RSI 14 phiên (Wilder smoothing) |
| GT GD TB | Trung bình 20 phiên gần nhất (tỷ đồng) |

---

## ⚠️ Lưu ý

- **vnstock chưa cài**: App tự dùng demo data để test giao diện
- **Rate limit**: App giới hạn 300–500 mã/lần fetch để tránh bị block
- Dữ liệu chỉ mang tính **tham khảo**, không phải khuyến nghị đầu tư

---

## 🛠️ Nâng cấp tiếp theo

- [ ] Thêm biểu đồ giá (candlestick) khi click vào mã
- [ ] Lọc theo ngành (VNM sector)
- [ ] Alert email khi mã đáp ứng điều kiện
- [ ] Tích hợp dữ liệu tài chính (P/E, ROE, EPS)
- [ ] Deploy lên Streamlit Cloud
