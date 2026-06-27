"""
data_loader.py — hỗ trợ vnstock3 (>= 0.3) và vnstock cũ (<= 0.2)
Cache Parquet 1h để tránh lag.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os, time, warnings
warnings.filterwarnings("ignore")

CACHE_FILE = "cache_market_data.parquet"
CACHE_TTL_SECONDS = 3600

# ── Detect vnstock version ─────────────────────────────────────────────────────
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
#  RSI (thuần numpy)
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
    return round(float(rsi.iloc[-1]), 2) if not rsi.empty else np.nan


# ══════════════════════════════════════════════════════════════════════════════
#  DEMO DATA
# ══════════════════════════════════════════════════════════════════════════════
def _generate_demo_data() -> pd.DataFrame:
    np.random.seed(42)
    tickers = [
        "VNM","VIC","VHM","VCB","BID","CTG","TCB","MBB","VPB","HPG",
        "MSN","SAB","GAS","PLX","POW","PVD","VJC","HVN","FPT","MWG",
        "DXG","NVL","PDR","KDH","VRE","CII","SHB","STB","EIB","LPB",
        "ACB","OCB","HDB","SSB","TPB","VIB","SSI","HCM","VCI","MBS",
        "GEX","REE","PC1","TV2","BWE","SZC","KBC","IDC","BCM","SNZ",
        "VCG","HBC","CTD","LCG","FCN","ROS","DIG","SCG","DPM","DCM",
        "PAN","HAG","HNG","TAR","ANV","CMX","IDI","VHC","MPC","FMC",
        "VFS","CTS","APG","BSI","SBS","AGR","VBB","NVB","ABB","KLB",
    ]
    exchanges = np.random.choice(["HOSE","HNX","UPCOM"], len(tickers), p=[0.6,0.25,0.15])
    rows = []
    for i, tk in enumerate(tickers):
        rows.append({
            "Mã":                  tk,
            "Sàn":                 exchanges[i],
            "Giá":                 round(np.random.uniform(5, 150), 1),
            "Giá trị GD TB (tỷ)": round(abs(np.random.lognormal(3, 1.5)), 1),
            "% 1 tháng":           round(np.random.normal(2, 12), 2),
            "% 3 tháng":           round(np.random.normal(5, 20), 2),
            "% 6 tháng":           round(np.random.normal(10, 30), 2),
            "RSI":                 round(np.random.uniform(20, 80), 1),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH QUA VNSTOCK3
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_v3(max_tickers: int = 300) -> pd.DataFrame | None:
    """Dùng vnstock3 API."""
    try:
        vn = _VN3(source="TCBS")
        # Lấy danh sách mã
        listing = vn.stock(symbol="VNM", source="VCI").listing
        df_list = listing.all_symbols()

        ticker_col = next((c for c in df_list.columns
                           if c.lower() in ["ticker","symbol","code"]), df_list.columns[0])
        exc_col    = next((c for c in df_list.columns
                           if "exchange" in c.lower()), None)

        tickers = df_list[ticker_col].dropna().str.strip().str.upper().tolist()[:max_tickers]

        end_dt   = datetime.today()
        start_dt = end_dt - timedelta(days=200)

        records = []
        progress = st.progress(0, text="Đang tải dữ liệu...")
        total = len(tickers)

        for i, tk in enumerate(tickers):
            if i % 20 == 0:
                progress.progress(i / total, text=f"Xử lý {i}/{total} mã...")
            try:
                stock = _VN3(source="TCBS").stock(symbol=tk, source="TCBS")
                hist  = stock.quote.history(
                    start=start_dt.strftime("%Y-%m-%d"),
                    end=end_dt.strftime("%Y-%m-%d"),
                    interval="1D",
                )
                if hist is None or len(hist) < 30:
                    continue

                hist.columns = [c.lower() for c in hist.columns]
                close_col = next((c for c in hist.columns if c == "close"), None)
                val_col   = next((c for c in hist.columns if c in ["value","tradingvalue"]), None)
                vol_col   = next((c for c in hist.columns if c == "volume"), None)

                if not close_col:
                    continue

                prices  = hist[close_col].astype(float)
                avg_val = np.nan
                if val_col:
                    avg_val = hist[val_col].astype(float).tail(20).mean() / 1e9
                elif vol_col:
                    avg_val = (prices * hist[vol_col].astype(float)).tail(20).mean() / 1e9

                def pct(n):
                    if len(prices) >= n + 1:
                        return round((prices.iloc[-1] / prices.iloc[-1-n] - 1) * 100, 2)
                    return np.nan

                exc = ""
                if exc_col:
                    row_exc = df_list[df_list[ticker_col].str.upper() == tk]
                    exc = row_exc[exc_col].values[0] if len(row_exc) else ""

                records.append({
                    "Mã":                  tk,
                    "Sàn":                 str(exc).upper() if exc else "HOSE",
                    "Giá":                 round(float(prices.iloc[-1]), 2),
                    "Giá trị GD TB (tỷ)": round(avg_val, 2) if not np.isnan(avg_val) else np.nan,
                    "% 1 tháng":           pct(21),
                    "% 3 tháng":           pct(63),
                    "% 6 tháng":           pct(126),
                    "RSI":                 calc_rsi(prices),
                })
            except Exception:
                continue
            time.sleep(0.05)

        progress.empty()
        return pd.DataFrame(records) if records else None
    except Exception as e:
        st.warning(f"vnstock3 lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH QUA VNSTOCK CŨ
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_v2(max_tickers: int = 300) -> pd.DataFrame | None:
    try:
        companies = _lc()
        ticker_col = next((c for c in companies.columns
                           if c.lower() in ["ticker","symbol","code"]), companies.columns[0])
        exc_col    = next((c for c in companies.columns
                           if "exchange" in c.lower()), None)

        tickers = companies[ticker_col].dropna().str.strip().str.upper().tolist()[:max_tickers]

        end_dt   = datetime.today()
        start_dt = end_dt - timedelta(days=200)

        records  = []
        progress = st.progress(0, text="Đang tải dữ liệu...")
        total    = len(tickers)

        for i, tk in enumerate(tickers):
            if i % 20 == 0:
                progress.progress(i / total, text=f"Xử lý {i}/{total} mã...")
            try:
                hist = _shd(tk,
                            start_dt.strftime("%Y-%m-%d"),
                            end_dt.strftime("%Y-%m-%d"),
                            "1D", type="stock", source="TCBS")
                if hist is None or len(hist) < 30:
                    continue

                hist.columns = [c.lower() for c in hist.columns]
                close_col = next((c for c in hist.columns if c in ["close","price"]), None)
                val_col   = next((c for c in hist.columns if c in ["value","tradingvalue"]), None)
                vol_col   = next((c for c in hist.columns if c == "volume"), None)

                if not close_col:
                    continue

                prices  = hist[close_col].astype(float)
                avg_val = np.nan
                if val_col:
                    avg_val = hist[val_col].astype(float).tail(20).mean() / 1e9
                elif vol_col:
                    avg_val = (prices * hist[vol_col].astype(float)).tail(20).mean() / 1e9

                def pct(n):
                    if len(prices) >= n + 1:
                        return round((prices.iloc[-1] / prices.iloc[-1-n] - 1) * 100, 2)
                    return np.nan

                exc = ""
                if exc_col:
                    row_exc = companies[companies[ticker_col].str.upper() == tk]
                    exc = row_exc[exc_col].values[0] if len(row_exc) else ""

                records.append({
                    "Mã":                  tk,
                    "Sàn":                 str(exc).upper() if exc else "HOSE",
                    "Giá":                 round(float(prices.iloc[-1]), 2),
                    "Giá trị GD TB (tỷ)": round(avg_val, 2) if not np.isnan(avg_val) else np.nan,
                    "% 1 tháng":           pct(21),
                    "% 3 tháng":           pct(63),
                    "% 6 tháng":           pct(126),
                    "RSI":                 calc_rsi(prices),
                })
            except Exception:
                continue
            time.sleep(0.05)

        progress.empty()
        return pd.DataFrame(records) if records else None
    except Exception as e:
        st.warning(f"vnstock v2 lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  CACHE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _is_cache_fresh() -> bool:
    if not os.path.exists(CACHE_FILE):
        return False
    return (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_TTL_SECONDS


def _load_cache() -> pd.DataFrame:
    return pd.read_parquet(CACHE_FILE)


def _save_cache(df: pd.DataFrame):
    try:
        df.to_parquet(CACHE_FILE, index=False)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC: load_market_data
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_market_data():
    # 1. Cache còn mới
    if _is_cache_fresh():
        try:
            df = _load_cache()
            ts = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).strftime("%H:%M %d/%m/%Y")
            return df, f"{ts} (cache)"
        except Exception:
            pass

    # 2. Không có vnstock
    if not VNSTOCK_AVAILABLE:
        st.info(
            "ℹ️ **vnstock chưa được cài.** Đang dùng dữ liệu demo.\n\n"
            "```\npip install vnstock3\n```\nrồi khởi động lại app."
        )
        df = _generate_demo_data()
        _save_cache(df)
        return df, f"{datetime.now().strftime('%H:%M %d/%m/%Y')} (demo)"

    # 3. Fetch live
    df = None
    if VNSTOCK_V3:
        df = _fetch_v3()
    if df is None or df.empty:
        df = _fetch_v2()

    if df is None or df.empty:
        st.warning("⚠️ Không fetch được dữ liệu live. Dùng demo.")
        df = _generate_demo_data()

    _save_cache(df)
    return df, f"{datetime.now().strftime('%H:%M %d/%m/%Y')} (live)"


# ── Summary stats ──────────────────────────────────────────────────────────────
def get_summary_stats(df: pd.DataFrame) -> dict:
    col1m = "% 1 tháng"
    return {
        "total":   len(df),
        "tang":    int((df[col1m] > 0).sum()) if col1m in df.columns else 0,
        "giam":    int((df[col1m] < 0).sum()) if col1m in df.columns else 0,
        "rsi_ob":  int((df["RSI"] > 70).sum()) if "RSI" in df.columns else 0,
        "rsi_os":  int((df["RSI"] < 30).sum()) if "RSI" in df.columns else 0,
        "avg_val": float(df["Giá trị GD TB (tỷ)"].median()) if "Giá trị GD TB (tỷ)" in df.columns else 0,
    }
