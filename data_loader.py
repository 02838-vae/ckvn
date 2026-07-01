"""
data_loader.py
Tải toàn bộ cổ phiếu HOSE+HNX+UPCOM, lưu Parquet.
Hỗ trợ vnstock3 >= 0.3 và vnstock cũ <= 0.2, fallback demo.
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
#  RSI — tính cho nhiều timeframe
#  series: giá đóng cửa theo khung (daily / weekly / monthly / ...)
# ══════════════════════════════════════════════════════════════════════════════
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    s = series.dropna()
    if len(s) < period + 1:
        return np.nan
    delta    = s.diff().dropna()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    v   = rsi.iloc[-1]
    return round(float(v), 2) if pd.notna(v) else np.nan


def _resample_rsi(daily_close: pd.Series, daily_dates, tf: str) -> float:
    """
    Resample series theo tf rồi tính RSI 14 phiên.
    tf: '1D','1W','1ME','3ME','6ME'
    """
    try:
        s = pd.Series(daily_close.values,
                      index=pd.to_datetime(daily_dates))
        s = s.sort_index()
        if tf == "1D":
            resampled = s
        else:
            resampled = s.resample(tf).last().dropna()
        return calc_rsi(resampled)
    except Exception:
        return np.nan


# ══════════════════════════════════════════════════════════════════════════════
#  % THAY ĐỔI GIÁ
#  close  = giá đóng cửa mỗi ngày (sorted asc)
#  open_  = giá mở cửa mỗi ngày
#  Công thức: (close cuối kỳ - open đầu kỳ) / open đầu kỳ * 100
# ══════════════════════════════════════════════════════════════════════════════
def _pct_change(close: pd.Series, open_: pd.Series, n_sessions: int) -> float:
    """n_sessions = số phiên GD cần nhìn lại"""
    if len(close) < 2 or len(open_) < 2:
        return np.nan
    n = min(n_sessions, len(close) - 1)
    price_end   = float(close.iloc[-1])
    price_start = float(open_.iloc[-1 - n])
    if price_start == 0:
        return np.nan
    return round((price_end - price_start) / price_start * 100, 2)


# ══════════════════════════════════════════════════════════════════════════════
#  GTGD BÌNH QUÂN / NGÀY
#  = tổng value trong tháng gần nhất / số phiên GD trong tháng đó
# ══════════════════════════════════════════════════════════════════════════════
def _avg_daily_value(dates, values: pd.Series) -> float:
    try:
        df = pd.DataFrame({"date": pd.to_datetime(dates), "val": values.values})
        df = df.sort_values("date")
        last_month_start = df["date"].max() - pd.DateOffset(months=1)
        df_m = df[df["date"] >= last_month_start]
        if df_m.empty:
            return np.nan
        return round(df_m["val"].sum() / len(df_m) / 1e9, 3)   # tỷ đồng
    except Exception:
        return np.nan


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
        "CMX","IDI","TAR","HNG","PVD","VJC","HVN","CII","VRE","MSN",
        "TCH","NLG","DXS","CEO","TDH","IJC","HDG","SIP","PHR","GVR",
        "VPH","DBC","BAF","GTN","MML","ASM","SAM","TIG","HHV","CNG",
        "PPC","NT2","VSH","SHP","TMP","REE","TV2","BWE","SZC","GEG",
        "HAH","GMD","PHP","VSC","DVP","SGP","MVN","VOS","VNA","PVT",
    ]
    excs = np.random.choice(["HOSE","HNX","UPCOM"], len(tickers), p=[0.6,0.25,0.15])
    rows = []
    for i, tk in enumerate(tickers):
        rows.append({
            "Mã":                   tk,
            "Sàn":                  excs[i],
            "Giá":                  round(np.random.uniform(5, 150), 1),
            "GTGD TB/ngày (tỷ)":    round(abs(np.random.lognormal(1.5, 1.5)), 3),
            "% 1 tuần":             round(np.random.normal(0.5,  5),  2),
            "% 1 tháng":            round(np.random.normal(2,   12),  2),
            "% 3 tháng":            round(np.random.normal(5,   20),  2),
            "% 6 tháng":            round(np.random.normal(10,  30),  2),
            "% 1 năm":              round(np.random.normal(15,  40),  2),
            "RSI 1D":               round(np.random.uniform(20, 80),  1),
            "RSI 1W":               round(np.random.uniform(20, 80),  1),
            "RSI 1M":               round(np.random.uniform(20, 80),  1),
            "RSI 3M":               round(np.random.uniform(20, 80),  1),
            "RSI 6M":               round(np.random.uniform(20, 80),  1),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  XỬ LÝ 1 MÃ → dict chỉ số
# ══════════════════════════════════════════════════════════════════════════════
def _build_record(tk: str, exc: str, hist: pd.DataFrame) -> dict | None:
    try:
        hist = hist.copy()
        hist.columns = [c.lower().strip() for c in hist.columns]

        # Cột giá
        close_col = next((c for c in hist.columns if c == "close"), None)
        open_col  = next((c for c in hist.columns if c == "open"),  None)
        val_col   = next((c for c in hist.columns if c in ["value","tradingvalue","trade_value"]), None)
        vol_col   = next((c for c in hist.columns if c == "volume"), None)
        date_col  = next((c for c in hist.columns if c in ["time","date","tradingdate"]), None)

        if close_col is None or len(hist) < 15:
            return None

        hist = hist.sort_values(date_col) if date_col else hist
        hist = hist.reset_index(drop=True)

        close  = hist[close_col].astype(float)
        open_  = hist[open_col].astype(float)  if open_col  else close
        dates  = hist[date_col]                if date_col  else pd.RangeIndex(len(hist))

        # GTGD
        if val_col:
            val_s = hist[val_col].astype(float)
        elif vol_col:
            val_s = close * hist[vol_col].astype(float)
        else:
            val_s = pd.Series([np.nan] * len(hist))

        avg_val = _avg_daily_value(dates, val_s)

        # % thay đổi  (1T≈5p, 1M≈21p, 3M≈63p, 6M≈126p, 1Y≈252p)
        pct_1w  = _pct_change(close, open_, 5)
        pct_1m  = _pct_change(close, open_, 21)
        pct_3m  = _pct_change(close, open_, 63)
        pct_6m  = _pct_change(close, open_, 126)
        pct_1y  = _pct_change(close, open_, 252)

        # RSI theo timeframe
        rsi_1d = calc_rsi(close)
        rsi_1w = _resample_rsi(close, dates, "1W")
        rsi_1m = _resample_rsi(close, dates, "1ME")
        rsi_3m = _resample_rsi(close, dates, "3ME")
        rsi_6m = _resample_rsi(close, dates, "6ME")

        return {
            "Mã":                  tk,
            "Sàn":                 exc,
            "Giá":                 round(float(close.iloc[-1]), 2),
            "GTGD TB/ngày (tỷ)":   avg_val,
            "% 1 tuần":            pct_1w,
            "% 1 tháng":           pct_1m,
            "% 3 tháng":           pct_3m,
            "% 6 tháng":           pct_6m,
            "% 1 năm":             pct_1y,
            "RSI 1D":              rsi_1d,
            "RSI 1W":              rsi_1w,
            "RSI 1M":              rsi_1m,
            "RSI 3M":              rsi_3m,
            "RSI 6M":              rsi_6m,
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
    out = []
    for _, row in df.iterrows():
        tk  = str(row[tc]).strip().upper()
        exc = str(row[ec]).strip().upper() if ec else "HOSE"
        if tk and tk != "NAN":
            out.append((tk, exc))
    return out


def _get_tickers_v3():
    vn  = _VN3(source="VCI")
    df  = vn.stock(symbol="VNM", source="VCI").listing.all_symbols()
    tc  = next((c for c in df.columns if c.lower() in ["ticker","symbol","code"]), df.columns[0])
    ec  = next((c for c in df.columns if "exchange" in c.lower()), None)
    out = []
    for _, row in df.iterrows():
        tk  = str(row[tc]).strip().upper()
        exc = str(row[ec]).strip().upper() if ec else "HOSE"
        if tk and tk != "NAN":
            out.append((tk, exc))
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH LỊCH SỬ 1 MÃ
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_hist_v2(tk, start, end):
    return _shd(tk, start, end, "1D", type="stock", source="TCBS")

def _fetch_hist_v3(tk, start, end):
    stock = _VN3(source="TCBS").stock(symbol=tk, source="TCBS")
    return stock.quote.history(start=start, end=end, interval="1D")


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC: fetch_and_save_all
# ══════════════════════════════════════════════════════════════════════════════
def fetch_and_save_all() -> tuple[bool, str]:
    if not VNSTOCK_AVAILABLE:
        df = _demo_data()
        df.to_parquet(CACHE_FILE, index=False)
        return True, f"vnstock chưa cài — đã lưu {len(df)} mã demo. Cài `pip install vnstock3` để dùng dữ liệu thật."

    # 400 ngày để đủ tính 1 năm (252 phiên) + RSI 14 phiên buffer
    end_str   = datetime.today().strftime("%Y-%m-%d")
    start_str = (datetime.today() - timedelta(days=400)).strftime("%Y-%m-%d")

    # Danh sách mã
    try:
        tickers = _get_tickers_v3() if VNSTOCK_V3 else _get_tickers_v2()
    except Exception as e:
        return False, f"Không lấy được danh sách mã: {e}"

    if not tickers:
        return False, "Danh sách mã rỗng."

    total    = len(tickers)
    records  = []
    err_cnt  = 0
    progress = st.progress(0.0, text=f"Bắt đầu tải {total} mã...")

    for i, (tk, exc) in enumerate(tickers):
        if i % 15 == 0:
            progress.progress(i / total, text=f"Đang tải: {tk}  ({i}/{total})")
        try:
            hist = _fetch_hist_v3(tk, start_str, end_str) if VNSTOCK_V3 \
                   else _fetch_hist_v2(tk, start_str, end_str)
            rec  = _build_record(tk, exc, hist) if hist is not None else None
            if rec:
                records.append(rec)
            else:
                err_cnt += 1
        except Exception:
            err_cnt += 1
        time.sleep(0.04)

    progress.empty()

    if not records:
        df = _demo_data()
        df.to_parquet(CACHE_FILE, index=False)
        return True, f"Không fetch được dữ liệu thật → lưu demo ({len(df)} mã)."

    df = pd.DataFrame(records)
    df.to_parquet(CACHE_FILE, index=False)
    ts = datetime.now().strftime("%H:%M %d/%m/%Y")
    return True, f"Đã tải {len(df)}/{total} mã (lỗi/bỏ qua: {err_cnt}). Lưu lúc {ts}."


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
        "tang":    int((df["% 1 tháng"] > 0).sum())    if "% 1 tháng"         in df.columns else 0,
        "giam":    int((df["% 1 tháng"] < 0).sum())    if "% 1 tháng"         in df.columns else 0,
        "rsi_ob":  int((df["RSI 1D"]    > 70).sum())   if "RSI 1D"            in df.columns else 0,
        "rsi_os":  int((df["RSI 1D"]    < 30).sum())   if "RSI 1D"            in df.columns else 0,
        "avg_val": float(df["GTGD TB/ngày (tỷ)"].median()) if "GTGD TB/ngày (tỷ)" in df.columns else 0.0,
    }
