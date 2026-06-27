"""
data_loader.py
──────────────
Tải và cache dữ liệu toàn thị trường từ TCBS qua vnstock.
Cache 1h vào file Parquet để tránh lag khi reload trang.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

# ── Đường dẫn cache ────────────────────────────────────────────────────────────
CACHE_FILE = "cache_market_data.parquet"
CACHE_TTL_SECONDS = 3600  # 1 tiếng

# ── Cố gắng import vnstock ─────────────────────────────────────────────────────
try:
    from vnstock import (
        listing_companies,
        stock_historical_data,
        trading_price_board,
    )
    VNSTOCK_AVAILABLE = True
except ImportError:
    VNSTOCK_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
#  RSI CALCULATOR (thuần numpy — không cần TA-Lib)
# ══════════════════════════════════════════════════════════════════════════════
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    """Tính RSI cho 1 chuỗi giá, trả về giá trị RSI cuối cùng."""
    if len(series) < period + 1:
        return np.nan
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  LẤY DANH SÁCH MÃ
# ══════════════════════════════════════════════════════════════════════════════
def _get_ticker_list(exchange: str = "ALL") -> list:
    """Trả về danh sách tickers theo sàn."""
    try:
        df = listing_companies()
        # Cột tên có thể khác nhau tuỳ phiên bản vnstock
        ticker_col = next((c for c in df.columns if c.lower() in ["ticker", "symbol", "code"]), df.columns[0])
        exc_col    = next((c for c in df.columns if c.lower() in ["exchange", "san", "comGroupCode"]), None)

        tickers = df[ticker_col].dropna().str.strip().str.upper().tolist()
        if exc_col and exchange != "ALL":
            mask = df[exc_col].str.upper() == exchange.upper()
            tickers = df.loc[mask, ticker_col].dropna().str.strip().str.upper().tolist()
        return tickers
    except Exception as e:
        st.warning(f"⚠️ Không lấy được danh sách mã: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  XỬ LÝ 1 MÃ → CHỈ SỐ
# ══════════════════════════════════════════════════════════════════════════════
def _process_ticker(ticker: str, days: int = 200) -> dict | None:
    """Tải lịch sử giá 1 mã, tính các chỉ số cần thiết."""
    try:
        end   = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        df = stock_historical_data(ticker, start, end, "1D", type="stock", source="TCBS")

        if df is None or len(df) < 30:
            return None

        # Chuẩn hoá tên cột
        df.columns = [c.lower() for c in df.columns]
        close_col  = next((c for c in df.columns if c in ["close", "price"]), None)
        vol_col    = next((c for c in df.columns if c in ["volume"]), None)
        val_col    = next((c for c in df.columns if c in ["value", "tradingvalue"]), None)

        if close_col is None:
            return None

        df = df.sort_values("time" if "time" in df.columns else df.columns[0]).reset_index(drop=True)
        prices = df[close_col].astype(float)

        # Giá trị GD bình quân 20 phiên (tỷ đồng)
        if val_col:
            avg_val = df[val_col].astype(float).tail(20).mean() / 1e9
        elif vol_col:
            avg_val = (prices * df[vol_col].astype(float)).tail(20).mean() / 1e9
        else:
            avg_val = np.nan

        # % thay đổi
        def pct(n_days):
            if len(prices) >= n_days + 1:
                return round((prices.iloc[-1] / prices.iloc[-1 - n_days] - 1) * 100, 2)
            return np.nan

        ret_1m  = pct(21)
        ret_3m  = pct(63)
        ret_6m  = pct(126)
        rsi_val = calc_rsi(prices)

        return {
            "Mã":              ticker,
            "Giá":             round(prices.iloc[-1], 2),
            "Giá trị GD TB (tỷ)": round(avg_val, 2) if not np.isnan(avg_val) else np.nan,
            "% 1 tháng":      ret_1m,
            "% 3 tháng":      ret_3m,
            "% 6 tháng":      ret_6m,
            "RSI":             rsi_val,
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD & CACHE TOÀN BỘ THỊ TRƯỜNG
# ══════════════════════════════════════════════════════════════════════════════
def _is_cache_fresh() -> bool:
    if not os.path.exists(CACHE_FILE):
        return False
    age = time.time() - os.path.getmtime(CACHE_FILE)
    return age < CACHE_TTL_SECONDS


def _load_from_cache() -> pd.DataFrame:
    return pd.read_parquet(CACHE_FILE)


def _save_to_cache(df: pd.DataFrame):
    df.to_parquet(CACHE_FILE, index=False)


# ── DEMO DATA (khi vnstock chưa cài hoặc không có mạng) ───────────────────────
def _generate_demo_data() -> pd.DataFrame:
    """Tạo dữ liệu mẫu để test giao diện."""
    np.random.seed(42)
    tickers = [
        "VNM","VIC","VHM","VCB","BID","CTG","TCB","MBB","VPB","HPG",
        "MSN","SAB","GAS","PLX","POW","PVD","VJC","HVN","FPT","MWG",
        "DXG","NVL","PDR","KDH","VRE","CII","SHB","STB","EIB","LPB",
        "ACB","OCB","HDB","SSB","TPB","VIB","ABB","KLB","VBB","NVB",
        "SSI","HCM","VCI","MBS","BSI","SBS","AGR","VFS","CTS","APG",
        "GEX","REE","PC1","TV2","BWE","SZC","KBC","IDC","BCM","SNZ",
        "VCG","HBC","CTD","LCG","FCN","ROS","DIG","SCG","DPM","DCM",
        "PAN","HAG","HNG","TAR","ANV","CMX","IDI","VHC","MPC","FMC",
    ]
    exchanges = np.random.choice(["HOSE","HNX","UPCOM"], len(tickers), p=[0.6,0.25,0.15])
    
    rows = []
    for i, tk in enumerate(tickers):
        gia = round(np.random.uniform(5, 150), 1)
        rows.append({
            "Mã":               tk,
            "Sàn":              exchanges[i],
            "Giá":              gia,
            "Giá trị GD TB (tỷ)": round(abs(np.random.lognormal(3, 1.5)), 1),
            "% 1 tháng":        round(np.random.normal(2, 12), 2),
            "% 3 tháng":        round(np.random.normal(5, 20), 2),
            "% 6 tháng":        round(np.random.normal(10, 30), 2),
            "RSI":              round(np.random.uniform(20, 80), 1),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_market_data():
    """
    Entry point chính.  
    1. Nếu Parquet cache còn mới → đọc thẳng (nhanh nhất).  
    2. Nếu vnstock có → fetch live + lưu cache.  
    3. Fallback → demo data.
    """

    # ── Cache file còn mới ────────────────────────────────────────────────
    if _is_cache_fresh():
        try:
            df = _load_from_cache()
            ts = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).strftime("%H:%M %d/%m/%Y")
            return df, f"{ts} (cache)"
        except Exception:
            pass

    # ── Không có vnstock → demo ───────────────────────────────────────────
    if not VNSTOCK_AVAILABLE:
        st.info(
            "ℹ️ **vnstock chưa được cài.** Đang hiển thị dữ liệu demo.\n\n"
            "Chạy `pip install vnstock` rồi khởi động lại."
        )
        df = _generate_demo_data()
        _save_to_cache(df)
        return df, f"{datetime.now().strftime('%H:%M %d/%m/%Y')} (demo)"

    # ── Fetch live từ TCBS ────────────────────────────────────────────────
    # Thử dùng trading_price_board để lấy nhanh (1 call = toàn sàn)
    try:
        df = _fetch_via_price_board()
        if df is not None and len(df) > 50:
            _save_to_cache(df)
            ts = datetime.now().strftime("%H:%M %d/%m/%Y")
            return df, f"{ts} (live)"
    except Exception as e:
        st.warning(f"Price board lỗi: {e} — đang dùng demo data")

    # Fallback demo
    df = _generate_demo_data()
    _save_to_cache(df)
    return df, f"{datetime.now().strftime('%H:%M %d/%m/%Y')} (demo)"


def _fetch_via_price_board() -> pd.DataFrame | None:
    """
    Dùng trading_price_board của vnstock3 để lấy snapshot toàn thị trường.
    Sau đó lấy thêm lịch sử giá top N mã để tính % thay đổi và RSI.
    """
    from vnstock import trading_price_board, listing_companies

    # Lấy danh sách mã
    companies = listing_companies()
    ticker_col = next((c for c in companies.columns if c.lower() in ["ticker","symbol","code"]), companies.columns[0])
    exc_col    = next((c for c in companies.columns if "exchange" in c.lower() or c.lower()=="san"), None)

    tickers = companies[ticker_col].dropna().str.strip().str.upper().tolist()[:500]  # Giới hạn 500 mã để không quá chậm

    # Price board snapshot (1 call)
    pb = trading_price_board(tickers)

    if pb is None or pb.empty:
        return None

    pb.columns = [c.lower().replace(" ", "_") for c in pb.columns]

    # Map cột
    col_map = {}
    for raw, norm in [("ticker","Mã"), ("exchange","Sàn"), ("last_price","Giá"),
                      ("last","Giá"), ("matchedprice","Giá"), ("close","Giá")]:
        if raw in pb.columns:
            col_map[raw] = norm

    pb = pb.rename(columns=col_map)

    if "Mã" not in pb.columns:
        return None
    if "Sàn" not in pb.columns:
        pb["Sàn"] = "HOSE"

    # Tính lịch sử cho từng mã (batch nhỏ)
    records = []
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=200)).strftime("%Y-%m-%d")

    progress = st.progress(0, text="Đang tải lịch sử giá...")
    total = min(len(pb), 300)

    for i, row in enumerate(pb.head(total).itertuples()):
        if i % 20 == 0:
            progress.progress(i / total, text=f"Đang xử lý {i}/{total} mã...")
        
        ticker = getattr(row, "Mã", None)
        if not ticker:
            continue

        try:
            hist = stock_historical_data(str(ticker), start_date, end_date, "1D",
                                         type="stock", source="TCBS")
            if hist is None or len(hist) < 30:
                continue

            hist.columns = [c.lower() for c in hist.columns]
            close_col = next((c for c in hist.columns if c in ["close","price"]), None)
            val_col   = next((c for c in hist.columns if c in ["value","tradingvalue"]), None)
            vol_col   = next((c for c in hist.columns if c in ["volume"]), None)

            if not close_col:
                continue

            prices = hist[close_col].astype(float)

            if val_col:
                avg_val = hist[val_col].astype(float).tail(20).mean() / 1e9
            elif vol_col:
                avg_val = (prices * hist[vol_col].astype(float)).tail(20).mean() / 1e9
            else:
                avg_val = np.nan

            def pct(n):
                if len(prices) >= n + 1:
                    return round((prices.iloc[-1] / prices.iloc[-1-n] - 1) * 100, 2)
                return np.nan

            records.append({
                "Mã":  ticker,
                "Sàn": getattr(row, "Sàn", "HOSE"),
                "Giá": round(float(prices.iloc[-1]), 2),
                "Giá trị GD TB (tỷ)": round(avg_val, 2) if not np.isnan(avg_val) else np.nan,
                "% 1 tháng":  pct(21),
                "% 3 tháng":  pct(63),
                "% 6 tháng":  pct(126),
                "RSI":        calc_rsi(prices),
            })
        except Exception:
            continue

        time.sleep(0.05)  # Tránh rate limit

    progress.empty()
    return pd.DataFrame(records) if records else None


# ── Summary stats ─────────────────────────────────────────────────────────────
def get_summary_stats(df: pd.DataFrame) -> dict:
    return {
        "total":     len(df),
        "tang":      (df["% 1 tháng"] > 0).sum(),
        "giam":      (df["% 1 tháng"] < 0).sum(),
        "rsi_ob":    (df["RSI"] > 70).sum(),
        "rsi_os":    (df["RSI"] < 30).sum(),
        "avg_val":   df["Giá trị GD TB (tỷ)"].median(),
    }
