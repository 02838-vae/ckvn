"""
filters.py — áp dụng bộ lọc từ snapshot session_state
"""
import pandas as pd
import numpy as np

# Map tên hiển thị → tên cột
GTGD_MAP = {
    "Tất cả":      0,
    "≥ 200 triệu": 0.2,
    "≥ 500 triệu": 0.5,
    "≥ 1 tỷ":      1.0,
    "≥ 10 tỷ":     10.0,
}

PCT_PERIOD_MAP = {
    "1 tuần":  "% 1 tuần",
    "1 tháng": "% 1 tháng",
    "3 tháng": "% 3 tháng",
    "6 tháng": "% 6 tháng",
    "1 năm":   "% 1 năm",
}

PCT_DIR_MAP = {
    "Tất cả":      (None, None),
    "Tăng > 0%":   (0,    None),
    "Tăng > 5%":   (5,    None),
    "Tăng > 10%":  (10,   None),
    "Tăng > 20%":  (20,   None),
    "Giảm < 0%":   (None, 0),
    "Giảm < -5%":  (None, -5),
    "Giảm < -10%": (None, -10),
}

RSI_TF_MAP = {
    "1 ngày":  "RSI 1D",
    "1 tuần":  "RSI 1W",
    "1 tháng": "RSI 1M",
    "3 tháng": "RSI 3M",
    "6 tháng": "RSI 6M",
}

RSI_ZONE_MAP = {
    "Tất cả":          (0,   100),
    "Quá bán ≤ 30":    (0,   30),
    "Trung tính 30–70":(30,  70),
    "Quá mua ≥ 70":    (70,  100),
}


def apply_filters(df: pd.DataFrame, snap: dict) -> pd.DataFrame:
    result = df.copy()

    # ── GTGD ─────────────────────────────────────────────────────────────
    gtgd_label = snap.get("gtgd_val") or "Tất cả"
    min_val    = GTGD_MAP.get(gtgd_label, 0)
    col_val    = "GTGD TB/ngày (tỷ)"
    if min_val > 0 and col_val in result.columns:
        result = result[result[col_val].fillna(0) >= min_val]

    # ── % thay đổi ────────────────────────────────────────────────────────
    pct_period = snap.get("pct_period")
    pct_dir    = snap.get("pct_dir") or "Tất cả"
    if pct_period:
        col_pct = PCT_PERIOD_MAP.get(pct_period)
        lo, hi  = PCT_DIR_MAP.get(pct_dir, (None, None))
        if col_pct and col_pct in result.columns:
            if lo is not None:
                result = result[result[col_pct].fillna(-9999) > lo]
            if hi is not None:
                result = result[result[col_pct].fillna(9999)  < hi]

    # ── RSI ───────────────────────────────────────────────────────────────
    rsi_tf   = snap.get("rsi_period") or "1 ngày"
    rsi_zone = snap.get("rsi_zone")   or "Tất cả"
    col_rsi  = RSI_TF_MAP.get(rsi_tf, "RSI 1D")
    rsi_lo, rsi_hi = RSI_ZONE_MAP.get(rsi_zone, (0, 100))
    if col_rsi in result.columns and rsi_zone != "Tất cả":
        result = result[
            (result[col_rsi].fillna(50) >= rsi_lo) &
            (result[col_rsi].fillna(50) <= rsi_hi)
        ]

    # ── Sắp xếp mặc định: GTGD giảm dần ─────────────────────────────────
    sort_col = col_val if col_val in result.columns else result.columns[0]
    result   = result.sort_values(sort_col, ascending=False, na_position="last")

    return result.reset_index(drop=True)
