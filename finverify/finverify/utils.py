from __future__ import annotations

import re
from typing import Any, Dict


NUM_PATTERN = re.compile(r"[-+]?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?")


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Remove currency symbols and parentheses for negatives
        s = s.replace("$", "").replace("€", "").replace("£", "")
        negative = False
        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1]
        # Keep digits, dots, and commas then normalize
        match = NUM_PATTERN.search(s)
        if not match:
            return None
        num = match.group(0)
        # If both comma and dot exist, assume comma is thousand sep
        if "," in num and "." in num:
            num = num.replace(",", "")
        else:
            # If only comma, treat as thousand sep
            num = num.replace(",", "")
        try:
            val = float(num)
            return -val if negative else val
        except Exception:
            return None
    return None


def normalize_key(name: str) -> str:
    n = name.strip().lower()
    replacements = {
        "total assets": "assets",
        "assets total": "assets",
        "assets": "assets",
        "liabilities": "liabilities",
        "total liabilities": "liabilities",
        "equity": "equity",
        "total equity": "equity",
        "revenue": "revenue",
        "sales": "revenue",
        "turnover": "revenue",
        "gross profit": "gross_profit",
        "cogs": "cost_of_goods_sold",
        "cost of goods sold": "cost_of_goods_sold",
        "department total revenue": "department_total_revenue",
        # branch_* mapping handled elsewhere
    }
    return replacements.get(n, n)


def maybe_branch_revenue(header: str) -> str | None:
    h = header.strip().lower()
    # e.g., "Branch A Revenue" -> branch_a_revenue
    if "revenue" in h and "branch" in h:
        label = re.sub(r"[^a-z0-9]+", "_", h)
        if not label.endswith("_revenue"):
            label = label + "_revenue"
        label = label.replace("branch_", "branch_")
        return label
    return None


def collect_kv(result: Dict[str, float], key: str, value: Any) -> None:
    from .utils import parse_number, normalize_key

    k = normalize_key(key)
    v = parse_number(value)
    if v is not None and k:
        result[k] = v

