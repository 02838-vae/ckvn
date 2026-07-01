# 📈 Stock Screener VN

Lọc cổ phiếu Việt Nam (HOSE · HNX · UPCOM) theo:
- 💰 Giá trị GD bình quân/ngày (≥200tr / ≥500tr / ≥1tỷ / ≥10tỷ)
- 📊 % Tăng/giảm giá (1 tuần / 1 tháng / 3 tháng / 6 tháng / 1 năm)
- 📉 RSI 14 phiên theo khung (1D / 1W / 1M / 3M / 6M)

## Cài đặt & chạy

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Luồng sử dụng

1. Nhấn **"Tải dữ liệu tất cả cổ phiếu"** → fetch từ TCBS, lưu `market_data.parquet`
2. Lần sau vào lại → chọn **"Dùng dữ liệu đã lưu"** (nhanh) hoặc **"Tải lại từ đầu"**
3. Nhấn các nút **Giá trị GD / % Tăng giảm / RSI** → chọn tiêu chí trong panel
4. Nhấn **"Hiện kết quả"** → xem bảng + tải CSV

## Công thức tính

| Chỉ số | Công thức |
|--------|-----------|
| GTGD TB/ngày | Tổng value tháng gần nhất ÷ số phiên GD trong tháng |
| % thay đổi | (Giá đóng cửa cuối kỳ − Giá mở cửa đầu kỳ) ÷ Giá mở cửa đầu kỳ × 100 |
| RSI | EWM-RSI 14 phiên, resample theo khung (D/W/M/3M/6M) |

## Cấu trúc

```
app.py          — Giao diện chính, luồng UX
data_loader.py  — Fetch + cache + tính chỉ số
filters.py      — Logic lọc
components.py   — Bảng HTML kết quả
requirements.txt
```

> Dữ liệu từ TCBS qua vnstock3 · Chỉ tham khảo, không phải khuyến nghị đầu tư
