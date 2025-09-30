import argparse
import json
import sys
from pathlib import Path

from .verifier import run_verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify financial reports using formulas (Assets=Liabilities+Equity, "
            "Gross Profit=Revenue-COGS, and Department totals)."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify", help="Verify one or more input files")
    verify.add_argument(
        "inputs",
        nargs="+",
        type=str,
        help="Input paths (PDF, Excel, CSV, or images)",
    )
    verify.add_argument(
        "--tolerance",
        type=float,
        default=0.005,
        help="Relative/absolute tolerance for equality checks (default 0.5%)",
    )
    verify.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format",
    )
    verify.add_argument(
        "--show-values",
        action="store_true",
        help="Include the extracted values dictionary in the output",
    )

    return parser


def _print_text(result: dict, show_values: bool) -> int:
    checks = result.get("checks", [])
    extracted = result.get("extracted_values", {})
    used_ocr = result.get("used_ocr", False)

    print("Verification Results:")
    if used_ocr:
        print("- OCR was used for at least one input (scanned/unstructured PDF).")

    if not checks:
        print("- No checks could be performed (insufficient data detected).")
        if show_values:
            print("- Extracted values:")
            for k, v in sorted(extracted.items()):
                print(f"  {k}: {v}")
        return 2

    exit_code = 0
    for chk in checks:
        status = "PASS" if chk.get("pass") else "FAIL"
        if not chk.get("pass"):
            exit_code = 1
        name = chk.get("name")
        expected = chk.get("expected")
        reported = chk.get("reported")
        delta = chk.get("delta")
        print(f"- {name}: {status}")
        print(f"  expected={expected} reported={reported} delta={delta}")

    if show_values:
        print("\nExtracted values:")
        for k, v in sorted(extracted.items()):
            print(f"- {k}: {v}")

    return exit_code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        inputs = [str(Path(p)) for p in args.inputs]
        result = run_verification(inputs=inputs, tolerance=args.tolerance)

        if args.format == "json":
            payload = result.copy()
            if not args.show_values:
                payload.pop("extracted_values", None)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if all(c.get("pass", False) for c in result.get("checks", [])) else 1
        else:
            return _print_text(result, show_values=args.show_values)

    return 0

