from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

from ..utils import collect_kv, maybe_branch_revenue


def _extract_from_dataframe(df: pd.DataFrame) -> Dict[str, float]:
    results: Dict[str, float] = {}
    # Heuristics: try first column as keys and any numeric columns as values
    if df.shape[1] >= 2:
        key_col = df.columns[0]
        for _, row in df.iterrows():
            key_raw = str(row.get(key_col, "")).strip()
            # Look for the first numeric-looking cell in the row
            for col in df.columns[1:]:
                val = row.get(col)
                collect_kv(results, key_raw, val)
                # Special-case branch revenue headers
                br = maybe_branch_revenue(key_raw)
                if br is not None:
                    collect_kv(results, br, val)
                break
    # Also scan header row oriented tables
    for col in df.columns:
        if col is None:
            continue
        col_name = str(col)
        br = maybe_branch_revenue(col_name)
        if br is not None:
            for _, row in df.iterrows():
                val = row.get(col)
                collect_kv(results, br, val)
    return results


def extract_structured(path: str) -> Dict[str, float]:
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        if suffix in {".csv", ".tsv"}:
            sep = "," if suffix == ".csv" else "\t"
            df = pd.read_csv(p, sep=sep, dtype=str)
            return _extract_from_dataframe(df)
        if suffix in {".xlsx", ".xls"}:
            results: Dict[str, float] = {}
            xls = pd.ExcelFile(p)
            for sheet in xls.sheet_names:
                df = xls.parse(sheet_name=sheet, dtype=str)
                sheet_res = _extract_from_dataframe(df)
                results.update(sheet_res)
            return results
        # Fallback: attempt to read as CSV
        df = pd.read_csv(p, dtype=str)
        return _extract_from_dataframe(df)
    except Exception:
        return {}

