from __future__ import annotations

from typing import Dict

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None

from ..utils import collect_kv, maybe_branch_revenue, parse_number, normalize_key


def extract_pdf(path: str) -> Dict[str, float]:
    if pdfplumber is None:
        return {}

    results: Dict[str, float] = {}
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                # Try tables first
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []
                for tbl in tables:
                    for row in tbl:
                        if not row:
                            continue
                        key = str(row[0] if len(row) > 0 else "").strip()
                        # scan numeric cells
                        for cell in row[1:]:
                            collect_kv(results, key, cell)
                            br = maybe_branch_revenue(key)
                            if br is not None:
                                collect_kv(results, br, cell)
                            break

                # Fallback: text lines with key:value or key number
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    parts = line.split(":")
                    if len(parts) >= 2:
                        key = parts[0].strip()
                        val = ":".join(parts[1:]).strip()
                        collect_kv(results, key, val)
                        br = maybe_branch_revenue(key)
                        if br is not None:
                            collect_kv(results, br, val)
                    else:
                        # Try last token numeric
                        tokens = line.split()
                        if len(tokens) >= 2:
                            key = normalize_key(" ".join(tokens[:-1]))
                            num = parse_number(tokens[-1])
                            if num is not None and key:
                                results[key] = num

        return results
    except Exception:
        return {}

