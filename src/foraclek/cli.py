"""CLI arguments, local cart preview, and human review before browser entry."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from foraclek.parse import read_cart


def _nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    if any(ord(char) < 32 or 127 <= ord(char) < 160 or 0xE000 <= ord(char) <= 0xF8FF for char in value):
        raise argparse.ArgumentTypeError("must not contain control or keyboard characters")
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review a USD Thorlabs CSV cart and assist Oracle form entry.")
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview", help="validate and show the cart locally; no browser")
    preview.add_argument("csv", type=Path)
    preview.add_argument("--json", action="store_true", help="emit structured JSON; decimals are strings")
    fill = commands.add_parser("fill", help="open Chrome and confirm each line interactively")
    fill.add_argument("csv", type=Path)
    fill.add_argument("--url", required=True, type=_nonblank, help="approved Oracle HTTPS URL")
    fill.add_argument("--supplier", required=True, type=_nonblank)
    fill.add_argument("--supplier-site", required=True, type=_nonblank)
    fill.add_argument("--category", required=True, type=_nonblank)
    fill.add_argument("--uom", required=True, type=_nonblank)
    fill.add_argument("--start-row", type=int, default=2, help="first CSV line to process after manually checking earlier cart entries")
    args = parser.parse_args(argv)
    try:
        items = read_cart(args.csv)
        if args.command == "preview" and args.json:
            print(json.dumps({"currency": "USD", "items": [asdict(item) for item in items]}, default=str, indent=2))
            return 0
        if args.command == "fill":
            if args.start_row < 2:
                raise ValueError("--start-row must be at least 2 (the first data line).")
            items = [item for item in items if item.row >= args.start_row]
            if not items:
                raise ValueError("No items at or after --start-row.")
        for item in items:
            print(f"Row {item.row}: {item.part_number} | {item.description}")
            print(f"  {item.quantity} x ${item.unit_price:.2f} = ${item.line_total:.2f} USD")
        print(f"{len(items)} item(s); total ${sum(item.line_total for item in items):.2f} USD.")
        if args.command == "fill":
            if not sys.stdin.isatty():
                raise ValueError("Fill requires an interactive terminal for human review. Use preview --json for assistants.")
            from selenium.common.exceptions import WebDriverException
            from foraclek.oracle import FillError, OracleSettings, fill_cart, origin

            origin(args.url)
            settings = OracleSettings(args.supplier, args.supplier_site, args.category, args.uom)
            print(f"Supplier: {settings.supplier}; site: {settings.supplier_site}")
            print(f"Category: {settings.category}; UOM: {settings.uom}; currency: USD (confirm in Oracle)")
            if input("Review the cart and settings. Type OPEN to start Chrome, or press Enter to cancel: ").strip() != "OPEN":
                return 0
            try:
                fill_cart(items, args.url, settings)
            except FillError:
                return 1
            except WebDriverException:
                print("Stopped: Chrome/WebDriver failed. Inspect any open cart before retrying; see the tutorial.", file=sys.stderr)
                return 1
        return 0
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: could not read the CSV. Check the path and file permissions.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Stopped by user; check the Oracle cart before restarting.", file=sys.stderr)
        return 130
