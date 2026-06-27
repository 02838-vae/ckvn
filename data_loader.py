"""
data_loader.py
Tải toàn bộ cổ phiếu HOSE+HNX+UPCOM, lưu vào Parquet để dùng lại.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os, time, warnings
warnings.filterwarnings("ignore")

CACHE_FILE = "market_data.parquet"

# ── Detect vnstock ─────────────────────────────────────────────────────────────
VNSTOCK_AVAILABLE = False
VNSTOCK_V3 = False

try:
    from vnstock3 import Vnstock as _VN3
    VNSTOCK_V3 = True
    VNSTOCK_AVAILABLE = True
except ImportError:
    pass

if not VNSTOCK_AVAILABLE:
    try:
        from vnstock import listing_companies as _lc, stock_historical_data as _shd
        VNSTOCK_AVAILABLE = True
    except ImportError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  RSI
# ══════════════════════════════════════════════════════════════════════════════
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return np.nan
    delta    = series.diff().dropna()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi      = 100 - (100 / (1 + rs))
    v = rsi.iloc[-1]
    return round(float(v), 2) if not np.isnan(v) else np.nan


# ══════════════════════════════════════════════════════════════════════════════
#  DEMO DATA
# ══════════════════════════════════════════════════════════════════════════════
def _demo_data() -> pd.DataFrame:
    np.random.seed(42)
    tickers = [
        "VNM","VIC","VHM","VCB","BID","CTG","TCB","MBB","VPB","HPG",
        "MSN","SAB","GAS","PLX","POW","FPT","MWG","DXG","NVL","PDR",
        "KDH","VRE","SHB","STB","EIB","LPB","ACB","OCB","HDB","SSB",
        "TPB","VIB","SSI","HCM","VCI","MBS","GEX","REE","PC1","KBC",
        "VCG","HBC","CTD","DPM","DCM","PAN","HAG","VHC","MPC","FMC",
        "VFS","CTS","BSI","SBS","AGR","NVB","ABB","KLB","ROS","DIG",
        "VBB","BWE","SZC","IDC","BCM","SNZ","LCG","FCN","SCG","ANV",
        "CMX","IDI","TAR","HNG","PVD","VJC","HVN","POW","PLX","CII",
    ]
    excs = np.random.choice(["HOSE","HNX","UPCOM"], len(tickers), p=[0.6,0.25,0.15])
    rows = []
    for i, tk in enumerate(tickers):
        rows.append({
            "Mã":                  tk,
            "Sàn":                 excs[i],
            "Giá":                 round(np.random.uniform(5, 150), 1),
            "Giá trị GD TB (tỷ)": round(abs(np.random.lognormal(3, 1.5)), 1),
            "% 1 tháng":           round(np.random.normal(2, 12), 2),
            "% 3 tháng":           round(np.random.normal(5, 20), 2),
            "% 6 tháng":           round(np.random.normal(10, 30), 2),
            "RSI":                 round(np.random.uniform(20, 80), 1),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  XỬ LÝ 1 MÃ
# ══════════════════════════════════════════════════════════════════════════════
def _process_one_v2(tk: str, exc: str, start: str, end: str) -> dict | None:
    """vnstock cũ"""
    try:
        hist = _shd(tk, start, end, "1D", type="stock", source="TCBS")
        if hist is None or len(hist) < 30:
            return None
        hist.columns = [c.lower() for c in hist.columns]
        close_col = next((c for c in hist.columns if c in ["close","price"]), None)
        if not close_col:
            return None
        val_col = next((c for c in hist.columns if c in ["value","tradingvalue"]), None)
        vol_col = next((c for c in hist.columns if c == "volume"), None)
        prices  = hist[close_col].astype(float)
        avg_val = np.nan
        if val_col:
            avg_val = hist[val_col].astype(float).tail(20).mean() / 1e9
        elif vol_col:
            avg_val = (prices * hist[vol_col].astype(float)).tail(20).mean() / 1e9
        def pct(n):
            return round((prices.iloc[-1]/prices.iloc[-1-n]-1)*100,2) if len(prices)>=n+1 else np.nan
        return {
            "Mã": tk, "Sàn": exc,
            "Giá": round(float(prices.iloc[-1]),2),
            "Giá trị GD TB (tỷ)": round(avg_val,2) if not np.isnan(avg_val) else np.nan,
            "% 1 tháng": pct(21), "% 3 tháng": pct(63), "% 6 tháng": pct(126),
            "RSI": calc_rsi(prices),
        }
    except Exception:
        return None


def _process_one_v3(vn3_cls, tk: str, exc: str, start: str, end: str) -> dict | None:
    """vnstock3"""
    try:
        stock = vn3_cls(source="TCBS").stock(symbol=tk, source="TCBS")
        hist  = stock.quote.history(start=start, end=end, interval="1D")
        if hist is None or len(hist) < 30:
            return None
        hist.columns = [c.lower() for c in hist.columns]
        close_col = next((c for c in hist.columns if c == "close"), None)
        if not close_col:
            return None
        val_col = next((c for c in hist.columns if c in ["value","tradingvalue"]), None)
        vol_col = next((c for c in hist.columns if c == "volume"), None)
        prices  = hist[close_col].astype(float)
        avg_val = np.nan
        if val_col:
            avg_val = hist[val_col].astype(float).tail(20).mean() / 1e9
        elif vol_col:
            avg_val = (prices * hist[vol_col].astype(float)).tail(20).mean() / 1e9
        def pct(n):
            return round((prices.iloc[-1]/prices.iloc[-1-n]-1)*100,2) if len(prices)>=n+1 else np.nan
        return {
            "Mã": tk, "Sàn": exc,
            "Giá": round(float(prices.iloc[-1]),2),
            "Giá trị GD TB (tỷ)": round(avg_val,2) if not np.isnan(avg_val) else np.nan,
            "% 1 tháng": pct(21), "% 3 tháng": pct(63), "% 6 tháng": pct(126),
            "RSI": calc_rsi(prices),
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  LẤY DANH SÁCH MÃ
# ══════════════════════════════════════════════════════════════════════════════
def _get_tickers_v2():
    df = _lc()
    tc = next((c for c in df.columns if c.lower() in ["ticker","symbol","code"]), df.columns[0])
    ec = next((c for c in df.columns if "exchange" in c.lower()), None)
    tickers = []
    for _, row in df.iterrows():
        tk  = str(row[tc]).strip().upper()
        exc = str(row[ec]).strip().upper() if ec else "HOSE"
        if tk:
            tickers.append((tk, exc))
    return tickers


def _get_tickers_v3():
    vn = _VN3(source="VCI")
    listing = vn.stock(symbol="VNM", source="VCI").listing
    df  = listing.all_symbols()
    tc  = next((c for c in df.columns if c.lower() in ["ticker","symbol","code"]), df.columns[0])
    ec  = next((c for c in df.columns if "exchange" in c.lower()), None)
    tickers = []
    for _, row in df.iterrows():
        tk  = str(row[tc]).strip().upper()
        exc = str(row[ec]).strip().upper() if ec else "HOSE"
        if tk:
            tickers.append((tk, exc))
    return tickers


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC: fetch_and_save_all
# ══════════════════════════════════════════════════════════════════════════════
def fetch_and_save_all() -> tuple[bool, str]:
    """
    Tải toàn bộ dữ liệu, lưu vào CACHE_FILE.
    Trả về (success: bool, message: str).
    """
    if not VNSTOCK_AVAILABLE:
        # Dùng demo
        df = _demo_data()
        df.to_parquet(CACHE_FILE, index=False)
        return True, f"Đã lưu dữ liệu demo ({len(df)} mã) — cài vnstock3 để dùng dữ liệu thật."

    end_str   = datetime.today().strftime("%Y-%m-%d")
    start_str = (datetime.today() - timedelta(days=210)).strftime("%Y-%m-%d")

    # Lấy danh sách mã
    try:
        tickers = _get_tickers_v3() if VNSTOCK_V3 else _get_tickers_v2()
    except Exception as e:
        return False, f"Không lấy được danh sách mã: {e}"

    if not tickers:
        return False, "Danh sách mã rỗng."

    records  = []
    total    = len(tickers)
    progress = st.progress(0.0, text=f"Đang xử lý 0/{total} mã...")
    err_count = 0

    for i, (tk, exc) in enumerate(tickers):
        if i % 10 == 0:
            pct_done = i / total
            progress.progress(pct_done, text=f"Đang tải: {tk} ({i}/{total})")

        if VNSTOCK_V3:
            rec = _process_one_v3(_VN3, tk, exc, start_str, end_str)
        else:
            rec = _process_one_v2(tk, exc, start_str, end_str)

        if rec:
            records.append(rec)
        else:
            err_count += 1

        time.sleep(0.05)

    progress.empty()

    if not records:
        # Fallback demo
        df = _demo_data()
        df.to_parquet(CACHE_FILE, index=False)
        return True, f"Không fetch được dữ liệu thật, dùng demo ({len(df)} mã)."

    df = pd.DataFrame(records)
    df.to_parquet(CACHE_FILE, index=False)
    ts = datetime.now().strftime("%H:%M %d/%m/%Y")
    return True, f"Đã tải {len(df)}/{total} mã (lỗi: {err_count}). Lưu lúc {ts}."


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC: load_saved_data
# ══════════════════════════════════════════════════════════════════════════════
def load_saved_data() -> pd.DataFrame | None:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        return pd.read_parquet(CACHE_FILE)
    except Exception:
        return None


# ── Summary stats ──────────────────────────────────────────────────────────────
def get_summary_stats(df: pd.DataFrame) -> dict:
    return {
        "total":   len(df),
        "tang":    int((df["% 1 tháng"] > 0).sum()) if "% 1 tháng" in df.columns else 0,
        "giam":    int((df["% 1 tháng"] < 0).sum()) if "% 1 tháng" in df.columns else 0,
        "rsi_ob":  int((df["RSI"] > 70).sum()) if "RSI" in df.columns else 0,
        "rsi_os":  int((df["RSI"] < 30).sum()) if "RSI" in df.columns else 0,
        "avg_val": float(df["Giá trị GD TB (tỷ)"].median()) if "Giá trị GD TB (tỷ)" in df.columns else 0.0,
    }
