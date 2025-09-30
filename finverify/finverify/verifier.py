from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .formulas import compute_checks
from .extractors.structured import extract_structured
from .extractors.pdf import extract_pdf
from .extractors.ocr import extract_ocr


SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
SUPPORTED_TABLE_EXTS = {".csv", ".tsv", ".xls", ".xlsx"}


def _merge_values(maps: List[Dict[str, float]]) -> Tuple[Dict[str, float], bool]:
    merged: Dict[str, float] = {}
    used_ocr = False
    for m in maps:
        if not m:
            continue
        # OCR flag may be embedded under a special key
        if "__used_ocr__" in m:
            used_ocr = used_ocr or bool(m.pop("__used_ocr__"))
        merged.update(m)
    return merged, used_ocr


def _ext(path: str) -> str:
    return Path(path).suffix.lower()


def run_verification(inputs: List[str], tolerance: float = 0.005) -> Dict:
    extracted_maps: List[Dict[str, float]] = []
    used_ocr_any = False

    for p in inputs:
        ext = _ext(p)
        if ext in SUPPORTED_TABLE_EXTS:
            extracted_maps.append(extract_structured(p))
        elif ext == ".pdf":
            pdf_map = extract_pdf(p)
            if not pdf_map:
                ocr_map = extract_ocr(p)
                extracted_maps.append(ocr_map)
                used_ocr_any = True or used_ocr_any
            else:
                extracted_maps.append(pdf_map)
        elif ext in SUPPORTED_IMAGE_EXTS:
            ocr_map = extract_ocr(p)
            extracted_maps.append(ocr_map)
            used_ocr_any = True or used_ocr_any
        else:
            # Try best-effort structured read via pandas
            extracted_maps.append(extract_structured(p))

    merged_values, used_ocr_flag = _merge_values(extracted_maps)
    used_ocr_any = used_ocr_any or used_ocr_flag
    checks = compute_checks(merged_values, tolerance=tolerance)

    return {
        "extracted_values": merged_values,
        "checks": checks,
        "used_ocr": used_ocr_any,
    }

