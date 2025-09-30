from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


def _within_tolerance(a: float, b: float, tol: float) -> Tuple[bool, float]:
    delta = (a - b) if (a is not None and b is not None) else float("nan")
    scale = max(abs(a), 1.0) if a is not None else 1.0
    return (abs(delta) <= tol * scale), delta


@dataclass
class CheckResult:
    name: str
    expected: float | None
    reported: float | None
    delta: float | None
    passed: bool

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "expected": self.expected,
            "reported": self.reported,
            "delta": self.delta,
            "pass": self.passed,
        }


def compute_checks(values: Dict[str, float], tolerance: float) -> List[Dict]:
    checks: List[CheckResult] = []

    assets = values.get("assets")
    liabilities = values.get("liabilities")
    equity = values.get("equity")
    if assets is not None and liabilities is not None and equity is not None:
        ok, delta = _within_tolerance(assets, liabilities + equity, tolerance)
        checks.append(
            CheckResult(
                name="Assets = Liabilities + Equity",
                expected=liabilities + equity,
                reported=assets,
                delta=delta,
                passed=ok,
            )
        )

    revenue = values.get("revenue")
    cogs = values.get("cost_of_goods_sold")
    gross_profit = values.get("gross_profit")
    if revenue is not None and cogs is not None and gross_profit is not None:
        ok, delta = _within_tolerance(gross_profit, revenue - cogs, tolerance)
        checks.append(
            CheckResult(
                name="Gross Profit = Revenue - COGS",
                expected=revenue - cogs,
                reported=gross_profit,
                delta=delta,
                passed=ok,
            )
        )

    dept_total = values.get("department_total_revenue")
    branch_sum = 0.0
    branch_found = False
    for key, val in values.items():
        if key.startswith("branch_") and key.endswith("_revenue"):
            branch_sum += float(val)
            branch_found = True
    if dept_total is not None and branch_found:
        ok, delta = _within_tolerance(dept_total, branch_sum, tolerance)
        checks.append(
            CheckResult(
                name="Department Total Revenue = Sum(Branch Revenues)",
                expected=branch_sum,
                reported=dept_total,
                delta=delta,
                passed=ok,
            )
        )

    return [c.to_dict() for c in checks]

