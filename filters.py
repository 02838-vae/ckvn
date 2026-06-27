"""
filters.py
──────────
Áp dụng các bộ lọc lên DataFrame toàn thị trường.
"""

import pandas as pd
import numpy as np

SORT_COL_MAP = {
    "Giá trị GD TB (tỷ)": "Giá trị GD TB (tỷ)",
    "RSI":                 "RSI",
    "% 1 tháng":           "% 1 tháng",
    "% 3 tháng":           "% 3 tháng",
    "% 6 tháng":           "% 6 tháng",
}


def apply_filters(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    params keys:
        exchange    : str  — "Tất cả" | "HOSE" | "HNX" | "UPCOM"
        min_val     : float — tỷ đồng
        max_val     : float
        ret6m       : (min, max) %
        ret3m       : (min, max) %
        ret1m       : (min, max) %
        rsi_range   : (min, max)
        sort_col    : str
        sort_asc    : bool
    """
    result = df.copy()

    # ── Sàn ──────────────────────────────────────────────────────────────
    if params["exchange"] != "Tất cả" and "Sàn" in result.columns:
        result = result[result["Sàn"].str.upper() == params["exchange"].upper()]

    # ── Giá trị GD ───────────────────────────────────────────────────────
    col_val = "Giá trị GD TB (tỷ)"
    if col_val in result.columns:
        result = result[
            (result[col_val].fillna(0) >= params["min_val"]) &
            (result[col_val].fillna(0) <= params["max_val"])
        ]

    # ── % thay đổi ───────────────────────────────────────────────────────
    for col, key in [("% 6 tháng", "ret6m"), ("% 3 tháng", "ret3m"), ("% 1 tháng", "ret1m")]:
        if col in result.columns and key in params:
            lo, hi = params[key]
            result = result[
                (result[col].fillna(-9999) >= lo) &
                (result[col].fillna(9999)  <= hi)
            ]

    # ── RSI ───────────────────────────────────────────────────────────────
    if "RSI" in result.columns:
        rlo, rhi = params["rsi_range"]
        result = result[
            (result["RSI"].fillna(50) >= rlo) &
            (result["RSI"].fillna(50) <= rhi)
        ]

    # ── Sắp xếp ───────────────────────────────────────────────────────────
    sort_col = SORT_COL_MAP.get(params["sort_col"], "Giá trị GD TB (tỷ)")
    if sort_col in result.columns:
        result = result.sort_values(sort_col, ascending=params["sort_asc"], na_position="last")

    return result.reset_index(drop=True)
