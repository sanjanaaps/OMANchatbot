from __future__ import annotations

from typing import Dict

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

try:
    from pdf2image import convert_from_path  # type: ignore
except Exception:  # pragma: no cover
    convert_from_path = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

from ..utils import collect_kv, parse_number, normalize_key


def _ocr_image(img) -> Dict[str, float]:
    if pytesseract is None:
        return {}
    text = pytesseract.image_to_string(img) or ""
    return _kv_from_text(text)


def _kv_from_text(text: str) -> Dict[str, float]:
    results: Dict[str, float] = {"__used_ocr__": 1.0}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            key = normalize_key(parts[0].strip())
            val = ":".join(parts[1:]).strip()
            num = parse_number(val)
            if num is not None and key:
                results[key] = num
        else:
            tokens = line.split()
            if len(tokens) >= 2:
                key = normalize_key(" ".join(tokens[:-1]))
                num = parse_number(tokens[-1])
                if num is not None and key:
                    results[key] = num
    return results


def extract_ocr(path: str) -> Dict[str, float]:
    # Handle PDF via pdf2image; images via PIL
    if path.lower().endswith(".pdf"):
        if convert_from_path is None:
            return {"__used_ocr__": 1.0}
        try:
            images = convert_from_path(path)
        except Exception:
            return {"__used_ocr__": 1.0}
        aggregate: Dict[str, float] = {"__used_ocr__": 1.0}
        for img in images:
            res = _ocr_image(img)
            aggregate.update(res)
        return aggregate
    else:
        if Image is None:
            return {"__used_ocr__": 1.0}
        try:
            img = Image.open(path)
        except Exception:
            return {"__used_ocr__": 1.0}
        return _ocr_image(img)

