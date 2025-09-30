finverify
=========

Verify financial reports and statements across PDF/Excel/CSV automatically using common formulas:
- Assets = Liabilities + Equity
- Gross Profit = Revenue - COGS
- Department Total Revenue = Sum(branch revenues)

Install
-------

```bash
pip install -e .
```

Ensure OCR dependencies if you need scanned PDF/image support:
- tesseract-ocr, poppler-utils

On Debian/Ubuntu:
```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
```

Usage
-----

```bash
finverify verify report.xlsx report.pdf --tolerance 0.01 --format text --show-values
```

JSON output:
```bash
finverify verify report.csv --format json > result.json
```

Recognized keys (case-insensitive):
- assets, liabilities, equity, revenue, sales, gross profit, cogs, cost of goods sold
- department total revenue
- headers like "Branch A Revenue" are mapped to `branch_a_revenue`

Notes
-----
- PDF extraction uses tables first (via pdfplumber) and falls back to text parsing.
- If PDF is scanned or an image, OCR is attempted via Tesseract.
- Tolerance is relative to the expected magnitude (default 0.5%).

